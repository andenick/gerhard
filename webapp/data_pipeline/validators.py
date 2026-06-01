"""Refresh validators — guard against bad/short/empty fetches.

Honors the Anu no-synthetic / no-freeze rule: a fetch that fails validation must
NOT overwrite good data. Returns (ok, reason).
"""
from __future__ import annotations

import pandas as pd


def validate_fetch(new: pd.DataFrame, old: pd.DataFrame | None,
                   min_rows: int = 1, shrink_tolerance: float = 0.9) -> tuple[bool, str]:
    if new is None or new.empty:
        return False, "fetch returned empty frame"
    if len(new) < min_rows:
        return False, f"too few rows ({len(new)} < {min_rows})"
    id_cols = {"country_code", "country_name", "year", "date", "record_date"}
    data_cols = [c for c in new.columns if c not in id_cols]
    if data_cols and new[data_cols].notna().sum().sum() == 0:
        return False, "all data columns are NaN"
    if old is not None and not old.empty and len(new) < len(old) * shrink_tolerance:
        return False, f"row count shrank ({len(new)} < {len(old)}*{shrink_tolerance})"
    return True, "ok"
