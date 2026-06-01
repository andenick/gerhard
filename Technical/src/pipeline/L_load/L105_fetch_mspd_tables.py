#!/usr/bin/env python3
"""
L105: Fetch MSPD Tables
Pull Monthly Statement of Public Debt from Treasury FiscalData API.
Stage: L | ID: L105
Project: Gerhard
"""
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
    "id": "L105",
    "name": "Fetch MSPD Tables",
    "stage": "L",
    "description": "Pull Monthly Statement of Public Debt from Treasury FiscalData API (2001-present)",
    "depends_on": [],
    "inputs": [],
    "outputs": [
        {"path": "Technical/data/raw/treasury/mspd_table_1.csv"},
        {"path": "Technical/data/raw/treasury/mspd_table_3_market.csv"},
        {"path": "Technical/data/raw/treasury/mspd_table_4.csv"},
    ],
    "timeout": 600,
    "parallel_safe": True,
}

BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/debt/mspd"

TABLES = {
    'mspd_table_1': 'Summary of Treasury Securities Outstanding',
    'mspd_table_3_market': 'Marketable Securities Detail',
    'mspd_table_3_nonmarket': 'Non-Marketable Securities Detail',
    'mspd_table_4': 'Historical Debt Outstanding',
    'mspd_table_5': 'STRIPS Detail',
}


def fetch_table(table_name, start_date='2001-01-01', page_size=10000):
    """Fetch a complete MSPD table with pagination."""
    url = f"{BASE_URL}/{table_name}"
    all_records = []
    page = 1

    while True:
        params = {
            'page[number]': page,
            'page[size]': page_size,
            'filter': f'record_date:gte:{start_date}',
            'sort': 'record_date',
        }

        try:
            response = requests.get(url, params=params, timeout=60)
            if response.status_code != 200:
                logger.warning(f"  {table_name} page {page}: HTTP {response.status_code}")
                break

            data = response.json()
            records = data.get('data', [])
            total = data.get('meta', {}).get('total-count', 0)

            all_records.extend(records)
            logger.info(f"  {table_name}: page {page}, {len(all_records)}/{total} records")

            if len(all_records) >= total or not records:
                break

            page += 1
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            logger.error(f"  Error fetching {table_name} page {page}: {e}")
            break

    return pd.DataFrame(all_records)


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    raw_dir = project_root() / "Technical" / "data" / "raw" / "treasury"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for table_name, description in TABLES.items():
        logger.info(f"Fetching {table_name} ({description})...")
        df = fetch_table(table_name)

        if len(df) > 0:
            output_path = raw_dir / f"{table_name}.csv"
            df.to_csv(output_path, index=False)
            logger.info(f"  Saved {output_path.name}: {len(df)} records")

            # Report date range
            if 'record_date' in df.columns:
                logger.info(f"  Date range: {df['record_date'].min()} to {df['record_date'].max()}")
        else:
            logger.warning(f"  No data returned for {table_name}")

        time.sleep(1)  # Rate limiting between tables

    logger.info(f"[L105] Done. Files saved to {raw_dir}")


if __name__ == "__main__":
    run()
