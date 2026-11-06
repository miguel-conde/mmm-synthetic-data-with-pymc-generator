"""Tables, figures and the Markdown report, built only from saved run artefacts."""

from __future__ import annotations

import itertools
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from .evaluation import paired_bootstrap  # noqa: E402
from .provenance import ROOT  # noqa: E402

PRED_TASK = "prediction_conditional_future_inputs_known"
HIST_TASK = "attribution_historical"
FUT_TASK = "attribution_future_response"
BLIND_CONTRIB = ["M0_ols", "M1_ridge", "M2_adstock_sat", "M2_adstock_sat_noZ", "M3_pymc_marketing"]
PRIVILEGED = ["M2p_true_transforms", "M2p_true_transforms_plus_D", "M4_oracle_plugin"]

EXPERIMENTS = {
    "E00": ("Sanidad del generador", "tests + F0 bundles + worlds.csv"),
    "E01": ("Recuperación fácil (S0)", "matriz S0 × T × modelo"),
    "E02": ("Adstock y saturación", "M0/M1 vs M2 vs M2p (forma funcional); sin barrido controlado de familias"),
    "E03": ("Confusión latente (S1)", "S1 vs S0; M2p vs M2p_D"),
    "E04": ("Control observado y mediación (S2)", "M2 vs M2_noZ"),
    "E05": ("Halo y nulos (S3/S4)", "falsas atribuciones y feeders"),
    "E06": ("Predicción vs atribución", "rankings por mundo"),
    "E07": ("Incertidumbre", "cobertura M3/M4"),
    "E08": ("Intervención real", "motor do validado"),
    "E09": ("Valor de decisiones", "regret con motor do"),
    "E10": ("Cambio de distribución", None),
    "E11": ("DML / Causal Forest", None),
    "E12": ("MMM neuronal estructurado", None),
    "E13": ("Generador fuera de alcance", None),
    "E14": ("Multicolinealidad sin confusión", "estratos de correlación observada en S0 (diseño controlado no implementado)"),
}


def md_table(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if df.empty:
        return "_(sin filas)_\n"
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = []
        for v in row.values:
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else format(v, floatfmt))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def load_tables(run_dirs: list[Path]) -> dict[str, pd.DataFrame]:
    out: dict[str, list[pd.DataFrame]] = {}
    for rd in run_dirs:
        for p in (rd / "tables").glob("*.csv"):
            try:
                df = pd.read_csv(p)
            except pd.errors.EmptyDataError:
                continue
            df["run"] = rd.name
            out.setdefault(p.stem, []).append(df)
    tables = {k: pd.concat(v, ignore_index=True) for k, v in out.items()}
    # the same (world, model) may appear in several runs (F2 ⊂ F3): keep one copy, preferring the largest run
    for name, keys in (("metrics", ["world_id", "model_id", "task", "metric", "channel"]),
                       ("status", ["world_id", "model_id"]), ("worlds", ["world_id"]),
                       ("engine_validation", ["world_id"])):
        if name in tables and not tables[name].empty:
            tables[name] = tables[name].drop_duplicates(subset=[k for k in keys if k in tables[name]], keep="last")
    for name, keys in (("e08", ["world_id", "model_id", "channel", "intervention"]), ("e09", ["world_id", "policy"])):
        if name in tables and not tables[name].empty:
            tables[name] = tables[name].drop_duplicates(subset=keys, keep="last")
    return tables


def world_metric(m: pd.DataFrame, task: str, metric: str) -> pd.DataFrame:
    sel = m[(m.task == task) & (m.metric == metric) & (m.channel.isna())]
    return sel.pivot_table(index=["world_id", "scenario_id", "T"], columns="model_id", values="value")


def paired_table(wide: pd.DataFrame, pairs: list[tuple[str, str]], label: str) -> pd.DataFrame:
    rows = []
    for a, b in pairs:
        if a not in wide or b not in wide:
            continue
        both = wide[[a, b]].dropna()
        for scen, grp in [("all", both), *both.groupby(level="scenario_id")]:
            d = (grp[a] - grp[b]).to_numpy()
            mean, lo, hi = paired_bootstrap(d)
            rows.append({"metric": label, "A": a, "B": b, "scenario": scen, "N_worlds": len(d),
                         "mean_A_minus_B": mean, "ci95_lo": lo, "ci95_hi": hi,
                         "median_A_minus_B": float(np.median(d)) if len(d) else np.nan})
    return pd.DataFrame(rows)


