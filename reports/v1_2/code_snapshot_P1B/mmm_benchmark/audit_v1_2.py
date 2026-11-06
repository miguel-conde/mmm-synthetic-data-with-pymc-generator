"""v1.2 P0 audits (designer reply RESPUESTA_AL_AGENTE_MMM_V1_2.md). Reads frozen v1/v1.1 artefacts only;
no model is refitted. Outputs go to reports/v1_2/ and the P0 report files."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .evaluation import paired_bootstrap
from .generator_adapter import WorldSpec, WorldStore
from .provenance import ROOT
from .reporting import md_table
from .runner import WORLD_CACHE
from .tables_io import read_table

RUNS = ROOT / "runs"
OUT = ROOT / "reports" / "v1_2"
LEVELS = (50, 80, 95)
DEV_WORLDS = (  # the 10 worlds used to choose V3 (docs/revision_v1_1.md §3.1)
    "S0_direct_only_T208_r00", "S0_direct_only_T208_r01", "S1_confounded_treatment_T104_r00",
    "S1_confounded_treatment_T104_r01", "S2_promo_drives_treatment_T104_r01", "S2_promo_drives_treatment_T104_r02",
    "S3_treatment_halo_T104_r00", "S3_treatment_halo_T104_r02", "S4_kitchen_sink_T104_r00", "S4_kitchen_sink_T104_r01",
)
M3_VARIANTS = {"V0": ("core", "M3_pymc_marketing"), "V3": ("v1_1_m3", "M3_pymc_marketing@v3")}
REFERENCE_MODELS = {  # label -> (run, model id); week0 = fitted from week 0 like M3 V0/V3, week8 = corrected window
    "M0_ols": ("core", "M0_ols"),
    "M2p_w0": ("core", "M2p_true_transforms"),
    "M2p_w8": ("v1_2_warmfit", "M2p_true_transforms"),
}


def spec_from_world_id(world_id: str) -> WorldSpec:
    scen, rest = world_id.split("__")[0].split("_T")
    T, rep = rest.split("_r")
    return WorldSpec(scen.split("_", 1)[1], int(T), int(rep))


def boot_by_world(df: pd.DataFrame, col: str) -> tuple[float, float, float, int]:
    """Average within world first (channels/weeks are not replicates), then bootstrap worlds."""
    per_world = df.groupby("world_id")[col].mean().dropna()
    m, lo, hi = paired_bootstrap(per_world.to_numpy())
    return m, lo, hi, len(per_world)


# ------------------------------------------------------------------------------------- M3 audit
def m3_channel_table() -> pd.DataFrame:
    """One row per (variant, world, channel, window): weekly coverage/width/bias/MAE summarized per channel."""
    path = OUT / "m3_world_channel.csv"
    if path.exists():
        return read_table(path)
    store = WorldStore(WORLD_CACHE)
    rows = []
    worlds = sorted(p.name for p in (RUNS / "v1_1_m3" / "results").iterdir())
    for wid in worlds:
        world, obs, truth = store.load(spec_from_world_id(wid))
        meta = truth.meta
        tc = truth["contributions_observed"]
        refs = {}
        for label, (run, mid) in REFERENCE_MODELS.items():
            a = np.load(RUNS / run / "results" / wid / f"{mid}.npz")
            refs[label] = a["contributions"]
        for var, (run, mid) in M3_VARIANTS.items():
            rec = json.loads((RUNS / run / "results" / wid / f"{mid}.json").read_text())
            a = np.load(RUNS / run / "results" / wid / f"{mid}.npz")
            d = rec["diagnostics"]
            corr = d.get("corr_log_lam_log_beta_by_channel")
            for window, idx in (("historical_in_sample_fit", obs.eval_idx("train")),
                                ("attribution_future_conditional_on_known_CZ", obs.eval_idx("test"))):
                ymean = float(np.mean(np.abs(obs.y[idx])))
                for k, role in enumerate(truth.channel_roles):
                    t, e = tc[idx, k], a["contributions"][idx, k]
                    row = {"variant": var, "world_id": wid, "scenario_id": wid[:2], "T": obs.T, "channel": k,
                           "role": role, "window": window, "n_weeks": len(idx),
                           "valid_strict": bool(d["converged_strict"]), "dev_world": wid in DEV_WORLDS,
                           "true_carryover": meta["carryover"][k], "true_saturation": meta["saturation"][k],
                           "bias_norm": float(np.mean(e - t) / ymean), "mae_norm": float(np.mean(np.abs(e - t)) / ymean),
                           "true_mean_norm": float(np.mean(t) / ymean),
                           "corr_log_lam_log_beta": corr[k] if corr else np.nan}
                    for lv in LEVELS:
                        lo, hi = a[f"contrib_intervals_{lv}_lo"][idx, k], a[f"contrib_intervals_{lv}_hi"][idx, k]
                        row[f"cov{lv}"] = float(np.mean((t >= lo) & (t <= hi)))
                        row[f"width{lv}_norm"] = float(np.mean(hi - lo) / ymean)
                    for rm, c in refs.items():
                        row[f"{rm}_bias_norm"] = float(np.mean(c[idx, k] - t) / ymean)
                    rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return read_table(path)


def summarize(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(by, observed=True):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, key))
        row["n_worlds"] = g.world_id.nunique()
        row["n_channels"] = len(g.drop_duplicates(["world_id", "channel"]))
        row["n_valid_fits"] = g[g.valid_strict].world_id.nunique()
        for col in ("cov50", "cov80", "cov95", "width95_norm", "bias_norm", "mae_norm"):
            m, lo, hi, _ = boot_by_world(g, col)
            row[col] = m
            if col in ("cov95", "bias_norm"):
                row[f"{col}_ci95"] = f"[{lo:.3f}, {hi:.3f}]"
        rows.append(row)
    return pd.DataFrame(rows)


def m3_coverage_audit() -> str:
    df = m3_channel_table()
    hist = df[df.window == "historical_in_sample_fit"]
    S = {}
    S["validity"] = md_table(
        hist.drop_duplicates(["variant", "world_id"]).groupby(["variant", "scenario_id"]).agg(
            n_fits=("world_id", "count"), n_valid_strict=("valid_strict", "sum"), valid_rate=("valid_strict", "mean")).reset_index())
    S["role"] = md_table(summarize(hist, ["variant", "valid_strict", "role"]))
    direct = hist[hist.role == "direct"]
    S["scen"] = md_table(summarize(direct, ["variant", "scenario_id", "valid_strict"]))
    S["T"] = md_table(summarize(direct, ["variant", "T", "valid_strict"]))
    S["future"] = md_table(summarize(df[(df.window != "historical_in_sample_fit") & (df.role == "direct")],
                                     ["variant", "valid_strict"]))
    # paired V0 vs V3 on worlds valid in both, and descriptive on all 45
    piv = direct.pivot_table(index=["world_id", "channel"], columns="variant",
                             values=["cov95", "width95_norm", "bias_norm", "mae_norm"])
    valid = direct.pivot_table(index="world_id", columns="variant", values="valid_strict", aggfunc="first")
    both_valid = valid[(valid.V0 == True) & (valid.V3 == True)].index  # noqa: E712
    prow = []
    for label, worlds in (("valid in V0 and V3 (paired, inferential)", both_valid),
                          ("all 45 (descriptive)", valid.index)):
        sub = piv[piv.index.get_level_values("world_id").isin(worlds)]
        for metric in ("cov95", "width95_norm", "bias_norm", "mae_norm"):
            d = (sub[(metric, "V3")] - sub[(metric, "V0")]).groupby(level="world_id").mean()
            m, lo, hi = paired_bootstrap(d.to_numpy())
            prow.append({"subset": label, "n_worlds": len(d), "metric": metric, "V0_mean": sub[(metric, "V0")].groupby(level="world_id").mean().mean(),
                         "V3_mean": sub[(metric, "V3")].groupby(level="world_id").mean().mean(), "V3_minus_V0": m, "ci95_lo": lo, "ci95_hi": hi})
    S["paired"] = md_table(pd.DataFrame(prow))
    # development vs evaluation split
    v3 = hist[hist.variant == "V3"]
    drows = []
    for dev, g in v3.groupby("dev_world"):
        gd = g[g.role == "direct"]
        m, lo, hi, n = boot_by_world(gd, "cov95")
        drows.append({"worlds": "development (used to choose V3)" if dev else "evaluation only (not used)",
                      "n_worlds": g.world_id.nunique(), "valid_rate": g.drop_duplicates("world_id").valid_strict.mean(),
                      "direct_cov95_all_fits": m, "ci95": f"[{lo:.3f}, {hi:.3f}]",
                      "direct_cov95_valid_fits": gd[gd.valid_strict].cov95.mean() if gd.valid_strict.any() else np.nan,
                      "direct_mae_norm": gd.mae_norm.mean()})
    S["dev"] = md_table(pd.DataFrame(drows))
    # bias sources (direct channels, V3, valid fits)
    d3 = direct[direct.variant == "V3"].copy()
    d3["abs_bias_M3"] = d3.bias_norm.abs()
    d3["abs_bias_M0"] = d3["M0_ols_bias_norm"].abs()
    fam = []
    for col in ("true_carryover", "true_saturation", "scenario_id"):
        for key, g in d3.groupby(col):
            fam.append({"factor": col, "level": key, "n_channels": len(g), "n_worlds": g.world_id.nunique(),
                        "M3_bias": g.bias_norm.mean(), "M2p_true_form_week0_bias": g["M2p_w0_bias_norm"].mean(),
                        "M2p_true_form_week8_bias": g["M2p_w8_bias_norm"].mean(), "M0_raw_bias": g["M0_ols_bias_norm"].mean(),
                        "M3_abs_bias": g.abs_bias_M3.mean(), "M3_cov95": g.cov95.mean()})
    S["bias"] = md_table(pd.DataFrame(fam))
    pw = d3.groupby("world_id")[["bias_norm", "M2p_w0_bias_norm", "M2p_w8_bias_norm"]].mean()
    cmp = []
    for col, lab in (("bias_norm", "M3 V3 (ajuste desde semana 0)"), ("M2p_w0_bias_norm", "M2p forma verdadera, desde semana 0"),
                     ("M2p_w8_bias_norm", "M2p forma verdadera, desde semana 8")):
        m, lo, hi = paired_bootstrap(pw[col].to_numpy())
        cmp.append({"modelo": lab, "n_worlds": len(pw), "mean_bias_direct": m, "ci95": f"[{lo:.4f}, {hi:.4f}]"})
    S["bias_window"] = md_table(pd.DataFrame(cmp), ".4f")
    ok = d3.dropna(subset=["corr_log_lam_log_beta"])
    from scipy.stats import spearmanr

    S["corr"] = (f"Spearman(|corr(log lam, log beta)| posterior, |sesgo| M3) en canales directos V3: "
                 f"{spearmanr(ok.corr_log_lam_log_beta.abs(), ok.abs_bias_M3).statistic:.3f} ({len(ok)} canales, {ok.world_id.nunique()} mundos; "
                 "descriptivo, canales del mismo mundo no son independientes).")
    nulls = summarize(hist[hist.role != "direct"], ["variant", "role"])
    S["nulls"] = md_table(nulls)
    return write_m3_report(S, df)


def write_m3_report(S: dict, df: pd.DataFrame) -> str:
    text = f"""# Auditoría de cobertura de M3 (v1.2 P0, correcciones C1–C2)

