"""v1.2 P1B — audit of M2 shape selection (docs/protocolo_P1B_registrado.md §5). No refit, no model change.

Selection inputs (analyst-available): ALPHA_GRID × KAPPA_GRID, coordinate search, temporal validation RMSE on the
last 20 % of the training rows. The SCM truth is used only to diagnose, never to choose."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .audit_v1_2 import spec_from_world_id
from .evaluation import V1_METRICS, V1_TASKS, paired_bootstrap
from .generator_adapter import WorldStore
from .models.linear import ALPHA_GRID, KAPPA_GRID
from .provenance import ROOT
from .reporting import md_table
from .runner import WORLD_CACHE
from .tables_io import read_table

RUNS = ROOT / "runs"
OUT = ROOT / "reports" / "v1_2" / "m2_audit"
FITS = {"legacy_w0": "extended", "corrected_w8": "v1_2_corr_f3"}
MODELS = ("M2_adstock_sat", "M2_adstock_sat_noZ")
H = "historical_in_sample_fit"


def channel_table() -> pd.DataFrame:
    store = WorldStore(WORLD_CACHE)
    bias = {}
    for lab, run in FITS.items():
        m = read_table(RUNS / run / "tables" / "metrics.csv")
        m["task"], m["metric"] = m["task"].replace(V1_TASKS), m["metric"].replace(V1_METRICS)
        sel = m[(m.task == H) & (m.metric == "channel_total_bias_norm") & m.model_id.isin(MODELS)]
        for r in sel.itertuples():
            bias[(lab, r.model_id, r.world_id, int(r.channel))] = r.value
    rows, truth_cache = [], {}
    for lab, run in FITS.items():
        for wdir in sorted((RUNS / run / "results").iterdir()):
            wid = wdir.name
            if wid not in truth_cache:
                w, obs, tr = store.load(spec_from_world_id(wid))
                truth_cache[wid] = (obs.T, tr.channel_roles, tr.meta["carryover"], tr.meta["saturation"],
                                    np.asarray(w.params["carryover_alpha"], float))
            T, roles, carry, sat, alpha_true = truth_cache[wid]
            for mid in MODELS:
                rec = json.loads((wdir / f"{mid}.json").read_text())
                d = rec["diagnostics"]
                for k, (a, km) in enumerate(zip(d["alphas"], d["kappa_mult"])):
                    rows.append({"fit": lab, "model_id": mid, "world_id": wid, "scenario_id": wid[:2], "T": T,
                                 "channel": k, "role": roles[k], "alpha_sel": a,
                                 "kappa_sel": np.inf if km == "linear" else float(km), "val_rmse": d["val_rmse"],
                                 "true_carryover": carry[k], "true_alpha": float(alpha_true[k]) if carry[k] == "geometric" else np.nan,
                                 "true_saturation": sat[k], "bias_norm": bias.get((lab, mid, wid, k), np.nan)})
    df = pd.DataFrame(rows)
    df["linear_sel"] = ~np.isfinite(df.kappa_sel)
    df["n_nonlinear_world"] = df.groupby(["fit", "model_id", "world_id"]).linear_sel.transform(lambda s: int((~s).sum()))
    df["alpha_at_max"] = df.alpha_sel == max(ALPHA_GRID)
    df["kappa_at_min"] = df.kappa_sel == min(KAPPA_GRID)
    return df


def write_report() -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    df = channel_table()
    df.to_csv(OUT / "m2_channel_selection.csv", index=False)
    m2 = df[df.model_id == "M2_adstock_sat"]
    freq_a = (m2.groupby("fit").alpha_sel.value_counts(normalize=True).unstack().round(3).reset_index())
    freq_k = (m2.assign(kappa=m2.kappa_sel.astype(str)).groupby("fit").kappa.value_counts(normalize=True)
              .unstack().round(3).reset_index())
    # paired change of choices w0 -> w8 per (world, channel)
    piv = m2.pivot_table(index=["world_id", "channel"], columns="fit", values=["alpha_sel", "kappa_sel"], aggfunc="first")
    same_a = float((piv[("alpha_sel", "legacy_w0")] == piv[("alpha_sel", "corrected_w8")]).mean())
    same_k = float((piv[("kappa_sel", "legacy_w0")] == piv[("kappa_sel", "corrected_w8")]).mean())
    # choices vs truth (diagnostic only)
    geo = m2[m2.true_carryover == "geometric"]
    vs_truth = geo.groupby("fit").apply(lambda g: pd.Series({
        "n_canales_geom": len(g), "corr_alpha_sel_true": spearmanr(g.alpha_sel, g.true_alpha).statistic,
        "alpha_sel_medio": g.alpha_sel.mean(), "alpha_true_medio": g.true_alpha.mean()}), include_groups=False).reset_index()
    sat_tab = (m2.groupby(["fit", "true_saturation"]).agg(n=("channel", "size"), frac_lineal_elegida=("linear_sel", "mean"),
                                                          kappa_mediano=("kappa_sel", lambda s: np.median(s[np.isfinite(s)]) if np.isfinite(s).any() else np.nan))
               .reset_index())
    # bias of direct channels by selected shape
    direct = m2[m2.role == "direct"]
    by_shape = (direct.assign(forma=np.where(direct.linear_sel, "lineal (κ=∞)", "saturada (κ finito)"),
                              arrastre=np.where(direct.alpha_sel > 0, "α>0", "α=0"))
                .groupby(["fit", "forma", "arrastre"]).agg(n=("bias_norm", "size"), sesgo_medio=("bias_norm", "mean"),
                                                           sesgo_mediano=("bias_norm", "median")).reset_index())
    by_scen = (direct.groupby(["fit", "scenario_id", "T"]).agg(sesgo=("bias_norm", "mean"),
                                                               frac_lineal=("linear_sel", "mean"),
                                                               alpha_medio=("alpha_sel", "mean")).reset_index())
    by_role = m2.groupby(["fit", "role"], observed=True).agg(n=("channel", "size"), sesgo=("bias_norm", "mean"),
                                                             frac_lineal=("linear_sel", "mean"),
                                                             frac_alpha_max=("alpha_at_max", "mean"),
                                                             frac_kappa_min=("kappa_at_min", "mean")).reset_index()
    # does validation fit favour complexity that attributes badly? (world level, within fit)
    wl = m2.groupby(["fit", "world_id"]).agg(val_rmse=("val_rmse", "first"), n_nonlinear=("n_nonlinear_world", "first"),
                                             abs_bias=("bias_norm", lambda s: np.nanmean(np.abs(s))),
                                             T=("T", "first")).reset_index()
    comp = []
    for lab, g in wl.groupby("fit"):
        comp.append({"fit": lab, "n_mundos": len(g),
                     "Spearman(nº canales saturados, |sesgo|)": spearmanr(g.n_nonlinear, g.abs_bias).statistic,
                     "Spearman(val_rmse, |sesgo|)": spearmanr(g.val_rmse, g.abs_bias).statistic,
                     "nº medio canales saturados": g.n_nonlinear.mean()})
    comp = pd.DataFrame(comp)
    # channel-level: bias change w0->w8 split by whether the choice changed
    ch = direct.pivot_table(index=["world_id", "channel"], columns="fit", values=["bias_norm", "kappa_sel", "alpha_sel"], aggfunc="first")
    changed = (ch[("kappa_sel", "legacy_w0")] != ch[("kappa_sel", "corrected_w8")]) | (ch[("alpha_sel", "legacy_w0")] != ch[("alpha_sel", "corrected_w8")])
    dchg = []
    for lab, mask in (("misma forma", ~changed), ("forma distinta", changed)):
        d = (ch[("bias_norm", "corrected_w8")] - ch[("bias_norm", "legacy_w0")])[mask].groupby(level="world_id").mean()
        m, lo, hi = paired_bootstrap(d.to_numpy())
        dchg.append({"canales directos": lab, "n_canales": int(mask.sum()), "n_mundos": len(d), "Δsesgo (w8 − w0)": m,
                     "IC95 mundos": f"[{lo:.4f}, {hi:.4f}]"})
    dchg = pd.DataFrame(dchg)
    text = f"""# Auditoría de la selección de formas de M2 (sin modificar M2)