def build_report(run_dirs: list[Path], out_dir: Path) -> None:
    out_dir = Path(out_dir)
    fig_dir, tab_dir = out_dir / "figures", out_dir / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)
    t = load_tables(run_dirs)
    m, st = t.get("metrics", pd.DataFrame()), t.get("status", pd.DataFrame())
    worlds = t.get("worlds", pd.DataFrame())
    e08, e09 = t.get("e08", pd.DataFrame()), t.get("e09", pd.DataFrame())
    val = t.get("engine_validation", pd.DataFrame())
    sections: dict[str, str] = {}

    # ---- status / cost -------------------------------------------------------
    stat = st.groupby("model_id").agg(
        N=("world_id", "nunique"), ok=("fit_status", lambda s: int((s == "ok").sum())),
        failed=("fit_status", lambda s: int((s == "failed").sum())),
        runtime_s_median=("runtime_s", "median"), runtime_s_max=("runtime_s", "max"),
        peak_rss_mb_max=("peak_rss_mb", "max"),
        converged_strict=("converged_strict", lambda s: s.dropna().astype(bool).mean() if s.notna().any() else np.nan),
        converged_pilot=("converged_pilot", lambda s: s.dropna().astype(bool).mean() if s.notna().any() else np.nan),
        rhat_max=("rhat_max", "max"), ess_bulk_min=("ess_bulk_min", "min"),
    ).reset_index()
    stat.to_csv(tab_dir / "model_status_cost.csv", index=False)
    fails = st[st.fit_status != "ok"][["world_id", "model_id", "fit_status", "error"]]
    fails.to_csv(tab_dir / "failures.csv", index=False)
    sections["status"] = md_table(stat, ".2f") + "\n**Fallos registrados:**\n\n" + md_table(fails)

    # ---- main matrix ----------------------------------------------------------
    pred = world_metric(m, PRED_TASK, "rmse_scaled")
    hist = world_metric(m, HIST_TASK, "contrib_mae_norm")
    chan = world_metric(m, HIST_TASK, "channel_total_abs_err_norm")
    fut = world_metric(m, FUT_TASK, "contrib_mae_norm")
    long = []
    for name, wide in (("pred_rmse_scaled_test", pred), ("contrib_mae_norm_hist", hist),
                       ("channel_total_abs_err_hist", chan), ("contrib_mae_norm_future", fut)):
        s = wide.stack().dropna().rename("value").reset_index()
        s["quantity"] = name
        long.append(s)
    long = pd.concat(long, ignore_index=True) if long else pd.DataFrame()
    matrix = long.groupby(["scenario_id", "T", "model_id", "quantity"]).value.agg(["count", "median"]).unstack("quantity")
    matrix.columns = [f"{b}_{a}" if a == "count" else b for a, b in matrix.columns]
    keep = [c for c in matrix.columns if not c.startswith("count_") or c == "count_pred_rmse_scaled_test"]
    matrix = matrix[keep].rename(columns={"count_pred_rmse_scaled_test": "N"}).reset_index()
    matrix.to_csv(tab_dir / "matrix_scenario_T_model.csv", index=False)
    overall = long.groupby(["scenario_id", "model_id", "quantity"]).value.median().unstack("quantity").reset_index()
    overall.to_csv(tab_dir / "matrix_scenario_model.csv", index=False)
    n_by = long[long.quantity == "pred_rmse_scaled_test"].groupby("model_id").world_id.nunique()
    sections["matrix"] = (
        "Medianas por escenario (todas las `T`); `N` mundos por modelo: "
        + ", ".join(f"{k}={v}" for k, v in n_by.items()) + ".\n\n" + md_table(overall)
    )
    # common subset: worlds where the expensive Bayesian MMM was fitted
    if "M3_pymc_marketing" in hist:
        common = hist["M3_pymc_marketing"].dropna().index
        cm = long[long.set_index(["world_id", "scenario_id", "T"]).index.isin(common)]
        ct = cm.groupby(["model_id", "quantity"]).value.median().unstack("quantity").reset_index()
        ct.insert(1, "N", cm[cm.quantity == "pred_rmse_scaled_test"].groupby("model_id").world_id.nunique().reindex(ct.model_id).values)
        ct.to_csv(tab_dir / "matrix_common_subset_M3.csv", index=False)
        sections["matrix"] += (f"\n**Submuestra común pre-registrada donde se ajustó M3** ({len(common)} mundos; "
                               "medianas, todas las métricas sobre los mismos mundos):\n\n" + md_table(ct))
    # H2: horizon
    h2 = long[long.quantity == "contrib_mae_norm_hist"].groupby(["model_id", "T"]).value.agg(
        N="count", median="median", mean="mean").reset_index()
    h2.to_csv(tab_dir / "h2_horizon.csv", index=False)
    sections["h2"] = md_table(h2)

    # ---- paired comparisons ------------------------------------------------------
    contrib_models = [c for c in BLIND_CONTRIB + PRIVILEGED if c in hist]
    pairs_c = [(a, b) for a, b in itertools.combinations(contrib_models, 2)]
    pc = paired_table(hist, pairs_c, "contrib_mae_norm_hist")
    blind_pred = [c for c in pred.columns if c not in PRIVILEGED]
    pairs_p = [(a, "M2_adstock_sat") for a in blind_pred if a != "M2_adstock_sat"]
    pp = paired_table(pred, pairs_p, "pred_rmse_scaled_test")
    paired = pd.concat([pc, pp], ignore_index=True)
    paired.to_csv(tab_dir / "paired_comparisons.csv", index=False)
    key_pairs = {("M0_ols", "M2_adstock_sat"), ("M1_ridge", "M2_adstock_sat"), ("M2_adstock_sat", "M2p_true_transforms"),
                 ("M2_adstock_sat", "M3_pymc_marketing"), ("M3_pymc_marketing", "M4_oracle_plugin"),
                 ("M5_xgboost", "M2_adstock_sat"), ("M6_lightgbm", "M2_adstock_sat"), ("M0_ols", "M1_ridge"),
                 ("M2_adstock_sat", "M2_adstock_sat_noZ"), ("M2p_true_transforms", "M2p_true_transforms_plus_D")}
    show = paired[[(a, b) in key_pairs for a, b in zip(paired.A, paired.B)]]
    sections["paired"] = md_table(show)

    # ---- H1 / E06: prediction vs attribution rankings ---------------------------
    blind_c = [c for c in BLIND_CONTRIB if c in hist and c in pred]
    rho_rows = []
    for wid in hist.index:
        a = pred.loc[wid, blind_c].dropna()
        b = hist.loc[wid, a.index].dropna()
        a = a[b.index]
        if len(a) >= 3:
            rho_rows.append({"world_id": wid[0], "scenario_id": wid[1], "T": wid[2], "n_models": len(a),
                             "spearman_pred_vs_contrib": spearmanr(a, b).statistic,
                             "best_pred": a.idxmin(), "best_contrib": b.idxmin()})
    rho = pd.DataFrame(rho_rows)
    rho.to_csv(tab_dir / "h1_rank_agreement.csv", index=False)
    if not rho.empty:
        summ = rho.groupby("scenario_id").agg(
            N=("world_id", "count"), mean_spearman=("spearman_pred_vs_contrib", "mean"),
            same_best=("best_pred", lambda s: float((s == rho.loc[s.index, "best_contrib"]).mean())),
        ).reset_index()
        m_all, lo, hi = paired_bootstrap(rho.spearman_pred_vs_contrib.to_numpy())
        sections["h1"] = (f"Modelos ciegos con contribución: {', '.join(blind_c)}. Spearman medio (todas) = "
                          f"{m_all:.3f} [IC95 {lo:.3f}, {hi:.3f}], N = {len(rho)} mundos.\n\n" + md_table(summ))
    else:
        sections["h1"] = "_(insuficientes modelos por mundo)_\n"

    # ---- H3: confounding -----------------------------------------------------------
    h3 = []
    for mid in [c for c in contrib_models if c in hist]:
        for T in sorted(hist.index.get_level_values("T").unique()):
            s0 = hist.xs(("S0", T), level=("scenario_id", "T"))[mid].dropna() if ("S0" in hist.index.get_level_values(1)) else pd.Series(dtype=float)
            s1 = hist.xs(("S1", T), level=("scenario_id", "T"))[mid].dropna() if ("S1" in hist.index.get_level_values(1)) else pd.Series(dtype=float)
            if len(s0) and len(s1):
                rng = np.random.default_rng(0)
                boots = [rng.choice(s1, len(s1)).mean() - rng.choice(s0, len(s0)).mean() for _ in range(2000)]
                h3.append({"model_id": mid, "T": T, "N_S0": len(s0), "N_S1": len(s1), "mean_S0": s0.mean(),
                           "mean_S1": s1.mean(), "diff_S1_minus_S0": s1.mean() - s0.mean(),
                           "ci95_lo": np.quantile(boots, 0.025), "ci95_hi": np.quantile(boots, 0.975)})
    h3 = pd.DataFrame(h3)
    h3.to_csv(tab_dir / "h3_confounding.csv", index=False)
    sections["h3"] = md_table(h3)

    # ---- H5 / E14 partial: correlation strata in S0 ------------------------------------
    h5 = []
    if not worlds.empty:
        wd = worlds.set_index("world_id")
        for mid in [c for c in contrib_models if c in hist]:
            s = hist[mid].dropna().reset_index()
            s = s[s.scenario_id.isin(["S0", "S3"])].copy()
            s["corr"] = s.world_id.map(wd["mean_abs_channel_corr"])
            for scen, g in s.groupby("scenario_id"):
                if len(g) >= 5:
                    r = spearmanr(g["corr"], g[mid]).statistic
                    h5.append({"model_id": mid, "scenario_id": scen, "N": len(g), "spearman_corr_vs_error": r,
                               "median_mean_abs_corr": g["corr"].median()})
    h5 = pd.DataFrame(h5)
    h5.to_csv(tab_dir / "h5_correlation_strata.csv", index=False)
    sections["h5"] = md_table(h5)

    # ---- null / feeder false attribution ----------------------------------------------
    nf = m[(m.task == HIST_TASK) & (m.metric == "null_false_attribution")]
    nfa = nf.groupby(["model_id", "role"]).value.agg(["count", "mean"]).rename(
        columns={"count": "N_channel_worlds", "mean": "false_attribution_rate"}).reset_index()
    nfa.to_csv(tab_dir / "null_false_attribution.csv", index=False)
    sections["nulls"] = md_table(nfa)

    # ---- uncertainty ------------------------------------------------------------------
    cov = m[m.metric.str.startswith("coverage_") | m.metric.str.startswith("width_norm_")]
    covt = cov.groupby(["model_id", "task", "metric"]).value.agg(["count", "mean"]).reset_index()
    covt.to_csv(tab_dir / "coverage.csv", index=False)
    sections["coverage"] = md_table(covt)

    # ---- E08 / E09 ----------------------------------------------------------------------
    if not val.empty:
        sections["validation"] = md_table(val.groupby("status").world_id.count().rename("N_worlds").reset_index())
    else:
        sections["validation"] = "_(sin validación)_\n"
    if not e08.empty:
        est = e08[e08.model_id != "truth_do_engine"].copy()
        est["abs_err_norm"] = est.err_norm.abs()
        e8t = est.groupby(["scenario_id", "intervention", "model_id"]).agg(
            N=("world_id", "nunique"), mae_norm=("abs_err_norm", "mean"), bias_norm=("err_norm", "mean")).reset_index()
        e8t.to_csv(tab_dir / "e08_errors.csv", index=False)
        e8s = est[est.intervention == "do_zero"].groupby(["model_id"]).agg(
            N=("world_id", "nunique"), mae_norm=("abs_err_norm", "mean"), bias_norm=("err_norm", "mean")).reset_index()
        tru = e08[(e08.model_id == "truth_do_engine") & (e08.intervention == "do_zero")].copy()
        tru["attr_minus_do_norm"] = (-tru.observed_path_attribution_true - tru.delta_true) / tru.y_abs_sum
        h7 = tru.groupby(["scenario_id", "role"]).agg(
            N=("world_id", "count"), mean_do_zero_effect_norm=("delta_true", lambda s: (s / tru.loc[s.index, "y_abs_sum"]).mean()),
            mean_attr_minus_do_norm=("attr_minus_do_norm", "mean"),
            max_abs_attr_minus_do_norm=("attr_minus_do_norm", lambda s: s.abs().max())).reset_index()
        h7.to_csv(tab_dir / "h7_attribution_vs_do.csv", index=False)
        sections["e08"] = ("**do_zero, todos los escenarios:**\n\n" + md_table(e8s) +
                           "\n**H7 — atribución observada verdadera vs efecto total do_zero verdadero (normalizado por Σ|y|):**\n\n"
                           + md_table(h7))
    else:
        sections["e08"] = "_(no ejecutado)_\n"
    if not e09.empty:
        e9t = e09.groupby(["policy", "label"]).agg(
            N=("world_id", "nunique"), regret_norm_mean=("regret_norm", "mean"), regret_norm_median=("regret_norm", "median"),
            improvement_norm_mean=("improvement_vs_current_norm", "mean"),
            frac_at_bounds=("frac_at_bounds", "mean")).reset_index().sort_values("regret_norm_mean")
        e9t.to_csv(tab_dir / "e09_regret.csv", index=False)
        sections["e09"] = md_table(e9t, ".4f")
        if not pred.empty:
            e9m = e09.merge(pred.stack().dropna().rename("pred").reset_index().rename(columns={"model_id": "policy"}),
                            on=["world_id", "policy"], how="inner")
            if len(e9m) > 5:
                r = spearmanr(e9m.pred, e9m.regret_norm).statistic
                sections["e09"] += f"\nSpearman(RMSE predictivo test, regret) sobre {len(e9m)} pares mundo×modelo = {r:.3f}.\n"
    else:
        sections["e09"] = "_(no ejecutado)_\n"

    # ---- experiment status ------------------------------------------------------------
    present = set(m.model_id.unique()) if not m.empty else set()
    exp_rows = []
    for eid, (name, how) in EXPERIMENTS.items():
        if how is None:
            status = "not_run_v1" if eid != "E13" else "not_applicable_v1"
        elif eid == "E07":
            status = "completed" if {"M3_pymc_marketing", "M4_oracle_plugin"} & present else "blocked"
        elif eid in ("E08", "E09"):
            status = "completed" if (not e08.empty if eid == "E08" else not e09.empty) else "blocked_counterfactual_not_validated"
        elif eid == "E14":
            status = "partial_observational_strata"
        elif eid == "E02":
            status = "partial"
        else:
            status = "completed"
        exp_rows.append({"experiment": eid, "name": name, "status": status, "evidence": how or "—"})
    exp = pd.DataFrame(exp_rows)
    exp.to_csv(tab_dir / "experiment_status.csv", index=False)
    sections["experiments"] = md_table(exp)

    # ---- figures ------------------------------------------------------------------------
    figs = make_figures(t, hist, pred, rho, run_dirs, fig_dir)
    sections["figures"] = "\n".join(f"![{n}](figures/{n})" for n in figs) + "\n"
    write_markdown(out_dir, sections, t, run_dirs)


