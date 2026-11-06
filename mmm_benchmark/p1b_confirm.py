"""v1.2 P1B — M3 confirmatory evaluation on reserved worlds (docs/protocolo_P1B_registrado.md §3).

Runs only if the sampler gate passed. Unit of inference: the world (metrics averaged over its channels first)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluation import paired_bootstrap
from .p1a import channel_rows
from .provenance import ROOT
from .reporting import md_table
from .revision import cluster_bootstrap

OUT = ROOT / "reports" / "v1_2" / "p1b_confirm"
MIN_PAIRS = 20
ROPE_PROB = 0.95


def rope_revised(row) -> str:
    """P1B rule: relevant if P(c > δ) ≥ .95; not relevant if P(c ≤ δ) ≥ .95; else indeterminate."""
    if row.p_gt >= ROPE_PROB:
        return "relevante"
    if 1 - row.p_gt >= ROPE_PROB:
        return "no_relevante"
    return "indeterminado"


def table(arms: dict[str, tuple[str, str]]) -> pd.DataFrame:
    from .audit_v1_2 import spec_from_world_id
    from .generator_adapter import WorldStore, structure_cell_id
    from .runner import WORLD_CACHE

    df = pd.DataFrame(sum((channel_rows(run, mid, lab) for lab, (run, mid) in arms.items()), []))
    store = WorldStore(WORLD_CACHE)
    cells = {w: structure_cell_id(store.get(spec_from_world_id(w)).g) for w in df.world_id.unique()}
    df["structure_cell_id"] = df.world_id.map(cells)
    # revised ROPE: P(c > δ) from the saved per-draw estimand
    p_gt = []
    for r in df.itertuples():
        if r.window != "historical_in_sample_fit" or r.fit_status != "ok":
            p_gt.append(np.nan)
            continue
        run, mid = arms[r.variant]
        post = np.load(ROOT / "runs" / run / "results" / r.world_id / f"{mid}.posterior.npz")
        p_gt.append(float(np.mean(post["contrib_mean_w8_train"][:, r.channel] > r.rope_delta)))
    df["p_gt"] = p_gt
    df["rope_revised"] = [rope_revised(r) if np.isfinite(r.p_gt) else None for r in df.itertuples()]
    return df


def _ratio_boot(g: pd.DataFrame, num, den, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float, int, int]:
    """Pooled ratio Σnum/Σden with a world-bootstrap CI."""
    per = g.groupby("world_id").apply(lambda x: pd.Series({"n": num(x).sum(), "d": den(x).sum()}), include_groups=False)
    per = per[per.d > 0]
    if per.empty:
        return np.nan, np.nan, np.nan, 0, 0
    est = per.n.sum() / per.d.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(per), (n_boot, len(per)))
    b = per.n.to_numpy()[idx].sum(1) / np.maximum(per.d.to_numpy()[idx].sum(1), 1e-12)
    return float(est), float(np.quantile(b, .025)), float(np.quantile(b, .975)), int(per.d.sum()), len(per)


def write_report(arms: dict[str, tuple[str, str]], variant: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    df = table(arms)
    df.to_csv(OUT / "confirm_world_channel.csv", index=False)
    ok = df[df.fit_status == "ok"]
    h = ok[ok.window == "historical_in_sample_fit"]
    valid = h.drop_duplicates(["variant", "world_id"]).pivot(index="world_id", columns="variant", values="valid_strict")
    both = valid[(valid.legacy_w0 == True) & (valid.corrected_w8 == True)].index  # noqa: E712
    n_pairs = len(both)
    rows = []
    for subset, worlds in (("pares converged_strict (principal)", both), ("todos los ajustes (descriptivo)", valid.index)):
        for role in ("direct", "feeder", "isolated"):
            g = h[h.world_id.isin(worlds) & (h.role == role)]
            if g.empty:
                continue
            pw = g.groupby(["variant", "world_id"])[["bias_norm", "mae_norm", "cov50", "cov80", "cov95", "width95_norm"]].mean()
            cells = g.drop_duplicates("world_id").set_index("world_id").structure_cell_id
            for m in ("bias_norm", "mae_norm", "cov50", "cov80", "cov95", "width95_norm"):
                a, c = pw.loc["legacy_w0"][m], pw.loc["corrected_w8"][m]
                d = (c - a).dropna()
                mm, lo, hi = paired_bootstrap(d.to_numpy())
                _, loc, hic, nc = cluster_bootstrap(d, cells.reindex(d.index))
                rows.append({"subconjunto": subset, "rol": role, "métrica": m, "n_mundos": len(d), "legacy_w0": a.mean(),
                             "corrected_w8": c.mean(), "dif": mm, "IC95 mundos": f"[{lo:.4f}, {hi:.4f}]",
                             "IC95 células": f"[{loc:.4f}, {hic:.4f}]" if np.isfinite(loc) else f"— ({nc})"})
    comp = pd.DataFrame(rows)
    comp.to_csv(OUT / "confirm_paired.csv", index=False)
    strat = (h[h.world_id.isin(both) & (h.role == "direct")]
             .groupby(["variant", "scenario_id", "T"])[["bias_norm", "cov95"]].mean().unstack("variant").reset_index())
    strat.columns = [" ".join(map(str, c)).strip() for c in strat.columns]
    rope = []
    for lab in ("legacy_w0", "corrected_w8"):
        for subset, worlds in (("pares válidos", both), ("todos", valid.index)):
            g = h[(h.variant == lab) & h.world_id.isin(worlds)]
            for role in ("direct", "feeder", "isolated"):
                gr = g[g.role == role]
                if gr.empty:
                    continue
                rel = gr.truth_relevant.astype(str).str.lower().eq("true")
                gr = gr.assign(_rel=rel)
                sens = _ratio_boot(gr, lambda x: (x.rope_revised == "relevante") & x._rel, lambda x: x._rel)
                fp = _ratio_boot(gr, lambda x: (x.rope_revised == "relevante") & ~x._rel, lambda x: ~x._rel)
                prec = _ratio_boot(gr, lambda x: (x.rope_revised == "relevante") & x._rel, lambda x: x.rope_revised == "relevante")
                absn = _ratio_boot(gr, lambda x: x.rope_revised == "indeterminado", lambda x: pd.Series(True, index=x.index))
                nr_ok = _ratio_boot(gr, lambda x: (x.rope_revised == "no_relevante") & ~x._rel, lambda x: ~x._rel)
                rope.append({"brazo": lab, "subconjunto": subset, "rol": role, "n_canales": len(gr), "n_mundos": gr.world_id.nunique(),
                             "sensibilidad": sens[0], "IC_sens": f"[{sens[1]:.2f}, {sens[2]:.2f}] (den {sens[3]})",
                             "falsos_pos": fp[0], "IC_fp": f"[{fp[1]:.2f}, {fp[2]:.2f}] (den {fp[3]})",
                             "precisión": prec[0], "no_relevante_correcto": nr_ok[0], "IC_nr": f"(den {nr_ok[3]})",
                             "abstención": absn[0]})
    rope = pd.DataFrame(rope)
    rope.to_csv(OUT / "confirm_rope.csv", index=False)
    conclusive = n_pairs >= MIN_PAIRS
    text = f"""# P1a.2 — Evaluación confirmatoria de M3: `legacy_w0` frente a `corrected_w8`

