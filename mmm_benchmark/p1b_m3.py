"""v1.2 P1B — M3: A/B/C control (mask vs scale) and sampler diagnostics (docs/protocolo_P1B_registrado.md §1–§2)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .evaluation import paired_bootstrap
from .p1a import channel_rows
from .provenance import ROOT
from .reporting import md_table

RUNS = ROOT / "runs"
OUT = ROOT / "reports" / "v1_2" / "p1b_m3"
ARMS = {"A": ("v1_2_p1b_abc_w0", "M3_pymc_marketing@A"), "B": ("v1_2_p1b_abc_w0", "M3_pymc_marketing@B"),
        "C": ("v1_2_p1b_abc_w8", "M3_pymc_marketing@C")}
VARIANTS = {"S0r": ("v1_2_p1b_samp_S0r", "M3_pymc_marketing@C_S0r"), "S1": ("v1_2_p1b_samp_S1", "M3_pymc_marketing@C_S1"),
            "S2": ("v1_2_p1b_samp_S2", "M3_pymc_marketing@C_S2")}
PILOT_S0 = ("v1_2_p1a_pilot", "M3_pymc_marketing@v3m")
SCALED_PRIORS = ("intercept_contribution", "saturation_beta", "gamma_control", "gamma_fourier", "y_sigma")
GATE_MIN = 8
RHAT_SECONDARY = 1.015


def _fits(run: str, model_id: str, label: str) -> pd.DataFrame:
    rows = []
    for wdir in sorted((RUNS / run / "results").iterdir()):
        f = wdir / f"{model_id}.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())
        d = r["diagnostics"] or {}
        geo_corr = d.get("max_abs_corr_log_lam_log_beta")
        bad = {k: round(v, 4) for k, v in (d.get("rhat_max_by_var") or {}).items() if v > 1.01}
        low = {k: round(v) for k, v in (d.get("ess_bulk_min_by_var") or {}).items() if v < 400}
        rows.append({"variante": label, "world_id": wdir.name, "escenario": wdir.name[:2], "estado": r["fit_status"],
                     "converged_strict": d.get("converged_strict"), "rhat_max": d.get("rhat_max"),
                     "ess_bulk_min": d.get("ess_bulk_min"),
                     "ess_tail_min": min((d.get("ess_tail_min_by_var") or {"_": np.nan}).values()),
                     "divergencias": d.get("divergences"), "bfmi_min": d.get("bfmi_min"),
                     "frac_maxdepth": d.get("frac_maxdepth"), "prof_media": d.get("mean_depth"),
                     "paso_medio": float(np.mean(d["step_size_by_chain"])) if d.get("step_size_by_chain") else np.nan,
                     "max|corr(log λ, log β)|": geo_corr, "params_rhat>1.01": bad or "", "params_ess<400": low or "",
                     "tiempo_s": r["runtime_s"], "rss_mb": r["peak_rss_mb"], "escala_Y": d.get("target_scale"),
                     "ventana_verosimilitud": str(d.get("likelihood_window")),
                     "secundario_rhat≤1.015": bool(d.get("rhat_max", 9) <= RHAT_SECONDARY and d.get("ess_bulk_min", 0) >= 400
                                                  and d.get("divergences", 1) == 0)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ §1 A/B/C
def abc_report() -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    fits = pd.concat([_fits(run, mid, arm) for arm, (run, mid) in ARMS.items()], ignore_index=True)
    ch = pd.DataFrame(sum((channel_rows(run, mid, arm) for arm, (run, mid) in ARMS.items()), []))
    ch.to_csv(OUT / "abc_world_channel.csv", index=False)
    h = ch[(ch.window == "historical_in_sample_fit") & (ch.role == "direct")]
    pw = h.groupby(["variant", "world_id"])[["bias_norm", "mae_norm", "cov95", "cov80", "cov50", "width95_norm"]].mean()
    scale = fits.pivot(index="world_id", columns="variante", values="escala_Y")
    valid = fits.pivot(index="world_id", columns="variante", values="converged_strict")
    prior = pd.DataFrame({"s_A": scale.A, "s_B = s_C": scale.B, "s_B/s_A": scale.B / scale.A,
                          "válido A": valid.A, "válido B": valid.B, "válido C": valid.C}).reset_index()
    rows = []
    for name, (x, y) in {"B − A (escala)": ("B", "A"), "C − B (máscara)": ("C", "B"), "C − A (total)": ("C", "A")}.items():
        for subset in ("todos", "ambos válidos"):
            for m in ("bias_norm", "cov95", "width95_norm", "mae_norm"):
                d = pw.loc[x][m] - pw.loc[y][m]
                if subset == "ambos válidos":
                    ok = valid[(valid[x] == True) & (valid[y] == True)].index  # noqa: E712
                    d = d[d.index.isin(ok)]
                mm, lo, hi = paired_bootstrap(d.to_numpy())
                rows.append({"contraste": name, "subconjunto": subset, "métrica": m, "n_mundos": len(d), "media": mm,
                             "IC95 (exploratory)": f"[{lo:.4f}, {hi:.4f}]"})
    con = pd.DataFrame(rows)
    con.to_csv(OUT / "abc_contrasts.csv", index=False)
    by_world = pw.unstack("variant")
    by_world.columns = [f"{a}·{b}" for a, b in by_world.columns]
    text = f"""# P1a.0 — Control A/B/C: enmascaramiento frente a escala de `Y`

