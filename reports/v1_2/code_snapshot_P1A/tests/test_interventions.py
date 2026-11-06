from __future__ import annotations

import numpy as np
import pytest

from mmm_benchmark.interventions import VALIDATED, InterventionEngine, _descendants, validate_engine

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def engines(worlds):
    return {name: (InterventionEngine(w), obs, truth) for name, (_, w, obs, truth) in worlds.items()
            if name in ("direct_only", "treatment_halo", "kitchen_sink")}


@pytest.mark.parametrize("name", ["direct_only", "treatment_halo", "kitchen_sink"])
def test_engine_validates(engines, name):
    eng, obs, truth = engines[name]
    assert validate_engine(eng, obs.world_id, truth.channel_roles).status == VALIDATED


def test_null_intervention_reproduces_outcome(engines):
    eng, obs, _ = engines["kitchen_sink"]
    out = eng.run({k: (np.ones(obs.T), obs.C[:, k]) for k in range(obs.K)})
    np.testing.assert_allclose(out["outcome"], obs.y, atol=1e-12)


def test_null_channel_has_zero_total_effect(engines):
    eng, obs, truth = engines["kitchen_sink"]
    for k, role in enumerate(truth.channel_roles):
        if role == "isolated":
            assert np.abs(eng.effect({k: (np.ones(obs.T), 3 * obs.C[:, k])})).max() < 1e-12


def test_late_intervention_does_not_change_past(engines):
    eng, obs, truth = engines["direct_only"]
    s = 30
    mask = (np.arange(obs.T) >= s).astype(float)
    dy = eng.effect({0: (mask, np.zeros(obs.T))})
    assert np.abs(dy[:s]).max() == 0.0
    assert np.abs(dy[s:]).max() > 0


def test_pulse_effect_persists_with_carryover(engines):
    eng, obs, truth = engines["direct_only"]
    fam = truth.meta["carryover"]
    k = next(i for i, f in enumerate(fam) if f != "none")
    s = 20
    mask = (np.arange(obs.T) == s).astype(float)
    dy = eng.effect({k: (mask, obs.C[:, k] + 5.0)})
    assert np.abs(dy[:s]).max() == 0.0
    assert np.abs(dy[s + 1 : s + 8]).sum() > 0


def test_halo_propagates_to_descendants_only(engines):
    eng, obs, truth = engines["treatment_halo"]
    g_cc = np.asarray(truth.g["g_cc"]) != 0
    i = int(np.flatnonzero(g_cc.any(1))[0])
    desc = _descendants(g_cc, i)
    base = eng.run()["treatments"]
    alt = eng.run({i: (np.ones(obs.T), np.zeros(obs.T))})["treatments"]
    changed = np.abs(alt - base).max(0)
    assert all(changed[j] > 0 for j in desc)
    assert all(changed[j] == 0 for j in range(obs.K) if j != i and j not in desc)


def test_no_mediation_effect_excludes_other_channels(engines):
    eng, obs, truth = engines["direct_only"]
    base = eng.run()
    alt = eng.run({1: (np.ones(obs.T), np.zeros(obs.T))})
    others = [j for j in range(obs.K) if j != 1]
    np.testing.assert_array_equal(alt["contributions_observed"][:, others], base["contributions_observed"][:, others])


# ---- v1.1 (D3): independent route, multiple interventions, edges, shocks, innovations -------------
from mmm_benchmark.generator_adapter import WorldSpec, generate, split_world  # noqa: E402
from mmm_benchmark.transforms import true_channel_response  # noqa: E402


def _isp(x):
    return np.log(np.expm1(x))


def _analytic(world, C, new_cols: dict[int, np.ndarray]):
    """Independent counterfactual: C_j = softplus(softplus⁻¹(C_j_obs) + Σ_p α_pj (C_p_new − C_p_obs))
    in topological order, then ΔY = Σ_k g·β·(f_k(C_new) − f_k(C_obs)) with the true transforms."""
    g = np.asarray(world.g["g_cc"]) != 0
    a = np.asarray(world.params["alpha_cc"])
    Cn = C.copy()
    for j in range(C.shape[1]):
        if j in new_cols:
            Cn[:, j] = new_cols[j]
            continue
        par = [p for p in range(j) if g[p, j]]
        if par:
            Cn[:, j] = np.logaddexp(0, _isp(C[:, j]) + sum(a[p, j] * (Cn[:, p] - C[:, p]) for p in par))
    gate = np.asarray(world.g["g_cy"]) * np.asarray(world.params["beta"])
    return Cn, ((true_channel_response(world, Cn) - true_channel_response(world, C)) * gate).sum(1)


@pytest.fixture(scope="module")
def halo_worlds():
    out = []
    for name, r in (("treatment_halo", 0), ("treatment_halo", 1), ("kitchen_sink", 1), ("kitchen_sink", 2)):
        spec = WorldSpec(name, 104, r)
        w = generate(spec)
        obs, truth = split_world(w, spec)
        out.append((w, obs, truth, InterventionEngine(w)))
    return out


