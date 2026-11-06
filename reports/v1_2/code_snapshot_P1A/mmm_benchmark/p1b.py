"""v1.2 P1b — E10A confounding pilot (docs/protocolo_P1_registrado.md, Anexo A).

Primary metric: bias of the ``do_zero`` intervention effect on direct channels, err_norm = (Δ_est − Δ_true)/Σ|Y|
over [8, n_train), averaged per world; paired contrast high level − level 0 per model, world bootstrap."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluation import V1_METRICS, V1_TASKS, paired_bootstrap
from .provenance import ROOT
from .reporting import md_table
from .tables_io import read_table

RUNS = ROOT / "runs"
OUT = ROOT / "reports" / "v1_2" / "p1b"
MECH = {"dc": ("v1_2_p1b_e10a_dc", "dc_coeff_range"), "dy": ("v1_2_p1b_e10a_dy", "dy_coeff_range"),
        "rho": ("v1_2_p1b_e10a_rho", "confounding_strength_range")}
PRIMARY = "do_zero"
POWERED = ("M2p_true_transforms", "M2p_true_transforms_plus_D")


def _split(world_id: str) -> tuple[str, str]:
    base, var = world_id.split("__")
    return base, var


def primary(mech: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    run, _ = MECH[mech]
    e = read_table(RUNS / run / "tables" / "e08.csv")
    e = e[(e.intervention == PRIMARY) & (e.role == "direct") & (e.model_id != "truth_do_engine")]
    e[["pair", "level"]] = e.world_id.apply(lambda w: pd.Series(_split(w)))
    pw = e.groupby(["model_id", "level", "pair"]).err_norm.mean().reset_index()
    levels = sorted(pw.level.unique())
    rows = []
    for mid, g in pw.groupby("model_id"):
        piv = g.pivot(index="pair", columns="level", values="err_norm")
        for lv in levels:
            m, lo, hi = paired_bootstrap(piv[lv].dropna().to_numpy())
            rows.append({"mecanismo": mech, "modelo": mid, "nivel": lv, "contraste": "nivel", "n_pares": int(piv[lv].notna().sum()),
                         "sesgo_do_zero": m, "IC95_lo": lo, "IC95_hi": hi})
        for lv in levels[1:]:
            d = (piv[lv] - piv[levels[0]]).dropna()
            m, lo, hi = paired_bootstrap(d.to_numpy())
            rows.append({"mecanismo": mech, "modelo": mid, "nivel": f"{lv} − {levels[0]}", "contraste": "pareado",
                         "n_pares": len(d), "sesgo_do_zero": m, "IC95_lo": lo, "IC95_hi": hi})
    return pd.DataFrame(rows), pw


def secondary(mech: str) -> pd.DataFrame:
    run, _ = MECH[mech]
    m = read_table(RUNS / run / "tables" / "metrics.csv")
    m["task"], m["metric"] = m["task"].replace(V1_TASKS), m["metric"].replace(V1_METRICS)
    m[["pair", "level"]] = m.world_id.apply(lambda w: pd.Series(_split(w)))
    rows = []
    for metric, task, role in (("channel_total_bias_norm", "historical_in_sample_fit", "direct"),
                               ("contrib_mae_norm", "historical_in_sample_fit", None),
                               ("rmse_scaled", "prediction_future_conditional_on_known_CZ", None)):
        s = m[(m.metric == metric) & (m.task == task)]
        if role:
            s = s[s.role == role]
        pw = s.groupby(["model_id", "level", "pair"]).value.mean().reset_index()
        for (mid, lv), g in pw.groupby(["model_id", "level"]):
            mm, lo, hi = paired_bootstrap(g.value.to_numpy())
            rows.append({"mecanismo": mech, "métrica": metric + (f"·{role}" if role else ""), "modelo": mid, "nivel": lv,
                         "n": len(g), "media": mm, "IC95": f"[{lo:.4f}, {hi:.4f}]"})
    return pd.DataFrame(rows)


def descriptors(mech: str) -> pd.DataFrame:
    run, _ = MECH[mech]
    w = read_table(RUNS / run / "tables" / "worlds.csv")
    w["level"] = w.world_id.str.split("__").str[1]
    cols = ["mean_abs_channel_corr", "condition_number", "media_share_of_y", "noise_to_y_sd", "confounding_strength"]
    d = w.groupby("level")[[c for c in cols if c in w]].mean().reset_index()
    d.insert(0, "mecanismo", mech)
    return d


def latent_correlation(mech: str) -> pd.DataFrame:
    """Achieved correlation between each channel and the unobserved D / baseline (privileged, descriptive)."""
    from .config import RunConfig
    from .generator_adapter import WorldStore
    from .runner import WORLD_CACHE

    cfg = RunConfig.load(ROOT / "configs" / f"{MECH[mech][0]}.yaml")
    store = WorldStore(WORLD_CACHE)
    rows = []
    for spec in cfg.worlds():
        world = store.get(spec)
        C = np.asarray(world.data["treatments"], dtype=float)
        base = np.asarray(world.data["baseline"], dtype=float)
        lat = np.asarray(world.data.get("latent_unobserved_contribution", np.zeros_like(base)), dtype=float)
        lat = lat.sum(-1) if lat.ndim > 1 else lat
        def corr(x, y):
            return float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 0 and np.std(y) > 0 else np.nan
        rows.append({"mecanismo": mech, "level": spec.variant,
                     "corr_C_baseline_media_abs": np.nanmean([abs(corr(C[:, k], base)) for k in range(C.shape[1])]),
                     "corr_C_latentD_media_abs": np.nanmean([abs(corr(C[:, k], lat)) for k in range(C.shape[1])])})
    return pd.DataFrame(rows).groupby(["mecanismo", "level"]).mean().reset_index()


def write_report() -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    prim, sec, desc, lat, costs = [], [], [], [], []
    for mech, (run, _) in MECH.items():
        p, _ = primary(mech)
        prim.append(p)
        sec.append(secondary(mech))
        desc.append(descriptors(mech))
        lat.append(latent_correlation(mech))
        s = read_table(RUNS / run / "tables" / "status.csv")
        ev = read_table(RUNS / run / "tables" / "engine_validation.csv")
        costs.append({"run": run, "mundos": s.world_id.nunique(), "ajustes": len(s), "fallos": int((s.fit_status != "ok").sum()),
                      "motor_validado": int((ev.status == "validated").sum()) if "status" in ev else np.nan,
                      "tiempo_ajustes_min": s.runtime_s.sum() / 60})
    prim, sec = pd.concat(prim, ignore_index=True), pd.concat(sec, ignore_index=True)
    desc, lat = pd.concat(desc, ignore_index=True), pd.concat(lat, ignore_index=True)
    for name, df in (("primary_do_zero_bias", prim), ("secondary", sec), ("descriptors", desc), ("latent_corr", lat)):
        df.to_csv(OUT / f"{name}.csv", index=False)
    paired = prim[prim.contraste == "pareado"]
    text = f"""# P1b — E10A: confusión (piloto pareado)