Protocolo: `docs/protocolo_P1B_registrado.md` §1. Todos los brazos usan V3, el muestreo S0, la misma semilla y la misma escala de canales. Son resultados `exploratory` (6 mundos).

| Brazo | Verosimilitud | Escala de `Y` |
|---|---|---|
| A (`legacy_w0`) | `[0, n_train)` | `max Y[0:n_train)` |
| B (control) | `[0, n_train)` | `max Y[8:n_train)` |
| C (`corrected_w8`) | `[8, n_train)` | `max Y[8:n_train)` |

## 1. Identificación del contraste (sin MCMC)

1. **Tests deterministas** (`tests/test_p1a_masking.py`):
   - `test_abc_scales`: B y C tienen la misma escala y difieren de A.
   - `test_abc_mask_is_the_only_difference_between_b_and_c`: `logp(B) − logp(C)` = suma de los términos de log-verosimilitud de `y` de B en las semanas 0–7, en puntos aleatorios. Es decir, C − B cambia solo la verosimilitud.
   - `test_b_equals_a_when_max_is_after_warmup`: si el máximo de `Y` cae después de la semana 8, B ≡ A exactamente.
2. **Consecuencia para la Entrega A:** en los 10 mundos piloto, `max Y[0:n) = max Y[8:n)`, de modo que la escala de A y C era idéntica y **la comparación A frente a C de la Entrega A ya aislaba el enmascaramiento**. La escala solo difiere en 6 de los 45 mundos de `v1_1_m3` y en 26 de los 150 de F2.

## 2. Priors en unidades originales

Las priors de `intercept`, `saturation_beta`, `gamma_control`, `gamma_fourier` y `y_sigma` están en unidades escaladas: en unidades de `Y` se multiplican por la escala. Usar `max Y[8:n)` en lugar de `max Y[0:n)` las **estrecha** en el factor `s_B/s_A`.

`adstock_alpha` y `saturation_lam` no dependen de la escala de `Y`. `lam` sí depende de la escala de canales, que es la misma en los tres brazos.

{md_table(prior, ".3f")}
## 3. Ajustes y diagnósticos

{md_table(fits[["variante", "world_id", "converged_strict", "rhat_max", "ess_bulk_min", "divergencias", "bfmi_min", "escala_Y", "ventana_verosimilitud", "tiempo_s"]], ".3f")}
## 4. Contrastes (directos, ventana `[8, n_train)`, media por mundo, bootstrap de mundos; n = 6, `exploratory`)

{md_table(con, ".4f")}
Por mundo:

