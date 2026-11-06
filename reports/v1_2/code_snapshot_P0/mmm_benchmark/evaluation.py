"""Metric primitives and scoring of one ModelOutput against one TruthRegistry."""

from __future__ import annotations

import numpy as np

from .schema import OBS_PATH, PREDICTION, ModelOutput, ObservedDataset, TruthRegistry

NULL_FALSE_ATTRIBUTION_THRESHOLD = 0.02  # pre-registered in docs/methods.md

# task labels (v1.1, decision D2); v1 artefacts used the names on the right
PRED_IN = "prediction_in_sample"
PRED_FUT = "prediction_future_conditional_on_known_CZ"  # v1: prediction_conditional_future_inputs_known
HIST = "historical_in_sample_fit"  # v1: attribution_historical
HIST_FULL = "historical_full_refit"
ATTR_FUT = "attribution_future_conditional_on_known_CZ"  # v1: attribution_future_response
V1_TASKS = {
    "prediction_conditional_future_inputs_known": PRED_FUT,
    "attribution_historical": HIST,
    "attribution_future_response": ATTR_FUT,
}
V1_METRICS = {"null_false_attribution": "false_direct_attribution"}
V1_ROLES = {"null": "isolated"}


def mae(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def coverage(lo: np.ndarray, hi: np.ndarray, truth: np.ndarray) -> float:
    """Closed-interval convention: lo <= truth <= hi."""
    return float(np.mean((truth >= lo) & (truth <= hi)))


def interval_score(lo: np.ndarray, hi: np.ndarray, truth: np.ndarray, level: float) -> float:
    a = 1 - level
    return float(np.mean((hi - lo) + (2 / a) * (lo - truth) * (truth < lo) + (2 / a) * (truth - hi) * (truth > hi)))


def safe_ratio(num: float, den: float) -> float:
    return float(num / den) if abs(den) > 1e-12 else float("nan")


def paired_bootstrap(diff: np.ndarray, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Mean of per-world paired differences with a percentile 95% CI resampling worlds."""
    diff = np.asarray(diff, dtype=float)
    diff = diff[np.isfinite(diff)]
    if diff.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    boots = rng.choice(diff, size=(n_boot, diff.size), replace=True).mean(1)
    return float(diff.mean()), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


def score(out: ModelOutput, obs: ObservedDataset, truth: TruthRegistry, *, full_refit: bool = False,
          eval_start: int | None = None) -> list[dict]:
    """``eval_start`` overrides the attribution warm-up exclusion (default ``obs.warmup``)."""
    base = {
        "world_id": obs.world_id,
        "scenario_id": obs.scenario_id,
        "T": obs.T,
        "replicate": truth.meta["replicate"],
        "model_id": out.model_id,
        "family": out.family,
        "information_set": out.information_set,
    }
    rows: list[dict] = []

    def add(task, estimand, metric, value, channel=None, role=None, units="y_units", truth_source=""):
        rows.append(
            {**base, "task": task, "estimand_id": estimand, "metric": metric, "value": float(value),
             "channel": channel, "role": role, "units": units, "truth_source": truth_source}
        )

    if out.fit_status != "ok":
        return rows
    y = obs.y
    y_scale = float(np.mean(np.abs(y[obs.train_idx])))
    start = obs.warmup if eval_start is None else eval_start

    def window(split: str) -> np.ndarray:
        idx = obs.train_idx if split == "train" else obs.test_idx
        return idx[idx >= start]

    if out.y_pred is not None:
        for split, idx in (("train", window("train")), ("test", obs.test_idx)):
            if idx.size == 0:
                continue
            task = PRED_IN if split == "train" else PRED_FUT
            add(task, PREDICTION, "mae", mae(out.y_pred[idx], y[idx]), truth_source="outcome")
            add(task, PREDICTION, "rmse", rmse(out.y_pred[idx], y[idx]), truth_source="outcome")
            add(task, PREDICTION, "rmse_scaled", rmse(out.y_pred[idx], y[idx]) / y_scale, units="ratio", truth_source="outcome")
        if out.y_intervals and obs.test_idx.size:
            idx = obs.test_idx
            for lv, (lo, hi) in out.y_intervals.items():
                add(PRED_FUT, PREDICTION, f"coverage_{int(lv * 100)}",
                    coverage(lo[idx], hi[idx], y[idx]), units="fraction", truth_source="outcome")

    if out.contributions is None:
        return rows
    true_c = truth["contributions_observed"]
    roles = truth.channel_roles
    for split in ("train", "test"):
        idx = window(split)
        if idx.size == 0:
            continue
        task = (HIST_FULL if full_refit else HIST) if split == "train" else ATTR_FUT
        est, tru = out.contributions[idx], true_c[idx]
        denom_mean = float(np.mean(np.abs(y[idx])))
        denom_sum = float(np.sum(np.abs(y[idx])))
        src = "world.data['contributions_observed']"
        add(task, OBS_PATH, "contrib_mae_norm", mae(est, tru) / denom_mean, units="ratio", truth_source=src)
        add(task, OBS_PATH, "contrib_rmse_norm", rmse(est, tru) / denom_mean, units="ratio", truth_source=src)
        add(task, OBS_PATH, "contrib_mae", mae(est, tru), truth_source=src)
        add(task, OBS_PATH, "total_media_err_norm", (est.sum() - tru.sum()) / denom_sum, units="ratio", truth_source=src)
        biases = (est.sum(0) - tru.sum(0)) / denom_sum
        add(task, OBS_PATH, "channel_total_abs_err_norm", np.mean(np.abs(biases)), units="ratio", truth_source=src)
        for k in range(obs.K):
            add(task, OBS_PATH, "channel_total_bias_norm", biases[k], channel=k, role=roles[k], units="ratio", truth_source=src)
            if roles[k] != "direct":
                flag = abs(est[:, k].sum()) / denom_sum > NULL_FALSE_ATTRIBUTION_THRESHOLD
                add(task, OBS_PATH, "false_direct_attribution", flag, channel=k, role=roles[k], units="indicator", truth_source=src)
        if out.contrib_intervals:
            for lv, (lo, hi) in out.contrib_intervals.items():
                add(task, OBS_PATH, f"coverage_{int(lv * 100)}", coverage(lo[idx], hi[idx], tru), units="fraction", truth_source=src)
                add(task, OBS_PATH, f"width_norm_{int(lv * 100)}", np.mean(hi[idx] - lo[idx]) / denom_mean, units="ratio", truth_source=src)
                add(task, OBS_PATH, f"interval_score_norm_{int(lv * 100)}", interval_score(lo[idx], hi[idx], tru, lv) / denom_mean, units="ratio", truth_source=src)
    return rows


def world_descriptors(obs: ObservedDataset, truth: TruthRegistry) -> dict:
    """Observable and truth-side descriptors for subgroup analysis (evaluation side only)."""
    C = obs.C[obs.train_idx]
    corr = np.corrcoef(C.T) if obs.K > 1 else np.ones((1, 1))
    off = corr[~np.eye(obs.K, dtype=bool)]
    Xs = (C - C.mean(0)) / np.where(C.std(0) > 0, C.std(0), 1)
    y = obs.y
    tc = truth["contributions_observed"]
    return {
        "world_id": obs.world_id,
        "scenario_id": obs.scenario_id,
        "T": obs.T,
        "replicate": truth.meta["replicate"],
        "structure_cell_id": obs.structure_cell_id,
        "K": obs.K,
        "n_direct": sum(r == "direct" for r in truth.channel_roles),
        "n_feeder": sum(r == "feeder" for r in truth.channel_roles),
        "n_isolated": sum(r == "isolated" for r in truth.channel_roles),
        "mean_abs_channel_corr": float(np.mean(np.abs(off))) if off.size else 0.0,
        "max_abs_channel_corr": float(np.max(np.abs(off))) if off.size else 0.0,
        "condition_number": float(np.linalg.cond(Xs)),
        "noise_to_y_sd": float(np.std(truth["outcome_noise"]) / np.std(y)),
        "media_share_of_y": float(tc.sum() / np.abs(y).sum()),
        "indirect_share_of_y": float(np.abs(truth["indirect_effects"]).sum() / np.abs(y).sum()),
        "confounding_strength": truth.meta["confounding_strength"],
        "carryover": ",".join(truth.meta["carryover"]),
        "saturation": ",".join(truth.meta["saturation"]),
        "roles": ",".join(truth.channel_roles),
    }
