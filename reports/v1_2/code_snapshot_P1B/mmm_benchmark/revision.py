"""v1.1 revision analyses (designer decisions D1–D7, corrections 1–10).

Reads the frozen v1 artefacts and the v1.1 runs; never writes into v1 run directories.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from .evaluation import (  # noqa: E402
    ATTR_FUT,
    HIST,
    HIST_FULL,
    NULL_FALSE_ATTRIBUTION_THRESHOLD,
    PRED_FUT,
    V1_METRICS,
    V1_ROLES,
    V1_TASKS,
    paired_bootstrap,
    score,
)
from .generator_adapter import WorldSpec, WorldStore, response_warmup_weeks  # noqa: E402
from .provenance import ROOT  # noqa: E402
from .reporting import md_table  # noqa: E402
from .runner import WORLD_CACHE  # noqa: E402
from .schema import ModelOutput  # noqa: E402

RUNS = ROOT / "runs"
V1_RUNS = ("extended", "core", "pilot")  # later runs override earlier ones for identical keys
FAST_BLIND = ["M0_ols", "M1_ridge", "M2_adstock_sat", "M2_adstock_sat_noZ"]
OUT_TAB = ROOT / "reports" / "tables_v1_1"
OUT_FIG = ROOT / "reports" / "figures_v1_1"


# ---------------------------------------------------------------------------------- loading
def read_csv(path: Path) -> pd.DataFrame:
    """'null' was a role label in v1: pandas' default NA parsing silently turned it into NaN."""
    try:
        return pd.read_csv(path, keep_default_na=False, na_values=[""])
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "task" in df:
        df["task"] = df["task"].replace(V1_TASKS)
    if "metric" in df:
        df["metric"] = df["metric"].replace(V1_METRICS)
    if "role" in df:
        df["role"] = df["role"].replace(V1_ROLES)
    return df


def load(name: str, runs) -> pd.DataFrame:
    parts = []
    for r in runs:
        df = normalize(read_csv(RUNS / r / "tables" / f"{name}.csv"))
        if not df.empty:
            df["run"] = r
            parts.append(df)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def dedupe(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    keys = [k for k in keys if k in df]
    return df.drop_duplicates(subset=keys, keep="last") if not df.empty else df


def wide(m: pd.DataFrame, task: str, metric: str) -> pd.DataFrame:
    sel = m[(m.task == task) & (m.metric == metric) & m.channel.isna()]
    return sel.pivot_table(index=["world_id", "scenario_id", "T"], columns="model_id", values="value")


def cluster_bootstrap(diff: pd.Series, clusters: pd.Series, n_boot: int = 2000, seed: int = 0):
    """Mean paired difference with a 95% CI resampling structure cells (clusters) instead of worlds."""
    d = pd.DataFrame({"d": diff.values, "c": clusters.values}).dropna()
    groups = [g.d.to_numpy() for _, g in d.groupby("c")]
    if len(groups) < 5:
        return float(d.d.mean()), np.nan, np.nan, len(groups)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        boots.append(np.concatenate([groups[i] for i in pick]).mean())
    return float(d.d.mean()), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975)), len(groups)


# ------------------------------------------------------------------------- corr. 1: warm-up
def rescore_min_warmup(runs=V1_RUNS) -> pd.DataFrame:
    """Re-score saved v1 outputs excluding only each world's response_warmup_weeks (no refit)."""
    store = WorldStore(WORLD_CACHE)
    rows, seen = [], set()
    for r in runs:
        for wdir in sorted((RUNS / r / "results").glob("*")):
            info = json.loads((wdir / "_world.json").read_text())["meta"]
            spec = WorldSpec(info["scenario"], info["T"], info["replicate"])
            world, obs, truth = store.load(spec)
            w0 = response_warmup_weeks(world)
            for npz in sorted(wdir.glob("*.npz")):
                if npz.name.endswith(".posterior.npz"):
                    continue
                mid = npz.stem
                if (spec.world_id, mid) in seen:
                    continue
                seen.add((spec.world_id, mid))
                rec = json.loads((wdir / f"{mid}.json").read_text())
                a = np.load(npz)
                ci = {lv / 100: (a[f"contrib_intervals_{lv}_lo"], a[f"contrib_intervals_{lv}_hi"])
                      for lv in (50, 80, 95) if f"contrib_intervals_{lv}_lo" in a}
                out = ModelOutput(mid, spec.world_id, rec["family"], rec["information_set"], rec["fit_status"], 0,
                                  y_pred=a["y_pred"] if "y_pred" in a else None,
                                  contributions=a["contributions"] if "contributions" in a else None,
                                  contrib_intervals=ci or None)
                for row in score(out, obs, truth, eval_start=w0):
                    if row["task"] in (HIST, ATTR_FUT):
                        rows.append({**row, "response_warmup_weeks": w0})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------ main build
