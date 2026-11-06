"""Experiment configuration (YAML) expanded into a concrete, pre-registered work list."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from .generator_adapter import WorldSpec


@dataclass
class Subset:
    scenarios: list[str] | None = None
    horizons: list[int] | None = None
    replicates: list[int] | None = None

    def contains(self, spec: WorldSpec) -> bool:
        return (
            (self.scenarios is None or spec.scenario in self.scenarios)
            and (self.horizons is None or spec.T in self.horizons)
            and (self.replicates is None or spec.replicate in self.replicates)
        )


@dataclass
class RunConfig:
    name: str
    phase: str
    scenarios: list[str]
    horizons: list[int]
    replicates: list[int]
    fast_models: list[str]
    expensive_models: dict[str, dict] = field(default_factory=dict)
    expensive_subset: Subset = field(default_factory=Subset)
    causal_models: list[str] = field(default_factory=list)
    causal_subset: Subset = field(default_factory=Subset)
    run_e08: bool = True
    run_e09: bool = True
    e09_random: bool = False
    e09_selected_channels: bool = False
    write_bundles: bool = False
    description: str = ""
    variants: dict[str, dict] = field(default_factory=lambda: {"": {}})
    world_list: list[str] | None = None
    fit_scope: str = "train"  # train | full (historical_full_refit sensitivity)

    @classmethod
    def load(cls, path: str | Path) -> RunConfig:
        raw = yaml.safe_load(Path(path).read_text())
        raw["expensive_subset"] = Subset(**(raw.get("expensive_subset") or {}))
        raw["causal_subset"] = Subset(**(raw.get("causal_subset") or {}))
        return cls(**raw)

    def worlds(self) -> list[WorldSpec]:
        specs = [
            WorldSpec(s, T, r, variant=v, overrides=tuple(sorted(
                (k, tuple(x) if isinstance(x, list) else x) for k, x in (ov or {}).items())))
            for s in self.scenarios
            for T in self.horizons
            for r in self.replicates
            for v, ov in self.variants.items()
        ]
        if self.world_list is not None:
            specs = [s for s in specs if s.world_id in set(self.world_list)]
        return specs

    def models_for(self, spec: WorldSpec) -> list[str]:
        models = list(self.fast_models)
        if self.expensive_subset.contains(spec):
            models += list(self.expensive_models)
        return models

    def to_dict(self) -> dict:
        return asdict(self)
