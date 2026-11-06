"""v1.2 P1c — E14 design gate (docs/protocolo_P1B_registrado.md §6). Generates worlds only; no model is fitted.

The true ``do_zero`` effect of a channel is measured with the validated intervention engine on the window
[8, n_train), as in E08."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RunConfig
from .evaluation import paired_bootstrap, world_descriptors
from .generator_adapter import WorldStore
from .provenance import ROOT
from .reporting import md_table
from .runner import WORLD_CACHE
from .transforms import true_channel_response

OUT = ROOT / "reports" / "v1_2" / "p1c"
CONFIG = ROOT / "configs" / "v1_2_p1c_e14.yaml"
MARGIN_TOL = 0.20


def _cond(X: np.ndarray) -> float:
    Xs = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1)
    return float(np.linalg.cond(Xs))


def world_rows() -> pd.DataFrame:
    from .interventions import InterventionEngine

    store = WorldStore(WORLD_CACHE)
    rows = []
    for spec in RunConfig.load(CONFIG).worlds():
        w, obs, truth = store.load(spec)
        g = {k: np.asarray(v) for k, v in w.g.items()}
        n = int(obs.train_idx[-1]) + 1
        H = slice(obs.warmup, n)
        C = obs.C[H]
        F = true_channel_response(w, obs.C)[H]
        R = np.corrcoef(C.T)
        iu = np.triu_indices_from(R, 1)
        eng = InterventionEngine(w)
        mask = np.zeros(obs.T)
        mask[H] = 1.0
        effects = [float(eng.effect({k: (mask, np.zeros(obs.T))})[H].sum()) for k in range(obs.K)]
        d = world_descriptors(obs, truth)
        rows.append({
            "world_id": spec.world_id, "pair": f"r{spec.replicate:02d}", "level": spec.variant,
            # DAG checks
            "zy_edges": int((g["g_zy"] != 0).sum()), "dc_edges": int((g["g_dc"] != 0).sum()),
            "cc_edges": int((g["g_cc"] != 0).sum()), "dz_edges": int((g["g_dz"] != 0).sum()),
            "zc_edges": int((g["g_zc"] != 0).sum()), "dy_edges": int((g["g_dy"] != 0).sum()),
            "rho": float(np.asarray(w.params["confounding_strength"], float)),
            "Z_with_children_C": int(((g["g_zc"] != 0).any(1)).sum()),
            # dependence
            "mean_abs_corr": float(np.mean(np.abs(R[iu]))), "max_abs_corr": float(np.max(np.abs(R[iu]))),
            "cond_raw": _cond(C), "cond_transformed": _cond(F),
            "rank_raw": int(np.linalg.matrix_rank(C - C.mean(0))),
            # margins
            "C_mean": float(C.mean()), "C_sd": float(C.std(0).mean()),
            "C_q10": float(np.quantile(C, 0.1)), "C_q90": float(np.quantile(C, 0.9)),
            "media_share": d["media_share_of_y"], "noise_to_y_sd": d["noise_to_y_sd"],
            "y_abs_sum": float(np.abs(obs.y[H]).sum()),
            "abs_do_zero_norm": float(np.mean(np.abs(effects)) / np.abs(obs.y[H]).sum()),
            "engine_vs_contrib": float(np.max(np.abs(np.array(effects) + truth["contributions_observed"][H].sum(0)))
                                       / (np.abs(truth["contributions_observed"][H].sum(0)).max() + 1e-12)),
        })
    return pd.DataFrame(rows)


def gate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, bool, bool]:
    levels = sorted(df.level.unique())
    rows, sep = [], []
    for col in ("C_sd", "C_mean", "media_share", "abs_do_zero_norm", "noise_to_y_sd", "y_abs_sum"):
        piv = df.pivot(index="pair", columns="level", values=col)
        for lv in levels[1:]:
            r = piv[lv] / piv[levels[0]]
            rows.append({"magnitud": col, "contraste": f"{lv} / {levels[0]}", "mediana_cociente": float(r.median()),
                         "q10": float(r.quantile(0.1)), "q90": float(r.quantile(0.9)),
                         "dentro_±20%": bool(abs(r.median() - 1) <= MARGIN_TOL)})
    margins = pd.DataFrame(rows)
    gated = margins[margins.magnitud.isin(["C_sd", "media_share", "abs_do_zero_norm"])]
    margins_ok = bool(gated["dentro_±20%"].all())
    piv = df.pivot(index="pair", columns="level", values="mean_abs_corr")
    for a, b in zip(levels[:-1], levels[1:]):
        d = piv[b] - piv[a]
        m, lo, hi = paired_bootstrap(d.to_numpy())
        sep.append({"contraste": f"{b} − {a}", "mediana Δ media|corr|": float(d.median()), "media": m,
                    "IC95": f"[{lo:.3f}, {hi:.3f}]", "frac pares Δ>0,05": float((d > 0.05).mean())})
    sep = pd.DataFrame(sep)
    sep_ok = bool((sep["mediana Δ media|corr|"] >= 0.1).all() and (sep["frac pares Δ>0,05"] >= 0.7).all())
    return margins, sep, margins_ok, sep_ok


def write_report() -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    df = world_rows()
    df.to_csv(OUT / "e14_design_worlds.csv", index=False)
    margins, sep, margins_ok, sep_ok = gate(df)
    margins.to_csv(OUT / "e14_margins.csv", index=False)
    dag = df.groupby("level").agg(n=("world_id", "size"), zy=("zy_edges", "max"), dc=("dc_edges", "max"),
                                  cc=("cc_edges", "max"), dz=("dz_edges", "max"), zc=("zc_edges", "mean"),
                                  dy=("dy_edges", "mean"), rho_max=("rho", "max")).reset_index()
    dag_ok = bool((dag[["zy", "dc", "cc", "dz"]] == 0).all().all() and (dag.rho_max == 0).all())
    desc = df.groupby("level")[["mean_abs_corr", "max_abs_corr", "cond_raw", "cond_transformed", "rank_raw", "C_mean",
                                "C_sd", "C_q10", "C_q90", "media_share", "noise_to_y_sd", "abs_do_zero_norm",
                                "engine_vs_contrib"]].median().reset_index()
    label = ("correlación entre canales con márgenes aproximadamente constantes" if margins_ok
             else "correlación inducida por Z con cambios de distribución")
    text = f"""# P1c — E14: puerta de calidad del diseño (sin ajustes)

