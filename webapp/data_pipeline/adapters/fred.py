"""FRED adapter (key from FRED_API_KEY env var via config).

Docs: https://fred.stlouisfed.org/docs/api/fred/
Monetary (S025) and yield-curve cross-check (S027). Wide DataFrame by date.
"""
from __future__ import annotations

import requests
import pandas as pd

from app import config as C

BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES_MAP = {"S025": ["M2SL", "M1SL", "BOGMBASE", "WALCL"],
              "S027": ["DGS3MO", "DGS2", "DGS5", "DGS10", "DGS30"]}


def _fetch_one(fred_id: str, key: str) -> pd.Series:
    r = requests.get(BASE, params={"series_id": fred_id, "api_key": key, "file_type": "json"}, timeout=60)
    r.raise_for_status()
    obs = r.json().get("observations", [])
    s = pd.Series({o["date"]: o["value"] for o in obs}, name=fred_id)
    s.index = pd.to_datetime(s.index, errors="coerce")
    return pd.to_numeric(s.replace(".", None), errors="coerce")


def fetch(series_id: str) -> pd.DataFrame:
    key = C.get_api_key("fred")
    if not key:
        raise RuntimeError("FRED API key not available; set the FRED_API_KEY environment variable (free key: https://fred.stlouisfed.org/docs/api/api_key.html)")
    ids = SERIES_MAP.get(series_id)
    if not ids:
        raise ValueError(f"fred adapter has no mapping for {series_id}")
    df = pd.DataFrame({fid: _fetch_one(fid, key) for fid in ids})
    df.index.name = "date"
    df = df.reset_index()
    df["year"] = df["date"].dt.year
    return df
