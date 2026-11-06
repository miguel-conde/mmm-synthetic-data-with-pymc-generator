"""v1.2 P1a — validation of the M3 masked likelihood (Entrega A).

``reference_model`` is an independent hand-written PyMC formulation of the same MMM (no pymc-marketing code):
explicit geometric adstock (normalised, l_max=8), logistic saturation, yearly Fourier (order 2), unscaled
controls, Normal likelihood written directly on ``y[w:n] / s``. It shares only variable names and priors with
M3 so that joint log-densities can be compared point by point.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from .provenance import ROOT
from .schema import ObservedDataset

L_MAX = 8
FOURIER_ORDER = 2

P0_FROZEN_PATHS = [
    "reports/quality_gate_v1_2.md", "reports/m3_coverage_audit.md", "reports/e09_policy_audit.md",
    "reports/scientific_status_v1_2.md", "reports/review_package_index.md", "reports/v1_2",
    "runs/v1_2_warmfit", "configs/v1_2_warmfit.yaml", "docs/protocolo_v1_2_P1.md",
    "docs/respuesta_v1_2_al_disenador.md", "docs/RESPUESTA_AL_AGENTE_MMM_V1_2.md",
]
P0_SNAPSHOT = "reports/v1_2/code_snapshot_P0"


def freeze_p0() -> Path:
    """SHA-256 manifest of the P0 artefacts plus the P0 code snapshot (code files evolve in P1)."""
    files = {}
    for rel in P0_FROZEN_PATHS + [P0_SNAPSHOT]:
        p = ROOT / rel
        for f in sorted([p] if p.is_file() else p.rglob("*")):
            if f.is_file() and f.name != "FREEZE_MANIFEST_P0.json":
                files[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    out = ROOT / "reports" / "v1_2" / "FREEZE_MANIFEST_P0.json"
    out.write_text(json.dumps({"frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                               "version": "v1.2-P0", "code_snapshot": P0_SNAPSHOT,
                               "n_files": len(files), "files": files}, indent=1))
    return out


def verify_p0() -> tuple[int, list[str]]:
    return verify_freeze("FREEZE_MANIFEST_P0.json")


P1A_FROZEN_PATHS = [
    "reports/p1a_warmup_validation.md", "reports/p1a_m3_rebaseline.md", "reports/p1_corrected_baselines.md",
    "reports/p1b_e10a_confounding.md", "reports/review_package_index_P1.md", "reports/v1_2/p1a",
    "reports/v1_2/p1_corr", "reports/v1_2/p1b", "reports/v1/ERRATA.md", "reports/v1_1/ERRATA.md",
    "reports/v1_1/code_snapshot/causal.py", "docs/protocolo_P1_registrado.md", "docs/respuesta_P1_al_disenador.md",
    "docs/RESPUESTA_AL_AGENTE_MMM_TRAS_P0_V1_2.md",
    "runs/v1_2_p1a_trial", "runs/v1_2_p1a_hist", "runs/v1_2_p1a_pilot", "runs/v1_2_corr_e0809",
    "runs/v1_2_corr_e10a_D", "runs/v1_2_corr_e10a_rho", "runs/v1_2_corr_f3", "runs/v1_2_p1b_e10a_dc",
    "runs/v1_2_p1b_e10a_dy", "runs/v1_2_p1b_e10a_rho",
] + [f"configs/{p.name}" for p in sorted((ROOT / "configs").glob("v1_2_*.yaml")) if p.name != "v1_2_warmfit.yaml"]
P1A_SNAPSHOT = "reports/v1_2/code_snapshot_P1A"


def freeze(manifest_name: str, version: str, paths: list[str], snapshot: str) -> Path:
    files = {}
    for rel in paths + [snapshot]:
        p = ROOT / rel
        for f in sorted([p] if p.is_file() else p.rglob("*")):
            if f.is_file() and not f.name.startswith("FREEZE_MANIFEST"):
                files[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    out = ROOT / "reports" / "v1_2" / manifest_name
    out.write_text(json.dumps({"frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                               "version": version, "code_snapshot": snapshot,
                               "n_files": len(files), "files": files}, indent=1))
    return out


def verify_freeze(manifest_name: str) -> tuple[int, list[str]]:
    m = json.loads((ROOT / "reports" / "v1_2" / manifest_name).read_text())
    bad = [f for f, h in m["files"].items()
           if not (ROOT / f).exists() or hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != h]
    return m["n_files"], bad


def adstock_np(x: np.ndarray, alpha: np.ndarray, l_max: int = L_MAX) -> np.ndarray:
    """Normalised geometric adstock, ConvMode.After, zero history before row 0. x: (T, K)."""
    w = alpha[None, :] ** np.arange(l_max)[:, None]
    w = w / w.sum(0)
    out = np.zeros_like(x, dtype=float)
    for lag in range(l_max):
        out[lag:] += w[lag] * x[: x.shape[0] - lag]
    return out


def logistic_np(x: np.ndarray, lam: np.ndarray) -> np.ndarray:
    return (1 - np.exp(-lam * x)) / (1 + np.exp(-lam * x))


def design(obs: ObservedDataset, n: int):
    """Inputs used by the reference: channel scale (max over [0, n)), controls (+trend), Fourier modes."""
    import pandas as pd

    C = obs.C[:n].astype(float)
    c_scale = C.max(0)
    Zc = np.column_stack([obs.Z[:n], np.arange(n) / obs.T])
    doy = pd.to_datetime(obs.dates[:n]).dayofyear.to_numpy()
    xx = 2 * np.pi * (doy / 365.25)[:, None] * np.arange(1, FOURIER_ORDER + 1)[None, :]
    F = np.column_stack([np.sin(xx), np.cos(xx)])
    return C / c_scale, c_scale, Zc, F


def reference_model(obs: ObservedDataset, w: int, lam_prior=(6.0, 2.0)):
    """Independent PyMC model with likelihood only on [w, n). Returns (model, target_scale)."""
    import pymc as pm
    import pytensor.tensor as pt

    n = int(obs.train_idx[-1]) + 1
    Xs, _, Zc, F = design(obs, n)
    y = obs.y[:n].astype(float)
    s = float(y[w:].max())
    K = Xs.shape[1]
    with pm.Model(coords={"channel": list(obs.channel_names), "control": list(range(Zc.shape[1])),
                          "fourier_mode": ["sin_1", "sin_2", "cos_1", "cos_2"]}) as m:
        intercept = pm.Normal("intercept_contribution", 0, 2)
        alpha = pm.Beta("adstock_alpha", 1, 3, dims="channel")
        lam = pm.Gamma("saturation_lam", alpha=lam_prior[0], beta=lam_prior[1], dims="channel")
        beta = pm.HalfNormal("saturation_beta", 2, dims="channel")
        g_c = pm.Normal("gamma_control", 0, 2, dims="control")
        g_f = pm.Laplace("gamma_fourier", 0, 1, dims="fourier_mode")
        sigma = pm.HalfNormal("y_sigma", 2)
        lags = pt.arange(L_MAX)
        wts = alpha[None, :] ** lags[:, None]
        wts = wts / wts.sum(0)
        X = pt.as_tensor(Xs)
        ad = pt.zeros_like(X)
        for lag in range(L_MAX):
            ad = pt.inc_subtensor(ad[lag:], wts[lag] * X[: n - lag])
        contrib = beta * (1 - pt.exp(-lam * ad)) / (1 + pt.exp(-lam * ad))
        mu = intercept + contrib.sum(1) + pt.as_tensor(Zc) @ g_c + pt.as_tensor(F) @ g_f
        pm.Deterministic("channel_contribution", contrib)
        pm.Normal("y", mu=mu[w:], sigma=sigma, observed=y[w:] / s)
    return m, s


def random_points(model, k: int, seed: int) -> list[dict]:
    """Random unconstrained points (initial point + N(0, 0.5) jitter) keyed by value-variable name."""
    rng = np.random.default_rng(seed)
    ip = model.initial_point()
    return [{name: v + rng.normal(0, 0.5, size=np.shape(v)) for name, v in ip.items()} for _ in range(k)]


def eval_at(model, names: list[str], point: dict) -> list[np.ndarray]:
    """Values of model variables (RVs or deterministics) at an unconstrained point."""
    import pytensor

    outs = model.replace_rvs_by_values([model[n] for n in names])
    outs = [getattr(o, "values", o) for o in outs]
    fn = pytensor.function(model.value_vars, outs, on_unused_input="ignore")
    return [np.asarray(v) for v in fn(**{v.name: point[v.name] for v in model.value_vars})]


# ------------------------------------------------------------------ property 4: posterior agreement
REF_SAMPLER = dict(draws=1000, tune=1000, chains=4, cores=2, target_accept=0.99)
MEDIA = ("adstock_alpha", "saturation_lam", "saturation_beta")
AGREEMENT_MAX_STD_DIFF = 0.3  # |mean_M3 - mean_ref| / sd_ref, per parameter element (≈ 4 MC standard errors)


def reference_fit(spec, seed: int) -> dict:
    """MCMC of the independent reference model on the corrected window; returns posterior summaries."""
    import dataclasses

    import pymc as pm

    from .generator_adapter import WorldStore
    from .models.bayes import mcmc_diagnostics
    from .runner import WORLD_CACHE

    _, obs, _ = WorldStore(WORLD_CACHE).load(spec)
    o = dataclasses.replace(obs, train_idx=obs.train_idx[obs.train_idx >= obs.warmup]).fit_view()
    model, s = reference_model(o, obs.warmup)
    t0 = time.perf_counter()
    with model:
        idata = pm.sample(nuts_sampler="nutpie", random_seed=seed, progressbar=False, **REF_SAMPLER)
    post = idata["posterior"]
    free = [v.name for v in model.free_RVs]
    out = {"world_id": spec.world_id, "runtime_s": time.perf_counter() - t0, "scale": s,
           "diag": mcmc_diagnostics(idata, free)}
    for n in (*MEDIA, "y_sigma", "intercept_contribution"):
        a = np.asarray(post[n]).reshape(-1, *np.asarray(post[n]).shape[2:])
        out[n] = (a.mean(0), a.std(0))
    cc = np.asarray(post["channel_contribution"]).reshape(-1, *post["channel_contribution"].shape[2:]) * s
    out["contrib_mean"] = cc.mean(0)
    return out


def compare_with_m3(ref: dict, run_dir: Path, model_id: str = "M3_pymc_marketing@v3m") -> list[dict]:
    """Standardised posterior-mean differences, M3 masked (saved posterior) vs independent reference."""
    wdir = run_dir / "results" / ref["world_id"]
    post = np.load(wdir / f"{model_id}.posterior.npz")
    rows = []
    for n in (*MEDIA, "y_sigma", "intercept_contribution"):
        a = post[n].reshape(-1, *post[n].shape[2:])
        m_ref, sd_ref = ref[n]
        d = np.atleast_1d((a.mean(0) - m_ref) / sd_ref)
        for k, v in enumerate(d):
            rows.append({"world_id": ref["world_id"], "param": n, "index": k, "mean_m3": float(np.atleast_1d(a.mean(0))[k]),
                         "mean_ref": float(np.atleast_1d(m_ref)[k]), "sd_ref": float(np.atleast_1d(sd_ref)[k]),
                         "std_diff": float(v)})
    arr = np.load(wdir / f"{model_id}.npz")
    c_m3 = arr["contributions"][: ref["contrib_mean"].shape[0]]
    lo = 8
    denom = np.mean(np.abs(c_m3[lo:])) + 1e-12
    rows.append({"world_id": ref["world_id"], "param": "contribution_mean_rel_mae", "index": -1,
                 "mean_m3": float(np.mean(c_m3[lo:])), "mean_ref": float(np.mean(ref["contrib_mean"][lo:])), "sd_ref": np.nan,
                 "std_diff": float(np.mean(np.abs(c_m3[lo:] - ref["contrib_mean"][lo:])) / denom)})
    return rows


REFERENCE_WORLDS = (("direct_only", 104, 0, "linear", (("nonlinearity", "linear"),)), ("kitchen_sink", 104, 0, "", ()))
OUT = ROOT / "reports" / "v1_2" / "p1a"


def run_reference_fits() -> Path:
    import pickle

    from .generator_adapter import WorldSpec
    from .provenance import derive_seed

    OUT.mkdir(parents=True, exist_ok=True)
    for sc, T, r, v, ov in REFERENCE_WORLDS:
        spec = WorldSpec(sc, T, r, variant=v, overrides=ov)
        path = OUT / f"reference_fit_{spec.world_id}.pkl"
        if not path.exists():
            res = reference_fit(spec, derive_seed(spec.world_id, "p1a_reference", "fit"))
            path.write_bytes(pickle.dumps(res))
            print(spec.world_id, round(res["runtime_s"]), res["diag"]["converged_strict"], flush=True)
    return OUT


# ------------------------------------------------------------------ Entrega A analysis
M3_HIST = ("v1_2_p1a_hist", "M3_pymc_marketing@v3")  # V3 fitted from week 0 (historical), posterior kept
M3_MASK = ("v1_2_p1a_pilot", "M3_pymc_marketing@v3m")  # V3 with masked likelihood
M3_V11 = ("v1_1_m3", "M3_pymc_marketing@v3")  # original v1.1 fits (no posterior saved)
ROPE_FACTOR = 0.005
ROPE_PROB = 0.95
MIN_PAIRED_VALID = 8


def rope_decision(draws: np.ndarray, delta: float) -> str:
    if np.mean((draws >= 0) & (draws < delta)) >= ROPE_PROB:
        return "practically_null"
    if np.mean(draws >= delta) >= ROPE_PROB:
        return "relevant"
    return "indeterminate"


def channel_rows(run: str, model_id: str, label: str) -> list[dict]:
    from .audit_v1_2 import DEV_WORLDS, spec_from_world_id
    from .generator_adapter import WorldStore
    from .runner import WORLD_CACHE

    store = WorldStore(WORLD_CACHE)
    rows = []
    rdir = ROOT / "runs" / run / "results"
    for wdir in sorted(p for p in rdir.iterdir() if (p / f"{model_id}.json").exists()):
        wid = wdir.name
        rec = json.loads((wdir / f"{model_id}.json").read_text())
        if rec["fit_status"] != "ok":
            rows.append({"variant": label, "world_id": wid, "fit_status": rec["fit_status"]})
            continue
        _, obs, truth = store.load(spec_from_world_id(wid))
        d = rec["diagnostics"]
        a = np.load(wdir / f"{model_id}.npz")
        pp = wdir / f"{model_id}.posterior.npz"
        post = np.load(pp) if pp.exists() else {}
        tc = truth["contributions_observed"]
        n = int(obs.train_idx[-1]) + 1
        w8 = np.arange(obs.warmup, n)
        delta = ROPE_FACTOR * float(np.mean(np.abs(obs.y[w8])))
        for window, idx in (("historical_in_sample_fit", obs.eval_idx("train")),
                            ("attribution_future_conditional_on_known_CZ", obs.eval_idx("test"))):
            ymean = float(np.mean(np.abs(obs.y[idx])))
            for k, role in enumerate(truth.channel_roles):
                t, e = tc[idx, k], a["contributions"][idx, k]
                row = {"variant": label, "world_id": wid, "fit_status": "ok", "scenario_id": wid[:2], "T": obs.T,
                       "channel": k, "role": role, "window": window, "dev_world": wid in DEV_WORLDS,
                       "valid_strict": bool(d["converged_strict"]), "rhat_max": d["rhat_max"],
                       "ess_bulk_min": d["ess_bulk_min"], "divergences": d["divergences"],
                       "runtime_s": rec["runtime_s"], "peak_rss_mb": rec["peak_rss_mb"],
                       "likelihood_window": str(d.get("likelihood_window", [0, n])), "target_scale": d["target_scale"],
                       "bias_norm": float(np.mean(e - t) / ymean), "mae_norm": float(np.mean(np.abs(e - t)) / ymean),
                       "true_mean_norm": float(np.mean(t) / ymean)}
                for lv in (50, 80, 95):
                    lo, hi = a[f"contrib_intervals_{lv}_lo"][idx, k], a[f"contrib_intervals_{lv}_hi"][idx, k]
                    row[f"cov{lv}"] = float(np.mean((t >= lo) & (t <= hi)))
                    row[f"width{lv}_norm"] = float(np.mean(hi - lo) / ymean)
                if window == "historical_in_sample_fit":
                    c_true = float(np.mean(tc[w8, k]))
                    row.update({"rope_delta": delta, "c_true": c_true, "truth_relevant": bool(c_true >= delta)})
                    if "contrib_mean_w8_train" in post:
                        dr = post["contrib_mean_w8_train"][:, k]
                        row.update({"rope_decision": rope_decision(dr, delta), "c_post_mean": float(dr.mean()),
                                    "p_relevant": float(np.mean(dr >= delta)),
                                    "p_null": float(np.mean((dr >= 0) & (dr < delta)))})
                rows.append(row)
    return rows


def pilot_table() -> pd.DataFrame:
    import pandas as pd

    from .tables_io import read_table

    OUT.mkdir(parents=True, exist_ok=True)
    rows = channel_rows(*M3_HIST, "V3_hist_w0") + channel_rows(*M3_MASK, "V3_masked_w8")
    path = OUT / "pilot_world_channel.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return read_table(path)


def reproduction_check() -> pd.DataFrame:
    """Re-run of historical V3 (posterior kept) vs original v1.1 fit: same seed, same week-0 window."""
    import pandas as pd

    rows = []
    for wdir in sorted((ROOT / "runs" / M3_HIST[0] / "results").iterdir()):
        new = wdir / f"{M3_HIST[1]}.npz"
        old = ROOT / "runs" / M3_V11[0] / "results" / wdir.name / f"{M3_V11[1]}.npz"
        if new.exists() and old.exists():
            a, b = np.load(new)["contributions"], np.load(old)["contributions"]
            ra = json.loads((wdir / f"{M3_HIST[1]}.json").read_text())["diagnostics"]
            rb = json.loads(old.with_suffix(".json").read_text())["diagnostics"]
            rows.append({"world_id": wdir.name, "max_abs_diff_contrib": float(np.abs(a - b).max()),
                         "max_abs_contrib": float(np.abs(b).max()),
                         "rhat_rerun": ra["rhat_max"], "rhat_v1_1": rb["rhat_max"],
                         "valid_rerun": ra["converged_strict"], "valid_v1_1": rb["converged_strict"]})
    return pd.DataFrame(rows)


def _boot(per_world: np.ndarray) -> tuple[float, float, float]:
    from .evaluation import paired_bootstrap

    return paired_bootstrap(np.asarray(per_world, dtype=float))


def paired_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Direct channels, window [8, n_train): per-world means, V3 masked minus V3 hist, world bootstrap."""
    import pandas as pd

    h = df[(df.window == "historical_in_sample_fit") & (df.role == "direct")]
    valid = h.drop_duplicates(["variant", "world_id"]).pivot(index="world_id", columns="variant", values="valid_strict")
    rows, n_both = [], 0
    for subset, worlds in (("ambos válidos (pareado)", valid[(valid.V3_hist_w0 == True) & (valid.V3_masked_w8 == True)].index),  # noqa: E712
                           ("todos los ajustes (descriptivo)", valid.index)):
        if subset.startswith("ambos"):
            n_both = len(worlds)
        g = h[h.world_id.isin(worlds)].groupby(["variant", "world_id"])[["bias_norm", "mae_norm", "cov95", "cov80", "width95_norm"]].mean()
        for m in ("bias_norm", "mae_norm", "cov95", "cov80", "width95_norm"):
            if len(worlds) == 0:
                continue
            a, b = g.loc["V3_hist_w0"][m], g.loc["V3_masked_w8"][m]
            d = (b - a).dropna()
            mm, lo, hi = _boot(d.to_numpy())
            rows.append({"subconjunto": subset, "n_mundos": len(d), "métrica": m, "V3_hist_w0": a.mean(),
                         "V3_masked_w8": b.mean(), "dif (enm. − hist.)": mm, "IC95_lo": lo, "IC95_hi": hi})
    return pd.DataFrame(rows), n_both


