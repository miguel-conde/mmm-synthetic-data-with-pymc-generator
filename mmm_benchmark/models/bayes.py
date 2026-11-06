"""M3 PyMC-Marketing MMM (blind) and M4 oracle_structure_known_plugin (privileged)."""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from ..schema import PRIVILEGED, ObservedDataset
from .base import Estimator

LEVELS = (0.5, 0.8, 0.95)
RHAT_MAX = 1.01
ESS_MIN = 400
ESS_MIN_PILOT = 100
MASK_POTENTIAL = "y_history_likelihood_mask"


def V3_SATURATION_PRIORS(Prior) -> dict:
    """V3 (reports/mcmc_diagnostics.md §4): same prior mean for lam, thinner tails along the lam–beta ridge."""
    return {
        "lam": Prior("Gamma", alpha=6, beta=2, dims="channel"),
        "beta": Prior("HalfNormal", sigma=2, dims="channel"),
    }


def mcmc_diagnostics(idata, var_names: list[str]) -> dict:
    import arviz as az

    post = idata["posterior"].to_dataset()[var_names]
    rhat_ds, ess_ds = az.rhat(post, method="rank"), az.ess(post, method="bulk")
    rhat = np.concatenate([np.ravel(v) for v in rhat_ds.data_vars.values()])
    ess = np.concatenate([np.ravel(v) for v in ess_ds.data_vars.values()])
    stats = idata["sample_stats"].to_dataset()
    diverging = np.asarray(stats["diverging"]) if "diverging" in stats else None
    div = int(diverging.sum()) if diverging is not None else -1
    rhat_max = float(np.nanmax(rhat))
    ess_min = float(np.nanmin(ess))
    ess_tail_ds = az.ess(post, method="tail")
    sampler = {}
    if "energy" in stats:
        e = np.asarray(stats["energy"], dtype=float)  # (chain, draw); E-BFMI = E[dE^2] / Var[E] per chain
        sampler["bfmi_min"] = float(np.min(np.mean(np.diff(e, axis=1) ** 2, axis=1) / np.var(e, axis=1)))
    if "maxdepth_reached" in stats:
        sampler["frac_maxdepth"] = float(np.mean(np.asarray(stats["maxdepth_reached"])))
    if "depth" in stats:
        sampler["mean_depth"] = float(np.mean(np.asarray(stats["depth"])))
    if "step_size" in stats:
        sampler["step_size_by_chain"] = np.asarray(stats["step_size"])[:, -1].tolist()
    return {
        "rhat_max": rhat_max,
        "ess_bulk_min": ess_min,
        "divergences": div,
        "divergences_per_chain": diverging.sum(axis=1).tolist() if diverging is not None else None,
        "rhat_max_by_var": {k: float(np.nanmax(v)) for k, v in rhat_ds.data_vars.items()},
        "ess_bulk_min_by_var": {k: float(np.nanmin(v)) for k, v in ess_ds.data_vars.items()},
        "ess_tail_min_by_var": {k: float(np.nanmin(v)) for k, v in ess_tail_ds.data_vars.items()},
        **sampler,
        "converged_strict": bool(rhat_max <= RHAT_MAX and ess_min >= ESS_MIN and div == 0),
        "converged_pilot": bool(rhat_max <= RHAT_MAX and ess_min >= ESS_MIN_PILOT and div == 0),
    }


def _intervals(samples: np.ndarray) -> dict[float, tuple[np.ndarray, np.ndarray]]:
    """samples: (S, ...) -> central intervals per level."""
    out = {}
    for lv in LEVELS:
        lo, hi = np.quantile(samples, [(1 - lv) / 2, (1 + lv) / 2], axis=0)
        out[lv] = (lo, hi)
    return out