Protocolo: `docs/protocolo_P1B_registrado.md` §5. Datos: F3, 600 mundos, ajustes `legacy_w0` (`runs/extended`) y `corrected_w8` (`runs/v1_2_corr_f3`). No se reajusta nada.

**Selección (información de analista):**
- adstock geométrico (no normalizado) con `α ∈ {ALPHA_GRID}`;
- saturación `x/(x+κ)` con `κ = κ_mult × media en entrenamiento del canal con adstock`, `κ_mult ∈ {list(KAPPA_GRID)}` (`inf` = lineal);
- búsqueda por coordenadas (2 pasadas) que minimiza el RMSE de validación temporal en el último 20 % de las filas de entrenamiento.

**Adstock entre entrenamiento y test:** se calcula sobre la serie completa de canales, de modo que el test hereda el estado de arrastre del entrenamiento. Los coeficientes se estiman solo con filas de entrenamiento.

La verdad del SCM aparece solo en las columnas de diagnóstico (§3–§5).

## 1. Frecuencia de formas elegidas (M2, todos los canales)

α:

{md_table(freq_a, ".3f")}
κ_mult:

{md_table(freq_k, ".3f")}
Estabilidad de la elección entre `legacy_w0` y `corrected_w8` (mismo canal): α igual en {same_a:.1%} de los canales, κ igual en {same_k:.1%}.

