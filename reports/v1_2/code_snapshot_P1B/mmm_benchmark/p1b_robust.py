"""v1.2 P1B — E10A robustness (docs/protocolo_P1B_registrado.md §4). Reads the 360 existing worlds and runs only.

Channel k is *structurally confounded by D* when some latent D_j has an active edge D_j→C_k (g_dc, w_dc ≠ 0) and an
active edge D_j→Y (g_dy, delta_dy ≠ 0)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RunConfig
from .evaluation import paired_bootstrap
from .generator_adapter import WorldStore
from .p1b import MECH, RUNS
from .provenance import ROOT
from .reporting import md_table
from .revision import cluster_bootstrap
from .runner import WORLD_CACHE
from .tables_io import read_table

OUT = ROOT / "reports" / "v1_2" / "p1b_robust"
BLIND = ("M0_ols", "M1_ridge", "M2_adstock_sat", "M2_adstock_sat_noZ")
PRIV = ("M2p_true_transforms", "M2p_true_transforms_plus_D")
INTERVENTIONS = ("do_zero", "do_reduce_10", "do_increase_10")


def world_table() -> pd.DataFrame:
    store = WorldStore(WORLD_CACHE)
    rows = []
    for mech, (run, _) in MECH.items():
        for spec in RunConfig.load(ROOT / "configs" / f"{run}.yaml").worlds():
            w = store.get(spec)
            g = {k: np.asarray(v) for k, v in w.g.items()}
            wdc, ddy = np.asarray(w.params["w_dc"], float), np.asarray(w.params["delta_dy"], float)
            dc_on, dy_on = (g["g_dc"] != 0) & (wdc != 0), (g["g_dy"] != 0) & (ddy != 0)
            conf = (dc_on & dy_on[:, None]).any(0)
            exposed = ((g["g_dc"] != 0) & (g["g_dy"] != 0)[:, None]).any(0)  # structural: same in all levels
            C = np.asarray(w.data["treatments"], float)
            R = np.corrcoef(C.T)
            iu = np.triu_indices_from(R, 1)
            rows.append({
                "mecanismo": mech, "world_id": spec.world_id, "pair": f"r{spec.replicate:02d}", "level": spec.variant,
                "w_dc_activos": ",".join(f"{v:.2f}" for v in np.unique(wdc[g["g_dc"] != 0])) or "—",
                "delta_dy_activos": ",".join(f"{v:.2f}" for v in np.unique(ddy[g["g_dy"] != 0])) or "—",
                "confounding_strength": float(np.asarray(w.params["confounding_strength"], float)),
                "n_aristas_DC": int((g["g_dc"] != 0).sum()), "n_aristas_DY": int((g["g_dy"] != 0).sum()),
                "n_aristas_ZC": int((g["g_zc"] != 0).sum()), "n_aristas_CC": int((g["g_cc"] != 0).sum()),
                "n_canales_confundidos_D": int(conf.sum()), "confounded_channels": ",".join(map(str, np.flatnonzero(exposed))),
                "mean_abs_channel_corr": float(np.mean(np.abs(R[iu]))),
                "C_sd_media": float(C.std(0).mean()), "C_media": float(C.mean(0).mean()),
            })
    df = pd.DataFrame(rows)
    cells = pd.concat([read_table(RUNS / run / "tables" / "worlds.csv")[["world_id", "structure_cell_id"]]
                       for run, _ in MECH.values()])
    return df.merge(cells, on="world_id", how="left")


def series_changes(wt: pd.DataFrame) -> pd.DataFrame:
    """Resulting series that change across levels (primitive innovations are identical by construction)."""
    store = WorldStore(WORLD_CACHE)
    rows = []
    for mech, (run, _) in MECH.items():
        specs = RunConfig.load(ROOT / "configs" / f"{run}.yaml").worlds()
        by_pair = {}
        for s in specs:
            by_pair.setdefault(s.replicate, []).append(s)
        for rep, ss in by_pair.items():
            ss = sorted(ss, key=lambda s: s.variant)
            ws = [store.get(s) for s in ss]
            base = ws[0]
            for s, w in zip(ss[1:], ws[1:]):
                row = {"mecanismo": mech, "pair": f"r{rep:02d}", "level": s.variant}
                for k in ("treatments", "baseline", "outcome"):
                    a, b = np.asarray(base.data[k], float), np.asarray(w.data[k], float)
                    row[f"{k}_rel_change"] = float(np.mean(np.abs(b - a)) / (np.mean(np.abs(a)) + 1e-12))
                    row[f"{k}_corr_with_level0"] = float(np.mean([np.corrcoef(a[:, j], b[:, j])[0, 1] for j in range(a.shape[1])])
                                                         if a.ndim == 2 else np.corrcoef(a, b)[0, 1])
                row["eps_identicas"] = all(np.array_equal(np.asarray(base.exogenous[k]), np.asarray(w.exogenous[k]))
                                           for k in base.exogenous)
                rows.append(row)
    return pd.DataFrame(rows)


def e08_long(wt: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for mech, (run, _) in MECH.items():
        e = read_table(RUNS / run / "tables" / "e08.csv")
        e = e[(e.role == "direct") & e.intervention.isin(INTERVENTIONS)]
        e["mecanismo"] = mech
        frames.append(e)
    e = pd.concat(frames, ignore_index=True)
    e = e.merge(wt[["world_id", "pair", "level", "confounded_channels", "structure_cell_id"]], on="world_id")
    e["confounded_D"] = [str(int(c)) in str(cc).split(",") for c, cc in zip(e.channel, e.confounded_channels)]
    est = e[e.model_id != "truth_do_engine"].copy()
    est["bias_orig"] = est.delta_est - est.delta_true
    lvl0 = est.groupby("mecanismo")["level"].transform("min")
    ref = est[est.level == lvl0].drop_duplicates("world_id").set_index(["mecanismo", "pair"]).y_abs_sum
    est["y_abs_sum_ref"] = [ref.get((m, p), np.nan) for m, p in zip(est.mecanismo, est.pair)]
    est["bias_norm_own"] = est.bias_orig / est.y_abs_sum
    est["bias_norm_ref"] = est.bias_orig / est.y_abs_sum_ref
    return est


def contrasts(est: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mech, mid, inter), g in est.groupby(["mecanismo", "model_id", "intervention"]):
        levels = sorted(g.level.unique())
        for subset, gg in (("todos los directos", g), ("confundidos por D", g[g.confounded_D]),
                           ("no confundidos por D", g[~g.confounded_D])):
            pw = gg.groupby(["pair", "level"]).agg(delta_true=("delta_true", "mean"), delta_est=("delta_est", "mean"),
                                                   bias_orig=("bias_orig", "mean"), bias_norm_own=("bias_norm_own", "mean"),
                                                   bias_norm_ref=("bias_norm_ref", "mean"),
                                                   cell=("structure_cell_id", "first")).reset_index()
            for lv in levels[1:]:
                a = pw[pw.level == levels[0]].set_index("pair")
                b = pw[pw.level == lv].set_index("pair")
                j = a.join(b, lsuffix="_0", rsuffix="_1", how="inner")
                if j.empty:
                    continue
                row = {"mecanismo": mech, "modelo": mid, "clase": "privileged" if mid in PRIV else "blind",
                       "intervención": inter, "subconjunto": subset, "contraste": f"{lv} − {levels[0]}", "n_pares": len(j),
                       "n_células": j.cell_0.nunique(),
                       "Δtrue_0": j.delta_true_0.mean(), "Δtrue_1": j.delta_true_1.mean(),
                       "Δest_0": j.delta_est_0.mean(), "Δest_1": j.delta_est_1.mean(),
                       "sesgo_orig_0": j.bias_orig_0.mean(), "sesgo_orig_1": j.bias_orig_1.mean()}
                for col in ("bias_orig", "bias_norm_own", "bias_norm_ref"):
                    m, lo, hi = paired_bootstrap((j[f"{col}_1"] - j[f"{col}_0"]).to_numpy())
                    row[f"Δsesgo_{col}"] = m
                    row[f"IC95_{col}"] = f"[{lo:.4g}, {hi:.4g}]"
                m, lo, hi, nc = cluster_bootstrap(j.bias_norm_ref_1 - j.bias_norm_ref_0, j.cell_0)
                row["IC95_células_norm_ref"] = f"[{lo:.4g}, {hi:.4g}]" if np.isfinite(lo) else f"— ({nc} células)"
                row["Δsesgo/|Δtrue_0|"] = row["Δsesgo_bias_orig"] / abs(row["Δtrue_0"])
                rows.append(row)
    return pd.DataFrame(rows)


def correlation_by_world(wt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mech, g in wt.groupby("mecanismo"):
        levels = sorted(g.level.unique())
        piv = g.pivot(index="pair", columns="level", values="mean_abs_channel_corr")
        cells = g.drop_duplicates("pair").set_index("pair").structure_cell_id
        for lv in levels[1:]:
            d = piv[lv] - piv[levels[0]]
            m, lo, hi = paired_bootstrap(d.to_numpy())
            mc, loc, hic, nc = cluster_bootstrap(d, cells.reindex(d.index))
            rows.append({"mecanismo": mech, "contraste": f"{lv} − {levels[0]}", "n_pares": d.notna().sum(),
                         "Δ media|corr| canales": m, "IC95 mundos": f"[{lo:.3f}, {hi:.3f}]",
                         "IC95 células": f"[{loc:.3f}, {hic:.3f}]" if np.isfinite(loc) else f"— ({nc} células)",
                         "frac pares Δ>0": float((d > 0).mean()), "rango Δ": f"[{d.min():.3f}, {d.max():.3f}]"})
    return pd.DataFrame(rows)


def write_report() -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    wt = world_table()
    wt.to_csv(OUT / "world_parameters.csv", index=False)
    sc = series_changes(wt)
    sc.to_csv(OUT / "series_changes.csv", index=False)
    est = e08_long(wt)
    est.to_csv(OUT / "e08_direct_long.csv", index=False)
    con = contrasts(est)
    con.to_csv(OUT / "contrasts.csv", index=False)
    cor = correlation_by_world(wt)
    cor.to_csv(OUT / "correlation_by_world.csv", index=False)
    par = (wt.groupby(["mecanismo", "level"])
             .agg(n_mundos=("world_id", "size"), w_dc=("w_dc_activos", lambda s: ",".join(sorted(set(s)))),
                  delta_dy=("delta_dy_activos", lambda s: ",".join(sorted(set(s)))),
                  rho=("confounding_strength", "mean"), aristas_DC=("n_aristas_DC", "mean"),
                  aristas_DY=("n_aristas_DY", "mean"), aristas_ZC=("n_aristas_ZC", "mean"),
                  aristas_CC=("n_aristas_CC", "mean"), canales_confundidos_D=("n_canales_confundidos_D", "mean"),
                  células_DAG=("structure_cell_id", "nunique"), media_abs_corr=("mean_abs_channel_corr", "mean"),
                  sd_canal=("C_sd_media", "mean")).reset_index())
    ser = sc.groupby(["mecanismo", "level"]).agg(
        n=("pair", "size"), eps_identicas=("eps_identicas", "all"),
        **{f"{k}_cambio_rel": (f"{k}_rel_change", "mean") for k in ("treatments", "baseline", "outcome")},
        **{f"{k}_corr_nivel0": (f"{k}_corr_with_level0", "mean") for k in ("treatments", "baseline", "outcome")}).reset_index()
    key_models = [*BLIND[:3], *PRIV]
    main = con[(con.subconjunto == "todos los directos") & con.modelo.isin(key_models)]
    split = con[(con.subconjunto != "todos los directos") & (con.intervención == "do_zero") & con.modelo.isin(key_models)]
    cols = ["mecanismo", "clase", "modelo", "intervención", "contraste", "n_pares", "n_células", "Δtrue_0", "Δtrue_1",
            "Δest_0", "Δest_1", "Δsesgo_bias_orig", "IC95_bias_orig", "Δsesgo_bias_norm_own", "IC95_bias_norm_own",
            "Δsesgo_bias_norm_ref", "IC95_bias_norm_ref", "IC95_células_norm_ref", "Δsesgo/|Δtrue_0|"]
    text = f"""# P1B — E10A: robustez y cierre analítico (sin nuevos ajustes)

