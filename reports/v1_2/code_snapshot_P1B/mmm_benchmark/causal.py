"""E08 (interventions) and E09 (budget decisions), only on worlds whose do-engine validated.

Truth/reference rows and per-model rows are computed separately so results can be stored per
(world, model) and resumed idempotently.
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize

from .interventions import InterventionEngine, protocol_requests
from .models.base import Estimator
from .schema import DECISION_VALUE, DO_TOTAL, WARMUP, ObservedDataset, TruthRegistry

M_LO, M_HI = 0.5, 1.5
M_GRID = np.linspace(M_LO, M_HI, 11)
ENGINE_LABEL = "research_validated_private_api"
N_RANDOM = 20


def horizon(obs: ObservedDataset) -> slice:
    """Historical window for interventions and policies: [WARMUP, end of train).

    Uses the last training index, not ``len(train_idx)``: with ``fit_scope=train_after_warmup`` the
    training rows start at WARMUP and the window must not shrink (v1.2 P1 fix)."""
    return slice(WARMUP, int(obs.train_idx[-1]) + 1)


def _requests(obs: ObservedDataset):
    H = horizon(obs)
    for k in range(obs.K):
        for name, (mask, value) in protocol_requests(obs.C, k, H.start, H.stop, pulse_at=(H.start + H.stop) // 2).items():
            yield k, name, mask, value


def e08_truth(engine: InterventionEngine, obs: ObservedDataset, truth: TruthRegistry) -> list[dict]:
    H = horizon(obs)
    y_abs = float(np.abs(obs.y[H]).sum())
    rows = []
    for k, name, mask, value in _requests(obs):
        d_true = float(engine.effect({k: (mask, value)})[H].sum())
        d_units = float(((value - obs.C[:, k]) * mask)[H].sum())
        rows.append({
            "world_id": obs.world_id, "scenario_id": obs.scenario_id, "T": obs.T,
            "replicate": truth.meta["replicate"], "channel": k, "role": truth.channel_roles[k],
            "intervention": name, "estimand_id": DO_TOTAL, "delta_true": d_true,
            "delta_treatment_units": d_units, "y_abs_sum": y_abs,
            "observed_path_attribution_true": float(truth["contributions_observed"][H, k].sum()),
            "true_response_per_treatment_unit": d_true / d_units if abs(d_units) > 1e-9 else float("nan"),
            "model_id": "truth_do_engine", "delta_est": d_true, "err_norm": 0.0,
            "label": "true_interventional_effect", "counterfactual_engine": ENGINE_LABEL,
        })
    return rows


def e08_model(model_id: str, model: Estimator, obs: ObservedDataset, truth_rows: list[dict]) -> list[dict]:
    r0 = model.channel_response(obs, obs.C)
    if r0 is None:
        return []
    H = horizon(obs)
    lookup = {(r["channel"], r["intervention"]): r for r in truth_rows}
    keep = ("world_id", "scenario_id", "T", "replicate", "channel", "role", "intervention", "estimand_id",
            "delta_true", "delta_treatment_units", "y_abs_sum", "observed_path_attribution_true")
    rows = []
    for k, name, mask, value in _requests(obs):
        A = obs.C.copy()
        A[:, k] = np.where(mask > 0, value, obs.C[:, k])
        d_est = float((model.channel_response(obs, A) - r0)[H].sum())
        t = lookup[(k, name)]
        rows.append({
            **{key: t[key] for key in keep},
            "model_id": model_id, "delta_est": d_est, "err_norm": (d_est - t["delta_true"]) / t["y_abs_sum"],
            "label": "model_implied_under_exogeneity_assumption", "counterfactual_engine": ENGINE_LABEL,
        })
    return rows


def _project(m: np.ndarray, S: np.ndarray, total: float) -> np.ndarray:
    """Clip to [M_LO, M_HI] and shift free coordinates until Σ m_k S_k = total."""
    m = np.clip(np.asarray(m, dtype=float), M_LO, M_HI)
    for _ in range(100):
        gap = total - float(m @ S)
        if abs(gap) <= 1e-10 * total:
            break
        free = (m < M_HI - 1e-12) if gap > 0 else (m > M_LO + 1e-12)
        if not free.any():
            break
        m = np.clip(m + free * gap / float(S[free].sum()), M_LO, M_HI)
    return m


def _optimize(value_fn, S: np.ndarray, total: float) -> np.ndarray:
    K = len(S)
    cons = [{"type": "eq", "fun": lambda m: (m @ S - total) / total}]
    best, best_v = None, -np.inf
    for start in (np.ones(K), _project(total / (K * np.maximum(S, 1e-12)), S, total)):
        res = minimize(lambda m: -value_fn(m), start, method="SLSQP", bounds=[(M_LO, M_HI)] * K,
                       constraints=cons, options={"maxiter": 200, "ftol": 1e-12})
        cand = _project(res.x, S, total)
        v = value_fn(cand)
        if v > best_v:
            best, best_v = cand, v
    return best


class BudgetProblem:
    """Fixed treatment-unit budget over the horizon, per-channel multipliers m_k ∈ [0.5, 1.5].

    Truth value applies do() to ALL channels (a full media plan), so C→C links into planned
    channels are cut by construction. Budget is dimensionless treatment units, not euros.
    """

    def __init__(self, engine: InterventionEngine, obs: ObservedDataset):
        self.engine, self.obs = engine, obs
        self.H = horizon(obs)
        self.S = obs.C[self.H].sum(0)
        self.total = float(self.S.sum())
        self.mask = np.zeros(obs.T)
        self.mask[self.H] = 1.0
        self.y_abs = float(np.abs(obs.y[self.H]).sum())

    def plan(self, m: np.ndarray) -> np.ndarray:
        A = self.obs.C.copy()
        A[self.H] = self.obs.C[self.H] * m
        return A

    def v_true(self, m: np.ndarray) -> float:
        A = self.plan(m)
        out = self.engine.run({k: (self.mask, A[:, k]) for k in range(self.obs.K)})
        return float(out["outcome"][self.H].sum())

    def row(self, truth: TruthRegistry, pid: str, label: str, m: np.ndarray, v_cur: float, v_orc: float) -> dict:
        v = self.v_true(m)
        obs = self.obs
        return {
            "world_id": obs.world_id, "scenario_id": obs.scenario_id, "T": obs.T,
            "replicate": truth.meta["replicate"], "policy": pid, "label": label,
            "estimand_id": DECISION_VALUE, "value_true": v, "value_current": v_cur, "value_oracle": v_orc,
            "policy_family": "all_channels_clamped_policy", "counterfactual_engine": ENGINE_LABEL,
            "improvement_vs_current_norm": (v - v_cur) / self.y_abs,
            "regret_norm": (v_orc - v) / self.y_abs,
            "budget_violation": float(abs(m @ self.S - self.total) / self.total),
            "frac_at_bounds": float(np.mean((m <= M_LO + 1e-6) | (m >= M_HI - 1e-6))),
            "multipliers": ",".join(f"{x:.3f}" for x in m),
        }


def e09_reference(problem: BudgetProblem, truth: TruthRegistry, random_policy: bool = False) -> tuple[list[dict], float, float]:
    K = problem.obs.K
    m_orc = _optimize(problem.v_true, problem.S, problem.total)
    v_cur, v_orc = problem.v_true(np.ones(K)), problem.v_true(m_orc)
    m_eq = _project(problem.total / (K * np.maximum(problem.S, 1e-12)), problem.S, problem.total)
    rows = [
        problem.row(truth, "current", "reference_current_plan", np.ones(K), v_cur, v_orc),
        problem.row(truth, "equal_allocation", "reference_equal_allocation_bounded", m_eq, v_cur, v_orc),
        problem.row(truth, "oracle_interventional", "oracle_interventional_policy", m_orc, v_cur, v_orc),
    ]
    if random_policy:
        rng = np.random.default_rng(int(truth.meta["world_seed"]) % 2**31)
        draws = [problem.row(truth, "random_feasible", "reference_random_feasible",
                             _project(rng.uniform(M_LO, M_HI, K), problem.S, problem.total), v_cur, v_orc)
                 for _ in range(N_RANDOM)]
        mean = {k: float(np.mean([d[k] for d in draws])) for k in
                ("value_true", "improvement_vs_current_norm", "regret_norm", "budget_violation", "frac_at_bounds")}
        rows.append({**draws[0], **mean, "multipliers": f"mean_of_{N_RANDOM}_random_draws",
                     "regret_norm_sd": float(np.std([d["regret_norm"] for d in draws]))})
    return rows, v_cur, v_orc


def e09_model(model_id: str, model: Estimator, problem: BudgetProblem, truth: TruthRegistry,
              v_cur: float, v_orc: float) -> list[dict]:
    obs, K, H = problem.obs, problem.obs.K, problem.H
    if model.channel_response(obs, obs.C) is not None:
        grid = np.stack([model.channel_response(obs, problem.plan(np.full(K, g)))[H].sum(0) for g in M_GRID])
        splines = [CubicSpline(M_GRID, grid[:, k]) for k in range(K)]
        m = _optimize(lambda mm: float(sum(splines[k](mm[k]) for k in range(K))), problem.S, problem.total)
        label = "model_implied_under_exogeneity_assumption"
    elif model.predict_inputs(obs, obs.C) is not None:
        m = _optimize(lambda mm: float(model.predict_inputs(obs, problem.plan(mm))[H].sum()), problem.S, problem.total)
        label = "naive_predictive_plugin_policy"
    else:
        return []
    return [problem.row(truth, model_id, label, m, v_cur, v_orc)]


class SelectedChannelsProblem:
    """``selected_channels_do_policy`` (decision D5): only channels without C→C parents are set;
    descendants react through the SCM. Budget = Σ over ALL realized treatments in the horizon,
    equal to the observed total. Multipliers for actionable channels in [0.5, 1.5]."""

    def __init__(self, engine: InterventionEngine, obs: ObservedDataset, g_cc: np.ndarray):
        self.engine, self.obs = engine, obs
        self.H = horizon(obs)
        self.act = np.flatnonzero(~(np.asarray(g_cc) != 0).any(0))
        self.S_all = obs.C[self.H].sum(0)
        self.total = float(self.S_all.sum())
        self.mask = np.zeros(obs.T)
        self.mask[self.H] = 1.0
        self.y_abs = float(np.abs(obs.y[self.H]).sum())
        self.base = engine.run()
        self._cache: dict[bytes, dict] = {}

    def run(self, m_act: np.ndarray) -> dict:
        key = np.round(np.asarray(m_act, dtype=float), 12).tobytes()
        if key not in self._cache:
            do = {int(k): (self.mask, np.where(self.mask > 0, self.obs.C[:, k] * m, self.obs.C[:, k]))
                  for k, m in zip(self.act, m_act)}
            self._cache[key] = self.engine.run(do)
        return self._cache[key]

    def realized_total(self, m_act) -> float:
        return float(self.run(m_act)["treatments"][self.H].sum())

    def value(self, m_act) -> float:
        return float(self.run(m_act)["outcome"][self.H].sum())

    def project_true_budget(self, m_act: np.ndarray) -> np.ndarray:
        """Scale actionable multipliers (clipped) until the realized total budget is met (truth engine)."""
        from scipy.optimize import brentq

        f = lambda s: self.realized_total(np.clip(m_act * s, M_LO, M_HI)) - self.total
        lo, hi = 1e-3, 10.0
        if f(lo) > 0 or f(hi) < 0:
            return np.clip(m_act, M_LO, M_HI)
        return np.clip(m_act * brentq(f, lo, hi, xtol=1e-10), M_LO, M_HI)

    def oracle(self) -> np.ndarray:
        n = len(self.act)
        cons = [{"type": "eq", "fun": lambda m: (self.realized_total(m) - self.total) / self.total}]
        best, best_v = np.ones(n), self.value(np.ones(n))
        for start in (np.ones(n), np.full(n, 0.9), np.full(n, 1.1)):
            res = minimize(lambda m: -self.value(m), start, method="SLSQP", bounds=[(M_LO, M_HI)] * n,
                           constraints=cons, options={"maxiter": 200, "ftol": 1e-12})
            cand = np.clip(res.x, M_LO, M_HI)
            if abs(self.realized_total(cand) - self.total) <= 1e-6 * self.total and self.value(cand) > best_v:
                best, best_v = cand, self.value(cand)
        return best

    def row(self, truth, pid, label, m_act, v_cur, v_orc) -> dict:
        v = self.value(m_act)
        obs = self.obs
        return {
            "world_id": obs.world_id, "scenario_id": obs.scenario_id, "T": obs.T,
            "replicate": truth.meta["replicate"], "policy": pid, "label": label,
            "policy_family": "selected_channels_do_policy", "counterfactual_engine": ENGINE_LABEL,
            "estimand_id": DECISION_VALUE, "value_true": v, "value_current": v_cur, "value_oracle": v_orc,
            "improvement_vs_current_norm": (v - v_cur) / self.y_abs, "regret_norm": (v_orc - v) / self.y_abs,
            "realized_budget_deviation": self.realized_total(m_act) / self.total - 1.0,
            "frac_at_bounds": float(np.mean((m_act <= M_LO + 1e-6) | (m_act >= M_HI - 1e-6))),
            "actionable_channels": ",".join(map(str, self.act)), "multipliers": ",".join(f"{x:.3f}" for x in m_act),
        }


def e09_selected_reference(p: SelectedChannelsProblem, truth: TruthRegistry) -> tuple[list[dict], float, float]:
    n = len(p.act)
    m_orc = p.oracle()
    v_cur, v_orc = p.value(np.ones(n)), p.value(m_orc)
    S_act = p.S_all[p.act]
    m_eq = p.project_true_budget(S_act.sum() / (n * np.maximum(S_act, 1e-12)))
    rows = [
        p.row(truth, "current", "reference_current_plan", np.ones(n), v_cur, v_orc),
        p.row(truth, "equal_allocation", "reference_equal_allocation_true_budget", m_eq, v_cur, v_orc),
        p.row(truth, "oracle_interventional", "oracle_interventional_policy", m_orc, v_cur, v_orc),
    ]
    rng = np.random.default_rng(int(truth.meta["world_seed"]) % 2**31 + 1)
    draws = [p.row(truth, "random_feasible", "reference_random_true_budget",
                   p.project_true_budget(rng.uniform(M_LO, M_HI, n)), v_cur, v_orc) for _ in range(N_RANDOM)]
    mean = {k: float(np.mean([d[k] for d in draws])) for k in
            ("value_true", "improvement_vs_current_norm", "regret_norm", "realized_budget_deviation", "frac_at_bounds")}
    rows.append({**draws[0], **mean, "multipliers": f"mean_of_{N_RANDOM}_random_draws",
                 "regret_norm_sd": float(np.std([d["regret_norm"] for d in draws]))})
    return rows, v_cur, v_orc


def e09_selected_model(model_id: str, model: Estimator, p: SelectedChannelsProblem, truth: TruthRegistry,
                       v_cur: float, v_orc: float) -> list[dict]:
    """The model believes channels are exogenous: descendants stay at observed levels in its view, so its
    budget constraint is Σ_act m_k S_k = Σ_act S_k. Truth value and realized budget are then reported."""
    obs, H, act = p.obs, p.H, p.act
    if model.channel_response(obs, obs.C) is None:
        return []
    S_act = p.S_all[act]

    def plan(g: float) -> np.ndarray:
        A = obs.C.copy()
        A[H.start:H.stop, act] = obs.C[H.start:H.stop, act] * g
        return A

    grid = np.stack([model.channel_response(obs, plan(g))[H].sum(0)[act] for g in M_GRID])
    splines = [CubicSpline(M_GRID, grid[:, j]) for j in range(len(act))]
    m = _optimize(lambda mm: float(sum(splines[j](mm[j]) for j in range(len(act)))), S_act, float(S_act.sum()))
    return [p.row(truth, model_id, "model_implied_under_exogeneity_assumption", m, v_cur, v_orc)]


def budget_equalized_rows(world, obs, truth, rows: list[dict], v_cur: float, v_orc: float) -> list[dict]:
    """Post-hoc: rescale stored model policies (selected_channels_do_policy) to the realized true budget.

    Regret is only comparable at equal realized spend. The rescaling uses the truth engine, so the
    result is labelled as such and is not something the model could do on its own.
    """
    p = SelectedChannelsProblem(InterventionEngine(world), obs, world.g["g_cc"])
    out = []
    for r in rows:
        m = np.array([float(x) for x in r["multipliers"].split(",")])
        out.append({**p.row(truth, f"{r['policy']}|budget_equalized", "model_policy_rescaled_to_true_budget_via_engine",
                            p.project_true_budget(m), v_cur, v_orc), "base_policy": r["policy"]})
    return out