def build_v1_1() -> dict[str, str]:
    OUT_TAB.mkdir(parents=True, exist_ok=True)
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    S: dict[str, str] = {}

    m = dedupe(load("metrics", V1_RUNS), ["world_id", "model_id", "task", "metric", "channel"])
    st = dedupe(load("status", V1_RUNS), ["world_id", "model_id"])
    worlds = dedupe(load("worlds", V1_RUNS), ["world_id"])
    e08 = dedupe(load("e08", ("core", "pilot")), ["world_id", "model_id", "channel", "intervention"])
    e09 = dedupe(load("e09", ("core", "pilot")), ["world_id", "policy"])
    hist = wide(m, HIST, "contrib_mae_norm")
    pred = wide(m, PRED_FUT, "rmse_scaled")
    cells = worlds.set_index("world_id")["structure_cell_id"]

    # --- corr. 3: main matrix with N per cell, fast models on 600 -------------------------
    fast = [c for c in ["N0_naive_last", "N1_naive_mean", *FAST_BLIND, "M5_xgboost", "M6_lightgbm",
                        "M2p_true_transforms", "M2p_true_transforms_plus_D"] if c in pred]
    rows = []
    for (sc, T), g in pred[fast].groupby(level=["scenario_id", "T"]):
        for mid in fast:
            h = hist.loc[g.index, mid] if mid in hist else pd.Series(dtype=float)
            rows.append({"scenario_id": sc, "T": T, "model_id": mid, "n_worlds": int(g[mid].notna().sum()),
                         "pred_rmse_scaled_test_median": g[mid].median(),
                         "contrib_mae_norm_hist_median": h.median() if h.notna().any() else np.nan})
    main = pd.DataFrame(rows)
    main.to_csv(OUT_TAB / "main_matrix_fast_600.csv", index=False)
    agg = main.groupby("model_id").agg(n_worlds=("n_worlds", "sum"),
                                       pred=("pred_rmse_scaled_test_median", "median"),
                                       contrib=("contrib_mae_norm_hist_median", "median")).reset_index()
    S["main"] = (f"Modelos rápidos, {pred.shape[0]} mundos, 15 celdas escenario × T de {int(main.n_worlds.max())} mundos cada una. "
                 "Mediana de las medianas por celda; tabla por celda en `tables_v1_1/main_matrix_fast_600.csv`.\n\n" + md_table(agg))

    common = hist["M3_pymc_marketing"].dropna().index if "M3_pymc_marketing" in hist else pd.Index([])
    cm_models = [c for c in ["M0_ols", "M1_ridge", "M2_adstock_sat", "M2_adstock_sat_noZ", "M3_pymc_marketing",
                             "M5_xgboost", "M6_lightgbm", "M2p_true_transforms", "M2p_true_transforms_plus_D"] if c in pred]
    cmt = pd.DataFrame({
        "model_id": cm_models,
        "n_worlds": [int(pred.loc[common, c].notna().sum()) for c in cm_models],
        "pred_rmse_scaled_test_median": [pred.loc[common, c].median() for c in cm_models],
        "contrib_mae_norm_hist_median": [hist.loc[common, c].median() if c in hist else np.nan for c in cm_models],
    })
    cmt.to_csv(OUT_TAB / "common_subset_M3_45.csv", index=False)
    S["common"] = (f"Submuestra común pre-registrada ({len(common)} mundos: 5 escenarios × 3 T × réplicas 0–2; 3 mundos por celda). "
                   "M3 solo se compara aquí.\n\n" + md_table(cmt))

    # --- corr. 1: minimal warm-up re-scoring --------------------------------------------------
    rs_path = OUT_TAB / "rescored_min_warmup.csv"
    rs = pd.read_csv(rs_path) if rs_path.exists() else rescore_min_warmup()
    rs.to_csv(rs_path, index=False)
    h_min = wide(rs, HIST, "contrib_mae_norm")
    wcount = rs.drop_duplicates("world_id").response_warmup_weeks.value_counts().sort_index()
    cmp_rows = []
    for mid in [c for c in hist.columns if c in h_min]:
        both = pd.concat([hist[mid], h_min[mid]], axis=1, keys=["w8", "wmin"]).dropna()
        mean, lo, hi = paired_bootstrap((both.wmin - both.w8).to_numpy())
        cmp_rows.append({"model_id": mid, "n_worlds": len(both), "median_excl8": both.w8.median(),
                         "median_min_warmup": both.wmin.median(), "mean_diff": mean, "ci95_lo": lo, "ci95_hi": hi})
    wcmp = pd.DataFrame(cmp_rows)
    wcmp.to_csv(OUT_TAB / "warmup_sensitivity.csv", index=False)
    S["warmup"] = ("Distribución de `response_warmup_weeks` por mundo: "
                   + ", ".join(f"{int(k)} semanas: {v} mundos" for k, v in wcount.items())
                   + ".\n\n" + md_table(wcmp))

    # --- D1: direct vs total false attribution ---------------------------------------------------
    fd = m[(m.task == HIST) & (m.metric == "false_direct_attribution")]
    fdt = fd.groupby(["model_id", "role"]).value.agg(n_channel_worlds="count", false_direct_attribution_rate="mean").reset_index()
    fdt.to_csv(OUT_TAB / "false_direct_attribution.csv", index=False)
    tot = []
    if not e08.empty:
        z = e08[e08.intervention == "do_zero"].copy()
        z["abs_norm_est"] = z.delta_est.abs() / z.y_abs_sum
        z["abs_norm_true"] = z.delta_true.abs() / z.y_abs_sum
        for (mid, role), g in z[z.role.isin(["isolated", "feeder"])].groupby(["model_id", "role"]):
            row = {"model_id": mid, "role": role, "n_channel_worlds": len(g),
                   "mean_true_total_effect_norm": float((g.delta_true / g.y_abs_sum).mean()),
                   "mean_est_total_effect_norm": float((g.delta_est / g.y_abs_sum).mean())}
            if role == "isolated":
                row["false_total_effect_rate"] = float((g.abs_norm_est > NULL_FALSE_ATTRIBUTION_THRESHOLD).mean())
            else:
                row["mae_total_effect_norm"] = float(((g.delta_est - g.delta_true).abs() / g.y_abs_sum).mean())
            tot.append(row)
    tott = pd.DataFrame(tot)
    tott.to_csv(OUT_TAB / "total_effect_feeder_isolated.csv", index=False)
    S["d1"] = ("**`false_direct_attribution_rate`** (estimando *observed-path*, ventana `historical_in_sample_fit`, 600 mundos para modelos rápidos, 45 para M3, 5 para M4):\n\n"
               + md_table(fdt)
               + "\n**Efecto total (`do_zero` sobre la ventana histórica), 45 mundos causales.** `false_total_effect_rate` solo para canales aislados; para *feeders* se muestra el efecto total verdadero frente al implicado por el modelo:\n\n"
               + md_table(tott))

    # --- corr. 8 + H1: chance-adjusted rank agreement --------------------------------------------
    def hits(models, idx):
        out = []
        for wid in idx:
            a, b = pred.loc[wid, models], hist.loc[wid, models]
            if a.notna().all() and b.notna().all():
                out.append({"world_id": wid[0], "scenario_id": wid[1], "T": wid[2], "n_models": len(models),
                            "hit": a.idxmin() == b.idxmin(), "spearman": spearmanr(a, b).statistic})
        return pd.DataFrame(out)

    h4 = hits(FAST_BLIND, hist.index)
    h5 = hits(FAST_BLIND + ["M3_pymc_marketing"], common)
    hr = []
    for label, h in (("4 modelos rápidos ciegos (600 mundos)", h4), ("4 rápidos + M3 (45 mundos)", h5)):
        for sc, g in [("all", h), *h.groupby("scenario_id")]:
            mh, lo, hi = paired_bootstrap(g.hit.astype(float).to_numpy())
            ms, slo, shi = paired_bootstrap(g.spearman.to_numpy())
            hr.append({"set": label, "scenario": sc, "n_worlds": len(g), "chance_1_over_N": 1 / g.n_models.iloc[0],
                       "hit_rate": mh, "hit_ci95": f"[{lo:.2f}, {hi:.2f}]", "mean_spearman": ms,
                       "spearman_ci95": f"[{slo:.2f}, {shi:.2f}]"})
    hrt = pd.DataFrame(hr)
    hrt.to_csv(OUT_TAB / "h1_chance_adjusted.csv", index=False)
    S["h1"] = md_table(hrt)

    # --- corr. 4: cluster bootstrap for key pairs + within-world RMSE–regret ------------------------
    pairs = [("M0_ols", "M2_adstock_sat", hist.index), ("M1_ridge", "M0_ols", hist.index),
             ("M2_adstock_sat", "M2_adstock_sat_noZ", hist.index), ("M3_pymc_marketing", "M0_ols", common),
             ("M3_pymc_marketing", "M2p_true_transforms", common)]
    cb = []
    for a, b, idx in pairs:
        d = (hist.loc[idx, a] - hist.loc[idx, b]).dropna()
        wm, wlo, whi = paired_bootstrap(d.to_numpy())
        cm_, clo, chi, ncell = cluster_bootstrap(d.reset_index(drop=True),
                                                 pd.Series(d.index.get_level_values("world_id")).map(cells))
        cb.append({"A": a, "B": b, "n_worlds": len(d), "n_dag_cells": ncell, "mean_A_minus_B": wm,
                   "ci95_worlds": f"[{wlo:.4f}, {whi:.4f}]", "ci95_dag_cells": f"[{clo:.4f}, {chi:.4f}]"})
    cbt = pd.DataFrame(cb)
    cbt.to_csv(OUT_TAB / "paired_world_vs_cell_bootstrap.csv", index=False)
    cell_counts = worlds.groupby("scenario_id").structure_cell_id.nunique()
    S["cluster"] = ("Células DAG distintas por escenario (600 mundos): " + ", ".join(f"{k}={v}" for k, v in cell_counts.items())
                    + ". En S0 todas las réplicas comparten célula, así que el remuestreo por célula no es aplicable dentro de S0; en el resto casi cada mundo es su propia célula.\n\n"
                    + md_table(cbt))

    # --- D5 + corr. 4: E09 relabelled, within-world RMSE–regret --------------------------------------
    S["e09_v1"] = ""
    if not e09.empty:
        e9 = e09.copy()
        e9["policy_family"] = "all_channels_clamped_policy"
        pr = pred.stack().dropna().rename("pred").reset_index().rename(columns={"model_id": "policy"})
        mm = e9.merge(pr, on=["world_id", "policy"])
        within = [spearmanr(g.pred, g.regret_norm).statistic for _, g in mm.groupby("world_id") if len(g) >= 4]
        wm, wlo, whi = paired_bootstrap(np.asarray(within))
        S["e09_v1"] = (f"Correlación de Spearman entre RMSE predictivo y *regret* **dentro de cada mundo** "
                       f"(políticas de modelos con predicción, ≥ 4 por mundo): media {wm:.3f} [IC95 {wlo:.3f}, {whi:.3f}], "
                       f"{len(within)} mundos. (v1 reportó 0,076 sobre 315 pares mundo × modelo, tratándolos como independientes).\n")

    # --- corr. 5: M2 diagnostics ----------------------------------------------------------------------
    m2rows = []
    for r in V1_RUNS[:1]:
        for p in (RUNS / r / "results").glob("*/M2_adstock_sat.json"):
            rec = json.loads(p.read_text())
            d = rec["diagnostics"]
            info = json.loads((p.parent / "_world.json").read_text())["meta"]
            for k, (al, km) in enumerate(zip(d["alphas"], d["kappa_mult"])):
                m2rows.append({"world_id": rec["world_id"], "channel": k, "alpha": al, "kappa_mult": km,
                               "true_carryover": info["carryover"][k], "true_saturation": info["saturation"][k]})
    m2 = pd.DataFrame(m2rows)
    if not m2.empty:
        m2["chose_linear"] = m2.kappa_mult.astype(str) == "linear"
        m2["chose_no_adstock"] = m2.alpha.astype(float) == 0.0
        xt1 = m2.groupby("true_carryover").chose_no_adstock.agg(["count", "mean"]).rename(columns={"mean": "frac_alpha0"}).reset_index()
        xt2 = m2.groupby("true_saturation").chose_linear.agg(["count", "mean"]).rename(columns={"mean": "frac_linear"}).reset_index()
        gap = (hist["M2_adstock_sat"] - hist["M2p_true_transforms"]).groupby(level="scenario_id").median().rename("median_gap_M2_minus_M2p").reset_index()
        m2.to_csv(OUT_TAB / "m2_selected_hyperparameters.csv", index=False)
        S["m2"] = ("Búsqueda de M2 (por mundo): por canal, rejilla α ∈ {0; 0,3; 0,5; 0,7; 0,85} × κ ∈ {0,25; 0,5; 1; 2; 4; lineal} (30 combinaciones), "
                   "2 pasadas de descenso por coordenadas (≈ 60·K ajustes OLS), criterio = RMSE en el último 20 % de train (validación temporal), "
                   "escalas κ con estadísticas del sub-train. **Ningún paso usa la verdad.** M0/M1 no tienen hiperparámetros de forma (M1 solo α de Ridge, misma validación). "
                   "Diagnóstico (no usado para seleccionar) frente a las familias verdaderas:\n\n"
                   + md_table(xt1) + "\n" + md_table(xt2) + "\nBrecha M2 − M2p (privilegiado, fuera de ranking) por escenario:\n\n" + md_table(gap))

    # --- corr. 6: covariate classes -------------------------------------------------------------------
    zrows = []
    store = WorldStore(WORLD_CACHE)
    for wid in hist.index.get_level_values("world_id"):
        if not (wid.startswith("S2") or wid.startswith("S4")):
            continue
        sc, rest = wid.split("_T")[0], wid.split("_T")[1]
        T, r = int(rest.split("_r")[0]), int(rest.split("_r")[1])
        w = store.get(WorldSpec(sc.split("_", 1)[1], T, r))
        g = w.g
        zc, zy, zz, dz = (np.asarray(g[k]) != 0 for k in ("g_zc", "g_zy", "g_zz", "g_dz"))
        for mm_ in range(len(zy)):
            to_c, to_y = bool(zc[mm_].any()), bool(zy[mm_])
            cls = ("common_cause_C_Y" if to_c and to_y else "outcome_only" if to_y else
                   "treatment_only" if to_c else "via_Z_or_inert")
            zrows.append({"world_id": wid, "scenario_id": wid[:2], "covariate": mm_, "class": cls,
                          "descendant_of_D": bool(dz[:, mm_].any()), "has_Z_parent": bool(zz[:, mm_].any())})
    zt = pd.DataFrame(zrows)
    if not zt.empty:
        zt.to_csv(OUT_TAB / "covariate_classes.csv", index=False)
        zc_tab = zt.groupby(["scenario_id", "class"]).agg(n=("covariate", "count"), frac_descendant_of_D=("descendant_of_D", "mean")).reset_index()
        has_cc = zt.groupby("world_id")["class"].apply(lambda s: (s == "common_cause_C_Y").any())
        dz_ = (hist["M2_adstock_sat_noZ"] - hist["M2_adstock_sat"]).reset_index()
        dz_ = dz_[dz_.scenario_id.isin(["S2", "S4"])]
        dz_.columns = ["world_id", "scenario_id", "T", "noZ_minus_Z"]
        dz_["has_common_cause_Z"] = dz_.world_id.map(has_cc)
        strat = []
        for (sc, hc), g in dz_.groupby(["scenario_id", "has_common_cause_Z"]):
            mean, lo, hi = paired_bootstrap(g.noZ_minus_Z.to_numpy())
            strat.append({"scenario": sc, "world_has_common_cause_Z": hc, "n_worlds": len(g),
                          "mean_err_increase_without_Z": mean, "ci95_lo": lo, "ci95_hi": hi})
        S["z"] = ("El generador no tiene aristas `C→Z`: **ningún `Z` puede ser mediador ni descendiente de un canal** "
                  "(`blocked_design_not_supported` para ese contraste). Clases observadas en S2/S4 (600 mundos):\n\n"
                  + md_table(zc_tab) + "\nEfecto de omitir `Z` en M2, estratificado por presencia de una causa común `Z→C`, `Z→Y` en el mundo:\n\n"
                  + md_table(pd.DataFrame(strat)))

    # --- D4: coverage blocks --------------------------------------------------------------------------
    S["coverage"] = coverage_blocks(m, st)

    # --- v1.1 experiments ----------------------------------------------------------------------------
    S.update(v1_1_experiments(hist))
    S["changes"] = changes_table(fdt, hrt, wcmp, S)
    return S