Protocolo: `docs/protocolo_P1B_registrado.md` §4. Datos: los 360 mundos y 2 880 ajustes de `runs/v1_2_p1b_e10a_{{dc,dy,rho}}`, sin reajustar. Ventana `[8, n_train)`. Verdad: contrafactual `do` de cada mundo.

Clases de modelo:
- `blind`: M0, M1, M2, M2_noZ.
- `privileged`: M2p (transformaciones verdaderas) y M2p_D (además observa D).

Lo que hace M2p_D no prueba nada sobre lo que puede identificar un MMM ciego.

## 1. Configuración fijada por mecanismo (extraída de cada mundo)

{md_table(par, ".3f")}
- `w_dc`, `delta_dy`: valores activos en el mundo (aristas presentes).
- `canales_confundidos_D`: número medio de canales k con algún D_j→C_k **y** D_j→Y **activos** (coeficiente ≠ 0).
- En §4, «confundidos por D» se define con el **patrón estructural** del DAG (aristas presentes, igual en todos los niveles del par): son los canales con una ruta C_k←D_j→Y que el mecanismo activa al subir de nivel.

Lecturas:
- **dc:** `delta_dy = 0,30` fijo; en `p1bdc000` no hay ninguna D→C activa, así que ningún canal está confundido.
- **dy:** `w_dc = 0,30` fijo; en `p1bdy000`, D→Y = 0, así que tampoco hay canales confundidos.
- **rho:** `direct_only` no tiene aristas D→C; la dependencia entre tratamiento y base viene solo de `rho`.

