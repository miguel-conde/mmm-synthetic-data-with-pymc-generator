"""Single entry point to pymc-generator: deterministic world generation and the observed/truth split."""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymc_generator as pg
from pymc_generator.worlds import SCM, edges_with_coeffs, node_status, path_to_y

from .provenance import derive_seed
from .schema import ObservedDataset, TruthRegistry, temporal_split

SCENARIO_IDS = {
    "direct_only": "S0",
    "confounded_treatment": "S1",
    "promo_drives_treatment": "S2",
    "treatment_halo": "S3",
    "kitchen_sink": "S4",
}
CARRYOVER = ("none", "geometric", "weibull")
SATURATION = ("linear", "hill", "logistic", "michaelis_menten", "tanh", "root")
START_DATE = np.datetime64("2020-01-06")
TRUTH_KEYS = (
    "contributions_observed",
    "contributions",
    "indirect_effects",
    "indirect_effects_by_source",
    "baseline",
    "baseline_intrinsic",
    "outcome_noise",
    "covariate_contribution",
    "latent_unobserved_contribution",
    "latent_unobserved",
    "treatments_base",
    "saturation_scale",
    "outcome",
)


def get_scenario(name: str) -> pg.scenarios.Scenario:
    for sc in pg.SCENARIOS:
        if sc.name == name:
            return sc
    raise KeyError(f"unknown scenario {name!r}; installed: {[s.name for s in pg.SCENARIOS]}")


@dataclass(frozen=True)
class WorldSpec:
    scenario: str
    T: int
    replicate: int
    variant: str = ""
    overrides: tuple[tuple[str, object], ...] = ()

    @property
    def scenario_id(self) -> str:
        return SCENARIO_IDS[self.scenario]

    @property
    def world_id(self) -> str:
        base = f"{self.scenario_id}_{self.scenario}_T{self.T}_r{self.replicate:02d}"
        return f"{base}__{self.variant}" if self.variant else base

    # seeds deliberately ignore the variant: variants of one replicate are paired worlds
    @property
    def config_seed(self) -> int:
        return derive_seed(self.scenario, self.T, self.replicate, "config")

    @property
    def world_seed(self) -> int:
        return derive_seed(self.scenario, self.T, self.replicate, "world")


def scenario_prior(spec: WorldSpec):
    """Scenario prior; with overrides, the same ``make_scm_prior`` call ``Scenario.prior`` makes plus them."""
    sc = get_scenario(spec.scenario)
    if not spec.overrides:
        return sc.prior(n_time_steps=spec.T, seed=spec.config_seed)
    from pymc_generator.presets import make_scm_prior

    edge_budget = dict(sc.edge_budget)
    if sc.connect_all:
        edge_budget.update(sc.connect_all_edge_budget)
    return make_scm_prior(
        n_treatments=sc.n_treatments,
        n_covariates=sc.n_covariates,
        n_latent=sc.n_latent,
        edge_budget=edge_budget,
        n_time_steps=spec.T,
        n_cells=2,
        draws_per_cell=1,
        seed=spec.config_seed,
        **dict(spec.overrides),
    )


def generate(spec: WorldSpec) -> SCM:
    sc = get_scenario(spec.scenario)
    return pg.sample_scm(
        scenario_prior(spec), seed=spec.world_seed, connect_all=sc.connect_all, name=sc.name, purpose=sc.purpose
    )


def structure_cell_id(g: dict) -> str:
    """Hash of the binary DAG pattern: worlds sharing it belong to the same structure cell."""
    h = hashlib.sha1()
    for key in sorted(g):
        arr = np.asarray(g[key]) != 0
        h.update(key.encode())
        h.update(str(arr.shape).encode())
        h.update(arr.astype(np.uint8).tobytes())
    return h.hexdigest()[:12]


def channel_roles(g: dict) -> tuple[str, ...]:
    """direct (C→Y) | feeder (no C→Y but a C→C path to Y) | isolated (no path to Y)."""
    reach = path_to_y(g)
    K = len(g["g_cy"])
    return tuple(
        "direct" if g["g_cy"][k] else ("feeder" if reach[f"C{k + 1}"] else "isolated")
        for k in range(K)
    )


