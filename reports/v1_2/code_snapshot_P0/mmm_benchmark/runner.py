"""Resumable execution: one JSON (+NPZ) per (world, model); failures are recorded, never dropped."""

from __future__ import annotations

import dataclasses
import json
import threading
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

from . import causal
from .config import RunConfig
from .evaluation import score, world_descriptors
from .generator_adapter import WorldSpec, WorldStore
from .interventions import BLOCKED, InterventionEngine, validate_engine
from .models import make_model
from .models.base import Estimator
from .provenance import ROOT, config_hash, derive_seed, environment_fingerprint
from .schema import ModelOutput, ObservedDataset, TruthRegistry

WORLD_CACHE = ROOT / "runs" / "_worlds"


class PeakRSS:
    """Samples this process' RSS every 0.1 s; nutpie/numba allocations are included."""

    def __enter__(self):
        self.proc = psutil.Process()
        self.peak = self.proc.memory_info().rss
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
        return self

    def _run(self):
        while not self._stop.wait(0.1):
            self.peak = max(self.peak, self.proc.memory_info().rss)

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join()
        self.peak_mb = self.peak / 2**20


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    return str(o)


def write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_json_default))
    tmp.replace(path)


def fit_model(model_id: str, kwargs: dict, obs: ObservedDataset, world) -> tuple[ModelOutput, Estimator | None]:
    """``model_id`` may carry a variant label after '@' (e.g. ``M3_pymc_marketing@ta95``)."""
    seed = derive_seed(obs.world_id, model_id.split("@")[0], "fit")
    model = make_model(model_id.split("@")[0], **kwargs)
    out = ModelOutput(model_id, obs.world_id, model.family, model.information_set, "ok", seed)
    view = obs.fit_view()
    t0 = time.perf_counter()
    try:
        with PeakRSS() as mon:
            if model.privileged:
                model.attach_privileged(world)
            model.fit(view, seed=seed)
            out.y_pred = np.asarray(model.predict(view), dtype=float)
            c = model.contributions(view)
            out.contributions = None if c is None else np.asarray(c, dtype=float)
            out.contrib_intervals = model.contribution_intervals(view)
            out.y_intervals = model.y_intervals(view)
            out.explanation = model.explanation(view)
            out.diagnostics = model.diagnostics()
        out.peak_rss_mb = mon.peak_mb
    except Exception as exc:  # recorded, the run continues
        out.fit_status, out.error = "failed", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        model = None
    out.runtime_s = time.perf_counter() - t0
    return out, model


def save_arrays(path: Path, out: ModelOutput) -> None:
    arrays = {}
    for name in ("y_pred", "contributions", "explanation"):
        val = getattr(out, name)
        if val is not None:
            arrays[name] = val
    for kind in ("contrib_intervals", "y_intervals"):
        for lv, (lo, hi) in (getattr(out, kind) or {}).items():
            arrays[f"{kind}_{int(lv * 100)}_lo"] = lo
            arrays[f"{kind}_{int(lv * 100)}_hi"] = hi
    if arrays:
        np.savez_compressed(path, **arrays)