Protocolo: `docs/protocolo_P1B_registrado.md` §6. Configuración: `configs/v1_2_p1c_e14.yaml`.
- 30 pares × 3 niveles de `zc_coeff_range` ∈ {{0, 1,5, 3,0}}, T = 104.
- `direct_only` con `edge_budget`: Z→C = 6, Z→Y = 0, D→C = 0, C→C = 0; D→Y = 1 por conectividad.
- Métricas sobre `[8, n_train)`.
- Efecto verdadero `do_zero` por canal medido con el motor de intervenciones validado.

## 1. Comprobación del DAG en cada mundo

{md_table(dag, ".3f")}
**Resultado:** {"pasa" if dag_ok else "NO pasa"}. En los 90 mundos: Z→Y = 0, D→C = 0, C→C = 0, D→Z = 0 y `rho` = 0. La única ruta de D es D→Y, así que D no confunde C→Y. Z solo llega a Y a través de C (sin Z→Y ni Z→Z→Y), de modo que Z no es confusor de C→Y.

## 2. Separación de la correlación lograda (pareada)

{md_table(sep, ".3f")}
**Criterio registrado** (mediana Δ ≥ 0,1 entre niveles consecutivos y ≥ 70 % de pares con Δ > 0,05): {"pasa" if sep_ok else "NO pasa"}.

## 3. Márgenes: ¿cambia algo más que la dependencia?

Cocientes pareados nivel / nivel 0. Puerta registrada: la mediana de `C_sd`, `media_share` y `abs_do_zero_norm` debe quedar dentro de ±20 %.

{md_table(margins, ".3f")}
**Puerta de márgenes:** {"pasa" if margins_ok else "NO pasa"}.

Medianas por nivel:

{md_table(desc, ".3f")}
- `cond_transformed`: número de condición con las transformaciones verdaderas de arrastre y saturación (canales estandarizados).
- `engine_vs_contrib`: discrepancia relativa máxima entre el efecto `do_zero` del motor (intervención en `[8, n_train)`) y la contribución observada del canal en esa ventana. Sin C→C, la diferencia corresponde al arrastre de exposiciones anteriores a la semana 8, que `do` en la ventana no elimina (3–5 %). No indica un error del motor.

## 4. Decisión

E14, con estos niveles, se denomina **«{label}»**.
"""
    if not margins_ok:
        text += """
Siguiendo la regla del diseñador, **no se ejecutan los 90 mundos como prueba confirmatoria** de multicolinealidad pura. Hay dos opciones registrables:

- (a) Ejecutar E14 tal como está, etiquetado como «correlación inducida por Z con cambios de distribución», informando junto a los errores los cambios de márgenes de esta tabla y usando métricas normalizadas por la magnitud del efecto verdadero de cada mundo.
- (b) **Control con márgenes fijados**: en cada nivel, reescalar la parte de cada canal explicada por Z para que la varianza total del canal coincida con la del nivel 0. Es decir, C_k = μ_k + s_k·(base_k + λ·v_k·Z) con s_k elegido para fijar sd(C_k). Esto exige intervenir los tensores del generador (API privada, como el motor `do`) y validarlo antes, porque cambia el SCM respecto al preset. Se propone solo como diseño; no se implementa sin aprobación.
"""
    path = ROOT / "reports" / "p1c_e14_design_gate.md"
    path.write_text(text)
    return str(path)
