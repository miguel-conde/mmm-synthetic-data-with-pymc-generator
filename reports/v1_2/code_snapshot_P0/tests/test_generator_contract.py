from __future__ import annotations

import numpy as np
import pymc_generator as pg
import pytest

from mmm_benchmark.generator_adapter import WorldSpec, generate, split_world
from mmm_benchmark.schema import WARMUP
from mmm_benchmark.transforms import true_channel_response

from .conftest import SCENARIOS


def test_installed_presets_match_protocol():
    assert {s.name for s in pg.SCENARIOS} >= set(SCENARIOS)


@pytest.mark.parametrize("name", SCENARIOS)
def test_identity_native_precision(worlds, name):
    _, world, _, truth = worlds[name]
    assert world.identity_error() < 1e-10
    a = truth.arrays
    np.testing.assert_allclose(a["baseline"] + a["contributions_observed"].sum(1), a["outcome"], atol=1e-10)
    np.testing.assert_allclose(a["baseline"] + a["contributions"].sum(1) + a["indirect_effects"], a["outcome"], atol=1e-10)
    np.testing.assert_allclose(a["indirect_effects_by_source"].sum(1), a["indirect_effects"], atol=1e-10)
    np.testing.assert_allclose(a["baseline_no_noise"] + a["outcome_noise"], a["baseline"], atol=1e-12)


def test_direct_only_has_no_indirect_effects(worlds):
    _, world, _, truth = worlds["direct_only"]
    assert np.all(truth["indirect_effects"] == 0), "preset changed: direct_only now has indirect effects"
    for key in ("g_dc", "g_zc", "g_cc", "g_dz"):
        assert not np.asarray(world.g[key]).any()


@pytest.mark.parametrize(
    "name,edge",
    [("confounded_treatment", "g_dc"), ("promo_drives_treatment", "g_zc"), ("treatment_halo", "g_cc")],
)
def test_presets_have_their_mechanism(worlds, name, edge):
    assert np.asarray(worlds[name][1].g[edge]).any()


@pytest.mark.parametrize("name", SCENARIOS)
def test_non_direct_channels_have_zero_observed_path_response(worlds, name):
    _, _, _, truth = worlds[name]
    for k, role in enumerate(truth.channel_roles):
        if role != "direct":
            assert np.all(truth["contributions_observed"][:, k] == 0)


def test_seed_reproducibility():
    spec = WorldSpec("kitchen_sink", 52, 3)
    a, b = generate(spec), generate(spec)
    for key in ("outcome", "treatments", "contributions_observed"):
        np.testing.assert_array_equal(a.data[key], b.data[key])


def test_derived_seeds_differ_by_world():
    seeds = {WorldSpec(s, T, r).world_seed for s in SCENARIOS for T in (52, 104, 208) for r in range(10)}
    assert len(seeds) == 150


def test_observed_dataset_has_no_truth(worlds):
    _, _, obs, _ = worlds["confounded_treatment"]
    fields = set(vars(obs))
    assert not fields & {"latent_unobserved", "contributions", "contributions_observed", "baseline", "g", "params"}


def test_temporal_split(worlds):
    _, _, obs, _ = worlds["direct_only"]
    assert obs.train_idx.max() < obs.test_idx.min()
    assert len(obs.train_idx) + len(obs.test_idx) == obs.T
    assert np.isnan(obs.fit_view().y[obs.test_idx]).all()
    assert np.isfinite(obs.fit_view().y[obs.train_idx]).all()


@pytest.mark.slow
@pytest.mark.parametrize("name", ["direct_only", "kitchen_sink"])
def test_true_transforms_reproduce_observed_path_after_warmup(worlds, name):
    _, world, obs, truth = worlds[name]
    f = true_channel_response(world, obs.C)
    gate = np.asarray(world.g["g_cy"]) * np.asarray(world.params["beta"])
    np.testing.assert_allclose((f * gate)[WARMUP:], truth["contributions_observed"][WARMUP:], atol=1e-10)