{md_table(by_world.reset_index(), ".4f")}
"""
    path = ROOT / "reports" / "p1a_mask_vs_scale.md"
    path.write_text(text)
    return str(path)


# ------------------------------------------------------------------ §2 sampler
def sampling_report() -> tuple[str, str | None, bool]:
    OUT.mkdir(parents=True, exist_ok=True)
    fits = pd.concat([_fits(run, mid, v) for v, (run, mid) in VARIANTS.items()], ignore_index=True)
    pilot = _fits(*PILOT_S0, "S0 (piloto Entrega A)")
    fits.to_csv(OUT / "sampling_fits.csv", index=False)
    summ = []
    for v, g in fits.groupby("variante", sort=False):
        by_s = g.groupby("escenario").converged_strict.sum()
        summ.append({"variante": v, "n": len(g), "converged_strict": int(g.converged_strict.sum()),
                     "secundario R-hat≤1,015": int(g["secundario_rhat≤1.015"].sum()),
                     "escenarios con 0/2": ",".join(by_s[by_s == 0].index) or "—",
                     "divergencias_tot": int(g.divergencias.sum()), "bfmi_min": g.bfmi_min.min(),
                     "frac_maxdepth_media": g.frac_maxdepth.mean(), "tiempo_mediano_s": g.tiempo_s.median(),
                     "tiempo_total_min": g.tiempo_s.sum() / 60, "rss_max_mb": g.rss_mb.max()})
    summ = pd.DataFrame(summ)
    ranked = summ.sort_values(["converged_strict", "tiempo_mediano_s"], ascending=[False, True])
    chosen = ranked.iloc[0]
    passed = bool(chosen.converged_strict >= GATE_MIN and chosen["escenarios con 0/2"] == "—")
    noise = pd.DataFrame({"world_id": pilot.world_id, "S0 piloto": pilot.converged_strict.values}).merge(
        fits[fits.variante == "S0r"][["world_id", "converged_strict"]].rename(columns={"converged_strict": "S0r"}), on="world_id")
    cols = ["variante", "world_id", "converged_strict", "rhat_max", "ess_bulk_min", "ess_tail_min", "divergencias", "bfmi_min",
            "frac_maxdepth", "prof_media", "paso_medio", "max|corr(log λ, log β)|", "params_rhat>1.01", "params_ess<400",
            "tiempo_s", "rss_mb"]
    text = f"""# P1a.1 — Diagnóstico y variantes de muestreo de M3 (brazo C, V3)

Protocolo: `docs/protocolo_P1B_registrado.md` §2.

**Mundos de desarrollo:** los 10 del piloto de la Entrega A.
- Ninguno está entre los 10 usados para elegir V3.
- Todos pertenecen a los 45 de `v1_1_m3`, consultados en P0 y en la Entrega A: **no son independientes**.

**Variantes**, sin tocar priors ni parametrización (misma posterior objetivo):
- S0r: referencia re-ejecutada;
- S1: 2000 + 2000;
- S2: matriz de masa de rango bajo de nutpie.

**Selección:** por número de ajustes `converged_strict` y, en caso de empate, por menor tiempo mediano. **No se ha calculado ninguna métrica frente a la verdad** para estas variantes.

## 1. Resumen y selección

{md_table(summ, ".3f")}
**Variante elegida: {chosen.variante}** ({int(chosen.converged_strict)}/10 `converged_strict`). Puerta registrada (≥ {GATE_MIN}/10 y ningún escenario con 0/2): **{"PASA" if passed else "NO PASA"}**.

La sensibilidad con R-hat ≤ 1,015 es secundaria y no cambia la regla.

## 2. Ruido del muestreador: la misma configuración dos veces

S0 del piloto de la Entrega A frente a su re-ejecución S0r (misma semilla):

{md_table(noise, ".3f")}
## 3. Diagnósticos por mundo y variante

{md_table(fits[cols], ".3f")}
"""
    if not passed:
        text += """
## 4. Decisión

La puerta no se supera: M3 queda **no concluyente en convergencia** con V3 y estas variantes de muestreo. No se hace la evaluación confirmatoria (`reports/p1a_m3_confirmatory.md` no se genera). Los experimentos rápidos continúan.
"""
    path = ROOT / "reports" / "p1a_m3_sampling_diagnostics.md"
    path.write_text(text)
    return str(path), str(chosen.variante), passed