## 2. Innovaciones primitivas frente a series resultantes

Las innovaciones primitivas (`eps_*`) son idénticas entre niveles en todos los pares (columna `eps_identicas`). Lo que cambia son las series que se derivan de ellas:

{md_table(ser, ".3f")}
- **dc y rho** cambian los **tratamientos** realizados.
- **dy** deja intactos los tratamientos y solo cambia la base y `Y`.

Ningún factor ajeno al mecanismo cambia: el DAG y las innovaciones son iguales (test `test_e10a_mechanisms_are_paired`).

## 3. Contrastes pareados: efecto verdadero, estimación y sesgo

Medias por par, promediadas sobre los canales directos de cada mundo; contraste = nivel alto − nivel 0.
- `bias_orig`: unidades de `Y` (suma sobre `[8, n_train)`).
- `bias_norm_own`: dividido por Σ|Y| del propio mundo.
- `bias_norm_ref`: dividido por Σ|Y| del mundo de nivel 0 del par (denominador fijo).
- IC95: bootstrap de pares (mundos). Columna `IC95_células_norm_ref`: bootstrap por célula DAG cuando hay ≥ 5 células.

{md_table(main[cols], ".4g")}
## 4. Confusión comprobada en el DAG: canales confundidos frente a no confundidos (`do_zero`)