class PyMCMarketingMMM(Estimator):
    model_id = "M3_pymc_marketing"
    family = "bayesian_mmm"
    FREE = [
        "adstock_alpha",
        "saturation_lam",
        "saturation_beta",
        "gamma_fourier",
        "gamma_control",
        "intercept_contribution",
        "y_sigma",
    ]

    def __init__(self, draws: int = 500, tune: int = 500, chains: int = 2, cores: int = 2, target_accept: float = 0.9,
                 prior_variant: str | None = None, keep_posterior: bool = False, scale_from: int | None = None,
                 nuts_sampler_kwargs: dict | None = None):
        self.sample_kw = dict(draws=draws, tune=tune, chains=chains, cores=cores, target_accept=target_accept)
        if nuts_sampler_kwargs:
            self.sample_kw["nuts_sampler_kwargs"] = dict(nuts_sampler_kwargs)
        self.prior_variant = prior_variant
        self.keep_posterior = keep_posterior
        self.scale_from = scale_from  # P1B arm B: target scale from Y[scale_from:n) with the full likelihood

    def _frame(self, obs: ObservedDataset, C: np.ndarray) -> pd.DataFrame:
        df = pd.DataFrame(C, columns=list(obs.channel_names))
        for m, name in enumerate(obs.control_names):
            df[name] = obs.Z[:, m]
        df["trend"] = np.arange(obs.T) / obs.T
        df["date"] = pd.to_datetime(obs.dates)
        return df

    def build(self, obs: ObservedDataset):
        """Builds the PyMC-Marketing model for ``obs.train_idx`` = ``[w, n)`` without sampling.
        Returns ``(X, y)`` as passed to ``MMM.fit``."""
        from pymc_marketing.mmm import MMM, GeometricAdstock, LogisticSaturation

        adstock, saturation = self._components(GeometricAdstock, LogisticSaturation)
        tr = obs.train_idx
        w, n = int(tr[0]), int(tr[-1]) + 1
        if not np.array_equal(tr, np.arange(w, n)):
            raise NotImplementedError("M3 needs a contiguous training window")
        mmm_kw = {}
        y = obs.y[:n].astype(float, copy=True)
        s0 = w if w > 0 else self.scale_from
        if w > 0:
            # Masked likelihood (v1.2 P1a): rows [0, w) are adstock history only. Their Y is replaced by a
            # placeholder before it reaches the model, the target scale uses only [w, n), and a Potential
            # removes their likelihood terms (see _mask_history_likelihood).
            y[:w] = y[w:].mean()
        if s0:
            from pymc_marketing.mmm.scaling import DataDerivedScaling, FixedScaling, Scaling

            mmm_kw["scaling"] = Scaling(target=FixedScaling(dims=(), value=float(y[s0:].max())),
                                        channel=DataDerivedScaling(method="max", dims=()))
        self.likelihood_window = (w, n)
        self.mmm = MMM(
            date_column="date",
            channel_columns=list(obs.channel_names),
            control_columns=list(obs.control_names) + ["trend"],
            adstock=adstock,
            saturation=saturation,
            yearly_seasonality=2,
            **mmm_kw,
        )
        X, y = self._frame(obs, obs.C).iloc[:n], pd.Series(y, name="y")
        self.mmm.build_model(X, y)
        if w > 0:
            self._mask_history_likelihood(self.mmm.model, w)
        return X, y

    def fit(self, obs: ObservedDataset, *, seed: int) -> None:
        self.seed = seed
        X, y = self.build(obs)
        idata = self.mmm.fit(X, y, random_seed=seed, progressbar=False, nuts_sampler="nutpie", **self.sample_kw)
        self.scale = float(np.asarray(idata["constant_data"]["target_scale"]))
        self.diag = {**mcmc_diagnostics(idata, self.FREE), **self._geometry(idata)}
        if self.keep_posterior:
            post = idata["posterior"].to_dataset()
            self._posterior = {n: np.asarray(post[n]) for n in self.FREE}
            self._posterior["diverging"] = np.asarray(idata["sample_stats"].to_dataset()["diverging"])
        y_s, c_s = self._posterior_predictive(obs, obs.C, ["y", "channel_contribution"])
        self._y_samples, self._c_samples = y_s, c_s
        if self.keep_posterior:
            # P1 ROPE estimand per draw: mean weekly direct contribution over [warmup, n_train), original units
            n = int(obs.train_idx[-1]) + 1
            self._posterior["contrib_mean_w8_train"] = c_s[:, obs.warmup:n, :].mean(1)

    @staticmethod
    def _mask_history_likelihood(model, w: int) -> None:
        """Adds ``Potential(-sum_{t<w} log p(y_t | mu_t, sigma))`` built from the model's own per-week
        likelihood terms, so the total log-density only contains weeks ``[w, n)``. The standard
        pymc-marketing graph (adstock over the full sequence, deterministics, ``y``) is unchanged."""
        import pymc as pm
        import pytensor.tensor as pt

        terms = model.logp(vars=[model["y"]], sum=False)[0]
        terms = getattr(terms, "values", terms)  # XTensor -> TensorVariable, dim 0 = date
        with model:
            pm.Potential(MASK_POTENTIAL, -pt.sum(terms[:w]))

    def _posterior_predictive(self, obs: ObservedDataset, C: np.ndarray, names: list[str]):
        pp = self.mmm.sample_posterior_predictive(
            self._frame(obs, C),
            extend_idata=False,
            include_last_observations=False,
            random_seed=self.seed,
            progressbar=False,
            var_names=names,
        )
        out = []
        for n in names:
            da = pp[n]
            if n == "y":
                out.append(np.asarray(da.transpose("sample", "date")) * self.scale)
            else:
                out.append(np.asarray(da.transpose("sample", "date", "channel")) * self.scale)
        return out

    def predict(self, obs: ObservedDataset) -> np.ndarray:
        return self._y_samples.mean(0)

    def contributions(self, obs: ObservedDataset) -> np.ndarray:
        return self._c_samples.mean(0)

    def contribution_intervals(self, obs: ObservedDataset) -> dict:
        return _intervals(self._c_samples)

    def y_intervals(self, obs: ObservedDataset) -> dict:
        return _intervals(self._y_samples)

    def channel_response(self, obs: ObservedDataset, C_alt: np.ndarray) -> np.ndarray:
        """Posterior mean of channel_contribution (original units) for alternative channel data.

        Compiled once from the fitted model graph: free media RVs and ``channel_data`` are replaced
        by inputs and the function is evaluated for every posterior draw (no resampling)."""
        if not hasattr(self, "_resp_fn"):
            self._build_response_fn()
        total = np.zeros((C_alt.shape[0], C_alt.shape[1]))
        X = np.asarray(C_alt, dtype=float)
        for draw in self._media_draws:
            total += self._resp_fn(X, *draw)
        return total / len(self._media_draws) * self.scale

    def _build_response_fn(self) -> None:
        import pytensor
        import pytensor.tensor as pt
        from pytensor.graph.replace import clone_replace

        model = self.mmm.model
        names = [n for n in ("adstock_alpha", "saturation_lam", "saturation_beta") if n in model.named_vars]
        rvs = [model[n] for n in names]
        ins = [pt.tensor(name=f"{n}_in", dtype=rv.dtype, shape=rv.type.shape) for n, rv in zip(names, rvs)]
        data = model["channel_data"]
        x_in = pt.matrix("channel_data_in", dtype="float64")
        out = clone_replace(model["channel_contribution"], {**dict(zip(rvs, ins)), data: x_in})
        self._resp_fn = pytensor.function([x_in, *ins], out, on_unused_input="ignore")
        post = self.mmm.idata["posterior"].to_dataset()
        stacked = {n: np.asarray(post[n]).reshape(-1, *np.asarray(post[n]).shape[2:]) for n in names}
        self._media_draws = list(zip(*(stacked[n] for n in names)))

    def diagnostics(self) -> dict:
        return {**self.diag, "sampler": self.sample_kw, "target_scale": self.scale, "prior_variant": self.prior_variant,
                "likelihood_window": list(self.likelihood_window), "scale_from": self.scale_from,
                "architecture": "pymc_marketing.mmm.MMM standard + Potential masking history likelihood"
                if self.likelihood_window[0] > 0 else "pymc_marketing.mmm.MMM standard"}

    def posterior_arrays(self) -> dict:
        return getattr(self, "_posterior", {})

    def _components(self, adstock_cls, saturation_cls):
        """Default pymc-marketing priors, or the pre-registered V3 variant (see reports/mcmc_diagnostics.md)."""
        if self.prior_variant is None:
            return adstock_cls(l_max=8), saturation_cls()
        from pymc_extras.prior import Prior

        if self.prior_variant == "v3":
            return adstock_cls(l_max=8), saturation_cls(priors=V3_SATURATION_PRIORS(Prior))
        raise ValueError(f"unknown prior_variant {self.prior_variant!r}")

    @staticmethod
    def _geometry(idata) -> dict:
        """Posterior geometry summaries used to diagnose sampling problems (never uses the truth)."""
        post = idata["posterior"].to_dataset()
        div = np.asarray(idata["sample_stats"].to_dataset()["diverging"]).ravel().astype(bool)
        lam = np.asarray(post["saturation_lam"]).reshape(-1, post["saturation_lam"].shape[-1])
        beta = np.asarray(post["saturation_beta"]).reshape(lam.shape)
        alpha = np.asarray(post["adstock_alpha"]).reshape(lam.shape)
        corr_lb = [float(np.corrcoef(np.log(lam[:, k]), np.log(beta[:, k]))[0, 1]) for k in range(lam.shape[1])]
        out = {
            "corr_log_lam_log_beta_by_channel": corr_lb,
            "max_abs_corr_log_lam_log_beta": float(np.nanmax(np.abs(corr_lb))),
            "alpha_mass_below_0.05": float(np.mean(alpha < 0.05)),
            "lam_posterior_median_by_channel": np.median(lam, 0).tolist(),
            "lam_posterior_q95_by_channel": np.quantile(lam, 0.95, 0).tolist(),
            "beta_posterior_cv_by_channel": (beta.std(0) / beta.mean(0)).tolist(),
        }
        if div.any():
            # where divergences concentrate: mean log-lam of divergent vs non-divergent draws
            out["div_mean_log_lam_minus_rest"] = (np.log(lam[div]).mean(0) - np.log(lam[~div]).mean(0)).tolist()
            out["div_mean_alpha_minus_rest"] = (alpha[div].mean(0) - alpha[~div].mean(0)).tolist()
        return out