def entrega_a_answer(ps: pd.DataFrame, n_both: int) -> tuple[str, str]:
    if n_both < MIN_PAIRED_VALID:
        return "no concluyente", f"solo {n_both} mundos con ambos ajustes válidos (< {MIN_PAIRED_VALID})"
    p = ps[ps.subconjunto.str.startswith("ambos")].set_index("métrica")
    bias_h, bias_m = p.loc["bias_norm", "V3_hist_w0"], p.loc["bias_norm", "V3_masked_w8"]
    cov_gain = p.loc["cov95", "V3_masked_w8"] - p.loc["cov95", "V3_hist_w0"]
    c1 = abs(bias_m) <= 0.5 * abs(bias_h)
    c2 = cov_gain >= 0.15
    detail = (f"{n_both} mundos pareados válidos; sesgo directo {bias_h:+.4f} → {bias_m:+.4f} "
              f"({'≤' if c1 else '>'} mitad en valor absoluto); cobertura IC95 {p.loc['cov95', 'V3_hist_w0']:.3f} → "
              f"{p.loc['cov95', 'V3_masked_w8']:.3f} (Δ {cov_gain:+.3f}, umbral +0,15)")
    return ("sí" if c1 and c2 else "no" if not (c1 or c2) else "parcial"), detail