def make_figures(t, hist, pred, rho, run_dirs, fig_dir: Path) -> list[str]:
    names = []
    m = t.get("metrics", pd.DataFrame())
    # 1. DAG + decomposition bundles from F0
    for rd in run_dirs:
        bdir = rd / "bundles"
        if bdir.exists():
            for b in sorted(bdir.iterdir()):
                for f in ("dag.png", "decomposition.png"):
                    if (b / f).exists():
                        dst = f"F0_{b.name}_{f}"
                        shutil.copy(b / f, fig_dir / dst)
                        names.append(dst)
    # 2. example world: y and contributions
    ex = _example_world(run_dirs)
    if ex is not None:
        wid, rdir = ex
        names.append(_plot_example(wid, rdir, fig_dir))
    # 3. contribution error distribution by scenario and T
    if not hist.empty:
        models = [c for c in BLIND_CONTRIB + PRIVILEGED if c in hist]
        s = hist[models].stack().dropna().rename("v").reset_index()
        scen = sorted(s.scenario_id.unique())
        fig, axes = plt.subplots(1, len(scen), figsize=(4 * len(scen), 4.5), sharey=True)
        axes = np.atleast_1d(axes)
        for ax, sc in zip(axes, scen):
            g = s[s.scenario_id == sc]
            data, labels = [], []
            for mid in models:
                for T in sorted(g["T"].unique()):
                    v = g[(g.model_id == mid) & (g["T"] == T)].v
                    if len(v):
                        data.append(v.values)
                        labels.append(f"{mid.split('_')[0]}·{T}")
            ax.boxplot(data, tick_labels=labels, showfliers=False)
            ax.set_title(sc)
            ax.tick_params(axis="x", rotation=90, labelsize=7)
        axes[0].set_ylabel("MAE contribución / media|y| (histórica)")
        fig.tight_layout()
        fig.savefig(fig_dir / "contrib_error_by_scenario_T.png", dpi=120)
        plt.close(fig)
        names.append("contrib_error_by_scenario_T.png")
    # 4. prediction vs contribution scatter
    if not hist.empty and not pred.empty:
        fig, ax = plt.subplots(figsize=(7, 5.5))
        for mid in [c for c in BLIND_CONTRIB + PRIVILEGED if c in hist and c in pred]:
            both = pd.concat([pred[mid], hist[mid]], axis=1, keys=["p", "c"]).dropna()
            ax.scatter(both.p, both.c, s=12, alpha=0.6, label=mid)
        ax.set_xlabel("RMSE predicción test / media|y_train|")
        ax.set_ylabel("MAE contribución histórica / media|y|")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(fig_dir / "prediction_vs_contribution.png", dpi=120)
        plt.close(fig)
        names.append("prediction_vs_contribution.png")
    # 5. coverage
    cov = m[(m.task == HIST_TASK) & m.metric.str.startswith("coverage_")] if not m.empty else pd.DataFrame()
    if not cov.empty:
        fig, ax = plt.subplots(figsize=(5, 5))
        for mid, g in cov.groupby("model_id"):
            lv = g.metric.str.replace("coverage_", "").astype(int) / 100
            agg = g.assign(lv=lv).groupby("lv").value.mean()
            ax.plot(agg.index, agg.values, "o-", label=mid)
        ax.plot([0.4, 1], [0.4, 1], "k--", lw=1)
        ax.set_xlabel("nominal")
        ax.set_ylabel("empírica (contribuciones observed-path, histórica)")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(fig_dir / "coverage_calibration.png", dpi=120)
        plt.close(fig)
        names.append("coverage_calibration.png")
    # 6. null false attribution
    nf = m[(m.task == HIST_TASK) & (m.metric == "null_false_attribution")] if not m.empty else pd.DataFrame()
    if not nf.empty:
        agg = nf.groupby(["model_id", "role"]).value.mean().unstack("role")
        ax = agg.plot.bar(figsize=(8, 4.5), rot=45)
        ax.set_ylabel("tasa de falsa atribución (umbral 2 % Σ|y|)")
        plt.tight_layout()
        plt.savefig(fig_dir / "null_false_attribution.png", dpi=120)
        plt.close()
        names.append("null_false_attribution.png")
    # 7. E08 / E09
    e08, e09 = t.get("e08", pd.DataFrame()), t.get("e09", pd.DataFrame())
    if not e08.empty:
        est = e08[e08.model_id != "truth_do_engine"]
        fig, ax = plt.subplots(figsize=(9, 4.5))
        models = sorted(est.model_id.unique())
        ints = sorted(est.intervention.unique())
        for i, mid in enumerate(models):
            vals = [est[(est.model_id == mid) & (est.intervention == iv)].err_norm.abs().mean() for iv in ints]
            ax.bar(np.arange(len(ints)) + i * 0.8 / len(models), vals, width=0.8 / len(models), label=mid)
        ax.set_xticks(np.arange(len(ints)) + 0.4)
        ax.set_xticklabels(ints, rotation=30)
        ax.set_ylabel("|ΔY estimado − ΔY verdadero| / Σ|y|")
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(fig_dir / "e08_intervention_error.png", dpi=120)
        plt.close(fig)
        names.append("e08_intervention_error.png")
    if not e09.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        order = e09.groupby("policy").regret_norm.mean().sort_values().index
        ax.boxplot([e09[e09.policy == p].regret_norm for p in order], tick_labels=order, showfliers=True)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        ax.set_ylabel("regret / Σ|y| (valor verdadero vía do)")
        fig.tight_layout()
        fig.savefig(fig_dir / "e09_regret.png", dpi=120)
        plt.close(fig)
        names.append("e09_regret.png")
    # 8. cost and failures
    st = t.get("status", pd.DataFrame())
    if not st.empty:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        g = st.groupby("model_id")
        g.runtime_s.median().sort_values().plot.barh(ax=axes[0], logx=True)
        axes[0].set_xlabel("segundos por ajuste (mediana)")
        (1 - g.fit_status.apply(lambda s: (s == "ok").mean())).plot.barh(ax=axes[1])
        axes[1].set_xlabel("fracción de ajustes fallidos")
        fig.tight_layout()
        fig.savefig(fig_dir / "cost_and_failures.png", dpi=120)
        plt.close(fig)
        names.append("cost_and_failures.png")
    return names