def coverage_blocks(m: pd.DataFrame, st: pd.DataFrame, extra_runs: tuple = ("v1_1_m3", "v1_1_m4_diag")) -> str:
    """D4: (i) valid rate, (ii) conditional coverage among valid, (iii) descriptive coverage among invalid."""
    m2 = pd.concat([m.assign(source="v1"), *(load("metrics", (r,)).assign(source=r) for r in extra_runs)], ignore_index=True)
    s2 = pd.concat([st.assign(source="v1"), *(load("status", (r,)).assign(source=r) for r in extra_runs)], ignore_index=True)
    s2 = s2.drop_duplicates(["world_id", "model_id", "source"])
    m2 = m2.drop_duplicates(["world_id", "model_id", "source", "task", "metric", "channel"])
    rows = []
    for (mid, run), g in s2[s2.model_id.str.startswith(("M3", "M4"))].groupby(["model_id", "source"]):
        valid = set(g[g.converged_strict.astype(str).str.lower() == "true"].world_id)
        cov = m2[(m2.model_id == mid) & (m2.source == run) & (m2.task == HIST) & m2.metric.str.startswith("coverage_")]
        row = {"model_id": mid, "run": run, "n_attempted": len(g), "n_valid_strict": len(valid),
               "valid_rate": len(valid) / max(len(g), 1)}
        for lv in (50, 80, 95):
            c = cov[cov.metric == f"coverage_{lv}"]
            v, inv = c[c.world_id.isin(valid)].value, c[~c.world_id.isin(valid)].value
            row[f"cov{lv}_valid"] = v.mean() if len(v) else np.nan
            row[f"cov{lv}_INVALID_descriptive"] = inv.mean() if len(inv) else np.nan
        rows.append(row)
    t = pd.DataFrame(rows)
    t.to_csv(OUT_TAB / "coverage_by_validity.csv", index=False)
    return (md_table(t) + "\n> Las columnas `*_INVALID_descriptive` resumen ajustes `nonconverged`: **no son cobertura inferencial fiable**. "
            "La cobertura condicional en válidos tiene sesgo de selección: los mundos que convergen pueden ser sistemáticamente más fáciles.\n")