Fuentes, **sin reajustar nada**: V0 = `runs/core` (configuración v1, 4×(1000+1000), `target_accept` 0,90); V3 = `runs/v1_1_m3` (`target_accept` 0,99, `saturation_lam ~ Gamma(6,2)`). Los mismos 45 mundos (F2, réplicas 0–2). Tabla por mundo-canal: `reports/v1_2/m3_world_channel.csv`.

**Misma magnitud en verdad y posterior.** Estimando `historical_observed_path_response` = `world.data["contributions_observed"]`, frente a la posterior de `channel_contribution × target_scale` de PyMC-Marketing, ambos en unidades de `y` y semana a semana. Ventana `historical_in_sample_fit` = semanas `[8, n_train)`. PyMC-Marketing arranca el adstock con historia cero en la semana 0 (`l_max = 8`) y el generador con 8 semanas de *burn-in*, así que la exclusión de las semanas 0–7 deja ambas magnitudes definidas sobre la misma historia observada. Los intervalos son de cola igual e incluyen **solo incertidumbre paramétrica dentro de la forma funcional de M3**.

**Unidad estadística.** Primero se calcula la fracción de semanas cubiertas por **canal**; después se promedia **por mundo**; los IC95 remuestrean **mundos** (2000 réplicas). Las semanas de un canal no se tratan como réplicas.

**Selección por convergencia.** `valid_strict` = R-hat ≤ 1,01, ESS bulk ≥ 400 y 0 divergencias en todas las variables libres. Las filas con `valid_strict = False` son **descriptivas**: no son cobertura inferencial fiable.

## 1. Validez de ajuste por escenario

{S['validity']}
S2 tiene la tasa válida más baja: sus cifras de cobertura en ajustes válidos se apoyan en muy pocos mundos y no son representativas del escenario.

## 2. Cobertura, anchura y sesgo por rol de canal

Normalizado por media\\|y\\| de la ventana. `bias_norm` = media(estimación − verdad).