def test_cc_matches_independent_analytic_route(halo_worlds):
    for w, obs, _, eng in halo_worlds:
        C = obs.C
        i = int(np.flatnonzero((np.asarray(w.g["g_cc"]) != 0).any(1))[0])
        mask = (np.arange(obs.T) >= 40).astype(float)
        new_i = np.where(mask > 0, 0.5 * C[:, i], C[:, i])
        Cn, dy_a = _analytic(w, C, {i: new_i})
        out = eng.run({i: (mask, 0.5 * C[:, i])})
        np.testing.assert_allclose(out["treatments"], Cn, atol=1e-12)
        np.testing.assert_allclose((out["outcome"] - obs.y)[8:], dy_a[8:], atol=1e-12)


def test_multiple_simultaneous_interventions(halo_worlds):
    """Upstream and downstream set at once: downstream follows its own do where masked, the SCM elsewhere."""
    for w, obs, _, eng in halo_worlds:
        g = np.asarray(w.g["g_cc"]) != 0
        i, j = map(int, np.argwhere(g)[0])
        C, T = obs.C, obs.T
        m_i = (np.arange(T) >= 30).astype(float)
        m_j = ((np.arange(T) >= 30) & (np.arange(T) < 60)).astype(float)
        out = eng.run({i: (m_i, 0.0 * C[:, i]), j: (m_j, 2.0 * C[:, j])})
        np.testing.assert_allclose(out["treatments"][m_j > 0, j], 2.0 * C[m_j > 0, j])
        Cn, _ = _analytic(w, C, {i: np.where(m_i > 0, 0.0, C[:, i])})
        free = (m_j == 0)
        np.testing.assert_allclose(out["treatments"][free, j], Cn[free, j], atol=1e-12)


@pytest.mark.parametrize("week", ["first", "last"])
def test_pulse_at_window_edges(engines, week):
    eng, obs, truth = engines["kitchen_sink"]
    k = truth.channel_roles.index("direct")
    s = 0 if week == "first" else obs.T - 1
    mask = (np.arange(obs.T) == s).astype(float)
    dy = eng.effect({k: (mask, obs.C[:, k] + 3.0)})
    assert np.abs(dy[:s]).max(initial=0.0) == 0.0
    assert np.abs(dy[s]) > 0 or truth.meta["carryover"][k] != "none"
    assert np.isfinite(dy).all()


def test_shock_world_null_and_do():
    spec = WorldSpec("treatment_halo", 104, 0, variant="shocks",
                     overrides=(("n_treatment_shocks", 2), ("treatment_shock_length_range", (3, 5)),
                                ("treatment_shock_level_range", (0.0, 2.0))))
    w = generate(spec)
    obs, truth = split_world(w, spec)
    assert np.asarray(w.data["treatment_shock_mask"]).any()
    eng = InterventionEngine(w)
    np.testing.assert_array_equal(eng.run()["outcome"], obs.y)
    np.testing.assert_allclose(eng.run({k: (np.ones(obs.T), obs.C[:, k]) for k in range(obs.K)})["outcome"], obs.y, atol=1e-12)
    k = int(w.data["treatment_shock_index"][0])
    s = int(w.data["treatment_shock_start"][0])
    mask = (np.arange(obs.T) >= s).astype(float)
    dy = eng.effect({k: (mask, np.zeros(obs.T))})
    assert np.abs(dy[:s]).max(initial=0.0) == 0.0


def test_exogenous_innovations_unchanged_by_interventions(halo_worlds):
    w, obs, _, eng = halo_worlds[0]
    before = {k: v.copy() for k, v in w.primitive_parameters.items()}
    values_before = [np.array(v, copy=True) for v in eng._values]
    eng.run({0: (np.ones(obs.T), np.zeros(obs.T))})
    eng.effect({1: (np.ones(obs.T), 2 * obs.C[:, 1])})
    for k, v in w.primitive_parameters.items():
        np.testing.assert_array_equal(v, before[k])
    for a, b in zip(eng._values, values_before):
        np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(eng.run()["outcome"], obs.y)


def test_selected_channels_policy_respects_realized_budget(halo_worlds):
    from mmm_benchmark import causal

    w, obs, truth, eng = halo_worlds[0]
    p = causal.SelectedChannelsProblem(eng, obs, w.g["g_cc"])
    assert set(p.act) == set(np.flatnonzero(~(np.asarray(w.g["g_cc"]) != 0).any(0)))
    rows, v_cur, v_orc = causal.e09_selected_reference(p, truth)
    by = {r["policy"]: r for r in rows}
    assert abs(by["oracle_interventional"]["realized_budget_deviation"]) < 1e-6
    assert abs(by["equal_allocation"]["realized_budget_deviation"]) < 1e-6
    assert by["oracle_interventional"]["regret_norm"] == 0.0
    assert all(r["regret_norm"] >= -1e-9 for r in rows)
    assert np.isclose(by["current"]["value_true"], obs.y[causal.horizon(obs)].sum())
