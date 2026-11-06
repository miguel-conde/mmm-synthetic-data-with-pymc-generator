"""v1.2 P1a — essential tests of the M3 masked likelihood (designer's properties 1-5).

Deterministic (no MCMC) except the ``slow`` end-to-end test."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest
from scipy import stats

from mmm_benchmark import p1a
from mmm_benchmark.models.bayes import MASK_POTENTIAL, PyMCMarketingMMM

W = 8


def _late(obs):
    return dataclasses.replace(obs, train_idx=obs.train_idx[obs.train_idx >= W]).fit_view()


def _built(obs):
    m = PyMCMarketingMMM(prior_variant="v3")
    m.build(obs)
    return m.mmm.model


@pytest.fixture(scope="module")
def masked(worlds):
    out = {}
    for name in ("direct_only", "kitchen_sink"):
        _, _, obs, _ = worlds[name]
        o = _late(obs)
        out[name] = (o, _built(o))
    return out


@pytest.mark.parametrize("name", ["direct_only", "kitchen_sink"])
def test_adstock_uses_full_input_sequence(masked, name):
    """(1) channel_contribution at fixed parameters = adstock over rows [0, n), not restarted at row W."""
    o, M = masked[name]
    n = int(o.train_idx[-1]) + 1
    p = p1a.random_points(M, 1, 0)[0]
    contrib, alpha, lam, beta = p1a.eval_at(M, ["channel_contribution", "adstock_alpha", "saturation_lam",
                                                "saturation_beta"], p)
    Xs, _, _, _ = p1a.design(o, n)
    full = beta * p1a.logistic_np(p1a.adstock_np(Xs, alpha), lam)
    np.testing.assert_allclose(contrib, full, rtol=1e-10, atol=1e-12)
    restarted = beta * p1a.logistic_np(p1a.adstock_np(Xs[W:], alpha), lam)
    assert np.abs(contrib[W:W + 3] - restarted[:3]).max() > 1e-6  # history before W reaches rows >= W


@pytest.mark.parametrize("name", ["direct_only", "kitchen_sink"])
def test_logp_is_manual_sum_over_permitted_weeks_only(masked, name):
    """(2) total y-likelihood (observed RV + mask) = sum of Normal log-densities over [W, n); one observed RV."""
    o, M = masked[name]
    n = int(o.train_idx[-1]) + 1
    assert [v.name for v in M.observed_RVs] == ["y"]
    assert [p.name for p in M.potentials] == [MASK_POTENTIAL]
    s = float(M["target_scale"].get_value())
    lp = M.compile_logp(vars=[M["y"], *M.potentials])
    for p in p1a.random_points(M, 5, 1):
        mu, sig = p1a.eval_at(M, ["mu", "y_sigma"], p)
        manual = stats.norm.logpdf(o.y[W:n] / s, mu[W:n], sig).sum()
        assert lp(p) == pytest.approx(manual, rel=1e-12, abs=1e-9)


def test_target_scale_uses_permitted_weeks_only(masked):
    o, M = masked["kitchen_sink"]
    n = int(o.train_idx[-1]) + 1
    assert float(M["target_scale"].get_value()) == pytest.approx(float(o.y[W:n].max()))


@pytest.mark.parametrize("name", ["direct_only", "kitchen_sink"])
def test_history_y_does_not_change_logp_or_gradient(masked, name):
    """(3) Y in weeks 0..W-1 does not enter: same model data, logp and gradient."""
    o, M = masked[name]
    y2 = o.y.copy()
    y2[:W] = y2[:W] * 5 + 100
    M2 = _built(dataclasses.replace(o, y=y2))
    np.testing.assert_array_equal(np.asarray(M["target_data"].get_value()), np.asarray(M2["target_data"].get_value()))
    f1, f2, g1, g2 = M.compile_logp(), M2.compile_logp(), M.compile_dlogp(), M2.compile_dlogp()
    for p in p1a.random_points(M, 3, 2):
        assert f1(p) == f2(p)
        np.testing.assert_array_equal(g1(p), g2(p))


def test_history_channels_do_change_logp(masked):
    """Not required to be invariant: channels in weeks 0..W-1 feed the carry-over of later weeks."""
    o, M = masked["direct_only"]
    C2 = o.C.copy()
    C2[:W] *= 0.2
    M2 = _built(dataclasses.replace(o, C=C2))
    p = p1a.random_points(M, 1, 3)[0]
    assert abs(M.compile_logp()(p) - M2.compile_logp()(p)) > 1e-6


@pytest.mark.parametrize("name", ["direct_only", "kitchen_sink"])
def test_masked_m3_equals_independent_reference(masked, name):
    """(4, deterministic part) joint log-density of masked M3 = hand-written PyMC reference up to a constant."""
    o, M = masked[name]
    R, _ = p1a.reference_model(o, W)
    assert sorted(v.name for v in M.value_vars) == sorted(v.name for v in R.value_vars)
    fM, fR, gM, gR = M.compile_logp(), R.compile_logp(), M.compile_dlogp(), R.compile_dlogp()
    pts = p1a.random_points(R, 10, 4)
    diffs = [fM(p) - fR(p) for p in pts]
    assert np.ptp(diffs) < 1e-8 and abs(diffs[0]) < 1e-5
    for p in pts[:3]:
        np.testing.assert_allclose(gM(p), gR(p), atol=1e-9)


def test_full_window_path_is_unchanged(worlds):
    """w = 0 keeps the standard model: no mask, data-derived target scale over [0, n)."""
    _, _, obs, _ = worlds["direct_only"]
    M = _built(obs.fit_view())
    n = int(obs.train_idx[-1]) + 1
    assert M.potentials == []
    assert float(M["target_scale"].get_value()) == pytest.approx(float(np.abs(obs.y[:n]).max()))


def test_non_contiguous_window_rejected(worlds):
    _, _, obs, _ = worlds["direct_only"]
    gap = dataclasses.replace(obs, train_idx=np.r_[obs.train_idx[:5], obs.train_idx[10:]])
    with pytest.raises(NotImplementedError):
        PyMCMarketingMMM().build(gap.fit_view())


def test_causal_horizon_does_not_shrink_with_late_fit_window(worlds):
    """E08/E09 window is [8, n_train) whatever the first fitted row (bug found in P1: len(train_idx) was used)."""
    from mmm_benchmark.causal import horizon

    _, _, obs, _ = worlds["kitchen_sink"]
    n = int(obs.train_idx[-1]) + 1
    assert horizon(obs) == horizon(_late(obs)) == slice(W, n)


@pytest.mark.slow
def test_masked_fit_end_to_end(worlds):
    """(5) contributions, scale, predictions, intervals, compiled response and diagnostics still work."""
    _, _, obs, _ = worlds["direct_only"]
    o = _late(obs)
    m = PyMCMarketingMMM(draws=100, tune=100, chains=2, prior_variant="v3", keep_posterior=True)
    m.fit(o, seed=3)
    n = int(o.train_idx[-1]) + 1
    assert m.contributions(o).shape == (o.T, o.K) and m.predict(o).shape == (o.T,)
    assert np.isfinite(m.predict(o)).all() and np.isfinite(m.contributions(o)).all()
    assert m.scale == pytest.approx(float(o.y[W:n].max()))
    d = m.diagnostics()
    assert d["likelihood_window"] == [W, n] and "Potential" in d["architecture"] and "rhat_max" in d
    np.testing.assert_allclose(m.channel_response(o, o.C), m.contributions(o), atol=1e-10)
    lo, hi = m.contribution_intervals(o)[0.95]
    assert (lo <= hi).all()
    assert set(m.posterior_arrays()) >= set(PyMCMarketingMMM.FREE)


# ---- P1B: A/B/C control (docs/protocolo_P1B_registrado.md §1) -------------------------------------
@pytest.fixture(scope="module")
def abc():
    """World whose max(Y) over [0, n_train) falls in weeks 0-7, so scales A and B/C differ."""
    from mmm_benchmark.generator_adapter import WorldSpec, generate, split_world

    spec = WorldSpec("direct_only", 52, 1)
    obs, _ = split_world(generate(spec), spec)
    n = int(obs.train_idx[-1]) + 1
    assert obs.y[:n].max() > obs.y[W:n].max()
    arms = {}
    for arm, (o, kw) in {"A": (obs.fit_view(), {}), "B": (obs.fit_view(), {"scale_from": W}),
                         "C": (_late(obs), {})}.items():
        m = PyMCMarketingMMM(prior_variant="v3", **kw)
        m.build(o)
        arms[arm] = m.mmm.model
    return obs, n, arms


def test_abc_scales(abc):
    obs, n, M = abc
    s = {k: float(m["target_scale"].get_value()) for k, m in M.items()}
    assert s["B"] == s["C"] == pytest.approx(float(obs.y[W:n].max()))
    assert s["A"] == pytest.approx(float(obs.y[:n].max())) and s["A"] != s["B"]


def test_abc_mask_is_the_only_difference_between_b_and_c(abc):
    """logp(B) - logp(C) = sum of B's own y log-terms of weeks 0..W-1 (real Y), at any parameter point."""
    _, _, M = abc
    terms = M["B"].logp(vars=[M["B"]["y"]], sum=False)[0]
    terms = getattr(terms, "values", terms)
    import pytensor

    head = pytensor.function(M["B"].value_vars, terms[:W].sum(), on_unused_input="ignore")
    fB, fC = M["B"].compile_logp(), M["C"].compile_logp()
    for p in p1a.random_points(M["B"], 5, 7):
        assert fB(p) - fC(p) == pytest.approx(float(head(**p)), rel=1e-9, abs=1e-8)


def test_b_equals_a_when_max_is_after_warmup(worlds):
    _, _, obs, _ = worlds["kitchen_sink"]
    n = int(obs.train_idx[-1]) + 1
    assert obs.y[:n].max() == obs.y[W:n].max()
    mA, mB = PyMCMarketingMMM(prior_variant="v3"), PyMCMarketingMMM(prior_variant="v3", scale_from=W)
    mA.build(obs.fit_view())
    mB.build(obs.fit_view())
    fA, fB = mA.mmm.model.compile_logp(), mB.mmm.model.compile_logp()
    for p in p1a.random_points(mA.mmm.model, 3, 8):
        assert fA(p) == fB(p)