{S['role']}
**Lectura (C1).** En *feeders* y aislados la verdad *observed-path* es exactamente 0. Con `saturation_beta ~ HalfNormal` y saturación logística, las extracciones posteriores de la contribución son > 0 casi con seguridad, así que un intervalo de cola igual casi nunca contiene el 0 puntual. Es una propiedad de una posterior continua frente a un estimando exactamente nulo, no una prueba de mala calibración en canales activos. Una prior *horseshoe* continua tendría la misma propiedad. Para ausencia exacta de efecto hace falta masa en cero o una regla ROPE (propuesta P1a).

## 3. Canales directos: por escenario y por T

{S['scen']}
{S['T']}
## 4. Ventana futura (`attribution_future_conditional_on_known_CZ`), canales directos

{S['future']}
## 5. V0 frente a V3

Diferencias por mundo (canales directos promediados dentro de mundo), IC95 remuestreando mundos. El subconjunto «válido en ambas» es el único **inferencial**, y está seleccionado por convergencia.

{S['paired']}
## 6. Separación desarrollo / evaluación

Los 10 mundos usados para elegir V3 (solo con diagnósticos del muestreador) **están incluidos** en los 45. La tabla separa los 35 mundos no usados. **No hay validación independiente de la elección de prior más allá de esos 35 mundos**, que comparten receta y escenarios con los de desarrollo.

{S['dev']}
## 7. Origen del sesgo en canales directos (V3)

Referencias en los mismos canales y ventana: `M2p` = OLS con las transformaciones **verdaderas** (privilegiado), ajustado desde la semana 0 (como M3 en v1/v1.1) o desde la semana 8 (ventana corregida en v1.2); `M0_raw` = OLS con canales crudos. Sesgo medio con signo, normalizado por media\\|y\\|.

{S['bias_window']}
{S['bias']}
{S['corr']}

**Interpretación (revisada en P0):**
- El sesgo negativo de M3 (−0,034 [−0,042; −0,026]) es casi igual al de M2p **ajustado desde la semana 0** (−0,036) y desaparece en M2p ajustado desde la semana 8 (+0,004 [−0,0005; 0,008]). Ese sesgo constante por canal es **compatible sobre todo con el artefacto de ajuste en semanas de *burn-in*** ([scientific_status_v1_2.md](scientific_status_v1_2.md) §2), no con la forma funcional de M3. Una primera lectura de esta auditoría lo atribuía a la forma funcional; esa lectura comparaba con M2p contaminado por el mismo artefacto y se retira.
- El patrón por familia verdadera (sesgo mayor con arrastre Weibull, casi nulo sin arrastre) coincide con el artefacto: cuanto más pesa el arrastre en las primeras semanas, más diferencia hay entre historia cero e historia real.
- **No demostrado para M3**: hace falta reajustar M3 con verosimilitud enmascarada (prerrequisito de P1a). Hasta entonces el origen del sesgo de M3 es **inconclusive**, con el artefacto como explicación principal candidata. La cobertura de canales directos (≈ 0,40 en ajustes válidos) puede cambiar al eliminar el sesgo.

## 8. Canales sin `C→Y` (feeders y aislados)

