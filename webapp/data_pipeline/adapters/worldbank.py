"""World Bank WDI adapter (no key required).

Docs: https://api.worldbank.org/v2/
Returns a tidy DataFrame (country_code, country_name, year, <indicator>).
"""
from __future__ import annotations

import requests
import pandas as pd

BASE = "https://api.worldbank.org/v2"

INDICATORS = {"S001": "GC.TAX.TOTL.GD.ZS", "S002": "GC.TAX.TOTL.GD.ZS", "S006": "GC.TAX.TOTL.GD.ZS"}


def fetch_indicator(indicator: str) -> pd.DataFrame:
    rows: list[dict] = []
    page = 1
    while True:
        r = requests.get(f"{BASE}/country/all/indicator/{indicator}",
                         params={"format": "json", "per_page": 20000, "page": page}, timeout=60)
        r.raise_for_status()
        js = r.json()
        if not isinstance(js, list) or len(js) < 2 or js[1] is None:
            break
        meta, data = js[0], js[1]
        for d in data:
            rows.append({"country_code": (d.get("countryiso3code") or "").strip(),
                         "country_name": (d.get("country") or {}).get("value"),
                         "year": int(d["date"]) if d.get("date") else None,
                         "value": d.get("value")})
        if page >= meta.get("pages", 1):
            break
        page += 1
    df = pd.DataFrame(rows).dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    return df


def fetch(series_id: str) -> pd.DataFrame:
    ind = INDICATORS.get(series_id)
    if not ind:
        raise ValueError(f"worldbank adapter has no indicator for {series_id}")
    return fetch_indicator(ind).rename(columns={"value": ind})
