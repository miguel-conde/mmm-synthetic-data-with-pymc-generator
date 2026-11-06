from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from mmm_benchmark.evaluation import coverage, mae, paired_bootstrap, rmse, safe_ratio, score
from mmm_benchmark.models import REGISTRY, make_model
from mmm_benchmark.models.linear import EngineeredRegression, RidgeRaw
from mmm_benchmark.runner import fit_model
from mmm_benchmark.schema import COMPARABILITY, ModelOutput

FAST_BLIND = ["N0_naive_last", "N1_naive_mean", "M0_ols", "M1_ridge", "M2_adstock_sat", "M5_xgboost", "M6_lightgbm"]


# ---- leakage -----------------------------------------------------------------
@pytest.mark.parametrize("model_id", FAST_BLIND)
def test_future_y_does_not_change_fit(worlds, model_id):
    _, world, obs, _ = worlds["confounded_treatment"]
    y2 = obs.y.copy()
    y2[obs.test_idx] += 100.0
    a, _ = fit_model(model_id, {}, obs, world)
    b, _ = fit_model(model_id, {}, dataclasses.replace(obs, y=y2), world)
    assert a.fit_status == b.fit_status == "ok"
    np.testing.assert_allclose(a.y_pred, b.y_pred)


@pytest.mark.parametrize("model_id", FAST_BLIND)
def test_blind_models_ignore_truth(worlds, model_id):
    """Blind fits take no truth/world argument; a world with permuted truth gives identical output."""
    _, world, obs, _ = worlds["kitchen_sink"]
    scrambled = dataclasses.replace(world, data={k: np.random.default_rng(0).permutation(np.asarray(v).ravel()).reshape(np.shape(v))
                                                 if k not in ("treatments", "covariates", "outcome") else v
                                                 for k, v in world.data.items()})
    a, _ = fit_model(model_id, {}, obs, world)
    b, _ = fit_model(model_id, {}, obs, scrambled)
    np.testing.assert_allclose(a.y_pred, b.y_pred)
    assert not REGISTRY[model_id].privileged


def test_engineered_scales_use_train_only(worlds):
    _, _, obs, _ = worlds["direct_only"]
    C2 = obs.C.copy()
    C2[obs.test_idx] *= 50.0
    m1, m2 = EngineeredRegression(), EngineeredRegression()
    m1.fit(obs.fit_view(), seed=0)
    m2.fit(dataclasses.replace(obs, C=C2).fit_view(), seed=0)
    np.testing.assert_allclose(m1.scales, m2.scales)
    np.testing.assert_allclose(m1.coef, m2.coef)


def test_ridge_selection_uses_train_only(worlds):
    _, _, obs, _ = worlds["promo_drives_treatment"]
    y2 = obs.y.copy()
    y2[obs.test_idx] = -1e6
    a, b = RidgeRaw(), RidgeRaw()
    a.fit(obs.fit_view(), seed=0)
    b.fit(dataclasses.replace(obs, y=y2).fit_view(), seed=0)
    assert a.ridge_alpha == b.ridge_alpha


# ---- reproducibility ---------------------------------------------------------
@pytest.mark.parametrize("model_id", ["M1_ridge", "M2_adstock_sat", "M5_xgboost", "M6_lightgbm"])
def test_same_seed_same_result(worlds, model_id):
    _, world, obs, _ = worlds["treatment_halo"]
    a, _ = fit_model(model_id, {}, obs, world)
    b, _ = fit_model(model_id, {}, obs, world)
    np.testing.assert_allclose(a.y_pred, b.y_pred, rtol=1e-10, atol=1e-12)


def test_rescoring_is_identical(worlds):
    _, world, obs, truth = worlds["direct_only"]
    out, _ = fit_model("M2_adstock_sat", {}, obs, world)
    assert score(out, obs, truth) == score(out, obs, truth)


# ---- model contract ----------------------------------------------------------
def test_unsupported_estimands_are_none(worlds):
    _, world, obs, _ = worlds["direct_only"]
    for mid in ("M5_xgboost", "M6_lightgbm", "N0_naive_last"):
        out, _ = fit_model(mid, {}, obs, world)
        assert out.contributions is None
        assert COMPARABILITY[out.family]["historical_observed_path_response"] == "not_applicable"


def test_tree_explanations_are_not_scored_as_contributions(worlds):
    _, world, obs, truth = worlds["direct_only"]
    out, _ = fit_model("M5_xgboost", {}, obs, world)
    assert out.explanation is not None
    assert not [r for r in score(out, obs, truth) if r["task"].startswith("attribution")]


def test_failure_is_recorded_not_raised(worlds):
    _, world, obs, _ = worlds["direct_only"]
    broken = dataclasses.replace(obs, C=obs.C[:, :0])
    out, model = fit_model("M2_adstock_sat", {}, broken, world)
    assert out.fit_status == "failed" and out.error and model is None


def test_privileged_models_flagged():
    for mid in ("M2p_true_transforms", "M2p_true_transforms_plus_D", "M4_oracle_plugin"):
        assert make_model(mid).privileged