{md_table(split[cols], ".4g")}
## 5. Correlación observada entre canales por mundo

{md_table(cor, ".3f")}
Datos: `reports/v1_2/p1b_robust/` (`world_parameters.csv`, `series_changes.csv`, `e08_direct_long.csv`, `contrasts.csv`, `correlation_by_world.csv`).

## 6. Lectura

1. **La confusión por D está comprobada en el DAG, no supuesta.**
   - Con D→C variable (D→Y = 0,3 fijo), el sesgo de M2p cambia solo en los canales con ruta C_k←D_j→Y: −0,012 [−0,019, −0,007] en `do_zero`, con denominador fijo. En los demás canales no cambia: +0,001 [−0,002, 0,003].
   - Al nivel 0 de cada mecanismo (D→C = 0 o D→Y = 0) no hay ningún canal confundido.
2. **No depende de `do_zero`.** Las intervenciones locales ±10 % dentro del soporte observado muestran el mismo signo en los canales confundidos: el efecto se **sobreestima en magnitud** (Δsesgo / |efecto verdadero| ≈ +7 % en M0, +11–13 % en M2p y +16–25 % en M2). Con D observado (M2p_D) el cambio es ≈ 0.
3. **Observar D elimina la confusión por D en el modelo privilegiado**, pero no la de `rho`, que no pasa por D. Que M2p_D la elimine no demuestra que un MMM ciego pueda identificar el mismo efecto.
4. **Los modelos ciegos:**
   - M0 muestra un cambio pequeño pero distinto de 0 en canales confundidos.
   - M2 no tiene potencia con `dc` (IC ±0,03). Con `dy = 0,5`, su sesgo crece en los canales confundidos (−0,073 [−0,116, −0,038]), pero también, sin significación, en los no confundidos: M2 cambia de forma elegida cuando cambia `Y` (véase `reports/m2_selection_audit.md`).
5. **Correlación observada:** apenas cambia (Δ media|corr| ≤ 0,03; con `dy`, exactamente 0 porque los tratamientos no cambian). Hay confusión causal sin aumento de correlación entre canales.
6. **Límites:** 40 pares; con `rho`, una sola célula DAG (bootstrap por células no disponible); T = 104.
"""
    path = ROOT / "reports" / "p1b_e10a_robustness.md"
    path.write_text(text)
    return str(path)
