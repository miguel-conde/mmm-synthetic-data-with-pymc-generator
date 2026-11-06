"""Typed reading of saved result tables (C5): no silent NA conversion of literal labels."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROLE_CATEGORIES = ("direct", "feeder", "isolated")
LEGACY_ROLES = {"null": "isolated"}  # v1 wrote 'null', which pandas' default NA parsing turns into NaN


def read_table(path: str | Path) -> pd.DataFrame:
    """Only empty fields are missing; ``role`` becomes a categorical with the three valid labels."""
    try:
        df = pd.read_csv(path, keep_default_na=False, na_values=[""], low_memory=False)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()
    if "role" in df:
        role = df["role"].replace(LEGACY_ROLES)
        bad = set(role.dropna().unique()) - set(ROLE_CATEGORIES)
        if bad:
            raise ValueError(f"{path}: unknown channel roles {sorted(bad)}")
        df["role"] = pd.Categorical(role, categories=ROLE_CATEGORIES)
    return df
