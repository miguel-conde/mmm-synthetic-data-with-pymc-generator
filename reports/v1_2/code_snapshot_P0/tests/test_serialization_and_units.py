"""C4/C5: serialization round trips and statistical-unit guarantees."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mmm_benchmark.evaluation import paired_bootstrap
from mmm_benchmark.generator_adapter import WorldSpec, WorldStore, channel_roles
from mmm_benchmark.provenance import ROOT
from mmm_benchmark.revision import cluster_bootstrap
from mmm_benchmark.runner import WORLD_CACHE
from mmm_benchmark.tables_io import ROLE_CATEGORIES, read_table

EXTENDED = ROOT / "runs" / "extended" / "tables" / "metrics.csv"


def test_literal_null_label_survives_round_trip(tmp_path):
    df = pd.DataFrame({"role": ["direct", "feeder", "null", "isolated"], "value": [1.0, 2.0, np.nan, 4.0]})
    p = tmp_path / "t.csv"
    df.to_csv(p, index=False)
    assert pd.read_csv(p)["role"].isna().sum() == 1  # the v1 failure mode
    back = read_table(p)
    assert list(back["role"]) == ["direct", "feeder", "isolated", "isolated"]
    assert list(back["role"].cat.categories) == list(ROLE_CATEGORIES)
    assert back["value"].isna().sum() == 1


def test_unknown_role_is_rejected(tmp_path):
    p = tmp_path / "t.csv"
    pd.DataFrame({"role": ["direct", "nul"]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        read_table(p)


def test_roles_round_trip_through_dag_and_tables():
    """Role written for each channel equals the role recomputed from the stored DAG."""
    for name, r in (("treatment_halo", 0), ("kitchen_sink", 1), ("direct_only", 0)):
        w = WorldStore(WORLD_CACHE).get(WorldSpec(name, 104, r))
        roles = channel_roles(w.g)
        g_cy = np.asarray(w.g["g_cy"]) != 0
        assert [ro == "direct" for ro in roles] == list(g_cy)


@pytest.mark.skipif(not EXTENDED.exists(), reason="v1 run artefacts not present")
def test_v1_isolated_pairs_are_recovered_and_match_dag():
    m = read_table(EXTENDED)
    fd = m[(m.metric == "null_false_attribution") & (m.task == "attribution_historical")]
    per_model = fd[fd.role == "isolated"].groupby("model_id").size()
    assert (per_model == 194).all() and len(per_model) >= 6
    store = WorldStore(WORLD_CACHE)
    sample = fd[fd.model_id == "M0_ols"].drop_duplicates(["world_id", "channel"])
    for wid, g in list(sample.groupby("world_id"))[:40]:
        scen, rest = wid.split("_T")
        T, rep = int(rest.split("_r")[0]), int(rest.split("_r")[1])
        roles = channel_roles(store.get(WorldSpec(scen.split("_", 1)[1], T, rep)).g)
        for _, row in g.iterrows():
            assert roles[int(row.channel)] == row.role


def test_bootstrap_unit_is_the_world_not_the_week():
    """Duplicating weeks inside a world must not narrow the interval: summarize per world first."""
    rng = np.random.default_rng(0)
    per_world = rng.normal(0.1, 0.05, 30)
    _, lo1, hi1 = paired_bootstrap(per_world)
    weekly = pd.DataFrame({"world": np.repeat(np.arange(30), 50), "v": np.repeat(per_world, 50)})
    _, lo2, hi2 = paired_bootstrap(weekly.groupby("world").v.mean().to_numpy())
    assert np.isclose(lo1, lo2) and np.isclose(hi1, hi2)


def test_cluster_bootstrap_widens_with_shared_cells():
    rng = np.random.default_rng(1)
    cell_effect = np.repeat(rng.normal(0, 1, 10), 10)
    d = pd.Series(cell_effect + rng.normal(0, 0.1, 100))
    _, wlo, whi = paired_bootstrap(d.to_numpy())
    _, clo, chi, n = cluster_bootstrap(d, pd.Series(np.repeat(np.arange(10), 10)))
    assert n == 10 and (chi - clo) > 2 * (whi - wlo)