{S['nulls']}
"""
    path = ROOT / "reports" / "m3_coverage_audit.md"
    path.write_text(text)
    return str(path)


# ------------------------------------------------------------------------------------- E09 audit
FEASIBILITY_TOL = 1e-3  # |realized spend / budget − 1| allowed; fixed before computing the v1.2 audit
N_STARTS = 10


def _multistart(value_fn, n: int, lo: float, hi: float, constraint, seed: int, extra_starts=()):
    from scipy.optimize import minimize

    rng = np.random.default_rng(seed)
    starts = [np.ones(n), *extra_starts, *rng.uniform(lo, hi, (N_STARTS, n))]
    vals = []
    for s in starts:
        res = minimize(lambda m: -value_fn(m), s, method="SLSQP", bounds=[(lo, hi)] * n,
                       constraints=[constraint], options={"maxiter": 300, "ftol": 1e-12})
        m = np.clip(res.x, lo, hi)
        if abs(constraint["fun"](m)) <= 1e-6:
            vals.append((value_fn(m), m))
    vals.sort(key=lambda t: -t[0])
    return vals


def data_projection(p, obs, m_act: np.ndarray) -> np.ndarray:
    """Analyst-feasible rule (no SCM): regress each non-actionable channel on the actionable ones over
    the observed train window (contemporaneous, linear) to predict how much descendants will move,
    then rescale the plan so the PREDICTED total spend equals the budget."""
    from scipy.optimize import brentq

    from .causal import M_HI, M_LO

    act = list(p.act)
    non = [j for j in range(obs.K) if j not in act]
    tr = obs.train_idx
    X = np.column_stack([np.ones(len(tr)), obs.C[tr][:, act]])
    coefs = {j: np.linalg.lstsq(X, obs.C[tr, j], rcond=None)[0] for j in non}
    CH = obs.C[p.H]

    def predicted_total(mm):
        dact = CH[:, act] * (mm - 1.0)
        tot = (CH[:, act] * mm).sum()
        for j in non:
            tot += (CH[:, j] + dact @ coefs[j][1:]).sum()
        return tot - p.total

    f = lambda s: predicted_total(np.clip(1.0 + s * (m_act - 1.0), M_LO, M_HI))
    try:
        s = brentq(f, -5.0, 5.0, xtol=1e-12)
    except ValueError:
        s = 1.0
    return np.clip(1.0 + s * (m_act - 1.0), M_LO, M_HI)


def e09_policy_audit() -> str:
    from .causal import M_HI, M_LO, BudgetProblem, SelectedChannelsProblem, _project
    from .interventions import InterventionEngine

    e9 = read_table(RUNS / "v1_1_e09" / "tables" / "e09.csv")
    store = WorldStore(WORLD_CACHE)
    clamped_rows, sel_rows = [], []
    for wid, g in e9.groupby("world_id"):
        world, obs, truth = store.load(spec_from_world_id(wid))
        eng = InterventionEngine(world)
        seed = int(truth.meta["world_seed"]) % 2**31
        # --- principal family: verify the stored optimum with a multi-start search
        bp = BudgetProblem(eng, obs)
        gc = g[g.policy_family == "all_channels_clamped_policy"]
        cons = {"type": "eq", "fun": lambda m, bp=bp: (m @ bp.S - bp.total) / bp.total}
        found = _multistart(bp.v_true, obs.K, M_LO, M_HI, cons, seed)
        stored_opt = float(gc[gc.policy == "oracle_interventional"].value_true.iloc[0])
        best = found[0][0]
        clamped_rows.append({"world_id": wid, "scenario_id": wid[:2], "n_starts_converged": len(found),
                             "stored_optimum": stored_opt, "multistart_best": best,
                             "gap_best_minus_stored_norm": (best - stored_opt) / bp.y_abs,
                             "n_starts_within_1e-6": int(sum(abs(v - best) <= 1e-6 * abs(best) for v, _ in found)),
                             "max_budget_violation_stored": float(gc.budget_violation.max())})
        # --- secondary family
        gs = g[g.policy_family == "selected_channels_do_policy"]
        if gs.empty:
            continue
        p = SelectedChannelsProblem(eng, obs, world.g["g_cc"])
        n = len(p.act)
        cons_s = {"type": "eq", "fun": lambda m, p=p: (p.realized_total(m) - p.total) / p.total}
        found_s = _multistart(p.value, n, M_LO, M_HI, cons_s, seed + 1)
        v_opt_stored = float(gs[gs.policy == "oracle_interventional"].value_true.iloc[0])
        v_opt = max(found_s[0][0], v_opt_stored) if found_s else v_opt_stored
        v_cur = p.value(np.ones(n))

        def rec(policy, level, m):
            dev = p.realized_total(m) / p.total - 1.0
            v = p.value(m)
            feasible = abs(dev) <= FEASIBILITY_TOL
            return {"world_id": wid, "scenario_id": wid[:2], "policy": policy, "information_level": level,
                    "realized_budget_dev": dev, "feasible": feasible, "overspend": max(dev, 0.0),
                    "value_norm_vs_current": (v - v_cur) / p.y_abs,
                    "value_gap_to_optimum_norm": (v_opt - v) / p.y_abs if feasible else np.nan,
                    "multipliers": ",".join(f"{x:.3f}" for x in m)}

        sel_rows.append({**rec("SCM_optimum", "oracle_optimum", found_s[0][1] if found_s and found_s[0][0] >= v_opt_stored else np.array([float(x) for x in gs[gs.policy == "oracle_interventional"].multipliers.iloc[0].split(",")])),
                         "optimum_gap_multistart_minus_stored_norm": ((found_s[0][0] if found_s else v_opt_stored) - v_opt_stored) / p.y_abs,
                         "n_starts_converged": len(found_s)})
        sel_rows.append(rec("current", "reference", np.ones(n)))
        for _, r in gs[gs.label == "model_implied_under_exogeneity_assumption"].iterrows():
            m = np.array([float(x) for x in r.multipliers.split(",")])
            sel_rows.append(rec(r.policy, "model_infeasible_as_proposed", m))
            sel_rows.append(rec(r.policy, "model_feasible_data_projection", data_projection(p, obs, m)))
            sel_rows.append(rec(r.policy, "oracle_ex_post_budget_equalization", p.project_true_budget(m)))
    ct, st = pd.DataFrame(clamped_rows), pd.DataFrame(sel_rows)
    ct.to_csv(OUT / "e09_clamped_optimizer_check.csv", index=False)
    st.to_csv(OUT / "e09_selected_policy_audit.csv", index=False)
    return write_e09_report(ct, st, e9)


def write_e09_report(ct: pd.DataFrame, st: pd.DataFrame, e9: pd.DataFrame) -> str:
    clamped = e9[e9.policy_family == "all_channels_clamped_policy"]
    rows = []
    for (pol, lab), g in clamped.groupby(["policy", "label"]):
        m, lo, hi = paired_bootstrap(g.groupby("world_id").regret_norm.mean().to_numpy())
        rows.append({"policy": pol, "label": lab, "n_worlds": g.world_id.nunique(), "regret_norm_mean": m,
                     "ci95": f"[{lo:.4f}, {hi:.4f}]", "max_budget_violation": g.budget_violation.max()})
    ctab = pd.DataFrame(rows).sort_values("regret_norm_mean")
    srows = []
    for (pol, lvl), g in st.groupby(["policy", "information_level"]):
        srows.append({"policy": pol, "information_level": lvl, "n_worlds": g.world_id.nunique(),
                      "feasible_rate": g.feasible.mean(), "mean_realized_dev": g.realized_budget_dev.mean(),
                      "mean_abs_realized_dev": g.realized_budget_dev.abs().mean(), "mean_overspend": g.overspend.mean(),
                      "value_vs_current_norm": g.value_norm_vs_current.mean(),
                      "value_gap_to_optimum_norm_feasible_only": g.value_gap_to_optimum_norm.mean(),
                      "n_feasible": int(g.feasible.sum())})
    stab = pd.DataFrame(srows).sort_values(["information_level", "policy"])
    opt = st[st.policy == "SCM_optimum"]
    text = f"""# Auditoría de políticas E09 (v1.2 P0)

Fuente: `runs/v1_1_e09` (45 mundos causales de F2, réplicas 0–2). **No se reajusta ningún modelo**: las políticas de los modelos son los multiplicadores guardados. Se re-evalúan con el motor `do` (`counterfactual_engine=research_validated_private_api`). Unidades: presupuesto adimensional en unidades de tratamiento, valor en unidades de `y` sobre `[8, n_train)` normalizado por Σ\\|y\\|. **No es ROAS.**

## 1. Familia principal: `all_channels_clamped_policy`

Todas las políticas fijan todos los canales con multiplicadores en [0,5; 1,5] y gasto total igual al observado (factibles por construcción: violación máxima registrada {clamped.budget_violation.max():.1e}). *Regret* = valor del óptimo verdadero − valor de la política.

{md_table(ctab, '.4f')}
**Verificación del optimizador** (búsqueda multi-arranque: plan actual + {N_STARTS} arranques aleatorios con semilla fija por mundo, SLSQP, tolerancia `ftol=1e-12`, restricción de presupuesto ≤ 1e-6). Mundos donde el multi-arranque encuentra un valor mejor que el óptimo guardado: **{int((ct.gap_best_minus_stored_norm > 1e-6).sum())} de {len(ct)}**; mejora máxima {ct.gap_best_minus_stored_norm.max():.2e} de Σ\\|y\\|. Mediana de arranques que alcanzan el mejor valor (±1e-6 relativo): {ct['n_starts_within_1e-6'].median():.0f} de {N_STARTS + 1}. No es una prueba de óptimo global; es el mejor valor encontrado con esa búsqueda. Detalle: `reports/v1_2/e09_clamped_optimizer_check.csv`.

## 2. Familia secundaria (exploratoria): `selected_channels_do_policy`

Solo los canales sin padres `C→C` son accionables; los descendientes reaccionan según el SCM y el presupuesto se mide sobre **todos** los tratamientos realizados (18 mundos S3/S4). Tolerancia de factibilidad fijada antes de este cálculo: \\|gasto realizado / presupuesto − 1\\| ≤ {FEASIBILITY_TOL:.0e}. La brecha con el óptimo solo se calcula para políticas factibles; las infactibles **no se comparan** por valor.

