#!/usr/bin/env python3
"""
L110: Fetch Yield Curves
Pull complete Treasury yield curve history from FRED for all maturities.
Stage: L | ID: L110
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
    "id": "L110",
    "name": "Fetch Yield Curves",
    "stage": "L",
    "description": "Pull complete Treasury yield curve from FRED (19 series, 1962-present)",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/raw/treasury/yield_curves_daily.csv"}],
    "timeout": 300,
    "parallel_safe": True,
}

FRED_API_KEY = os.environ.get("FRED_API_KEY")
if not FRED_API_KEY:
    raise RuntimeError("Set the FRED_API_KEY environment variable (free key: https://fred.stlouisfed.org/docs/api/api_key.html)")

FRED_SERIES = {
    'DGS1MO': '1-Month CM',
    'DGS3MO': '3-Month CM',
    'DGS6MO': '6-Month CM',
    'DGS1': '1-Year CM',
    'DGS2': '2-Year CM',
    'DGS3': '3-Year CM',
    'DGS5': '5-Year CM',
    'DGS7': '7-Year CM',
    'DGS10': '10-Year CM',
    'DGS20': '20-Year CM',
    'DGS30': '30-Year CM',
    'DFII5': '5-Year TIPS',
    'DFII10': '10-Year TIPS',
    'DFII20': '20-Year TIPS',
    'DFII30': '30-Year TIPS',
    'T10Y2Y': '10Y-2Y Spread',
    'T10Y3M': '10Y-3M Spread',
    'T10YIE': '10Y Breakeven Inflation',
    'DFF': 'Fed Funds Rate',
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

        output_path = raw_dir / "yield_curves_daily.csv"
        combined.to_csv(output_path)
        logger.info(f"Saved {output_path.name}: {len(combined)} days x {len(combined.columns)} series")
        logger.info(f"  Date range: {combined.index.min()} to {combined.index.max()}")

    logger.info(f"[L110] Done.")


if __name__ == "__main__":
    run()
