"""v1.2 P1 — corrected fast-model baselines (fit window [8, n_train)) vs historical (week 0).

Same configs, seeds and worlds; only ``fit_scope`` changes. Writes reports/p1_corrected_baselines.md and
tables under reports/v1_2/p1_corr/. Historical runs are read, never modified."""

from __future__ import annotations

import pandas as pd

from .evaluation import V1_METRICS, V1_TASKS, paired_bootstrap
from .provenance import ROOT
from .reporting import md_table
from .tables_io import read_table

RUNS = ROOT / "runs"
OUT = ROOT / "reports" / "v1_2" / "p1_corr"
PAIRS = {  # label -> (historical run, corrected run)
    "F3 (600 mundos)": ("extended", "v1_2_corr_f3"),
    "E10A_D (30)": ("v1_1_e10a_D", "v1_2_corr_e10a_D"),
    "E10A_rho (30)": ("v1_1_e10a_rho", "v1_2_corr_e10a_rho"),
    "E08/E09 (45)": ("v1_1_e09", "v1_2_corr_e0809"),
}
H = "historical_in_sample_fit"
P = "prediction_future_conditional_on_known_CZ"


def _metrics(run: str) -> pd.DataFrame:
    m = read_table(RUNS / run / "tables" / "metrics.csv")
    m["task"] = m["task"].replace(V1_TASKS)
    m["metric"] = m["metric"].replace(V1_METRICS)
    return m


def _per_world(m: pd.DataFrame, task: str, metric: str, role: str | None = None) -> pd.DataFrame:
    sel = m[(m.task == task) & (m.metric == metric)]
    if role is not None:
        sel = sel[sel.role == role]
    return sel.groupby(["world_id", "model_id"]).value.mean().unstack()


def compare_metrics(label: str, old: str, new: str) -> pd.DataFrame:
    mo, mn = _metrics(old), _metrics(new)
    rows = []
    for metric, task, role in (("contrib_mae_norm", H, None), ("channel_total_bias_norm", H, "direct"),
                               ("rmse_scaled", P, None)):
        a, b = _per_world(mo, task, metric, role), _per_world(mn, task, metric, role)
        for mid in sorted(set(a.columns) & set(b.columns)):
            both = pd.concat([a[mid], b[mid]], axis=1, keys=["old", "new"]).dropna()
            if both.empty:
                continue
            m, lo, hi = paired_bootstrap((both.new - both.old).to_numpy())
            rows.append({"conjunto": label, "métrica": f"{metric}{'·' + role if role else ''}", "modelo": mid,
                         "n_mundos": len(both), "histórico_w0": both.old.mean(), "corregido_w8": both.new.mean(),
                         "dif": m, "IC95": f"[{lo:.4f}, {hi:.4f}]"})
    return pd.DataFrame(rows)


def compare_e08(label: str, old: str, new: str) -> pd.DataFrame:
    eo, en = read_table(RUNS / old / "tables" / "e08.csv"), read_table(RUNS / new / "tables" / "e08.csv")
    key = ["world_id", "channel", "intervention", "model_id"]
    rows = []
    for e, tag in ((eo, "old"), (en, "new")):
        e["abs_err"] = e.err_norm.abs()
    j = eo[eo.model_id != "truth_do_engine"].merge(en, on=key, suffixes=("_old", "_new"))
    for (mid, inter), g in j.groupby(["model_id", "intervention"]):
        if inter == "do_null":
            continue
        pw = g.groupby("world_id")[["abs_err_old", "abs_err_new", "err_norm_old", "err_norm_new"]].mean()
        m, lo, hi = paired_bootstrap((pw.abs_err_new - pw.abs_err_old).to_numpy())
        rows.append({"conjunto": label, "modelo": mid, "intervención": inter, "n_mundos": len(pw),
                     "|err|_hist": pw.abs_err_old.mean(), "|err|_corr": pw.abs_err_new.mean(),
                     "sesgo_hist": pw.err_norm_old.mean(), "sesgo_corr": pw.err_norm_new.mean(),
                     "dif |err|": m, "IC95": f"[{lo:.4f}, {hi:.4f}]"})
    # sanity: truth must be identical (same worlds, same engine, same window)
    t = eo[eo.model_id == "truth_do_engine"].merge(en[en.model_id == "truth_do_engine"], on=key)
    truth_same = bool((t.delta_true_x - t.delta_true_y).abs().max() < 1e-9) if len(t) else None
    out = pd.DataFrame(rows)
    out.attrs["truth_identical"] = truth_same
    return out


def compare_e09(old: str, new: str) -> pd.DataFrame:
    eo, en = read_table(RUNS / old / "tables" / "e09.csv"), read_table(RUNS / new / "tables" / "e09.csv")
    rows = []
    for fam in sorted(set(en.policy_family.dropna())):
        for pol in sorted(set(en[en.policy_family == fam].policy)):
            a = eo[(eo.policy_family == fam) & (eo.policy == pol)].groupby("world_id")[["regret_norm", "budget_violation"]].mean()
            b = en[(en.policy_family == fam) & (en.policy == pol)].groupby("world_id")[["regret_norm", "budget_violation"]].mean()
            both = a.join(b, lsuffix="_old", rsuffix="_new", how="inner")
            if both.empty:
                continue
            m, lo, hi = paired_bootstrap((both.regret_norm_new - both.regret_norm_old).to_numpy())
            rows.append({"familia": fam, "política": pol, "n_mundos": len(both), "regret_hist": both.regret_norm_old.mean(),
                         "regret_corr": both.regret_norm_new.mean(), "dif": m, "IC95": f"[{lo:.4f}, {hi:.4f}]",
                         "viol_presup_max_corr": both.budget_violation_new.max()})
    return pd.DataFrame(rows)