def test_float32_persistence_tolerance(tmp_path):
    cfg = pg.SCENARIOS[0].prior(n_time_steps=52, seed=1)
    corpus = pg.sample_prior_predictive(cfg, n=2)
    path = tmp_path / "c.npz"
    pg.save_corpus(corpus, path)
    loaded = pg.load_corpus(path)
    y = loaded["outcome_raw"].astype(np.float64)
    recon = (loaded["baseline_raw"].astype(np.float64) + loaded["treatment_contribution_raw"].astype(np.float64).sum(-1)
             + loaded["indirect_effects"].astype(np.float64))
    tol = 1e-5 * np.abs(y).max()
    assert np.abs(recon - y).max() < tol
    mask = loaded["treatment_active_mask"].astype(bool)
    assert np.all(loaded["treatment_contribution_raw"][~np.broadcast_to(mask[:, None, :], loaded["treatment_contribution_raw"].shape)] == 0)


# ---- v1.1 -----------------------------------------------------------------------------------------
from mmm_benchmark.generator_adapter import response_warmup_weeks  # noqa: E402


def test_unvaried_spec_reproduces_v1_world():
    """No overrides -> identical to the v1 world (Scenario.prior path)."""
    a = generate(WorldSpec("confounded_treatment", 52, 1))
    b = generate(WorldSpec("confounded_treatment", 52, 1, variant="", overrides=()))
    np.testing.assert_array_equal(a.data["outcome"], b.data["outcome"])


def test_dc_strength_variants_are_paired():
    specs = [WorldSpec("confounded_treatment", 104, 0, variant=f"dc{v}", overrides=(("dc_coeff_range", (v, v)),
                                                                                     ("confounding_strength_range", None)))
             for v in (0.0, 0.25, 0.5)]
    ws = [generate(s) for s in specs]
    assert len({s.world_id for s in specs}) == 3
    for w in ws[1:]:
        for key in ("g_dc", "g_dy", "g_cy"):
            np.testing.assert_array_equal(np.asarray(w.g[key]) != 0, np.asarray(ws[0].g[key]) != 0)
        np.testing.assert_array_equal(w.params["beta"], ws[0].params["beta"])
        np.testing.assert_array_equal(w.exogenous["eps_c"], ws[0].exogenous["eps_c"])
    assert np.all(ws[0].params["w_dc"] == 0) and np.allclose(ws[2].params["w_dc"][ws[2].g["g_dc"] != 0], 0.5)


def test_rho_variants_are_paired():
    ws = [generate(WorldSpec("direct_only", 104, 0, variant=f"rho{r}", overrides=(("confounding_strength_range", (r, r)),)))
          for r in (1e-6, 0.3, 0.6)]
    for w in ws[1:]:
        np.testing.assert_array_equal(w.exogenous["eps_c"], ws[0].exogenous["eps_c"])
        np.testing.assert_array_equal(w.params["beta"], ws[0].params["beta"])
    assert [round(float(w.data["confounding_strength"]), 6) for w in ws] == [1e-6, 0.3, 0.6]


def test_linear_variant_has_no_memory_and_identity_saturation():
    w = generate(WorldSpec("direct_only", 52, 0, variant="linear", overrides=(("nonlinearity", "linear"),)))
    assert np.all(w.params["carryover_family"] == 0) and np.all(w.params["sat_family"] == 0)
    assert response_warmup_weeks(w) == 0


@pytest.mark.slow
@pytest.mark.parametrize("name", SCENARIOS)
def test_response_warmup_weeks_is_minimal_valid_exclusion(worlds, name):
    _, world, obs, truth = worlds[name]
    w0 = response_warmup_weeks(world)
    gate = np.asarray(world.g["g_cy"]) * np.asarray(world.params["beta"])
    err = np.abs(true_channel_response(world, obs.C) * gate - truth["contributions_observed"]).max(1)
    assert err[w0:].max() < 1e-10
    if w0 > 0:
        assert err[w0 - 1] > 1e-10