Protocolo: `docs/protocolo_P1B_registrado.md` §3. Variante de muestreo congelada: **{variant}**.

**Mundos reservados:** F2 réplicas 3–5, 45 mundos, nunca usados en decisiones sobre M3.
- Unidad de inferencia: el mundo.
- IC95 por bootstrap de mundos y, como sensibilidad, de células DAG.

## 1. Pares válidos

`converged_strict` en ambos brazos: **{n_pairs}** mundos. Umbral confirmatorio: ≥ {MIN_PAIRS}. Conclusión: **{"confirmatoria" if conclusive else "NO CONCLUYENTE"}**.

Validez por brazo: `legacy_w0` {int(valid.legacy_w0.sum())}/{len(valid)}; `corrected_w8` {int(valid.corrected_w8.sum())}/{len(valid)}.

## 2. Comparación pareada por rol (ventana `[8, n_train)`, `historical_observed_path`)

{md_table(comp, ".4f")}
## 3. Directos por escenario y T (pares válidos)

{md_table(strat, ".4f")}
## 4. ROPE (regla revisada)

- **Estimando:** contribución directa media semanal en `[8, n_train)`, en unidades de `Y`.
- **Umbral:** `δ = 0,005·media|Y[8:n_train)|`, igual en ambos brazos.
- **Decisión:** «relevante» si `P(c > δ) ≥ 0,95`; «no relevante» si `P(c ≤ δ) ≥ 0,95`; en otro caso, «indeterminado».
- Razones agregadas con IC por bootstrap de mundos; `den` = número de canales en el denominador.
- La verdad «relevante» es `c_true > δ`. En feeders, la contribución directa verdadera es 0.

{md_table(rope, ".3f")}
"""
    path = ROOT / "reports" / "p1a_m3_confirmatory.md"
    path.write_text(text)
    return str(path)