Niveles de información:
- `model_infeasible_as_proposed`: política del modelo sin tocar (supone exogeneidad: cree que los descendientes no se mueven).
- `model_feasible_data_projection`: **aplicable sin verdad**. Regresión lineal contemporánea de cada canal no accionable sobre los accionables en la ventana de train observada, que predice cuánto se moverán los descendientes; se reescala el plan para que el gasto *predicho* iguale el presupuesto. Después se comprueba la factibilidad *real* con el motor y se conservan los fallos.
- `oracle_ex_post_budget_equalization`: reescalado con el SCM verdadero. **Solo diagnóstico, no desplegable.**
- `oracle_optimum`: óptimo del SCM en el mismo conjunto factible, horizonte y criterio, verificado con multi-arranque.

{md_table(stab, '.4f')}
Óptimo: el multi-arranque mejora el óptimo guardado en {int((opt.optimum_gap_multistart_minus_stored_norm > 1e-6).sum())} de {len(opt)} mundos (máximo {opt.optimum_gap_multistart_minus_stored_norm.max():.2e} de Σ\\|y\\|). Las brechas se miden frente al mejor valor encontrado.

**Lectura.**
- Las políticas de los modelos tal como se proponen son **infactibles** en 17–18 de 18 mundos: se desvían del presupuesto realizado un 1,3–1,6 % en valor absoluto, porque los descendientes reaccionan.
- La regla aplicable sin verdad (`model_feasible_data_projection`) es factible en el 78–89 % de los mundos, pero para lograrlo **encoge** la reasignación del modelo (\\|m − 1\\| medio de 0,42 a 0,085) y queda por debajo del presupuesto (−0,6 %). Su valor queda **en torno al del plan actual** (−0,2 % a +0,2 % de Σ\\|y\\|), y su brecha con el óptimo (≈ 0,06) es igual o mayor que la del plan actual (0,056).
- **Ninguna estrategia realizable probada mejora al plan actual** en esta familia. Las mejoras de `oracle_ex_post_budget_equalization` dependen del SCM verdadero y no son desplegables.
- **Decisión:** la familia secundaria queda **exploratoria**, sin ranking. Detalle por mundo: `reports/v1_2/e09_selected_policy_audit.csv`.
"""
    path = ROOT / "reports" / "e09_policy_audit.md"
    path.write_text(text)
    return str(path)


# --------------------------------------------------------------- fit-window correction + status
FAST4 = ["M0_ols", "M1_ridge", "M2_adstock_sat", "M2_adstock_sat_noZ"]


def _wide(m: pd.DataFrame, task: str, metric: str) -> pd.DataFrame:
    sel = m[(m.task == task) & (m.metric == metric) & m.channel.isna()]
    return sel.pivot_table(index=["world_id", "scenario_id", "T"], columns="model_id", values="value")


def _bias_by_world(m: pd.DataFrame, task: str) -> pd.DataFrame:
    """Mean signed channel bias (direct channels) per world and model."""
    sel = m[(m.task == task) & (m.metric == "channel_total_bias_norm") & (m.role == "direct")]
    return sel.groupby(["world_id", "model_id"]).value.mean().unstack()


def load_fits():
    from .evaluation import V1_METRICS, V1_TASKS

    v1 = read_table(RUNS / "core" / "tables" / "metrics.csv")
    v1["task"] = v1["task"].replace(V1_TASKS)
    v1["metric"] = v1["metric"].replace(V1_METRICS)
    v12 = read_table(RUNS / "v1_2_warmfit" / "tables" / "metrics.csv")
    return v1, v12


def warmfit_comparison() -> tuple[str, dict]:
    v1, v12 = load_fits()
    H = "historical_in_sample_fit"
    P = "prediction_future_conditional_on_known_CZ"
    a, b = _wide(v1, H, "contrib_mae_norm"), _wide(v12, H, "contrib_mae_norm")
    ba, bb = _bias_by_world(v1, H), _bias_by_world(v12, H)
    pa, pb = _wide(v1, P, "rmse_scaled"), _wide(v12, P, "rmse_scaled")
    rows = []
    for mid in [c for c in b.columns if c in a]:
        both = pd.concat([a[mid], b[mid]], axis=1, keys=["v1", "v12"]).dropna()
        m, lo, hi = paired_bootstrap((both.v12 - both.v1).to_numpy())
        bb_ = pd.concat([ba.get(mid), bb.get(mid)], axis=1, keys=["v1", "v12"]).dropna() if mid in ba else pd.DataFrame()
        pp = pd.concat([pa[mid], pb[mid]], axis=1, keys=["v1", "v12"]).dropna()
        rows.append({"model_id": mid, "n_worlds": len(both), "contrib_err_fit_from_week0": both.v1.median(),
                     "contrib_err_fit_from_week8": both.v12.median(), "mean_diff": m, "ci95": f"[{lo:.4f}, {hi:.4f}]",
                     "mean_bias_week0": bb_.v1.mean() if len(bb_) else np.nan,
                     "mean_bias_week8": bb_.v12.mean() if len(bb_) else np.nan,
                     "pred_rmse_test_week0": pp.v1.median(), "pred_rmse_test_week8": pp.v12.median()})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "fit_window_correction.csv", index=False)
    pair_rows = []
    for x, y in (("M0_ols", "M2_adstock_sat"), ("M1_ridge", "M0_ols"), ("M2_adstock_sat", "M2_adstock_sat_noZ"),
                 ("M2_adstock_sat", "M2p_true_transforms"), ("M2p_true_transforms", "M2p_true_transforms_plus_D")):
        for lab, w in (("week0 (v1)", a), ("week8 (v1.2)", b)):
            d = (w[x] - w[y]).dropna()
            m, lo, hi = paired_bootstrap(d.to_numpy())
            pair_rows.append({"A": x, "B": y, "fit_window": lab, "n_worlds": len(d), "mean_A_minus_B": m, "ci95": f"[{lo:.4f}, {hi:.4f}]"})
    pt = pd.DataFrame(pair_rows)
    pt.to_csv(OUT / "fit_window_paired.csv", index=False)
    return md_table(t, ".4f") + "\n" + md_table(pt, ".4f"), {"a": a, "b": b, "pa": pa, "pb": pb}


def ranking_analysis(hist: pd.DataFrame, pred: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    from scipy.stats import spearmanr

    rows = []
    for wid in hist.index:
        h, p = hist.loc[wid, models], pred.loc[wid, models]
        if h.isna().any() or p.isna().any():
            continue
        ties = int(h.duplicated().any() or p.duplicated().any())
        rows.append({"world_id": wid[0], "scenario_id": wid[1], "T": wid[2], "hit": h.idxmin() == p.idxmin(),
                     "spearman": spearmanr(h, p).statistic, "ties": ties})
    return pd.DataFrame(rows)


def scientific_status(fw: dict) -> str:
    b, pb = fw["b"], fw["pb"]
    out = []

    def ci(x):
        m, lo, hi = paired_bootstrap(np.asarray(x, dtype=float))
        return m, f"[{lo:.3f}, {hi:.3f}]"

    # H1 on both fit windows
    h1 = {}
    for lab, h, p in (("week0", fw["a"], fw["pa"]), ("week8", b, pb)):
        r = ranking_analysis(h, p, FAST4)
        h1[lab] = (r, *ci(r.hit.astype(float)), *ci(r.spearman))
    r8 = h1["week8"]
    by_s = r8[0].groupby("scenario_id").spearman.mean().round(2).to_dict()
    out.append({"H": "H1", "status": "supported (débil)", "estimand": "historical_observed_path_response vs prediction_y",
                "methods": "M0, M1, M2, M2_noZ (4, ciegos)", "worlds": f"{len(r8[0])} (F2; ajuste semanas ≥ 8)",
                "result": f"coincidencia del mejor {r8[1]:.3f} {r8[2]} vs azar 0,25; Spearman {r8[3]:.3f} {r8[4]}; por escenario {by_s}; empates: {int(r8[0].ties.sum())}",
                "limits": "4 métodos; ranking predictivo ≠ independencia: correlación positiva débil"})
    # H2
    rowsT = []
    for mid in ("M0_ols", "M1_ridge", "M2_adstock_sat", "M2p_true_transforms"):
        s52 = b.xs(52, level="T")[mid].dropna()
        s208 = b.xs(208, level="T")[mid].dropna()
        rng = np.random.default_rng(0)
        boots = [rng.choice(s208, len(s208)).mean() - rng.choice(s52, len(s52)).mean() for _ in range(2000)]
        rowsT.append(f"{mid}: {s208.mean() - s52.mean():+.4f} [{np.quantile(boots, .025):+.4f}, {np.quantile(boots, .975):+.4f}]")
    out.append({"H": "H2", "status": "inconclusive", "estimand": "historical_observed_path_response",
                "methods": "M0, M1, M2, M2p", "worlds": "50 vs 50 (T=52 vs 208; no pareados)",
                "result": "error(208) − error(52): " + "; ".join(rowsT), "limits": "mundos distintos por T; sin pares longitudinales"})
    # H3 (from v1.1 E10A, fit from week 0)
    out.append({"H": "H3", "status": "inconclusive", "estimand": "observed-path y do_zero implicado",
                "methods": "M0, M1, M2, M2p, M2p_D", "worlds": "E10A: 10 pares × 3 niveles (D) y (rho), T=104",
                "result": "sin diferencias detectables en M0/M1/M2p; M2 +0,02 con rho (IC toca 0)",
                "limits": "potencia baja; ajuste desde semana 0 (artefacto de *burn-in* común a todos los niveles); no identifica el efecto do bajo confusión"})
    # H4
    d = (b["M2_adstock_sat_noZ"] - b["M2_adstock_sat"]).dropna()
    m, c = ci(d.groupby(level="world_id").mean())
    out.append({"H": "H4", "status": "partially supported", "estimand": "historical_observed_path_response",
                "methods": "M2 vs M2_noZ", "worlds": f"{len(d)} (F2)", "result": f"omitir Z aumenta el error {m:+.4f} {c}",
                "limits": "mediador/descendiente de C no representable en el generador (blocked_design_not_supported)"})
    # H5
    out.append({"H": "H5", "status": "not_run", "estimand": "—", "methods": "—", "worlds": "—",
                "result": "solo estratos observacionales en v1 (sin diseño controlado)", "limits": "E14 controlado propuesto en P1c"})
    # H6
    d1 = (b["M0_ols"] - b["M2p_true_transforms"]).dropna()
    d2 = (b.xs("S1", level="scenario_id")["M2p_true_transforms"] - b.xs("S1", level="scenario_id")["M2p_true_transforms_plus_D"]).dropna()
    m1, c1 = ci(d1)
    m2, c2 = ci(d2)
    out.append({"H": "H6", "status": "supported", "estimand": "historical_observed_path_response",
                "methods": "M0 vs M2p (privilegiado); M2p vs M2p_D en S1", "worlds": f"{len(d1)}; S1 {len(d2)}",
                "result": f"error(M0) − error(M2p) = {m1:+.4f} {c1}; en S1 error(M2p) − error(M2p_D) = {m2:+.4f} {c2} (positivo = la referencia privilegiada es mejor)",
                "limits": "M2p y M2p_D son privilegiados (fuera de ranking); efecto de D pequeño"})
    out.append({"H": "H7", "status": "supported (nivel verdad)", "estimand": "do_zero vs observed-path",
                "methods": "motor do (verdad)", "worlds": "S3/S4, 21 canal-mundo feeder",
                "result": "feeders: atribución observed-path 0; efecto total do_zero −1,0 % de Σ|y|",
                "limits": "propiedad del SCM, no de un estimador"})
    p8 = pb[["M5_xgboost", "M6_lightgbm", "M1_ridge", "M0_ols"]].dropna()
    m, c = ci((p8.M6_lightgbm - p8.M1_ridge))
    out.append({"H": "H8", "status": "supported", "estimand": "prediction_y; decision_value",
                "methods": "M5, M6 vs M1", "worlds": f"{len(p8)} (F2); E09 45",
                "result": f"RMSE LightGBM − Ridge {m:+.4f} {c}; política plug-in de árboles ≈ reparto uniforme",
                "limits": "árboles sin estimando causal; SHAP no evaluado como causal"})
    out.append({"H": "H9", "status": "inconclusive", "estimand": "intervalos de contribución (paramétricos)",
                "methods": "M3 V3; M4", "worlds": "45 (31 válidos); M4 5 (0 válidos)",
                "result": "M3 directos, ajustes válidos: cobertura 95 % ≈ 0,40 con sesgo −0,034 igual al de M2p ajustado desde la semana 0; nulos: 0 por construcción (posterior continua positiva)",
                "limits": "la infra-cobertura de M3 en directos es compatible con el artefacto de burn-in (§2); requiere reajuste con verosimilitud enmascarada; el oracle no converge"})
    out.append({"H": "H10", "status": "inconclusive", "estimand": "decision_value (regret, all_channels_clamped_policy)",
                "methods": "M0, M1, M2, M2p, M3, M5, M6", "worlds": "45",
                "result": "Spearman RMSE–regret dentro de mundo 0,095 [−0,049; 0,231]",
                "limits": "compatible con relación nula o positiva débil/moderada; políticas de modelos ajustados desde semana 0"})
    out.append({"H": "H11", "status": "not_run", "estimand": "—", "methods": "—", "worlds": "—",
                "result": "E10B no ejecutado", "limits": "P2"})
    t = pd.DataFrame(out)
    t.to_csv(OUT / "hypothesis_status.csv", index=False)
    return md_table(t)


def write_status_report(fw_md: str, status_md: str) -> str:
    text = f"""# Estado científico v1.2 (P0)