def _example_world(run_dirs):
    for rd in run_dirs:
        for wdir in sorted((rd / "results").glob("S1_*")):
            if (wdir / "M3_pymc_marketing.npz").exists():
                return wdir.name, rd
    for rd in run_dirs:
        for wdir in sorted((rd / "results").glob("S1_*")):
            if (wdir / "M2_adstock_sat.npz").exists():
                return wdir.name, rd
    return None


def _plot_example(wid: str, rd: Path, fig_dir: Path) -> str:
    from .generator_adapter import WorldSpec, WorldStore, get_scenario  # noqa: F401
    from .runner import WORLD_CACHE

    info = json.loads((rd / "results" / wid / "_world.json").read_text())["meta"]
    spec = WorldSpec(info["scenario"], info["T"], info["replicate"])
    _, obs, truth = WorldStore(WORLD_CACHE).load(spec)
    models = [mid for mid in ("M2_adstock_sat", "M3_pymc_marketing", "M4_oracle_plugin")
              if (rd / "results" / wid / f"{mid}.npz").exists()]
    K = obs.K
    fig, axes = plt.subplots(K + 1, 1, figsize=(10, 2.2 * (K + 1)), sharex=True)
    axes[0].plot(obs.y, "k", label="y")
    for mid in models:
        a = np.load(rd / "results" / wid / f"{mid}.npz")
        axes[0].plot(a["y_pred"], label=mid, alpha=0.8)
        for k in range(K):
            axes[k + 1].plot(a["contributions"][:, k], label=mid, alpha=0.8)
            if "contrib_intervals_95_lo" in a:
                axes[k + 1].fill_between(np.arange(obs.T), a["contrib_intervals_95_lo"][:, k],
                                         a["contrib_intervals_95_hi"][:, k], alpha=0.15)
    for k in range(K):
        axes[k + 1].plot(truth["contributions_observed"][:, k], "k", lw=2, label="verdad observed-path")
        axes[k + 1].set_ylabel(f"C{k + 1} ({truth.channel_roles[k]})", fontsize=8)
    for ax in axes:
        ax.axvline(len(obs.train_idx), color="grey", ls=":")
        ax.axvspan(0, obs.warmup, color="grey", alpha=0.1)
    axes[0].legend(fontsize=7)
    axes[1].legend(fontsize=7)
    axes[0].set_title(f"{wid}: y y contribuciones por canal (gris: warm-up; línea: corte train/test)")
    fig.tight_layout()
    name = f"example_{wid}.png"
    fig.savefig(fig_dir / name, dpi=110)
    plt.close(fig)
    return name