def response_warmup_weeks(world: SCM) -> int:
    """Leading reported weeks whose direct-channel response reaches before the window.

    Same rule as ``signal_diagnostics.summarize_signal_metrics``: realized support of the
    normalized carryover kernels of channels with C→Y, or 0 without burn-in.
    """
    from pymc_generator.signal_diagnostics import _carryover_weights

    if int(world.cfg.carryover_burn_in) == 0:
        return 0
    p = world.params
    support = 0
    for k in np.flatnonzero(np.asarray(world.g["g_cy"]) != 0):
        w = _carryover_weights(int(p["carryover_family"][k]), float(p["carryover_alpha"][k]),
                               float(p["weibull_lam"][k]), float(p["weibull_k"][k]), int(world.cfg.l_max))
        if w is not None and np.flatnonzero(w > 0).size:
            support = max(support, int(np.flatnonzero(w > 0)[-1]))
    return support


def world_summary(world: SCM) -> dict:
    p = world.params
    K = world.n_treatments
    return {
        "carryover": [CARRYOVER[int(p["carryover_family"][k])] for k in range(K)],
        "saturation": [SATURATION[int(p["sat_family"][k])] for k in range(K)],
        "beta": [float(b) for b in p["beta"]],
        "confounding_strength": float(np.asarray(world.data["confounding_strength"])),
        "edges": [list(e) for e in edges_with_coeffs(world.g, p)],
        "node_status": node_status(world.g),
        "l_max": int(world.cfg.l_max),
        "carryover_burn_in": int(world.cfg.carryover_burn_in),
        "n_treatment_shocks": int(world.cfg.n_treatment_shocks),
        "identity_error": world.identity_error(),
        "response_warmup_weeks": response_warmup_weeks(world),
    }


def split_world(world: SCM, spec: WorldSpec) -> tuple[ObservedDataset, TruthRegistry]:
    d = world.data
    T = world.n_time_steps
    train_idx, test_idx = temporal_split(T)
    observed = ObservedDataset(
        world_id=spec.world_id,
        scenario_id=spec.scenario_id,
        structure_cell_id=structure_cell_id(world.g),
        T=T,
        seed=spec.world_seed,
        dates=START_DATE + 7 * np.arange(T).astype("timedelta64[D]"),
        y=np.asarray(d["outcome"], dtype=float).copy(),
        C=np.asarray(d["treatments"], dtype=float).copy(),
        Z=np.asarray(d["covariates"], dtype=float).copy(),
        channel_names=tuple(f"C{k + 1}" for k in range(world.n_treatments)),
        control_names=tuple(f"Z{m + 1}" for m in range(world.n_covariates)),
        train_idx=train_idx,
        test_idx=test_idx,
    )
    arrays = {k: np.asarray(d[k], dtype=float).copy() for k in TRUTH_KEYS}
    arrays["baseline_no_noise"] = arrays["baseline"] - arrays["outcome_noise"]
    truth = TruthRegistry(
        world_id=spec.world_id,
        arrays=arrays,
        g={k: np.asarray(v).copy() for k, v in world.g.items()},
        channel_roles=channel_roles(world.g),
        meta={
            "scenario": spec.scenario,
            "T": spec.T,
            "replicate": spec.replicate,
            "variant": spec.variant,
            "overrides": dict(spec.overrides),
            "config_seed": spec.config_seed,
            "world_seed": spec.world_seed,
            **world_summary(world),
        },
    )
    return observed, truth


class WorldStore:
    """On-disk cache of generated worlds, shared by all runs so F2 ⊂ F3 reuse identical worlds.

    Pickles are only ever written and read by this code base (trusted local artefacts).
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def path(self, spec: WorldSpec) -> Path:
        return self.root / spec.world_id

    def get(self, spec: WorldSpec) -> SCM:
        p = self.path(spec)
        pkl = p / "world.pkl"
        if pkl.exists():
            with pkl.open("rb") as fh:
                return pickle.load(fh)
        world = generate(spec)
        p.mkdir(parents=True, exist_ok=True)
        tmp = p / "world.pkl.tmp"
        with tmp.open("wb") as fh:
            pickle.dump(world, fh)
        tmp.replace(pkl)
        (p / "meta.json").write_text(
            json.dumps(split_world(world, spec)[1].meta, indent=2, default=float)
        )
        return world

    def load(self, spec: WorldSpec) -> tuple[SCM, ObservedDataset, TruthRegistry]:
        world = self.get(spec)
        observed, truth = split_world(world, spec)
        return world, observed, truth
