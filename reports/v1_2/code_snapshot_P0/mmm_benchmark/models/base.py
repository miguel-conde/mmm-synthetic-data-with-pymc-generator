"""Common estimator interface.

``fit`` receives ``ObservedDataset.fit_view()`` (future y masked) and NEVER a TruthRegistry.
Privileged references receive the generator world through a separate, explicitly named hook.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..schema import BLIND, ObservedDataset

N_FOURIER = 2
PERIOD = 52.1775


def calendar_features(T: int) -> np.ndarray:
    """Trend (t/T) + annual Fourier terms; deterministic, no data-dependent statistics."""
    t = np.arange(T, dtype=float)
    cols = [t / T]
    for h in range(1, N_FOURIER + 1):
        cols += [np.sin(2 * np.pi * h * t / PERIOD), np.cos(2 * np.pi * h * t / PERIOD)]
    return np.column_stack(cols)


def inner_split(train_idx: np.ndarray, frac: float = 0.2) -> tuple[np.ndarray, np.ndarray]:
    n_val = max(4, int(round(frac * len(train_idx))))
    return train_idx[:-n_val], train_idx[-n_val:]


class Estimator(ABC):
    model_id: str = ""
    family: str = ""
    information_set: str = BLIND
    privileged: bool = False

    @abstractmethod
    def fit(self, obs: ObservedDataset, *, seed: int) -> None: ...

    @abstractmethod
    def predict(self, obs: ObservedDataset) -> np.ndarray:
        """Point prediction of y for all T weeks (conditional on observed C and Z)."""

    def contributions(self, obs: ObservedDataset) -> np.ndarray | None:
        """(T, K) estimate of historical_observed_path_response, or None if not supported."""
        return None

    def channel_response(self, obs: ObservedDataset, C_alt: np.ndarray) -> np.ndarray | None:
        """(T, K) model response to an alternative treatment matrix (exogeneity assumed)."""
        return None

    def predict_inputs(self, obs: ObservedDataset, C_alt: np.ndarray) -> np.ndarray | None:
        """Predicted y under alternative inputs; for non-causal models this is a naive plug-in."""
        return None

    def contribution_intervals(self, obs: ObservedDataset) -> dict | None:
        return None

    def y_intervals(self, obs: ObservedDataset) -> dict | None:
        return None

    def explanation(self, obs: ObservedDataset) -> np.ndarray | None:
        return None

    def diagnostics(self) -> dict:
        return {}
