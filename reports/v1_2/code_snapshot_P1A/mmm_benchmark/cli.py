"""Command line: doctor | generate | run | report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_doctor(_: argparse.Namespace) -> int:
    from .generator_adapter import SCENARIO_IDS
    from .provenance import environment_fingerprint

    import pymc_generator as pg

    env = environment_fingerprint()
    print(json.dumps(env, indent=1))
    installed = [s.name for s in pg.SCENARIOS]
    missing = sorted(set(SCENARIO_IDS) - set(installed))
    print("scenarios installed:", installed)
    if missing:
        print("MISSING scenarios:", missing)
        return 1
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    from .config import RunConfig
    from .runner import Runner

    Runner(RunConfig.load(args.config), args.run_dir).generate()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .config import RunConfig
    from .runner import Runner

    cfg = RunConfig.load(args.config)
    run_dir = Path(args.run_dir) if args.run_dir else None
    runner = Runner(cfg, run_dir, retry_failed=args.retry_failed, max_worlds=args.max_worlds)
    if not args.resume and runner.run_dir.exists() and any((runner.run_dir / "results").glob("*/*.json")):
        print(f"{runner.run_dir} has results; pass --resume to continue it", file=sys.stderr)
        return 2
    runner.run()
    return 3 if runner.pending else 0


def cmd_report(args: argparse.Namespace) -> int:
    from .reporting import build_report

    build_report([Path(p) for p in args.run_dir], Path(args.out))
    return 0


def cmd_revise(_: argparse.Namespace) -> int:
    from .revision import build_v1_1, write_reports

    write_reports(build_v1_1())
    return 0


def cmd_audit_v1_2(_: argparse.Namespace) -> int:
    from .audit_v1_2 import build_p0

    build_p0()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mmm_benchmark")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    g = sub.add_parser("generate")
    g.add_argument("--config", required=True)
    g.add_argument("--run-dir")
    g.set_defaults(fn=cmd_generate)
    r = sub.add_parser("run")
    r.add_argument("--config", required=True)
    r.add_argument("--run-dir")
    r.add_argument("--resume", action="store_true")
    r.add_argument("--retry-failed", action="store_true")
    r.add_argument("--max-worlds", type=int, help="process at most N pending worlds, then exit 3 (bounded memory)")
    r.set_defaults(fn=cmd_run)
    rep = sub.add_parser("report")
    rep.add_argument("--run-dir", nargs="+", required=True)
    rep.add_argument("--out", default="reports")
    rep.set_defaults(fn=cmd_report)
    sub.add_parser("revise", help="v1.1 revision analyses and reports").set_defaults(fn=cmd_revise)
    sub.add_parser("audit-v1-2", help="v1.2 P0 audits (no refits)").set_defaults(fn=cmd_audit_v1_2)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