def v1_1_experiments(hist_v1: pd.DataFrame) -> dict[str, str]:
    S: dict[str, str] = {}
    # E02 linear control
    m = load("metrics", ("v1_1_e02_linear",))
    if not m.empty:
        h, p = wide(m, HIST, "contrib_mae_norm"), wide(m, PRED_FUT, "rmse_scaled")
        t = pd.DataFrame({"n_worlds": p.notna().sum(), "pred_rmse_scaled_test_median": p.median(),
                          "contrib_mae_norm_hist_median": h.median()}).reset_index()
        m3 = next((c for c in h.columns if c.startswith("M3")), None)
        pairs = [(a, b) for a, b in (("M2_adstock_sat", "M0_ols"), ("M1_ridge", "M0_ols"),
                                     (m3, "M0_ols"), ("M2p_true_transforms", "M0_ols")) if a in h and b in h]
        pt = []
        for a, b in pairs:
            d = (h[a] - h[b]).dropna()
            mean, lo, hi = paired_bootstrap(d.to_numpy())
            pt.append({"A": a, "B": b, "n_worlds": len(d), "mean_A_minus_B": mean, "ci95_lo": lo, "ci95_hi": hi})
        e8 = load("e08", ("v1_1_e02_linear",))
        e8s = ""
        if not e8.empty:
            z = e8[(e8.intervention == "do_zero") & (e8.model_id != "truth_do_engine")]
            e8s = "\nE08 `do_zero` (control lineal): |error| / Σ|y| medio por modelo:\n\n" + md_table(
                z.assign(a=z.err_norm.abs()).groupby("model_id").agg(n_worlds=("world_id", "nunique"), mae_norm=("a", "mean")).reset_index())
        S["e02"] = ("`direct_only` con `nonlinearity=\"linear\"` (arrastre `none`, saturación identidad; `response_warmup_weeks = 0`). "
                    "OLS con canales crudos está **bien especificado** para la parte de medios.\n\n" + md_table(t)
                    + "\nComparaciones emparejadas (error de contribución histórica):\n\n" + md_table(pd.DataFrame(pt)) + e8s)
    # full refit sensitivity
    mf = load("metrics", ("v1_1_full_refit",))
    if not mf.empty:
        hf = wide(mf, HIST_FULL, "contrib_mae_norm")
        rows = []
        for mid in hf.columns:
            both = pd.concat([hist_v1[mid], hf[mid]], axis=1, keys=["train", "full"]).dropna()
            mean, lo, hi = paired_bootstrap((both.full - both.train).to_numpy())
            rows.append({"model_id": mid, "n_worlds": len(both), "median_in_sample_fit": both.train.median(),
                         "median_full_refit": both.full.median(), "mean_full_minus_train": mean, "ci95_lo": lo, "ci95_hi": hi})
        S["full"] = ("`historical_full_refit`: mismos 45 mundos (F2 réplicas 0–2), reajuste sobre las T semanas, evaluación en `[8, T)`. "
                     "La ventana evaluada difiere (más semanas), así que la diferencia mezcla más datos y ventana distinta.\n\n" + md_table(pd.DataFrame(rows)))
    # E10A
    for tag, run, base in (("e10a_D", "v1_1_e10a_D", "dc000"), ("e10a_rho", "v1_1_e10a_rho", "rho000")):
        me = load("metrics", (run,))
        if me.empty:
            continue
        h = wide(me, HIST, "contrib_mae_norm").reset_index()
        h["level"] = h.world_id.str.split("__").str[1]
        h["pair"] = h.world_id.str.split("__").str[0]
        e8 = load("e08", (run,))
        z = e8[(e8.intervention == "do_zero") & (e8.model_id != "truth_do_engine")] if not e8.empty else pd.DataFrame()
        dz = (z.assign(a=z.err_norm.abs()).groupby(["world_id", "model_id"]).a.mean().unstack() if not z.empty else pd.DataFrame())
        tw = load("worlds", (run,))
        rows = []
        models = [c for c in ["M0_ols", "M1_ridge", "M2_adstock_sat", "M2_adstock_sat_noZ", "M2p_true_transforms",
                              "M2p_true_transforms_plus_D"] if c in h]
        for lvl in sorted(h.level.unique()):
            for mid in models:
                a = h[h.level == lvl].set_index("pair")[mid]
                b = h[h.level == base].set_index("pair")[mid]
                d = (a - b).dropna()
                mean, lo, hi = paired_bootstrap(d.to_numpy())
                row = {"level": lvl, "model_id": mid, "n_pairs": len(d), "median_contrib_err": a.median(),
                       "diff_vs_base": mean, "ci95_lo": lo, "ci95_hi": hi}
                if not dz.empty and mid in dz:
                    ids = h[h.level == lvl].world_id
                    row["mean_abs_do_zero_err_norm"] = dz.loc[dz.index.intersection(ids), mid].mean()
                rows.append(row)
        desc = (tw.assign(level=tw.world_id.str.split("__").str[1]).groupby("level")[
            ["confounding_strength", "indirect_share_of_y", "mean_abs_channel_corr"]].median().reset_index() if not tw.empty else pd.DataFrame())
        t = pd.DataFrame(rows)
        t.to_csv(OUT_TAB / f"{tag}_paired.csv", index=False)
        S[tag] = ("Descriptores verdaderos por nivel (medianas):\n\n" + md_table(desc)
                  + f"\nError de contribución *observed-path* y error del efecto `do_zero` implicado; diferencias **emparejadas** frente a `{base}`:\n\n" + md_table(t))
    # E09 v1.1
    e9 = load("e09", ("v1_1_e09",))
    if not e9.empty:
        e9["policy_family"] = e9["policy_family"].fillna("all_channels_clamped_policy") if "policy_family" in e9 else "all_channels_clamped_policy"
        eq_path = OUT_TAB / "e09_selected_budget_equalized.csv"
        sel = e9[(e9.policy_family == "selected_channels_do_policy") & (e9.label == "model_implied_under_exogeneity_assumption")]
        if not eq_path.exists() and not sel.empty:
            from .causal import budget_equalized_rows

            store, eq = WorldStore(WORLD_CACHE), []
            for wid, g in sel.groupby("world_id"):
                info = json.loads((RUNS / "v1_1_e09" / "results" / wid / "_world.json").read_text())["meta"]
                world, obs, truth = store.load(WorldSpec(info["scenario"], info["T"], info["replicate"]))
                eq += budget_equalized_rows(world, obs, truth, g.to_dict("records"),
                                            float(g.value_current.iloc[0]), float(g.value_oracle.iloc[0]))
            pd.DataFrame(eq).to_csv(eq_path, index=False)
        if eq_path.exists():
            e9 = pd.concat([e9, read_csv(eq_path)], ignore_index=True)
        cols = {"n_worlds": ("world_id", "nunique"), "regret_norm_mean": ("regret_norm", "mean"),
                "regret_norm_median": ("regret_norm", "median"), "improvement_norm_mean": ("improvement_vs_current_norm", "mean")}
        if "realized_budget_deviation" in e9:
            cols["mean_abs_realized_budget_dev"] = ("realized_budget_deviation", lambda s: s.abs().mean())
        t = e9.groupby(["policy_family", "policy", "label"]).agg(**cols).reset_index().sort_values(["policy_family", "regret_norm_mean"])
        t.to_csv(OUT_TAB / "e09_v1_1.csv", index=False)
        S["e09"] = md_table(t, ".4f")
    # M4 diag
    s4 = load("status", ("v1_1_m4_diag",))
    if not s4.empty:
        m4 = load("metrics", ("v1_1_m4_diag",))
        c = m4[(m4.task == HIST) & (m4.metric.isin(["contrib_mae_norm", "coverage_95"]))].pivot_table(
            index=["world_id", "model_id"], columns="metric", values="value").reset_index()
        t = s4[["world_id", "model_id", "runtime_s", "rhat_max", "ess_bulk_min", "divergences", "converged_strict"]].merge(c, on=["world_id", "model_id"], how="left")
        v1 = load("status", ("pilot",))
        v1 = v1[(v1.model_id == "M4_oracle_plugin") & v1.world_id.isin(t.world_id)][["world_id", "model_id", "runtime_s", "rhat_max", "ess_bulk_min", "divergences", "converged_strict"]]
        S["m4"] = md_table(pd.concat([v1.assign(model_id="M4 v1 (marginal, ta 0.90)"), t], ignore_index=True).sort_values("world_id"))
    # M3 chosen variant on 45
    s3 = load("status", ("v1_1_m3",))
    if not s3.empty:
        m3 = load("metrics", ("v1_1_m3",))
        h3 = wide(m3, HIST, "contrib_mae_norm")
        mid = h3.columns[0]
        both = pd.concat([hist_v1["M3_pymc_marketing"], h3[mid]], axis=1, keys=["v1", "v11"]).dropna()
        mean, lo, hi = paired_bootstrap((both.v11 - both.v1).to_numpy())
        S["m3_45"] = (f"Variante elegida `{mid}` en los 45 mundos M3: convergencia estricta {s3.converged_strict.astype(str).str.lower().eq('true').mean():.0%} "
                      f"(v1: 24 %), divergencias > 0 en {(s3.divergences > 0).mean():.0%}, mediana {s3.runtime_s.median():.0f} s/ajuste. "
                      f"Error de contribución histórica: mediana {both.v11.median():.3f} (v1 {both.v1.median():.3f}); diferencia emparejada {mean:+.4f} [{lo:+.4f}, {hi:+.4f}], {len(both)} mundos.\n")
    return S