def write_markdown(out_dir: Path, s: dict[str, str], t: dict, run_dirs: list[Path]) -> None:
    manifests = []
    for rd in run_dirs:
        p = rd / "manifest.json"
        if p.exists():
            mf = json.loads(p.read_text())
            sess = mf.get("sessions", [{}])[-1]
            manifests.append({"run": rd.name, "phase": mf["config"].get("phase"), "worlds": len(mf.get("planned", {})),
                              "config_sha256": mf.get("config_sha256", "")[:12], "code_sha256": sess.get("code_sha256", "")[:12],
                              "generator_commit": (sess.get("pymc_generator_commit") or "")[:12]})
    narrative = ROOT / "docs" / "report_narrative.md"
    narr = narrative.read_text() if narrative.exists() else "_(pendiente)_\n"
    narr, _, closing = narr.partition("<!-- END-SUMMARY -->")
    hyp = (ROOT / "docs" / "methods.md").read_text().split("## Hipótesis")[1].split("## Umbrales")[0]
    text = f"""# Informe del banco MMM sobre pymc-generator

> Generado automáticamente por `python -m mmm_benchmark.cli report` a partir de los artefactos de `runs/`.
> Ningún resultado procede de River. Todas las cifras: unidad de repetición = mundo.

{narr}

## 2. Diseño, hipótesis (pre-registradas) y versión del generador

Ejecuciones incluidas:

{md_table(pd.DataFrame(manifests))}

Hipótesis (fijadas en [docs/methods.md](../docs/methods.md) antes de ejecutar):
{hyp}
Estimandos: [docs/estimands.md](../docs/estimands.md). Auditoría: [docs/generator_audit.md](../docs/generator_audit.md).

## 3. Estado por experimento

{s['experiments']}

## 4. Ajustes, coste y fallos

{s['status']}

## 5–6. Predicción y atribución histórica (matriz principal)

`pred_rmse_scaled_test` = RMSE en test / media|y_train| (modo B, `conditional_future_inputs_known`).
`contrib_mae_norm_hist` = MAE por canal-semana frente a `historical_observed_path_response` / media|y| (modo A, semanas ≥ 8 de train).
`contrib_mae_norm_future` = mismo estimando en test, respuesta del modelo a `C` futuro sin ver `Y` futuro.
Modelos `M2p*` y `M4` son **privilegiados** y no forman parte de ningún ranking ciego.

{s['matrix']}

### Comparaciones emparejadas (mismos mundos; IC95 bootstrap de mundos)

{s['paired']}
Tabla completa: `tables/paired_comparisons.csv`.

### H2 — horizonte `T` (error de contribución histórica)

{s['h2']}

### H1 / E06 — concordancia de rankings predicción vs atribución por mundo

{s['h1']}

### H3 / E03 — confusión latente (S1 − S0, no emparejado; IC95 bootstrap)

{s['h3']}

### H5 / E14 (parcial) — correlación observada entre canales vs error de contribución

{s['h5']}

### E05 — falsas atribuciones a canales sin `C→Y` (umbral pre-registrado 2 % de Σ|y|)

{s['nulls']}

## 7. Incertidumbre y diagnósticos

{s['coverage']}

## 8. Efectos de intervención (E08)

Validación del motor contrafactual por mundo:

{s['validation']}
{s['e08']}

## 9. Calidad de decisiones (E09)

Presupuesto adimensional en unidades de tratamiento (no euros), multiplicadores por canal en [0.5, 1.5] sobre la ventana histórica; valor evaluado con `do` sobre todos los canales.

{s['e09']}

## Figuras

{s['figures']}

{closing}
"""
    (out_dir / "benchmark_report.md").write_text(text)