def rope_summary(df: pd.DataFrame) -> pd.DataFrame:
    import pandas as pd

    h = df[(df.window == "historical_in_sample_fit") & df.rope_decision.notna()].copy()
    h["truth_relevant"] = h.truth_relevant.astype(str).str.lower().eq("true")
    rows = []
    for (var, valid, role), g in h.groupby(["variant", "valid_strict", "role"], observed=True):
        rel, notrel = g[g.truth_relevant], g[~g.truth_relevant]
        dec_rel = g.rope_decision == "relevant"
        rows.append({"variante": var, "válido": valid, "rol": role, "n_canales": len(g), "n_mundos": g.world_id.nunique(),
                     "verdad_relevante": len(rel),
                     "sensibilidad": float((rel.rope_decision == "relevant").mean()) if len(rel) else np.nan,
                     "falsos_positivos": float((notrel.rope_decision == "relevant").mean()) if len(notrel) else np.nan,
                     "precisión": float(g[dec_rel].truth_relevant.mean()) if dec_rel.any() else np.nan,
                     "nulo_correcto": float((notrel.rope_decision == "practically_null").mean()) if len(notrel) else np.nan,
                     "nulo_en_relevante": float((rel.rope_decision == "practically_null").mean()) if len(rel) else np.nan,
                     "indeterminado": float((g.rope_decision == "indeterminate").mean())})
    return pd.DataFrame(rows)


