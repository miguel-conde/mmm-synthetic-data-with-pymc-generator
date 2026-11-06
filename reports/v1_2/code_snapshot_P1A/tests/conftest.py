"""Shared fixtures: one small world per scenario, generated once per test session."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("MPLBACKEND", "Agg")

from mmm_benchmark.generator_adapter import WorldSpec, generate, split_world  # noqa: E402

SCENARIOS = ("direct_only", "confounded_treatment", "promo_drives_treatment", "treatment_halo", "kitchen_sink")


@pytest.fixture(scope="session")
def worlds():
    out = {}
    for name in SCENARIOS:
        spec = WorldSpec(name, 52, 0)
        world = generate(spec)
        obs, truth = split_world(world, spec)
        out[name] = (spec, world, obs, truth)
    return out
