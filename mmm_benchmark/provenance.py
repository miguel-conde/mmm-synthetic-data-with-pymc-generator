"""Seeds, versions, hashes and system fingerprint for manifests."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import psutil

MASTER_SEED = 20261105
ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    "pymc-generator",
    "pymc",
    "pymc-marketing",
    "pytensor",
    "numpy",
    "scipy",
    "pandas",
    "scikit-learn",
    "xgboost-cpu",
    "lightgbm",
    "nutpie",
    "arviz",
)


def derive_seed(*parts: object) -> int:
    """Stable 31-bit seed: SHA-256 of ``MASTER_SEED|part1|part2|...`` (never Python's ``hash``)."""
    key = "|".join(str(p) for p in (MASTER_SEED, *parts)).encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], "big") & 0x7FFFFFFF


def package_versions() -> dict[str, str]:
    out = {}
    for name in PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = "not-installed"
    return out


def generator_commit() -> str | None:
    try:
        raw = metadata.distribution("pymc-generator").read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return None
    if not raw:
        return None
    return json.loads(raw).get("vcs_info", {}).get("commit_id")


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def code_hash() -> str:
    h = hashlib.sha256()
    for path in sorted((ROOT / "mmm_benchmark").rglob("*.py")):
        h.update(path.relative_to(ROOT).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()


def system_info() -> dict:
    vm = psutil.virtual_memory()
    return {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "cpu_count_logical": os.cpu_count(),
        "ram_total_gb": round(vm.total / 2**30, 2),
        "ram_available_gb_at_start": round(vm.available / 2**30, 2),
    }


def environment_fingerprint() -> dict:
    return {
        "packages": package_versions(),
        "pymc_generator_commit": generator_commit(),
        "uv_lock_sha256": sha256_file(ROOT / "uv.lock"),
        "code_sha256": code_hash(),
        "system": system_info(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