## 2. Por rol y extremos de la rejilla

{md_table(by_role, ".3f")}
## 3. Elección frente a la verdad (solo diagnóstico)

Arrastre geométrico verdadero: correlación de rangos entre el α elegido y el verdadero.

{md_table(vs_truth, ".3f")}
Saturación verdadera frente a la forma elegida:

{md_table(sat_tab, ".3f")}
## 4. Sesgo de contribución directa según la forma elegida

{md_table(by_shape, ".4f")}
Por escenario y T:

{md_table(by_scen, ".4f")}
## 5. ¿Favorece la búsqueda modelos que predicen bien y atribuyen mal?

Correlaciones entre mundos, dentro de cada ajuste:

{md_table(comp, ".3f")}
Cambio del sesgo en directos al corregir la ventana, separando canales cuya forma elegida no cambió de los que sí cambió (bootstrap de mundos):

{md_table(dchg, ".4f")}
Datos por canal: `reports/v1_2/m2_audit/m2_channel_selection.csv`.

## 6. Lectura

1. **La selección es inestable.** Quitar 8 filas iniciales cambia α en {1 - same_a:.0%} de los canales y κ en {1 - same_k:.0%}. Una sola ventana de validación (≈ 20 % de las filas de entrenamiento) discrimina mal entre formas cercanas.
2. **Se usan mucho los extremos de la rejilla**: α = 0,85 y κ_mult = 0,25 (la saturación más fuerte), cada uno en ≈ 30 % de los canales. La rejilla no contiene la región preferida por los datos o la búsqueda compensa una forma con otra.
3. **El α elegido apenas sigue al verdadero** (Spearman ≈ {vs_truth.corr_alpha_sel_true.mean():.2f} en canales geométricos). La forma elegida no es una estimación fiable del mecanismo.
4. **El cambio de signo del sesgo tras la corrección** se concentra en los canales directos con saturación finita y α > 0. Su sesgo medio pasa a positivo con cola larga (media > mediana), y el cambio es mayor donde la forma elegida cambió. En `legacy_w0`, el defecto de inicialización (sesgo negativo) compensaba en parte esta sobreestimación propia de la búsqueda.
5. **No hay un patrón claro de «predice bien y atribuye mal» entre mundos.** El RMSE de validación correlaciona positivamente con |sesgo|: los mundos que se predicen peor también se atribuyen peor. La complejidad elegida correlaciona débilmente con |sesgo|. El problema es de identificación de forma dentro de cada mundo, no de un sesgo sistemático hacia la complejidad.

## 7. Propuesta M2v2 (solo diseño; no ejecutado)

- **Rejilla:** adstock normalizado (pesos con suma 1), para separar el arrastre de la escala del coeficiente; `α ∈ {{0, 0,2, 0,4, 0,6, 0,8}}` y `κ_mult ∈ {{0,5, 1, 2, ∞}}`, sin el extremo 0,25 que domina las elecciones.
- **Selección:** validación temporal con 3 orígenes rodantes dentro del entrenamiento (no una sola ventana), aplicando la regla de un error estándar a favor de la forma más simple (lineal y con α menor).
- **Presupuesto:** las mismas 2 pasadas de coordenadas por canal.
- **Desarrollo:** F2 réplicas 0–2, donde se fija la rejilla y la regla sin mirar la verdad, salvo para este diagnóstico ya hecho.
- **Evaluación:** F3 réplicas 10–39, nunca usadas para decidir. M2 se mantiene publicado como referencia; M2v2 sería un modelo adicional.
"""
    path = ROOT / "reports" / "m2_selection_audit.md"
    path.write_text(text)
    return str(path)
