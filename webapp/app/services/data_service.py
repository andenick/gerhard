"""Data access layer — reads the Parquet cache + manifest from build_cache.py."""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from app import config as C


@lru_cache(maxsize=1)
def manifest() -> dict:
    if not C.MANIFEST_PATH.exists():
        return {"series": {}, "us_history": {}, "treasury": {}, "pending": []}
    return json.loads(C.MANIFEST_PATH.read_text(encoding="utf-8"))


def reload_manifest() -> dict:
    manifest.cache_clear()
    load_dataset.cache_clear()
    return manifest()


def _entry(key: str) -> dict | None:
    m = manifest()
    for bucket in ("series", "us_history", "treasury"):
        if key in m.get(bucket, {}):
            return m[bucket][key]
    return None


@lru_cache(maxsize=256)
def load_dataset(key: str) -> pd.DataFrame:
    entry = _entry(key)
    if entry and entry.get("cache_file"):
        p = C.WEBAPP_ROOT / "site_data" / entry["cache_file"]
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()
    p = C.CACHE_DIR / f"{key}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def list_series() -> dict:
    return manifest().get("series", {})


def list_treasury() -> dict:
    return manifest().get("treasury", {})


def list_us_history() -> dict:
    return manifest().get("us_history", {})


def dataset_entry(key: str) -> dict | None:
    return _entry(key)


def headline_stats() -> list[dict]:
    stats: list[dict] = []
    try:
        df = load_dataset("us_tax_1913_2024")
        if not df.empty and "top_1_percent_share" in df.columns:
            row = df.dropna(subset=["top_1_percent_share"]).iloc[-1]
            stats.append({"label": f"Top 1% income share ({int(row['year'])})",
                          "value": f"{float(row['top_1_percent_share']):.1f}%"})
    except Exception:
        pass
    try:
        df = load_dataset("S006")
        if not df.empty and "country_code" in df.columns and "debt_pct_gdp" in df.columns:
            us = df[df["country_code"] == "US"].dropna(subset=["debt_pct_gdp"])
            if not us.empty:
                row = us.iloc[-1]
                stats.append({"label": f"U.S. debt-to-GDP ({int(row['year'])})",
                              "value": f"{float(row['debt_pct_gdp']):.0f}%"})
    except Exception:
        pass
    try:
        df = load_dataset("treasury_comprehensive_ts")
        for col, lbl, fmt in [("Market_Average_Duration", "Avg market duration", "{:.1f} yrs"),
                              ("Total_Outstanding_Billions", "Marketable debt", "${:,.0f}B")]:
            if not df.empty and col in df.columns:
                v = df.dropna(subset=[col]).iloc[-1][col]
                stats.append({"label": lbl, "value": fmt.format(float(v))})
                break
    except Exception:
        pass
    n = sum(1 for s in list_series().values() if s.get("cached"))
    stats.append({"label": "Fiscal data series", "value": str(n)})
    return stats[:4]