def cost(run: str) -> dict:
    s = read_table(RUNS / run / "tables" / "status.csv")
    return {"run": run, "n_mundos": s.world_id.nunique(), "n_ajustes": len(s), "fallos": int((s.fit_status != "ok").sum()),
            "tiempo_total_min": s.runtime_s.sum() / 60, "rss_pico_max_mb": s.peak_rss_mb.max()}


def write_report() -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    met = pd.concat([compare_metrics(k, *v) for k, v in PAIRS.items()], ignore_index=True)
    met.to_csv(OUT / "metrics_hist_vs_corr.csv", index=False)
    e08 = [compare_e08(k, *v) for k, v in PAIRS.items() if k != "F3 (600 mundos)"]
    truth_same = {k: d.attrs["truth_identical"] for k, d in zip([k for k in PAIRS if k != "F3 (600 mundos)"], e08)}
    e08 = pd.concat(e08, ignore_index=True)
    e08.to_csv(OUT / "e08_hist_vs_corr.csv", index=False)
    e09 = compare_e09(*PAIRS["E08/E09 (45)"])
    e09.to_csv(OUT / "e09_hist_vs_corr.csv", index=False)
    costs = pd.DataFrame([cost(v[1]) for v in PAIRS.values()])
    key_models = ["M0_ols", "M1_ridge", "M2_adstock_sat", "M2_adstock_sat_noZ", "M2p_true_transforms", "M2p_true_transforms_plus_D"]
    e08_main = e08[e08.modelo.isin(key_models) & e08.intervención.isin(["do_zero", "do_reduce_10", "do_increase_10"])]
    text = f"""# P1 — Líneas base corregidas de modelos rápidos (ventana de ajuste `[8, n_train)`)

Protocolo: `docs/protocolo_P1_registrado.md` §5. Mismas configuraciones, semillas, mundos y modelos que los runs históricos; solo cambia `fit_scope: train_after_warmup`. Las semanas 0–7 aportan únicamente historia de tratamiento. **Sin generación nueva.**

- «histórico_w0»: resultado antiguo, ajustado desde la semana 0 y contaminado por el defecto de inicialización. Se conserva como referencia.
- «corregido_w8»: resultado nuevo.

Las políticas y efectos de M3 **no** se incluyen: esperan al nuevo ajuste M3 (Entrega B).

Unidades:
- Errores de contribución y sesgos: normalizados por media|Y| de la ventana.
- Valor E09: en unidades de `Y` normalizado por Σ|Y|. **No es ROAS.**
- Intervalos: bootstrap de mundos.

## 1. Coste (separado de los experimentos nuevos)

{md_table(costs, ".1f")}
## 2. Atribución y predicción: histórico frente a corregido

Directos para el sesgo; todos los canales para el MAE de contribución; predicción en la ventana futura.

{md_table(met[met.modelo.isin(key_models)], ".4f")}
Tabla completa (incluye N0/N1, XGBoost y LightGBM): `reports/v1_2/p1_corr/metrics_hist_vs_corr.csv`.

## 3. E08 — efecto total de intervención (`do`) implicado por cada modelo

`err_norm` = (efecto estimado − efecto verdadero) / Σ|Y|, sobre `[8, n_train)`. La verdad de cada mundo es su propio contrafactual con el motor `do` (`research_validated_private_api`). Verdad idéntica entre runs: {truth_same}. Antes de esta comparación se corrigió un defecto: con la ventana tardía, la ventana E08/E09 se habría acortado 8 semanas (`causal.horizon`).

{md_table(e08_main, ".4f")}
Tabla completa: `reports/v1_2/p1_corr/e08_hist_vs_corr.csv`.

## 4. E09 — valor de decisión (45 mundos)

- `all_channels_clamped_policy` es una **intervención sintética definida por el protocolo**.
- `selected_channels_do_policy` sigue siendo exploratoria.
- La referencia `oracle_interventional` es la **estabilidad del mejor valor encontrado**, no un óptimo global certificado.

{md_table(e09, ".4f")}
## 5. Lectura

- Atribución histórica, efecto total de intervención y valor de decisión son magnitudes distintas. Una mejora en una no implica mejora en las otras.
- La corrección afecta sobre todo a los modelos con arrastre o transformaciones (M2, M2p). M0/M1 sin arrastre cambian poco porque sus filas 0–7 no tienen un estado de arrastre que reconstruir.
- Estas cifras sustituyen a las de v1/v1.1 para M0–M2p, M5 y M6 cuando se citen junto a M3 enmascarado. Las antiguas permanecen congeladas.
"""
    path = ROOT / "reports" / "p1_corrected_baselines.md"
    path.write_text(text)
    return str(path)