class OracleStructureKnownPlugin(Estimator):
    """PRIVILEGED reference: ``pg.sample_oracle`` knows the DAG, mechanism families and priors and
    conditions on observed C/Z as fixed inputs. NOT the full SCM posterior. Future outcomes are
    replaced by the train mean before the call and excluded from the likelihood by
    ``observed_indices`` (double protection against leakage)."""

    model_id = "M4_oracle_plugin"
    family = "oracle"
    information_set = PRIVILEGED
    privileged = True

    def __init__(self, draws: int = 500, tune: int = 500, chains: int = 2, cores: int = 2, latent: str = "marginal",
                 target_accept: float = 0.9):
        self.cfg_kw = dict(draws=draws, tune=tune, chains=chains, cores=cores, latent=latent, target_accept=target_accept)

    def attach_privileged(self, world) -> None:
        self._world = world

    def fit(self, obs: ObservedDataset, *, seed: int) -> None:
        import pymc_generator as pg

        w = self._world
        n_rows = w.oracle_model(latent=self.cfg_kw["latent"])["observed_indices_data"].get_value().size
        self.oracle_warmup = w.n_time_steps - n_rows
        n_train = int(obs.train_idx[-1]) + 1
        y = np.asarray(w.data["outcome"], dtype=float).copy()
        y[n_train:] = y[:n_train].mean()
        masked = dataclasses.replace(w, data={**w.data, "outcome": y})
        cfg = pg.OracleSamplingConfig(random_seed=seed, **self.cfg_kw)
        res = pg.sample_oracle(masked, cfg, observed_indices=np.arange(n_train - self.oracle_warmup))
        post = res.idata["posterior"].to_dataset()
        self._c_samples = np.asarray(post["contributions"]).reshape(-1, obs.T, obs.K)
        self._mu_samples = np.asarray(post["outcome_mu"]).reshape(-1, obs.T)
        rc = res.receipt.to_dict()
        d = rc["diagnostics"]
        rhat, ess, div = d["rhat"].get("value"), d["ess_bulk"].get("value"), d["divergences"].get("value")
        self.diag = {
            "rhat_max": rhat,
            "ess_bulk_min": ess,
            "divergences": div,
            "converged_strict": rc["health"]["status"] == "healthy",
            "converged_pilot": bool(rhat is not None and ess is not None and rhat <= RHAT_MAX and ess >= ESS_MIN_PILOT and div == 0),
            "health_failures": [f["code"] for f in rc["health"]["failure_reasons"]],
            "oracle_warmup": self.oracle_warmup,
            "latent": self.cfg_kw["latent"],
            "limitations": rc["limitations"],
            "elapsed_seconds": rc["timing"]["elapsed_seconds"],
        }

    def predict(self, obs: ObservedDataset) -> np.ndarray:
        return self._mu_samples.mean(0)

    def contributions(self, obs: ObservedDataset) -> np.ndarray:
        return self._c_samples.mean(0)

    def contribution_intervals(self, obs: ObservedDataset) -> dict:
        return _intervals(self._c_samples)

    def diagnostics(self) -> dict:
        return {**self.diag, "sampler": self.cfg_kw}