Diseño registrado antes de generar: `docs/protocolo_P1_registrado.md`, Anexo A. T = 104, 40 réplicas por nivel. Niveles pareados con la misma semilla de mundo: idénticos DAG e innovaciones exógenas; solo cambia el parámetro del mecanismo (test `test_e10a_mechanisms_are_paired`).

- Ventana de ajuste `[8, n_train)`.
- Verdad: el contrafactual `do` de **cada mundo** (`research_validated_private_api`).
- Sin M3.
- M2p y M2p_D son **privilegiados** (transformaciones verdaderas; M2p_D además observa D). Se presentan separados de los modelos ciegos.

## 1. Coste y validez del motor

{md_table(pd.DataFrame(costs), ".1f")}
## 2. ¿Qué cambia realmente con cada nivel? (descriptivo)

Correlación lograda entre canales y entre cada canal y la base o la contribución latente de D. Es información privilegiada, solo descriptiva. Correlación observada ≠ confusión causal ≠ falta de identificación.

{md_table(lat, ".3f")}
{md_table(desc, ".3f")}
## 3. Métrica primaria: sesgo del efecto `do_zero` en canales directos

`err_norm = (Δ_est − Δ_true)/Σ|Y|`, promedio por mundo sobre directos. Contraste pareado = nivel alto − nivel 0 del mismo par. IC95 por bootstrap de pares.

**Potencia:** solo se declara para los privilegiados M2p y M2p_D. Para los ciegos (M0, M1, M2, M2_noZ, M5/M6 si tienen efecto implicado), los intervalos se informan sin pretensión de potencia.

{md_table(paired, ".4f")}
Por nivel:

{md_table(prim[prim.contraste == "nivel"], ".4f")}
## 4. Métricas secundarias

Sesgo de contribución directa, MAE de contribución y RMSE de predicción futura.

{md_table(sec[sec.modelo.isin(["M0_ols", "M1_ridge", "M2_adstock_sat", "M2_adstock_sat_noZ", *POWERED])], ".4f")}
## 5. Límites

- Es un piloto: 40 pares por nivel y una sola T.
- El efecto de `rho` cambia los tratamientos realizados; los contrastes de `rho` comparan mundos con distinta verdad, cada uno evaluado frente a la suya.
- M2p_D usa D, que un analista no observa: es una cota de referencia, no un método aplicable.
- Atribución histórica (§4) y efecto de intervención (§3) son estimandos distintos.

Datos: `reports/v1_2/p1b/`.
"""
    path = ROOT / "reports" / "p1b_e10a_confounding.md"
    path.write_text(text)
    return str(path)
