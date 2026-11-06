"""Typed data contracts: what models may see vs. what only the evaluator may see."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

TRUTH_SEMANTICS_VERSION = "1.0"
WARMUP = 8  # weeks excluded from attribution metrics: generator burn-in = l_max = 8
TRAIN_FRAC = 0.8

# estimand ids (see docs/estimands.md)
OBS_PATH = "historical_observed_path_response"
DIRECT_ISOLATED = "historical_direct_isolated"
INDIRECT_TOTAL = "historical_indirect_total"
BASELINE_FULL = "historical_baseline_full"
BASELINE_NO_NOISE = "baseline_no_observation_noise"
DO_TOTAL = "interventional_total_effect"
RESPONSE_PER_UNIT = "incremental_response_per_treatment_unit"
DECISION_VALUE = "decision_value"
PREDICTION = "prediction_y"
PREDICTIVE_EXPLANATION = "predictive_explanation"

# information sets
BLIND = "blind_observed"
PRIVILEGED = "privileged"

# estimand -> which model families can legitimately target it
COMPARABILITY: dict[str, dict[str, str]] = {
    "regression": {
        OBS_PATH: "yes",
        DIRECT_ISOLATED: "not_applicable",
        DO_TOTAL: "model_implied_under_exogeneity_assumption",
        PREDICTION: "yes",
        "intervals": "no",
    },
    "bayesian_mmm": {
        OBS_PATH: "yes",
        DIRECT_ISOLATED: "not_applicable",
        DO_TOTAL: "model_implied_under_exogeneity_assumption",
        PREDICTION: "yes",
        "intervals": "yes",
    },
    "oracle": {
        OBS_PATH: "yes",
        DIRECT_ISOLATED: "not_applicable",
        DO_TOTAL: "not_applicable",
        PREDICTION: "yes",
        "intervals": "yes",
    },
    "tree": {
        OBS_PATH: "not_applicable",
        DIRECT_ISOLATED: "not_applicable",
        DO_TOTAL: "not_applicable",
        PREDICTION: "yes",
        "intervals": "no",
    },
    "naive": {
        OBS_PATH: "not_applicable",
        DIRECT_ISOLATED: "not_applicable",
        DO_TOTAL: "not_applicable",
        PREDICTION: "yes",
        "intervals": "no",
    },
}


def temporal_split(T: int) -> tuple[np.ndarray, np.ndarray]:
    n_train = int(round(TRAIN_FRAC * T))
    return np.arange(n_train), np.arange(n_train, T)


@dataclass(frozen=True)
class ObservedDataset:
    """Everything an ordinary (blind) analyst sees. Never contains latent D or generator truth."""

    world_id: str
    scenario_id: str
    structure_cell_id: str
    T: int
    seed: int
    dates: np.ndarray
    y: np.ndarray
    C: np.ndarray
    Z: np.ndarray
    channel_names: tuple[str, ...]
    control_names: tuple[str, ...]
    train_idx: np.ndarray
    test_idx: np.ndarray
    warmup: int = WARMUP

    @property
    def K(self) -> int:
        return self.C.shape[1]

    @property
    def M(self) -> int:
        return self.Z.shape[1]

    def fit_view(self) -> ObservedDataset:
        """Copy with future outcomes replaced by NaN: the only object passed to ``fit``."""
        y = self.y.astype(float, copy=True)
        y[self.test_idx] = np.nan
        return replace(self, y=y)

    def eval_idx(self, split: str) -> np.ndarray:
        idx = self.train_idx if split == "train" else self.test_idx
        return idx[idx >= self.warmup]


@dataclass(frozen=True)
class TruthRegistry:
    """Generator truth. Only the evaluator and explicitly privileged references may read it."""

    world_id: str
    arrays: dict[str, np.ndarray]
    g: dict[str, np.ndarray]
    channel_roles: tuple[str, ...]
    meta: dict[str, Any] = field(default_factory=dict)
    semantics_version: str = TRUTH_SEMANTICS_VERSION

    def __getitem__(self, key: str) -> np.ndarray:
        return self.arrays[key]


@dataclass
class ModelOutput:
    model_id: str
    world_id: str
    family: str
    information_set: str
    fit_status: str  # ok | failed | not_applicable
    seed: int
    runtime_s: float = float("nan")
    peak_rss_mb: float = float("nan")
    y_pred: np.ndarray | None = None
    contributions: np.ndarray | None = None  # (T, K), estimand OBS_PATH
    contrib_intervals: dict[float, tuple[np.ndarray, np.ndarray]] | None = None
    y_intervals: dict[float, tuple[np.ndarray, np.ndarray]] | None = None
    explanation: np.ndarray | None = None  # (T, K) predictive explanation only
    diagnostics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
