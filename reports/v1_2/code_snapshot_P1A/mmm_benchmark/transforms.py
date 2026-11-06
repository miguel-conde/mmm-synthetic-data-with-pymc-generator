"""Media transforms.

Blind transforms (numpy) are generic analyst choices. ``true_channel_response`` evaluates the
generator's own carryover/saturation and is PRIVILEGED: only M2p/M2p_D and tests may call it.
"""

from __future__ import annotations

import numpy as np

L_MAX = 8


def geometric_adstock(x: np.ndarray, alpha: float, l_max: int = L_MAX) -> np.ndarray:
    """Normalized causal geometric adstock along axis 0, zero history before t=0."""
    w = alpha ** np.arange(l_max)
    w = w / w.sum()
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(x)
    for lag, wl in enumerate(w):
        if lag == 0:
            out += wl * x
        else:
            out[lag:] += wl * x[:-lag]
    return out


def mm_saturation(x: np.ndarray, kappa: float) -> np.ndarray:
    """x / (x + kappa); kappa = inf means linear (identity)."""
    if not np.isfinite(kappa):
        return np.asarray(x, dtype=float)
    return x / (x + kappa)


_COMPILED: dict[int, tuple[object, object]] = {}


def _compiled_true_response(world, shape: tuple[int, int]):
    import pytensor
    import pytensor.tensor as pt
    from pymc_generator import symbolic_graph as sg

    key = (id(world), shape)
    if key not in _COMPILED:
        if len(_COMPILED) > 4:
            _COMPILED.clear()
        C = pt.tensor("C", dtype="float64", shape=shape)
        scale = np.asarray(world.data["saturation_scale"], dtype=float)
        cols = [
            sg._saturate_col(sg._carryover_col(C[:, k], world.params, k), pt.as_tensor_variable(scale[k]), world.params, k)
            for k in range(shape[1])
        ]
        # the world is kept in the value so its id() cannot be reused while cached
        _COMPILED[key] = (world, pytensor.function([C], pt.stack(cols, axis=1)))
    return _COMPILED[key][1]


def true_channel_response(world, C: np.ndarray) -> np.ndarray:
    """PRIVILEGED. Ungated true response f_k(adstock_k(C_k)) per channel, zero history before t=0.

    Multiplying column k by ``g_cy[k] * beta[k]`` reproduces ``contributions_observed`` exactly
    for t >= l_max when ``C`` is the observed treatment.
    """
    C = np.asarray(C, dtype=float)
    if C.shape[1] == 0:
        return np.zeros_like(C)
    return np.asarray(_compiled_true_response(world, C.shape)(C))