@pytest.mark.slow
def test_pymc_marketing_compiled_response_matches_posterior_predictive(worlds):
    _, _, obs, _ = worlds["direct_only"]
    m = make_model("M3_pymc_marketing", draws=100, tune=100, chains=2)
    m.fit(obs.fit_view(), seed=3)
    np.testing.assert_allclose(m.channel_response(obs, obs.C), m.contributions(obs), atol=1e-10)
    alt = obs.C * 0.7
    (pp,) = m._posterior_predictive(obs, alt, ["channel_contribution"])
    np.testing.assert_allclose(m.channel_response(obs, alt), pp.mean(0), atol=1e-10)


# ---- metrics -----------------------------------------------------------------
def test_perfect_predictions_and_contributions_score_zero(worlds):
    _, _, obs, truth = worlds["kitchen_sink"]
    out = ModelOutput("perfect", obs.world_id, "regression", "blind_observed", "ok", 0,
                      y_pred=obs.y.copy(), contributions=truth["contributions_observed"].copy())
    rows = score(out, obs, truth)
    for r in rows:
        if r["metric"] in ("mae", "rmse", "rmse_scaled", "contrib_mae_norm", "contrib_rmse_norm",
                           "channel_total_abs_err_norm", "false_direct_attribution"):
            assert r["value"] == 0.0, r


def test_metric_primitives():
    assert mae([1, 2], [1, 2]) == 0 and rmse([0, 0], [3, 4]) == pytest.approx(np.sqrt(12.5))
    assert np.isnan(safe_ratio(1.0, 0.0))
    t = np.array([0.0, 1.0, 2.0])
    assert coverage(np.array([0.0, 0.5, 2.5]), np.array([0.0, 1.0, 3.0]), t) == pytest.approx(2 / 3)


def test_paired_bootstrap_is_over_worlds():
    m, lo, hi = paired_bootstrap(np.array([1.0, 1.0, 1.0]))
    assert m == lo == hi == 1.0
    assert np.isnan(paired_bootstrap(np.array([np.nan]))[0])


def test_eval_window_excludes_warmup_and_padding(worlds):
    _, _, obs, _ = worlds["direct_only"]
    assert obs.eval_idx("train").min() >= obs.warmup
    assert set(obs.eval_idx("test")) <= set(obs.test_idx)


def test_full_refit_scope_scores_under_its_own_label(worlds):
    _, world, obs, truth = worlds["direct_only"]
    full = dataclasses.replace(obs, train_idx=np.arange(obs.T), test_idx=np.arange(0))
    out, _ = fit_model("M0_ols", {}, full, world)
    tasks = {r["task"] for r in score(out, full, truth, full_refit=True)}
    assert "historical_full_refit" in tasks
    assert not tasks & {"historical_in_sample_fit", "prediction_future_conditional_on_known_CZ"}


def test_eval_start_override_changes_only_attribution_window(worlds):
    _, world, obs, truth = worlds["kitchen_sink"]
    out, _ = fit_model("M0_ols", {}, obs, world)
    a = {(r["task"], r["metric"], r["channel"]): r["value"] for r in score(out, obs, truth)}
    b = {(r["task"], r["metric"], r["channel"]): r["value"] for r in score(out, obs, truth, eval_start=obs.warmup)}
    assert a == b


@pytest.mark.slow
def test_fitting_burn_in_weeks_biases_media_coefficients():
    """v1.2 P0 finding: weeks 0-7 have generator burn-in history that zero-history adstock cannot reproduce.
    Privileged OLS (true transforms, true noise-free baseline offset) is ~unbiased when fitted on weeks >= 8."""
    from mmm_benchmark.generator_adapter import WorldSpec, generate, split_world
    from mmm_benchmark.models.linear import _ols
    from mmm_benchmark.transforms import true_channel_response

    biases = {"from_week_0": [], "from_warmup": []}
    for r in range(4):
        spec = WorldSpec("direct_only", 104, r)
        w = generate(spec)
        obs, tr = split_world(w, spec)
        F = true_channel_response(w, obs.C)
        y = obs.y - tr["baseline_no_noise"]
        idx = obs.eval_idx("train")
        for label, rows in (("from_week_0", obs.train_idx), ("from_warmup", obs.eval_idx("train"))):
            c, _ = _ols(F[rows], y[rows])
            biases[label].append(np.mean(F[idx] * c - tr["contributions_observed"][idx]) / np.mean(np.abs(obs.y[idx])))
    assert abs(np.mean(biases["from_warmup"])) < 0.25 * abs(np.mean(biases["from_week_0"]))


def test_pymc_marketing_refuses_fit_window_without_history(worlds):
    _, _, obs, _ = worlds["direct_only"]
    late = dataclasses.replace(obs, train_idx=obs.train_idx[obs.train_idx >= obs.warmup])
    with pytest.raises(NotImplementedError):
        make_model("M3_pymc_marketing", draws=10, tune=10, chains=1).fit(late.fit_view(), seed=0)