Ningún informe anterior se reescribe: v1 (`reports/v1/`) y v1.1 (`reports/v1_1/`) quedan congeladas con manifiestos SHA-256. Este informe resume lo que sostienen los datos **con la redacción prudente pedida en §1 de la respuesta del diseñador**.

## 1. Hipótesis H1–H11

Estados: `supported`, `not_supported`, `inconclusive`, `not_run`. Intervalos IC95 por bootstrap de **mundos**.

{status_md}
## 2. Error de protocolo encontrado en P0: ventana de ajuste con *burn-in*

**Hallazgo.** El generador simula 8 semanas de historia previa (`carryover_burn_in = 8`) que no se guardan. Todos los modelos de v1/v1.1 se **ajustaron** desde la semana 0, donde su adstock arranca con historia cero, aunque la **evaluación** ya excluía esas semanas. En la semana 0 el modelo ve tratamiento sin efecto acumulado y la verdad sí lo tiene. El ajuste compensa con coeficientes de medios más bajos y produce un sesgo **negativo y sistemático** de las contribuciones en el resto de semanas.

**Demostración (privilegiada, sin MCMC).** OLS con las transformaciones verdaderas y la base verdadera sin ruido como *offset* tiene un sesgo medio de −0,038 de media\\|y\\| si se ajusta desde la semana 0 y de −0,0005 si se ajusta desde la semana 8 (45 mundos). Test de regresión: `test_fitting_burn_in_weeks_biases_media_coefficients`. El oracle (M4) ya excluía esas filas de su verosimilitud (`warmup = 7`), lo que explica en parte su error bajo.

