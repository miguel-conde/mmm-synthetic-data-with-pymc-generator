"""Paired counterfactuals: do(C_k = a) on the SAME SCM with the SAME exogenous innovations.

The generator exposes ``SCM.replay()`` but no ``do`` operator. This engine rebuilds the world's
generative graph, binds every primitive draw (parameters AND innovations eps_*) exactly as
``replay()`` does, and replaces the per-channel treatment tensors (post-softplus, post-schedule,
post-shock) with ``switch(mask, value, natural)``. Replacements are applied sequentially in
topological (index) order so downstream C→C children see the intervened parents.
Results are only labelled ``true_interventional_effect`` after ``validate_engine`` passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pytensor.tensor as pt
from pymc.pytensorf import compile as compile_pymc
from pytensor.graph.replace import clone_replace

from .transforms import true_channel_response

TOL = 1e-9
VALIDATED = "validated"
BLOCKED = "blocked_counterfactual_not_validated"


def _find_join(var):
    node = var
    while node.owner is not None:
        if type(node.owner.op).__name__ == "Join":
            return node
        node = node.owner.inputs[0]
    raise RuntimeError("could not locate the per-channel Join behind 'treatments'")


class InterventionEngine:
    OUTPUTS = ("outcome", "treatments", "contributions_observed")

    def __init__(self, world):
        from pymc_generator.world_model import build_world_model

        if "structural" not in world.extras:
            raise ValueError("world lacks primitive provenance; needs a world from sample_scm")
        self.world = world
        self.T = world.n_time_steps
        self.K = world.n_treatments
        model, _, _ = build_world_model(
            world.g,
            world.cfg,
            world.extras["structural"],
            world.cfg.n_time_steps,
            prior_cond=world.extras.get("prior_cond"),
        )
        free = list(model.free_RVs)
        prim = world.primitive_parameters
        inputs = [
            pt.tensor(name=f"{rv.name}_bound", dtype=rv.dtype, shape=rv.type.shape) for rv in free
        ]
        self._values = [prim[rv.name] for rv in free]
        join = _find_join(model["treatments"])
        offset = len(join.owner.inputs) - self.K  # 1 on PyTensor versions with a symbolic axis input
        c_cols = [join.owner.inputs[offset + k].owner.inputs[0] for k in range(self.K)]
        self.T_full = int(join.type.shape[0])
        self.burn_in = self.T_full - self.T

        outs = [model[name] for name in self.OUTPUTS]
        bound = clone_replace(outs + c_cols, dict(zip(free, inputs)))
        cur_outs, cur_cols = list(bound[: len(outs)]), list(bound[len(outs) :])
        masks = [pt.vector(f"do_mask_{k}", dtype="float64") for k in range(self.K)]
        vals = [pt.vector(f"do_value_{k}", dtype="float64") for k in range(self.K)]
        for k in range(self.K):
            new_k = pt.switch(pt.gt(masks[k], 0), vals[k], cur_cols[k])
            rest = clone_replace(cur_outs + cur_cols[k + 1 :], {cur_cols[k]: new_k})
            cur_outs = list(rest[: len(outs)])
            cur_cols = cur_cols[:k] + [new_k] + list(rest[len(outs) :])
        with model:
            self._fn = compile_pymc(
                inputs=inputs + masks + vals,
                outputs=cur_outs,
                mode="FAST_COMPILE",
                on_unused_input="ignore",
            )

    def run(self, do: dict[int, tuple[np.ndarray, np.ndarray]] | None = None) -> dict[str, np.ndarray]:
        """``do``: channel -> (mask (T,), value (T,)) in reported-window coordinates."""
        do = do or {}
        pad = np.zeros(self.burn_in)
        masks, vals = [], []
        for k in range(self.K):
            if k in do:
                m, v = do[k]
                masks.append(np.concatenate([pad, np.asarray(m, dtype=float)]))
                vals.append(np.concatenate([pad, np.asarray(v, dtype=float)]))
            else:
                masks.append(np.zeros(self.T_full))
                vals.append(np.zeros(self.T_full))
        res = self._fn(*self._values, *masks, *vals)
        return {name: np.asarray(r) for name, r in zip(self.OUTPUTS, res)}

    def effect(self, do: dict[int, tuple[np.ndarray, np.ndarray]]) -> np.ndarray:
        """Per-week ΔY = Y[do] − Y[factual]; exogenous noise is shared so it cancels exactly."""
        return self.run(do)["outcome"] - self.run()["outcome"]


@dataclass
class EngineValidation:
    world_id: str
    status: str
    checks: dict[str, dict] = field(default_factory=dict)


def _descendants(g_cc: np.ndarray, k: int) -> set[int]:
    out, frontier = set(), {k}
    while frontier:
        nxt = {j for i in frontier for j in np.flatnonzero(g_cc[i])} - out
        out |= nxt
        frontier = nxt
    return out


def validate_engine(engine: InterventionEngine, world_id: str, roles: tuple[str, ...]) -> EngineValidation:
    w = engine.world
    T, K = engine.T, engine.K
    obs = w.data
    C = np.asarray(obs["treatments"])
    g_cc = np.asarray(w.g["g_cc"]) != 0
    checks: dict[str, dict] = {}

    fact = engine.run()
    checks["factual_reproduces_world"] = {
        "max_abs": float(np.abs(fact["outcome"] - obs["outcome"]).max()),
    }
    explicit_null = engine.run({k: (np.ones(T), C[:, k]) for k in range(K)})
    checks["do_null_all_channels"] = {
        "max_abs": float(np.abs(explicit_null["outcome"] - obs["outcome"]).max()),
    }

    nulls = [k for k, r in enumerate(roles) if r == "isolated"]
    if nulls:
        worst = max(float(np.abs(engine.effect({k: (np.ones(T), np.zeros(T))})).max()) for k in nulls)
        checks["no_path_channel_zero_effect"] = {"max_abs": worst, "channels": nulls}
    else:
        checks["no_path_channel_zero_effect"] = {"status": "not_testable"}

    direct = [k for k, r in enumerate(roles) if r == "direct"]
    s = max(T // 2, 8)
    if direct:
        k = direct[0]
        mask = (np.arange(T) >= s).astype(float)
        dy = engine.effect({k: (mask, np.zeros(T))})
        checks["no_effect_before_intervention"] = {
            "max_abs_before": float(np.abs(dy[:s]).max()),
            "total_after": float(dy[s:].sum()),
            "max_abs": float(np.abs(dy[:s]).max()),
        }
        k_iso = next((k for k in direct if not g_cc[k].any()), None)
        if k_iso is not None:
            a = np.where(mask > 0, 0.0, C[:, k_iso])
            dy = engine.effect({k_iso: (mask, np.zeros(T))})
            gate = float(w.g["g_cy"][k_iso] * w.params["beta"][k_iso])
            f_alt = true_channel_response(w, np.column_stack([a if j == k_iso else C[:, j] for j in range(K)]))[:, k_iso]
            f_obs = true_channel_response(w, C)[:, k_iso]
            expected = gate * (f_alt - f_obs)
            checks["no_mediation_matches_channel_response"] = {
                "channel": k_iso,
                "max_abs": float(np.abs(dy[8:] - expected[8:]).max()),
            }
    edges = [(i, j) for i in range(K) for j in range(K) if g_cc[i, j]]
    if edges:
        i, _ = edges[0]
        desc = _descendants(g_cc, i)
        alt = engine.run({i: (np.ones(T), np.zeros(T))})
        dC = np.abs(alt["treatments"] - fact["treatments"]).max(axis=0)
        unaffected = [j for j in range(K) if j != i and j not in desc]
        checks["cc_propagation"] = {
            "upstream": i,
            "descendants": sorted(int(j) for j in desc),
            "min_change_descendants": float(min(dC[j] for j in desc)),
            "max_change_non_descendants": float(max((dC[j] for j in unaffected), default=0.0)),
        }
    else:
        checks["cc_propagation"] = {"status": "not_testable"}

    ok = True
    for name, c in checks.items():
        if "max_abs" in c:
            c["passed"] = c["max_abs"] <= (1e-8 if name == "no_mediation_matches_channel_response" else TOL)
        elif name == "cc_propagation" and "upstream" in c:
            c["passed"] = c["min_change_descendants"] > 1e-6 and c["max_change_non_descendants"] <= TOL
        else:
            c["passed"] = None
        ok &= c["passed"] is not False
    return EngineValidation(world_id, VALIDATED if ok else BLOCKED, checks)


def protocol_requests(
    C: np.ndarray, k: int, start: int, stop: int, pulse_at: int | None = None
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """E08 interventions on channel k over weeks [start, stop); one-week pulse at ``pulse_at``."""
    T = C.shape[0]
    mask = ((np.arange(T) >= start) & (np.arange(T) < stop)).astype(float)
    ck = C[:, k]
    pulse_mask = (np.arange(T) == (start if pulse_at is None else pulse_at)).astype(float)
    level = float(ck[start:stop].mean())
    return {
        "do_null": (mask, ck.copy()),
        "do_zero": (mask, np.zeros(T)),
        "do_reduce_10": (mask, 0.9 * ck),
        "do_reduce_20": (mask, 0.8 * ck),
        "do_increase_10": (mask, 1.1 * ck),
        "do_pulse": (pulse_mask, ck + level),
    }
