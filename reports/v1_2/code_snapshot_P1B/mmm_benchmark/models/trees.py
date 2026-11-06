"""M5 XGBoost, M6 LightGBM: predictive models. Their SHAP values are stored only as
``predictive_explanation`` and are never scored as causal contributions."""

from __future__ import annotations

import itertools

import numpy as np

from ..schema import ObservedDataset
from .base import Estimator, calendar_features, inner_split

LAGS = (1, 2, 3, 4)
ROLL = 8
N_THREADS = 2


def _lag(x: np.ndarray, lag: int) -> np.ndarray:
    out = np.zeros_like(x)
    out[lag:] = x[:-lag]
    return out


def _roll_mean(x: np.ndarray, w: int) -> np.ndarray:
    cs = np.concatenate([[0.0], np.cumsum(x)])
    idx = np.arange(1, len(x) + 1)
    lo = np.maximum(0, idx - w)
    return (cs[idx] - cs[lo]) / (idx - lo)


def tree_features(obs: ObservedDataset, C: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Causal features only (no future values). Returns (X, owner) where owner[j] = channel or -1."""
    cols, owner = [], []
    for k in range(C.shape[1]):
        c = C[:, k]
        for f in (c, *(_lag(c, lag) for lag in LAGS), _roll_mean(c, ROLL)):
            cols.append(f)
            owner.append(k)
    for m in range(obs.M):
        cols.append(obs.Z[:, m])
        owner.append(-1)
    cal = calendar_features(obs.T)
    for j in range(cal.shape[1]):
        cols.append(cal[:, j])
        owner.append(-1)
    return np.column_stack(cols), np.array(owner)


class _TreeBase(Estimator):
    family = "tree"
    grid: dict = {}

    def _make(self, params: dict, seed: int): ...

    def _shap(self, X: np.ndarray) -> np.ndarray: ...

    def fit(self, obs: ObservedDataset, *, seed: int) -> None:
        X, self.owner = tree_features(obs, obs.C)
        y = obs.y
        tr, va = inner_split(obs.train_idx)
        best, best_p = np.inf, None
        keys = list(self.grid)
        for vals in itertools.product(*self.grid.values()):
            p = dict(zip(keys, vals))
            m = self._make(p, seed)
            m.fit(X[tr], y[tr])
            s = float(np.sqrt(np.mean((m.predict(X[va]) - y[va]) ** 2)))
            if s < best:
                best, best_p = s, p
        self.params, self.val_rmse = best_p, best
        self.model = self._make(best_p, seed)
        self.model.fit(X[obs.train_idx], y[obs.train_idx])

    def predict(self, obs: ObservedDataset) -> np.ndarray:
        return self.model.predict(tree_features(obs, obs.C)[0])

    def predict_inputs(self, obs: ObservedDataset, C_alt: np.ndarray) -> np.ndarray:
        return self.model.predict(tree_features(obs, C_alt)[0])

    def explanation(self, obs: ObservedDataset) -> np.ndarray:
        contrib = self._shap(tree_features(obs, obs.C)[0])[:, :-1]
        return np.column_stack([contrib[:, self.owner == k].sum(1) for k in range(obs.K)])

    def diagnostics(self) -> dict:
        return {"params": self.params, "val_rmse": self.val_rmse}


class XGBoostPredictor(_TreeBase):
    model_id = "M5_xgboost"
    grid = {"max_depth": (2, 3, 4), "learning_rate": (0.03, 0.1), "n_estimators": (300,)}

    def _make(self, p: dict, seed: int):
        from xgboost import XGBRegressor

        return XGBRegressor(
            **p, subsample=0.8, colsample_bytree=0.8, random_state=seed, n_jobs=N_THREADS, verbosity=0
        )

    def _shap(self, X: np.ndarray) -> np.ndarray:
        from xgboost import DMatrix

        return self.model.get_booster().predict(DMatrix(X), pred_contribs=True)


class LightGBMPredictor(_TreeBase):
    model_id = "M6_lightgbm"
    grid = {"num_leaves": (4, 8, 15), "learning_rate": (0.03, 0.1), "n_estimators": (300,)}

    def _make(self, p: dict, seed: int):
        from lightgbm import LGBMRegressor

        return LGBMRegressor(
            **p,
            min_child_samples=5,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            random_state=seed,
            n_jobs=N_THREADS,
            verbose=-1,
        )

    def _shap(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X, pred_contrib=True)