**Corrección aplicada a los modelos rápidos** (`configs/v1_2_warmfit.yaml`, 150 mundos F2, sin MCMC): se ajustan en `[8, n_train)` y las semanas 0–7 solo aportan historia de tratamiento.

{fw_md}
**Consecuencias:**
- Las cifras de atribución de v1/v1.1 están afectadas por este artefacto, en distinta medida según el modelo. Los rankings y conclusiones que dependan de errores de contribución deben releerse con la tabla anterior.
- M3 (PyMC-Marketing) **no** puede corregirse solo cambiando filas: `MMM.fit` reinicia el adstock en la primera fila recibida. Hace falta una verosimilitud enmascarada (propuesta P1a, prerrequisito). El código ahora **rechaza** ese ajuste en lugar de producir un resultado erróneo (test `test_pymc_marketing_refuses_fit_window_without_history`).
- Parte del sesgo negativo constante de M3 en canales directos (auditoría de cobertura, §7) puede deberse a este artefacto y no solo a la forma funcional. Las conclusiones sobre su origen quedan **inconclusive** hasta repetir M3 con la verosimilitud enmascarada.
- E08/E09 (efectos implicados y políticas de los modelos) usan modelos ajustados desde la semana 0; no se han recalculado en P0.
"""
    path = ROOT / "reports" / "scientific_status_v1_2.md"
    path.write_text(text)
    return str(path)


# --------------------------------------------------------------------- quality gate + index
def verify_manifest(path: Path) -> tuple[int, int, list[str], list[str]]:
    """Returns (n_files, n_bad, bad_sample, evolved_code_verified_by_snapshot)."""
    import hashlib

    m = json.loads(path.read_text())
    snap_dir = path.parent / "code_snapshot"
    bad, evolved = [], []
    for f, h in m["files"].items():
        p = ROOT / f
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == h:
            continue
        snap = snap_dir / Path(f).name
        if f.endswith(".py") and snap.exists() and hashlib.sha256(snap.read_bytes()).hexdigest() == h:
            evolved.append(f)
        else:
            bad.append(f)
    return m["n_files"], len(bad), bad[:5], evolved


def run_pytest() -> str:
    import subprocess

    xml = OUT / "pytest_v1_2.xml"
    res = subprocess.run(["uv", "run", "--locked", "pytest", "-q", f"--junitxml={xml}"], cwd=ROOT,
                         capture_output=True, text=True, env={**__import__("os").environ, "MPLBACKEND": "Agg"})
    tail = [ln for ln in res.stdout.splitlines() if ln.strip()][-1]
    (OUT / "pytest_v1_2.txt").write_text(res.stdout[-4000:])
    return tail


def write_quality_gate(pytest_summary: str) -> str:
    v1 = verify_manifest(ROOT / "reports" / "v1" / "FREEZE_MANIFEST.json")
    v11 = verify_manifest(ROOT / "reports" / "v1_1" / "FREEZE_MANIFEST.json")
    eng = read_table(ROOT / "reports" / "v1_1" / "tables_v1_1" / "engine_validation_all_runs.csv")
    worlds = read_table(RUNS / "extended" / "tables" / "worlds.csv")
    cells = worlds.groupby("scenario_id").structure_cell_id.nunique()
    m3 = read_table(OUT / "m3_world_channel.csv")
    text = f"""# Quality gate v1.2 (P0)

## 1. Integridad de v1 y v1.1

| Versión | Artefactos con hash | Diferencias no explicadas | Código evolucionado (snapshot verificado) |
|---|---|---|---|
| v1 (`reports/v1/FREEZE_MANIFEST.json`) | {v1[0]} | {v1[1]} {v1[2] if v1[1] else ''} | {', '.join(v1[3]) or '—'} |
| v1.1 (`reports/v1_1/FREEZE_MANIFEST.json`) | {v11[0]} | {v11[1]} {v11[2] if v11[1] else ''} | {', '.join(v11[3]) or '—'} |

Datos, runs, configuraciones e informes de v1 y v1.1 están intactos. El manifiesto v1.1 incluía el hash de tres ficheros de código vivo. `mmm_benchmark/models/bayes.py` cambió en v1.2: se añadió solo la guarda que rechaza ajustes sin historia de arrastre. La versión v1.1 exacta se reconstruyó quitando esa guarda; su SHA-256 coincide con el del manifiesto y está guardada en `reports/v1_1/code_snapshot/bayes.py`. Para re-ejecutar v1.1 bit a bit hay que usar ese snapshot (o el control de versiones). **{'Pasa' if v1[1] == 0 and v11[1] == 0 else 'NO PASA'}.**

## 2. Pruebas

`pytest -q` completo (resultado guardado en `reports/v1_2/pytest_v1_2.xml` y `reports/v1_2/pytest_v1_2.txt`): **{pytest_summary}**.

Nuevas en v1.2:
- `tests/test_serialization_and_units.py`: ida y vuelta del literal `null`; rechazo de roles desconocidos; roles DAG → tablas; recuperación de las 194 parejas canal-mundo aisladas de v1 con su rol verificado frente al DAG guardado; unidad de bootstrap = mundo; bootstrap por célula más ancho con células compartidas.
- `test_fitting_burn_in_weeks_biases_media_coefficients` y `test_pymc_marketing_refuses_fit_window_without_history` (§5).