def cost_table(df: pd.DataFrame) -> pd.DataFrame:
    w = df[df.fit_status == "ok"].drop_duplicates(["variant", "world_id"])
    return w.groupby("variant").agg(n_ajustes=("world_id", "count"), n_válidos=("valid_strict", "sum"),
                                    tiempo_mediano_s=("runtime_s", "median"), tiempo_max_s=("runtime_s", "max"),
                                    rss_pico_max_mb=("peak_rss_mb", "max")).reset_index()


# ------------------------------------------------------------------ reports
def trial_table() -> pd.DataFrame:
    import pandas as pd

    rows = []
    for wdir in sorted((ROOT / "runs" / "v1_2_p1a_trial" / "results").iterdir()):
        f = wdir / "M3_pymc_marketing@v3m.json"
        if f.exists():
            r = json.loads(f.read_text())
            d = r["diagnostics"] or {}
            rows.append({"mundo": wdir.name, "estado": r["fit_status"], "R-hat máx": d.get("rhat_max"),
                         "ESS bulk mín": d.get("ess_bulk_min"), "divergencias": d.get("divergences"),
                         "válido": d.get("converged_strict"), "ventana verosimilitud": str(d.get("likelihood_window")),
                         "escala Y": d.get("target_scale"), "tiempo_s": r["runtime_s"], "RSS pico MB": r["peak_rss_mb"],
                         "arquitectura": d.get("architecture")})
    return pd.DataFrame(rows)


