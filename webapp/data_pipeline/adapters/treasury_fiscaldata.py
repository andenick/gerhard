"""U.S. Treasury Fiscal Data API adapter (no key required).

Docs: https://fiscaldata.treasury.gov/api-documentation/
Covers MTS (S022), average interest rates (S023), MSPD table 1 (S026).
"""
from __future__ import annotations

import requests
import pandas as pd

BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"

ENDPOINTS = {
    "S022": ("/v1/accounting/mts/mts_table_4", "record_date"),
    "S023": ("/v2/accounting/od/avg_interest_rates", "record_date"),
    "S026": ("/v1/debt/mspd/mspd_table_1", "record_date"),
    "S028": ("/v1/accounting/od/auctions_query", "auction_date"),
}


def _get(path: str, params: dict) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        p = dict(params, **{"page[number]": page, "page[size]": 10000})
        r = requests.get(BASE + path, params=p, timeout=60)
        r.raise_for_status()
        js = r.json()
        data = js.get("data", [])
        rows.extend(data)
        if page >= js.get("meta", {}).get("total-pages", 1) or not data:
            break
        page += 1
    return rows


def fetch(series_id: str) -> pd.DataFrame:
    if series_id not in ENDPOINTS:
        raise ValueError(f"treasury adapter has no endpoint for {series_id}")
    path, date_field = ENDPOINTS[series_id]
    df = pd.DataFrame(_get(path, {"sort": date_field}))
    if date_field in df.columns:
        df["date"] = pd.to_datetime(df[date_field], errors="coerce")
        df["year"] = df["date"].dt.year
    for c in df.columns:
        if c in (date_field, "date", "year"):
            continue
        coerced = pd.to_numeric(df[c], errors="coerce")
        # keep coercion only if it didn't wipe out a genuinely non-numeric column
        if coerced.notna().any():
            df[c] = coerced
    return df