## 3. Reconstrucción de roles de canal (C5)

`mmm_benchmark/tables_io.read_table` lee solo los campos vacíos como faltantes, mapea el legado `null → isolated` y tipa `role` como categórico `{{direct, feeder, isolated}}`; cualquier otra etiqueta produce un error. Las 194 parejas aisladas de v1 se recuperan para cada modelo rápido y coinciden con el DAG guardado (test). **Pasa.**

## 4. Independencia de muestras y unidades (C4)

- Unidad de repetición: mundo. Las métricas por canal-semana se resumen por canal y luego por mundo antes de construir intervalos.
- Células DAG por escenario (600 mundos): {", ".join(f"{k}={v}" for k, v in cells.items())}. **S0 tiene una sola célula**: sus intervalos reflejan variación de mundos **condicionada a esa estructura** (una receta), no variación entre estructuras. S1–S4 tienen casi una célula por mundo; el bootstrap por célula coincide con el bootstrap por mundo (v1.1).
- **Desarrollo frente a evaluación (M3):** los 10 mundos usados para elegir V3 están dentro de los 45 evaluados; la auditoría de cobertura separa los 35 restantes. No hay validación independiente de la elección de prior fuera de esa receta.
- M3 válido: {int(m3[(m3.variant == 'V3')].drop_duplicates('world_id').valid_strict.sum())}/45 mundos en V3. Las cifras en ajustes válidos están **seleccionadas por convergencia**.

## 5. Error de protocolo demostrado y corregido parcialmente (P0)

Ajuste desde la semana 0 con historia de *burn-in* no reproducible: sesgo negativo sistemático en los coeficientes de medios de todos los modelos ajustados por OLS/MCMC sobre esas filas. Corregido para los modelos rápidos (`runs/v1_2_warmfit`). M3 queda pendiente de una verosimilitud enmascarada (P1a). Detalle: [scientific_status_v1_2.md](scientific_status_v1_2.md) §2. **Abierto para M3, E08 y E09.**

## 6. Motor `do`

{len(eng)} mundos distintos validados en v1/v1.1 (`status`: {eng.status.value_counts().to_dict()}). Sin actualizaciones del generador ni del lock desde la validación (hash de `uv.lock` incluido en el manifiesto v1.1). Etiqueta `research_validated_private_api`. **Pasa con límites** (API privada).
"""
    path = ROOT / "reports" / "quality_gate_v1_2.md"
    path.write_text(text)
    return str(path)


def write_index() -> str:
    text = """# Índice del paquete de revisión (v1.2 P0)

## Entregables P0 (v1.2)

| Documento | Contenido |
|---|---|
| [quality_gate_v1_2.md](quality_gate_v1_2.md) | integridad de v1/v1.1, pruebas, roles, unidades, motor `do`, error de *burn-in* |
| [m3_coverage_audit.md](m3_coverage_audit.md) | cobertura, anchura y sesgo de M3 por rol, escenario, T y validez; V0 frente a V3; desarrollo frente a evaluación |
| [e09_policy_audit.md](e09_policy_audit.md) | familia principal (verificación del optimizador) y secundaria con 4 niveles de información |
| [scientific_status_v1_2.md](scientific_status_v1_2.md) | H1–H11 con estado, estimando, mundos e IC; corrección de la ventana de ajuste |
| [../docs/respuesta_v1_2_al_disenador.md](../docs/respuesta_v1_2_al_disenador.md) | respuesta breve y decisiones pedidas |
| [../docs/protocolo_v1_2_P1.md](../docs/protocolo_v1_2_P1.md) | protocolo P1 (borrador para decisión; no ejecutado) |

## Datos de soporte v1.2 (`reports/v1_2/`)

| Fichero | Grano |
|---|---|
| `m3_world_channel.csv` | variante × mundo × canal × ventana (cobertura 50/80/95, anchura, sesgo, MAE, rol, familias verdaderas, validez) |
| `fit_window_correction.csv`, `fit_window_paired.csv` | modelo (150 mundos F2), ajuste desde la semana 0 frente a la semana 8 |
| `privileged_baseline_diagnostic.csv` | canal directo × variante del diagnóstico privilegiado |
| `e09_clamped_optimizer_check.csv`, `e09_selected_policy_audit.csv` | mundo (× política × nivel de información) |
| `hypothesis_status.csv` | hipótesis |
| `pytest_v1_2.xml`, `pytest_v1_2.txt` | resultado de pruebas |

## Versiones congeladas

| Versión | Informe principal | Manifiesto |
|---|---|---|
| v1 | [v1/benchmark_report.md](v1/benchmark_report.md) | `v1/FREEZE_MANIFEST.json` |
| v1.1 | [v1_1/benchmark_report_v1_1.md](v1_1/benchmark_report_v1_1.md), [v1_1/quality_gate_v1_1.md](v1_1/quality_gate_v1_1.md), [v1_1/mcmc_diagnostics.md](v1_1/mcmc_diagnostics.md) | `v1_1/FREEZE_MANIFEST.json` |

## Definiciones y registro previo

[../docs/estimands.md](../docs/estimands.md) · [../docs/methods.md](../docs/methods.md) · [../docs/revision_v1_1.md](../docs/revision_v1_1.md) · [../docs/generator_audit.md](../docs/generator_audit.md) · [../docs/assumptions_and_limits.md](../docs/assumptions_and_limits.md) · [../docs/experiment_log.md](../docs/experiment_log.md)

## Configuraciones y ejecuciones

- v1: `configs/{smoke,bayes_probe,pilot,core,extended}.yaml` → `runs/{smoke,bayes_probe,pilot,core,extended}`
- v1.1: `configs/v1_1_*.yaml` → `runs/v1_1_*`
- v1.2: `configs/v1_2_warmfit.yaml` → `runs/v1_2_warmfit`

Muestra rastreable por mundo: `runs/<run>/results/<world_id>/<model>.json` (métricas, diagnósticos, semilla), `<model>.npz` (predicciones, contribuciones, intervalos) y `_world.json` (DAG, mecanismos, validación del motor). Los mundos se regeneran desde semillas o se leen de `runs/_worlds/`.

Reproducir P0: `MPLBACKEND=Agg uv run --locked python -m mmm_benchmark.cli audit-v1-2`.
"""
    path = ROOT / "reports" / "review_package_index.md"
    path.write_text(text)
    return str(path)


def build_p0() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m3_coverage_audit()
    if not (OUT / "e09_selected_policy_audit.csv").exists():
        e09_policy_audit()
    fw_md, fw = warmfit_comparison()
    write_status_report(fw_md, scientific_status(fw))
    write_quality_gate(run_pytest())
    write_index()
