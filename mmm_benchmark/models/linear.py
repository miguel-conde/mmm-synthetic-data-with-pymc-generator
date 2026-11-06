"""M0 OLS, M1 Ridge, M2 engineered adstock/saturation regression, M2p privileged true transforms."""

from __future__ import annotations

import itertools

import numpy as np

from ..schema import PRIVILEGED, ObservedDataset
from ..transforms import geometric_adstock, mm_saturation, true_channel_response
from .base import Estimator, calendar_features, inner_split

RIDGE_GRID = np.logspace(-3, 3, 13)
ALPHA_GRID = (0.0, 0.3, 0.5, 0.7, 0.85)
KAPPA_GRID = (0.25, 0.5, 1.0, 2.0, 4.0, np.inf)


def _ols(X: np.ndarray, y: np.ndarray, ridge: float = 0.0) -> tuple[np.ndarray, float]:
    """Least squares with unpenalized intercept; ``ridge`` on standardized columns."""
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 1e-12, sd, 1.0)
    Xs = (X - mu) / sd
    ym = y.mean()
    if ridge > 0:
        A = Xs.T @ Xs + ridge * np.eye(Xs.shape[1])
        w = np.linalg.solve(A, Xs.T @ (y - ym))
    else:
        w = np.linalg.lstsq(Xs, y - ym, rcond=None)[0]
    coef = w / sd
    return coef, float(ym - mu @ coef)


def _rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


class LinearMMM(Estimator):
    """y = intercept + Σ_k b_k·media_k + Z·γ + calendar·δ. Contribution_k = b_k·media_k (zero at zero media)."""

    family = "regression"
    use_controls = True
    ridge_select = False

    def media(self, obs: ObservedDataset, C: np.ndarray) -> np.ndarray:
        return C

    def extra_controls(self, obs: ObservedDataset) -> np.ndarray | None:
        return None

    def design(self, obs: ObservedDataset, C: np.ndarray) -> np.ndarray:
        parts = [self.media(obs, C)]
        if self.use_controls and obs.M:
            parts.append(obs.Z)
        extra = self.extra_controls(obs)
        if extra is not None:
            parts.append(extra)
        parts.append(calendar_features(obs.T))
        return np.column_stack(parts)

    def _fit_design(self, X: np.ndarray, y: np.ndarray, train: np.ndarray) -> None:
        self.ridge_alpha = 0.0
        if self.ridge_select:
            tr, va = inner_split(train)
            scores = []
            for a in RIDGE_GRID:
                c, b = _ols(X[tr], y[tr], a)
                scores.append(_rmse(X[va] @ c + b, y[va]))
            self.ridge_alpha = float(RIDGE_GRID[int(np.argmin(scores))])
        self.coef, self.intercept = _ols(X[train], y[train], self.ridge_alpha)

    def fit(self, obs: ObservedDataset, *, seed: int) -> None:
        self.K = obs.K
        self._fit_design(self.design(obs, obs.C), obs.y, obs.train_idx)

    def predict(self, obs: ObservedDataset) -> np.ndarray:
        return self.design(obs, obs.C) @ self.coef + self.intercept

    def contributions(self, obs: ObservedDataset) -> np.ndarray:
        return self.media(obs, obs.C) * self.coef[: self.K]

    def channel_response(self, obs: ObservedDataset, C_alt: np.ndarray) -> np.ndarray:
        return self.media(obs, C_alt) * self.coef[: self.K]

    def diagnostics(self) -> dict:
        return {"ridge_alpha": self.ridge_alpha, "media_coef": self.coef[: self.K].tolist()}


class OLSRaw(LinearMMM):
    model_id = "M0_ols"


class RidgeRaw(LinearMMM):
    model_id = "M1_ridge"
    ridge_select = True