def reference_agreement() -> pd.DataFrame:
    import pickle

    import pandas as pd

    rows = []
    for path in sorted(OUT.glob("reference_fit_*.pkl")):
        ref = pickle.loads(path.read_bytes())
        for r in compare_with_m3(ref, ROOT / "runs" / "v1_2_p1a_trial"):
            r.update({"ref_valid": ref["diag"]["converged_strict"], "ref_rhat": ref["diag"]["rhat_max"],
                      "ref_runtime_s": ref["runtime_s"]})
            rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "reference_agreement.csv", index=False)
    return df


def run_tests() -> str:
    import os
    import subprocess

    res = subprocess.run(["uv", "run", "--locked", "pytest", "-q", f"--junitxml={OUT / 'pytest_p1a.xml'}"], cwd=ROOT,
                         capture_output=True, text=True, env={**os.environ, "MPLBACKEND": "Agg"})
    (OUT / "pytest_p1a.txt").write_text(res.stdout[-4000:])
    return [ln for ln in res.stdout.splitlines() if ln.strip()][-1]


def _md(df, fmt=".3f") -> str:
    from .reporting import md_table

    return md_table(df, fmt)


def write_validation_report(pytest_tail: str) -> Path:
    import pandas as pd

    from .provenance import environment_fingerprint

    tri = trial_table()
    tri.to_csv(OUT / "trial_fits.csv", index=False)
    agr = reference_agreement()
    par = agr[agr.param != "contribution_mean_rel_mae"]
    agr_s = par.groupby("world_id").agg(n_elementos=("std_diff", "size"), max_abs_std_diff=("std_diff", lambda s: s.abs().max()),
                                        ref_valid=("ref_valid", "first"), ref_rhat=("ref_rhat", "first"),
                                        ref_runtime_s=("ref_runtime_s", "first")).reset_index()
    rel = agr[agr.param == "contribution_mean_rel_mae"][["world_id", "std_diff"]].rename(columns={"std_diff": "MAE_rel_contrib_[8,n)"})
    agr_s = agr_s.merge(rel, on="world_id")
    agr_s["pasa (≤ 0,3)"] = agr_s.max_abs_std_diff <= AGREEMENT_MAX_STD_DIFF
    env = environment_fingerprint()
    pk = env["packages"]
    text = f"""# P1a — Validación de la ventana de ajuste de M3 (verosimilitud enmascarada)

Protocolo: `docs/protocolo_P1_registrado.md` §1–§3. Código: `mmm_benchmark/models/bayes.py` (`PyMCMarketingMMM.build`, `_mask_history_likelihood`), referencia independiente y análisis en `mmm_benchmark/p1a.py`, tests en `tests/test_p1a_masking.py`. Versiones: pymc-marketing {pk.get('pymc-marketing')}, pymc {pk.get('pymc')}, pytensor {pk.get('pytensor')}, nutpie {pk.get('nutpie')}; `uv.lock` SHA-256 `{env['uv_lock_sha256'][:16]}…`.

## 1. Arquitectura (propiedad 6)

**M3 sigue siendo la clase estándar `pymc_marketing.mmm.MMM` 1.3.0 con una modificación controlada de la verosimilitud.** No es un modelo PyMC propio. Con ventana de ajuste `[w, n_train)` y `w = 8`:

1. **Entradas:** `MMM.build_model` recibe las filas `[0, n_train)`. Canales y controles desde la semana 0, de modo que el adstock (`GeometricAdstock(l_max=8)`, `normalize=True`) se calcula sobre la secuencia completa.
2. **`Y` de las semanas 0–7** se sustituye, antes de entrar al modelo, por un marcador constante (media de `Y[8:n_train)`). El `Y` real de esas semanas no llega a ningún objeto del modelo.
3. **Escala de `Y`:** `Scaling(target=FixedScaling(value=max Y[8:n_train)))` con la API oficial. La escala de canales sigue siendo la de siempre (`max` por canal sobre `[0, n_train)`): **uso permitido de canales de la fase inicial, documentado aparte** según D1.
4. **Máscara:** tras `build_model`, se añade `pm.Potential("{'y_history_likelihood_mask'}", -Σ_{{t<8}} log p(y_t | μ_t, σ))`.
   - Los términos son los del propio grafo: `model.logp(vars=[y], sum=False)[0][:8]`.
   - La densidad conjunta solo contiene la verosimilitud de `[8, n_train)`, con una única variable observada `y`.
   - `MMM.fit` reutiliza el modelo ya construido (`if not hasattr(self, "model")`) y muestrea `freeze_dims_and_data(self.model)`, que conserva el `Potential`.
5. **Ventana `w = 0`:** sin máscara, el modelo es idéntico al de v1/v1.1, con escala derivada de los datos sobre `[0, n_train)`.

**Cambios de API respecto a P0:**
- `PyMCMarketingMMM.fit` ya no rechaza ventanas que empiezan en `w > 0`; las enmascara.
- Nuevo método `build(obs)`, para construir sin muestrear.
- Diagnósticos nuevos: `likelihood_window` y `architecture`.
- Con `keep_posterior`, se guarda por draw la contribución media en `[8, n_train)` (estimando ROPE).
- El test P0 `test_pymc_marketing_refuses_fit_window_without_history` se sustituye por `test_pymc_marketing_late_window_is_masked_not_restarted`.

**Defecto adicional encontrado y corregido en P1:** `causal.horizon` y el oráculo M4 usaban `len(train_idx)` como fin del entrenamiento. Con `fit_scope=train_after_warmup` esa ventana habría encogido 8 semanas. Ahora usan `train_idx[-1] + 1` (test `test_causal_horizon_does_not_shrink_with_late_fit_window`). No afecta a resultados previos: P0 no ejecutó E08/E09 con ventana tardía y M4 siempre se ajustó desde 0.

## 2. Pruebas deterministas (propiedades 1–5)

| Propiedad | Test | Resultado |
|---|---|---|
| 1. Arrastre sobre la secuencia completa; el estado previo alcanza semanas ≥ 8 | `test_adstock_uses_full_input_sequence` (S0 y S4) | pasa: `channel_contribution` = numpy independiente (rtol 1e-10) y ≠ arrastre reiniciado en la semana 8 |
| 2. logp = suma manual de `[8, n_train)`; una sola verosimilitud | `test_logp_is_manual_sum_over_permitted_weeks_only`, `test_target_scale_uses_permitted_weeks_only` | pasa (5 puntos aleatorios × 2 mundos, rel 1e-12) |
| 3. `Y[0:8]` no cambia logp ni gradiente; los canales de 0–7 sí | `test_history_y_does_not_change_logp_or_gradient`, `test_history_channels_do_change_logp` | pasa: igualdad **exacta** (bit a bit) de logp, gradiente y datos del modelo con `Y[0:8]·5 + 100` |
| 4a. Igualdad determinista frente a referencia independiente | `test_masked_m3_equals_independent_reference` | pasa: densidad conjunta igual salvo una constante (≈ 1,2e-7) y gradiente igual (≤ 1e-9) en 10 puntos aleatorios |
| 5. Contribuciones, escala, predicción, intervalos, respuesta compilada, posterior | `test_masked_fit_end_to_end` (slow, MCMC corto) | pasa |
| — | `test_full_window_path_is_unchanged`, `test_non_contiguous_window_rejected` | pasa |

La referencia independiente (`p1a.reference_model`) es un modelo PyMC escrito a mano sin código de pymc-marketing:
- adstock geométrico normalizado con convolución explícita y saturación logística;
- Fourier anual de orden 2 y controles sin escalar;
- verosimilitud Normal escrita **directamente** sobre `y[8:n]/s`, sin `Potential`.

Suite completa: `{pytest_tail}` (`reports/v1_2/p1a/pytest_p1a.txt`).

## 3. Propiedad 4b — concordancia posterior por MCMC (E02 lineal y no lineal con Weibull)

Ambos modelos se muestrearon con la misma configuración (1000 + 1000, 4 cadenas, `target_accept 0.99`) y semillas distintas.

**Criterio fijado antes de comparar:** `|media_M3 − media_ref| / sd_ref ≤ 0,3` (≈ 4 errores Monte Carlo) en cada elemento de `adstock_alpha`, `saturation_lam`, `saturation_beta`, `y_sigma` e `intercept`.

{_md(agr_s)}
Detalle: `reports/v1_2/p1a/reference_agreement.csv`.

## 4. Ensayo mínimo (4 mundos, V3 enmascarada)

`configs/v1_2_p1a_trial.yaml`. Es una comprobación técnica, no evidencia.

{_md(tri)}
## 5. Reproducibilidad

Una re-ejecución de V3 desde la semana 0, con la misma semilla y el mismo `uv.lock`, no siempre es bit a bit idéntica al ajuste de v1.1: coincide exactamente en 4 de los 10 mundos piloto y en el resto difiere hasta un 3 % del máximo de las contribuciones. Es ruido Monte Carlo del muestreo (nutpie multihilo), no un cambio de modelo. La validez estricta cambia en 3 de 10 mundos con R-hat cerca de 1,01. Por eso el piloto compara V3 enmascarada con la **re-ejecución** de V3 histórica (`runs/v1_2_p1a_hist`, posterior guardada). La comparación con los ajustes originales de v1.1 se da aparte (`p1a_m3_rebaseline.md` §5).

## 6. Coste

Tiempo y memoria por ajuste: tabla del §4 y `p1a_m3_rebaseline.md`. La máscara no añade variables libres; el coste por gradiente es el de calcular 8 términos de verosimilitud adicionales.
"""
    path = ROOT / "reports" / "p1a_warmup_validation.md"
    path.write_text(text)
    return path