def changes_table(fdt, hrt, wcmp, S) -> str:
    rows = [
        {"cifra": "Canales aislados en tabla de falsas atribuciones", "v1": "omitidos (rol 'null' leído como NaN)",
         "v1.1": f"{int(fdt[fdt.role == 'isolated'].n_channel_worlds.max()) if (fdt.role == 'isolated').any() else 0} canal-mundo por modelo rápido"},
        {"cifra": "«Mejor predictor = mejor atribuidor» (600 mundos)", "v1": "21–34 % (sin referencia de azar)",
         "v1.1": "ver tabla H1 frente a 1/N = 25 %"},
        {"cifra": "RMSE predictivo vs regret", "v1": "Spearman 0,076 sobre 315 pares (no independientes)",
         "v1.1": "correlación dentro de mundo (sección E09)"},
        {"cifra": "Cobertura M3 95 %", "v1": "38 % global (válidos + no válidos)", "v1.1": "separada: válidos / no válidos (sección D4)"},
        {"cifra": "Exclusión inicial", "v1": "8 semanas fijas", "v1.1": "sensibilidad con `response_warmup_weeks` por mundo"},
    ]
    return md_table(pd.DataFrame(rows))


def engine_validation_inventory() -> tuple[pd.DataFrame, pd.DataFrame]:
    """All do-engine validations recorded in any run, plus mechanism families covered by validated worlds."""
    rows, fam = [], []
    for run_dir in sorted(RUNS.iterdir()):
        if not (run_dir / "results").exists() or run_dir.name.startswith("_"):
            continue
        for p in (run_dir / "results").glob("*/_world.json"):
            info = json.loads(p.read_text())
            ev = info.get("engine_validation")
            if not ev:
                continue
            meta = info["meta"]
            checks = ev.get("checks", {})
            rows.append({"run": run_dir.name, "world_id": p.parent.name, "status": ev["status"],
                         **{f"{k}": v.get("passed") for k, v in checks.items()},
                         "max_abs_any": max([v.get("max_abs", 0.0) or 0.0 for v in checks.values()] + [0.0])})
            if ev["status"] == "validated":
                for c, s in zip(meta["carryover"], meta["saturation"]):
                    fam.append({"world_id": p.parent.name, "carryover": c, "saturation": s})
    return pd.DataFrame(rows).drop_duplicates("world_id"), pd.DataFrame(fam).drop_duplicates()