class EngineeredRegression(LinearMMM):
    """Per-channel geometric adstock + x/(x+κ) saturation chosen by coordinate search on a
    temporal validation split; κ = kappa_mult × train-mean of the adstocked channel."""

    model_id = "M2_adstock_sat"

    def _transform(self, C: np.ndarray, alphas, kmults, scales) -> np.ndarray:
        cols = []
        for k in range(C.shape[1]):
            ad = geometric_adstock(C[:, k], alphas[k])
            cols.append(mm_saturation(ad, kmults[k] * scales[k]))
        return np.column_stack(cols)

    def _scales(self, C: np.ndarray, alphas, idx: np.ndarray) -> np.ndarray:
        return np.array(
            [max(geometric_adstock(C[:, k], alphas[k])[idx].mean(), 1e-8) for k in range(C.shape[1])]
        )

    def media(self, obs: ObservedDataset, C: np.ndarray) -> np.ndarray:
        return self._transform(C, self.alphas, self.kmults, self.scales)

    def fit(self, obs: ObservedDataset, *, seed: int) -> None:
        K = self.K = obs.K
        tr, va = inner_split(obs.train_idx)
        alphas, kmults = [0.5] * K, [np.inf] * K

        def score(al, km) -> float:
            self.alphas, self.kmults = al, km
            self.scales = self._scales(obs.C, al, tr)
            X = self.design(obs, obs.C)
            c, b = _ols(X[tr], obs.y[tr], 1e-6)
            return _rmse(X[va] @ c + b, obs.y[va])

        best = score(alphas, kmults)
        for _ in range(2):
            for k in range(K):
                for a, km in itertools.product(ALPHA_GRID, KAPPA_GRID):
                    al, kms = list(alphas), list(kmults)
                    al[k], kms[k] = a, km
                    s = score(al, kms)
                    if s < best - 1e-12:
                        best, alphas, kmults = s, al, kms
        self.alphas, self.kmults = alphas, kmults
        self.scales = self._scales(obs.C, alphas, obs.train_idx)
        self.val_rmse = best
        self._fit_design(self.design(obs, obs.C), obs.y, obs.train_idx)

    def diagnostics(self) -> dict:
        return {
            **super().diagnostics(),
            "alphas": list(map(float, self.alphas)),
            "kappa_mult": [float(k) if np.isfinite(k) else "linear" for k in self.kmults],
            "val_rmse": self.val_rmse,
        }


class EngineeredNoControls(EngineeredRegression):
    model_id = "M2_adstock_sat_noZ"
    use_controls = False


class PrivilegedTrueTransform(LinearMMM):
    """PRIVILEGED: generator's true carryover+saturation per channel; coefficients by OLS."""

    model_id = "M2p_true_transforms"
    information_set = PRIVILEGED
    privileged = True

    def attach_privileged(self, world) -> None:
        self._world = world
        self._cache: dict[bytes, np.ndarray] = {}

    def media(self, obs: ObservedDataset, C: np.ndarray) -> np.ndarray:
        key = np.ascontiguousarray(C, dtype=float).tobytes()
        if key not in self._cache:
            self._cache[key] = true_channel_response(self._world, C)
        return self._cache[key]


class PrivilegedTrueTransformWithLatent(PrivilegedTrueTransform):
    """PRIVILEGED: as M2p plus the latent demand D as a control (methodological check for E03)."""

    model_id = "M2p_true_transforms_plus_D"

    def extra_controls(self, obs: ObservedDataset) -> np.ndarray:
        return np.asarray(self._world.data["latent_unobserved"], dtype=float)


class NaiveLast(Estimator):
    model_id = "N0_naive_last"
    family = "naive"

    def fit(self, obs: ObservedDataset, *, seed: int) -> None:
        self.last = float(obs.y[obs.train_idx][-1])

    def predict(self, obs: ObservedDataset) -> np.ndarray:
        out = np.full(obs.T, self.last)
        tr = obs.train_idx
        out[tr[1:]] = obs.y[tr[:-1]]
        out[tr[0]] = obs.y[tr[0]]
        return out


class NaiveMean(Estimator):
    model_id = "N1_naive_mean"
    family = "naive"

    def fit(self, obs: ObservedDataset, *, seed: int) -> None:
        self.mean = float(np.mean(obs.y[obs.train_idx]))

    def predict(self, obs: ObservedDataset) -> np.ndarray:
        return np.full(obs.T, self.mean)
