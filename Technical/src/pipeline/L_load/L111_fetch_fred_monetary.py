#!/usr/bin/env python3
"""
L111: Fetch FRED Monetary
Pull monetary aggregates, Fed balance sheet, and key policy rates from FRED.
Stage: L | ID: L111
Project: Gerhard
"""
import os
import sys
import time
from pathlib import Path
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.config import project_root
logger = setup_logging(__name__)

MANIFEST = {
    "id": "L111",
    "name": "Fetch FRED Monetary",
    "stage": "L",
    "description": "Pull monetary aggregates, Fed balance sheet, and key policy rates from FRED",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/raw/treasury/fred_monetary.csv"}],
    "timeout": 300,
    "parallel_safe": True,
}

FRED_API_KEY = os.environ.get("FRED_API_KEY")
if not FRED_API_KEY:
    raise RuntimeError("Set the FRED_API_KEY environment variable (free key: https://fred.stlouisfed.org/docs/api/api_key.html)")

FRED_SERIES = {
    'M1SL': 'M1 Money Stock',
    'M2SL': 'M2 Money Stock',
    'BOGMBASE': 'Monetary Base',
    'WALCL': 'Fed Total Assets',
    'WTREGEN': 'Fed Treasury Holdings',
    'FEDFUNDS': 'Effective Fed Funds Rate',
    'SOFR': 'SOFR Rate',
    'DPRIME': 'Bank Prime Rate',
    'TOTRESNS': 'Total Reserves',
    'EXCSRESNS': 'Excess Reserves',
}


def fetch_fred(series_id, start='1950-01-01'):
    """Fetch a FRED series."""
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'observation_start': start,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            logger.warning(f"  {series_id}: HTTP {response.status_code}")
            return pd.DataFrame()

        data = response.json()
        observations = data.get('observations', [])

        df = pd.DataFrame(observations)
        if len(df) > 0:
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df[['date', 'value']].rename(columns={'value': series_id})

        return df

    except Exception as e:
        logger.error(f"  Error fetching {series_id}: {e}")
        return pd.DataFrame()


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    raw_dir = project_root() / "Technical" / "data" / "raw" / "treasury"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Fetch all series
    all_series = {}
    for series_id, description in FRED_SERIES.items():
        logger.info(f"  Fetching {series_id} ({description})...")
        df = fetch_fred(series_id)

        if len(df) > 0:
            all_series[series_id] = df.set_index('date')[series_id]
            logger.info(f"    {len(df)} observations, {df['date'].min()} to {df['date'].max()}")
        else:
            logger.warning(f"    No data for {series_id}")

        time.sleep(0.5)  # Rate limiting

    # Combine into single DataFrame
    if all_series:
        combined = pd.DataFrame(all_series)
        combined.index.name = 'date'
        combined = combined.sort_index()

        output_path = raw_dir / "fred_monetary.csv"
        combined.to_csv(output_path)
        logger.info(f"Saved {output_path.name}: {len(combined)} rows x {len(combined.columns)} series")
        logger.info(f"  Date range: {combined.index.min()} to {combined.index.max()}")

    logger.info(f"[L111] Done.")


if __name__ == "__main__":
    run()