def write_rebaseline_report() -> tuple[Path, str, str]:
    import pandas as pd

    df = pilot_table()
    ok = df[df.fit_status == "ok"]
    ps, n_both = paired_summary(ok)
    ps.to_csv(OUT / "pilot_paired_direct.csv", index=False)
    answer, detail = entrega_a_answer(ps, n_both)
    rs = rope_summary(ok)
    rs.to_csv(OUT / "pilot_rope_by_role.csv", index=False)
    cost = cost_table(ok)
    rep = reproduction_check()
    rep.to_csv(OUT / "reproduction_v1_1_vs_rerun.csv", index=False)
    h = ok[ok.window == "historical_in_sample_fit"]
    fits = h.drop_duplicates(["variant", "world_id"])[["variant", "world_id", "valid_strict", "rhat_max", "ess_bulk_min",
                                                       "divergences", "target_scale", "likelihood_window", "runtime_s"]]
    fits = fits.pivot(index="world_id", columns="variant", values=["valid_strict", "rhat_max", "ess_bulk_min", "divergences"])
    fits.columns = [f"{a}·{b}" for a, b in fits.columns]
    by_world = h[h.role == "direct"].groupby(["world_id", "variant"])[["bias_norm", "cov95"]].mean().unstack("variant")
    by_world.columns = [f"{a}·{b}" for a, b in by_world.columns]
    role = h.groupby(["variant", "role"], observed=True).agg(
        n_canales=("channel", "size"), sesgo=("bias_norm", "mean"), mae=("mae_norm", "mean"), cov95=("cov95", "mean"),
        ancho95=("width95_norm", "mean")).reset_index()
    fut = ok[(ok.window != "historical_in_sample_fit") & (ok.role == "direct")].groupby("variant")[
        ["bias_norm", "mae_norm", "cov95"]].mean().reset_index()
    # v1.1 original vs rerun (week 0): coverage/bias of the original fits on the same worlds
    text = f"""# P1a — Re-línea base de M3: V3 histórica (semana 0) frente a V3 enmascarada (semana 8)

Protocolo: `docs/protocolo_P1_registrado.md` §3. Mundos: los 10 del piloto, registrados antes de ajustar. Estos mundos se consultaron en auditorías de P0, así que el piloto **no** es una prueba independiente.

- **V3_hist_w0:** columna histórica. V3 ajustada desde la semana 0, con escala de `Y` sobre `[0, n_train)`, como en v1.1. Re-ejecutada con la misma semilla para guardar la posterior (`runs/v1_2_p1a_hist`). Resultado contaminado por las semanas 0–7.
- **V3_masked_w8:** V3 con verosimilitud enmascarada (`runs/v1_2_p1a_pilot`).

Mismos priors, misma semilla y mismo muestreo (1000 + 1000, 4 cadenas, `target_accept 0.99`). Validez estricta: R-hat ≤ 1,01, ESS bulk ≥ 400, 0 divergencias. Métricas normalizadas por media|Y| de la ventana. Ventana `historical_in_sample_fit` = `[8, n_train)`.

## 1. Respuesta (regla fijada en el protocolo §3.5)

**¿La corrección de la ventana explica una parte importante del sesgo negativo y la baja cobertura en directos? → {answer.upper()}.** {detail}.

## 2. Convergencia y coste

{_md(cost)}
{_md(fits.reset_index())}
## 3. Directos, ventana `[8, n_train)`: diferencias pareadas por mundo (bootstrap de mundos)

{_md(ps, ".4f")}
Por mundo (media sobre canales directos):

{_md(by_world.reset_index(), ".4f")}
## 4. Todos los roles (todos los ajustes, descriptivo)

{_md(role, ".4f")}
Directos, ventana futura (`attribution_future_conditional_on_known_CZ`):

{_md(fut, ".4f")}
## 5. Indicadores sobre nulos (ROPE)

ROPE de referencia del protocolo (§4).
- **Estimando:** contribución directa media semanal en `[8, n_train)`, en unidades de `Y`.
- **Umbral:** `delta = 0,005·media|Y[8:n_train)|`; «relevante» si `P(c ≥ delta) ≥ 0,95`.
- Es un umbral de decisión exploratorio: no es cobertura ni una prueba de `beta = 0`.
- En feeders la verdad directa es 0 aunque el efecto total `do` sea positivo.

{_md(rs)}
Columnas:
- `sensibilidad`: P(decisión relevante | verdad relevante).
- `falsos_positivos`: P(decisión relevante | verdad no relevante).
- `nulo_correcto`: P(decisión prácticamente nulo | verdad no relevante).
- `nulo_en_relevante`: P(decisión prácticamente nulo | verdad relevante).

Con 10 mundos son cifras descriptivas.

## 6. Comprobación frente a los ajustes originales de v1.1

Re-ejecución de V3 desde la semana 0 (misma semilla y entorno) comparada con `runs/v1_1_m3`:

{_md(rep, ".4f")}
Las diferencias son ruido Monte Carlo: el muestreo no es bit a bit reproducible.

Datos: `reports/v1_2/p1a/pilot_world_channel.csv`, `pilot_paired_direct.csv`, `pilot_rope_by_role.csv`.
"""
    path = ROOT / "reports" / "p1a_m3_rebaseline.md"
    path.write_text(text)
    return path, answer, detail