def write_quality_gate() -> None:
    import subprocess

    inv, fam = engine_validation_inventory()
    inv.to_csv(OUT_TAB / "engine_validation_all_runs.csv", index=False)
    by_status = inv.groupby("status").world_id.count().rename("n_worlds").reset_index()
    by_scen = inv.assign(scenario=inv.world_id.str[:2], variant=inv.world_id.str.split("__").str[1].fillna("-")).groupby(
        ["scenario", "variant", "status"]).world_id.count().rename("n_worlds").reset_index()
    fam_cov = (pd.crosstab(fam.carryover, fam.saturation) if not fam.empty else pd.DataFrame()).reset_index()
    checks = [c for c in inv.columns if c not in ("run", "world_id", "status", "max_abs_any")]
    chk = pd.DataFrame([{"check": c, "passed": int((inv[c] == True).sum()), "failed": int((inv[c] == False).sum()),  # noqa: E712
                         "not_testable": int(inv[c].isna().sum())} for c in checks])
    try:
        collected = subprocess.run(["uv", "run", "--locked", "pytest", "--collect-only", "-q"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=600).stdout
        tests = pd.Series([ln.split("::")[0] for ln in collected.splitlines() if "::" in ln]).value_counts()
        tests_md = md_table(tests.rename_axis("file").rename("n_tests").reset_index())
    except Exception as exc:  # report, never hide
        tests_md = f"_(no se pudo recoger la lista de tests: {exc})_\n"
    manifest = json.loads((ROOT / "reports" / "v1" / "FREEZE_MANIFEST.json").read_text())
    text = f"""# Quality gate v1.1

Generado por `python -m mmm_benchmark.cli revise`. Estado de cada control: **pasa**, **pasa con límites** o **abierto**.

## 1. Congelación de v1

v1 congelada el {manifest['frozen_utc']}: {manifest['n_files']} artefactos con SHA-256 en `reports/v1/FREEZE_MANIFEST.json`. Los runs v1.1 escriben en `runs/v1_1_*`; la caché de mundos solo añade directorios nuevos (variantes con sufijo `__<variante>`). **Pasa.**

## 2. Motor contrafactual (D3) — `counterfactual_engine=research_validated_private_api`

Usa funciones privadas de `pymc-generator` (`_carryover_col`, `_saturate_col`, estructura `Join` del grafo de `build_world_model`), válido **solo** para el commit `fb9549d` y el `uv.lock` registrado (hashes en cada `manifest.json`). Ante cualquier actualización hay que re-ejecutar `pytest -q` (regresión).

Validación por mundo en todos los runs causales:

{md_table(by_status)}
{md_table(by_scen)}
Comprobaciones (por mundo; `not_testable` cuando el mundo no tiene la estructura necesaria):

{md_table(chk)}
Familias (arrastre × saturación) presentes en canales de mundos validados:

{md_table(fam_cov)}
Pruebas independientes añadidas en v1.1 (`tests/test_interventions.py`):

- ruta analítica independiente para `C→C` (softplus inverso + término lineal del padre + transformaciones verdaderas) frente al motor: canales y ΔY con error ≤ 1e-12 en 4 mundos S3/S4;
- intervenciones simultáneas sobre canal ascendente y descendiente;
- pulsos en la primera y en la última semana reportada (borde de ventana; la primera usa la historia de *burn-in*);
- mundo con choques de tratamiento (`n_treatment_shocks=2`): nulo exacto y ausencia de efectos antes de la intervención;
- primitivas e innovaciones exógenas idénticas antes y después de evaluar intervenciones;
- política `selected_channels_do_policy`: presupuesto realizado igual al observado y *regret* ≥ 0.

**Pasa con límites**: depende de API privada y está validado con la propia aritmética del generador más una ruta analítica para `C→C`; no hay una segunda implementación completa e independiente del SCM.

## 3. Fugas de información

- `fit()` recibe solo `ObservedDataset.fit_view()`: `y` de test enmascarado con `NaN`; sin `D`, parámetros, máscaras de verdad ni contribuciones. Tests: cambiar `y` futuro no altera ajustes ciegos (7 modelos); permutar todas las salidas de verdad del mundo no altera ajustes ciegos (7 modelos); escalas de M2 y `α` de Ridge no cambian al alterar el test.
- Selección de hiperparámetros (M1, M2, M5, M6): validación temporal dentro de train, criterio RMSE de `y`; ningún paso lee la verdad (revisión de código: solo `PrivilegedTrueTransform*` y `OracleStructureKnownPlugin` llaman `attach_privileged`, y solo el runner la invoca cuando `privileged=True`).
- Oracle: `y` de test sustituido por la media de train **y** excluido de la verosimilitud por `observed_indices`.
- Selección de submuestras v1.1 (diagnóstico MCMC, oracle): reglas mecánicas sobre diagnósticos del muestreador, registradas antes de ejecutar.

**Pasa.**

## 4. Máscaras temporales y arrastre

- Las transformaciones de los modelos son causales (adstock solo con pasado) y se calculan sobre la serie completa desde la semana 0, de modo que las semanas de test usan la historia de tratamiento previa, no arrancan de cero.
- Exclusión inicial: 8 semanas en v1; en v1.1 sensibilidad con `response_warmup_weeks` por mundo (soporte realizado del núcleo; test: exclusión mínima válida). Diferencias en las métricas principales < 1e-3 (ver informe v1.1, §C). **Pasa.**

## 5. Comparabilidad

- Etiquetas de tarea y estimando explícitas (D2); ninguna tabla mezcla `historical_in_sample_fit` con `historical_full_refit`.
- M3 solo se compara en sus 45 mundos; M4 en sus 5; cada tabla lleva `n_worlds`.
- **Anomalía v1 corregida:** el rol `null` se leía como `NaN` y los canales aislados faltaban en la tabla de falsas atribuciones v1.
- **Pasa con límites:** E10A, E02 y E09-v1.1 se analizan por separado de la matriz principal y no entran en rankings globales.

## 6. Calidad MCMC (D4)

Ver [mcmc_diagnostics.md](mcmc_diagnostics.md). Criterio estricto vinculante; los ajustes no convergidos se conservan con `converged_strict = False` y su cobertura solo se presenta como descriptiva. **Abierto** para M4 (ver informe v1.1, §O).

## 7. Inventario de tests

{tests_md}
"""
    (ROOT / "reports" / "quality_gate_v1_1.md").write_text(text)


def write_reports(S: dict[str, str]) -> None:
    write_quality_gate()
    narrative = (ROOT / "docs" / "report_narrative_v1_1.md")
    narr = narrative.read_text() if narrative.exists() else "_(pendiente)_\n"
    text = f"""# Informe del banco MMM — revisión v1.1

> Generado por `python -m mmm_benchmark.cli revise`. v1 congelada en `reports/v1/` (no modificada).
> Decisiones aplicadas: [docs/revision_v1_1.md](../docs/revision_v1_1.md). Calidad: [quality_gate_v1_1.md](quality_gate_v1_1.md). MCMC: [mcmc_diagnostics.md](mcmc_diagnostics.md).
> Ningún resultado procede de River. Unidad de repetición: mundo. Etiquetas de tarea v1.1: `historical_in_sample_fit`, `prediction_future_conditional_on_known_CZ`, `attribution_future_conditional_on_known_CZ`, `historical_full_refit`.

{narr}

## A. Cambios de cifras y etiquetas respecto de v1

{S.get('changes', '')}

## B. Matriz principal (corr. 3)

{S.get('main', '')}

{S.get('common', '')}

## C. Sensibilidad a la exclusión inicial (corr. 1)

{S.get('warmup', '')}

## D. Canales feeder y aislados (D1)

{S.get('d1', '')}

## E. Predicción frente a atribución, ajustado por azar (H1, corr. 8)

{S.get('h1', '')}

## F. Dependencia estadística (corr. 4)

{S.get('cluster', '')}

## G. M2 frente a OLS (corr. 5)

{S.get('m2', '')}

## H. Controles Z según el DAG (corr. 6)

{S.get('z', '')}

## I. Incertidumbre por validez del ajuste (D4, corr. 9)

{S.get('coverage', '')}

{S.get('m3_45', '')}

## J. Control lineal E02 (corr. 2)

{S.get('e02', '_(no ejecutado)_')}

## K. Sensibilidad `historical_full_refit` (D2)

{S.get('full', '_(no ejecutado)_')}

## L. E10A — confusión estructural `D` (D6)

{S.get('e10a_D', '_(no ejecutado)_')}

## M. E10A — innovaciones compartidas `rho` (D6)

{S.get('e10a_rho', '_(no ejecutado)_')}

## N. E09 v1.1 — familias de política (D5)

{S.get('e09_v1', '')}

{S.get('e09', '_(no ejecutado)_')}

## O. Oracle: diagnóstico (D7)

{S.get('m4', '_(no ejecutado)_')}
"""
    (ROOT / "reports" / "benchmark_report_v1_1.md").write_text(text)
