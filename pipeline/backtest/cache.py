"""Pickle-backed memo so nflverse/FFC pulls happen once, then run offline.

Uses pandas to_pickle/read_pickle (no extra dep — pyarrow isn't installed) so the
harness stays light. The cache under data/ is gitignored and fully regenerable:
delete a file to force a fresh pull."""
from __future__ import annotations

import os
from typing import Callable

import pandas as pd

_DIR = os.path.join(os.path.dirname(__file__), "data")


def cached(name: str, builder: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    os.makedirs(_DIR, exist_ok=True)
    path = os.path.join(_DIR, f"{name}.pkl")
    if os.path.exists(path):
        # Safe: we only ever read back pickles this process wrote itself from
        # nflverse (a trusted source) into this gitignored dir — never untrusted input.
        return pd.read_pickle(path)
    df = builder()
    df.to_pickle(path)
    return df