class Runner:
    def __init__(self, cfg: RunConfig, run_dir: Path | None = None, retry_failed: bool = False,
                 max_worlds: int | None = None):
        self.cfg = cfg
        self.run_dir = Path(run_dir or ROOT / "runs" / cfg.name)
        self.store = WorldStore(WORLD_CACHE)
        self.retry_failed = retry_failed
        self.max_worlds = max_worlds
        self.pending = 0

    def log(self, msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with (self.run_dir / "run.log").open("a") as fh:
            fh.write(line + "\n")

    def write_manifest(self, extra: dict | None = None) -> None:
        cfgd = self.cfg.to_dict()
        manifest_path = self.run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        manifest.update({
            "config": cfgd,
            "config_sha256": config_hash(cfgd),
            "schema": "mmm_benchmark/1",
            "planned": {s.world_id: self.cfg.models_for(s) for s in self.cfg.worlds()},
            "expensive_subset_preregistered": [s.world_id for s in self.cfg.worlds() if self.cfg.expensive_subset.contains(s)],
            "causal_subset_preregistered": [s.world_id for s in self.cfg.worlds() if self.cfg.causal_subset.contains(s)],
        })
        manifest.setdefault("sessions", []).append(environment_fingerprint())
        if extra:
            manifest.update(extra)
        write_json(manifest_path, manifest)

    def generate(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for spec in self.cfg.worlds():
            t0 = time.perf_counter()
            world, obs, truth = self.store.load(spec)
            rows.append({**world_descriptors(obs, truth), "identity_error": truth.meta["identity_error"],
                         "generate_or_load_s": time.perf_counter() - t0})
            if self.cfg.write_bundles:
                import pymc_generator as pg

                bdir = self.run_dir / "bundles" / spec.world_id
                if not bdir.exists():
                    pg.write_scm_bundle(world, bdir, title=spec.world_id, plots=True)
            self.log(f"world {spec.world_id} ready ({rows[-1]['generate_or_load_s']:.1f}s)")
        pd.DataFrame(rows).to_csv(self.run_dir / "worlds.csv", index=False)

    def _world_level(self, spec: WorldSpec, world, obs, truth, wdir: Path):
        """Engine validation + truth/reference causal rows, computed once per world."""
        path = wdir / "_world.json"
        if path.exists():
            info = json.loads(path.read_text())
        else:
            info = {"descriptors": world_descriptors(obs, truth), "meta": truth.meta}
            if self.cfg.causal_subset.contains(spec) and (self.cfg.run_e08 or self.cfg.run_e09):
                t0 = time.perf_counter()
                try:
                    engine = InterventionEngine(world)
                    val = validate_engine(engine, obs.world_id, truth.channel_roles)
                    info["engine_validation"] = {"status": val.status, "checks": val.checks}
                    if self.cfg.run_e08:
                        info["e08_truth"] = causal.e08_truth(engine, obs, truth) if val.status != BLOCKED else []
                    if self.cfg.run_e09 and val.status != BLOCKED:
                        problem = causal.BudgetProblem(engine, obs)
                        rows, v_cur, v_orc = causal.e09_reference(problem, truth, random_policy=self.cfg.e09_random)
                        info["e09_reference"], info["e09_values"] = rows, {"current": v_cur, "oracle": v_orc}
                        if self.cfg.e09_selected_channels and np.asarray(world.g["g_cc"]).any():
                            sp = causal.SelectedChannelsProblem(engine, obs, world.g["g_cc"])
                            srows, s_cur, s_orc = causal.e09_selected_reference(sp, truth)
                            info["e09_reference"] += srows
                            info["e09_selected_values"] = {"current": s_cur, "oracle": s_orc}
                except Exception as exc:
                    info["engine_validation"] = {"status": BLOCKED, "error": f"{type(exc).__name__}: {exc}",
                                                 "traceback": traceback.format_exc()}
                info["causal_reference_s"] = time.perf_counter() - t0
            write_json(path, info)
        return info

    def run(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.write_manifest()
        if self.cfg.write_bundles:
            self.generate()
        specs = self.cfg.worlds()
        self.log(f"run {self.cfg.name}: {len(specs)} worlds")
        done_here = 0
        for i, spec in enumerate(specs):
            wdir = self.run_dir / "results" / spec.world_id
            wdir.mkdir(parents=True, exist_ok=True)
            todo = [m for m in self.cfg.models_for(spec) if self._needs(wdir / f"{m}.json")]
            if not todo and (wdir / "_world.json").exists():
                continue
            if self.max_worlds is not None and done_here >= self.max_worlds:
                self.pending += 1
                continue
            done_here += 1
            world, obs, truth = self.store.load(spec)
            info = self._world_level(spec, world, obs, truth, wdir)
            validated = info.get("engine_validation", {}).get("status") == "validated"
            full = self.cfg.fit_scope == "full"
            if full:
                obs = dataclasses.replace(obs, train_idx=np.arange(obs.T), test_idx=np.arange(0))
            elif self.cfg.fit_scope == "train_after_warmup":
                # weeks 0..WARMUP-1 stay as treatment history for adstock but are not fitted (v1.2 P0 finding)
                obs = dataclasses.replace(obs, train_idx=obs.train_idx[obs.train_idx >= obs.warmup])
            engine = problem = sproblem = None
            for model_id in todo:
                kwargs = self.cfg.expensive_models.get(model_id, {}) or {}
                out, model = fit_model(model_id, kwargs, obs, world)
                rec = {
                    "model_id": model_id, "world_id": spec.world_id, "fit_status": out.fit_status,
                    "family": out.family, "information_set": out.information_set, "seed": out.seed,
                    "runtime_s": out.runtime_s, "peak_rss_mb": out.peak_rss_mb,
                    "diagnostics": out.diagnostics, "error": out.error, "fit_scope": self.cfg.fit_scope,
                    "metrics": score(out, obs, truth, full_refit=full),
                }
                if model is not None and hasattr(model, "posterior_arrays"):
                    np.savez_compressed(wdir / f"{model_id}.posterior.npz", **model.posterior_arrays())
                if (model is not None and validated and not full and self.cfg.causal_subset.contains(spec)
                        and model_id in self.cfg.causal_models):
                    t0 = time.perf_counter()
                    try:
                        if engine is None:
                            engine = InterventionEngine(world)
                            problem = causal.BudgetProblem(engine, obs)
                        if self.cfg.run_e08:
                            rec["e08"] = causal.e08_model(model_id, model, obs, info.get("e08_truth", []))
                        if self.cfg.run_e09:
                            v = info["e09_values"]
                            rec["e09"] = causal.e09_model(model_id, model, problem, truth, v["current"], v["oracle"])
                            if "e09_selected_values" in info:
                                if sproblem is None:
                                    sproblem = causal.SelectedChannelsProblem(engine, obs, world.g["g_cc"])
                                sv = info["e09_selected_values"]
                                rec["e09"] += causal.e09_selected_model(model_id, model, sproblem, truth,
                                                                        sv["current"], sv["oracle"])
                    except Exception as exc:
                        rec["causal_error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
                    rec["causal_s"] = time.perf_counter() - t0
                save_arrays(wdir / f"{model_id}.npz", out)
                write_json(wdir / f"{model_id}.json", rec)
                self.log(f"[{i + 1}/{len(specs)}] {spec.world_id} {model_id}: {out.fit_status} "
                         f"{out.runtime_s:.1f}s peak {out.peak_rss_mb:.0f}MB")
        aggregate(self.run_dir)
        self.write_manifest({"finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "pending_worlds": self.pending})
        if self.pending:
            self.log(f"chunk done; {self.pending} worlds pending (re-run with --resume)")

    def _needs(self, path: Path) -> bool:
        if not path.exists():
            return True
        return self.retry_failed and json.loads(path.read_text())["fit_status"] == "failed"


def aggregate(run_dir: Path) -> dict[str, pd.DataFrame]:
    run_dir = Path(run_dir)
    metrics, e08, e09, status, worlds, validation = [], [], [], [], [], []
    for wdir in sorted((run_dir / "results").glob("*")):
        wpath = wdir / "_world.json"
        if wpath.exists():
            info = json.loads(wpath.read_text())
            worlds.append(info["descriptors"])
            e08 += info.get("e08_truth", [])
            e09 += info.get("e09_reference", [])
            ev = info.get("engine_validation")
            if ev:
                validation.append({"world_id": wdir.name, "status": ev["status"],
                                   **{f"{k}_passed": v.get("passed") for k, v in ev.get("checks", {}).items()},
                                   **{f"{k}_max_abs": v.get("max_abs") for k, v in ev.get("checks", {}).items()},
                                   "error": ev.get("error")})
        for p in sorted(wdir.glob("*.json")):
            if p.name.startswith("_"):
                continue
            rec = json.loads(p.read_text())
            metrics += rec["metrics"]
            e08 += rec.get("e08", [])
            e09 += rec.get("e09", [])
            d = rec.get("diagnostics") or {}
            status.append({
                "world_id": rec["world_id"], "model_id": rec["model_id"], "fit_status": rec["fit_status"],
                "family": rec["family"], "information_set": rec["information_set"],
                "runtime_s": rec["runtime_s"], "peak_rss_mb": rec["peak_rss_mb"],
                "rhat_max": d.get("rhat_max"), "ess_bulk_min": d.get("ess_bulk_min"),
                "divergences": d.get("divergences"), "converged_strict": d.get("converged_strict"),
                "converged_pilot": d.get("converged_pilot"), "causal_error": bool(rec.get("causal_error")),
                "error": (rec.get("error") or "").splitlines()[0] if rec.get("error") else None,
            })
    tables = {
        "metrics": pd.DataFrame(metrics), "e08": pd.DataFrame(e08), "e09": pd.DataFrame(e09),
        "status": pd.DataFrame(status), "worlds": pd.DataFrame(worlds), "engine_validation": pd.DataFrame(validation),
    }
    out = run_dir / "tables"
    out.mkdir(exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
    return tables
