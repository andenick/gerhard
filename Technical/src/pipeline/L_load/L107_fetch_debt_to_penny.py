#!/usr/bin/env python3
"""
L107: Fetch Debt to the Penny
Pull daily total public debt outstanding from FiscalData API.
Stage: L | ID: L107
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
    "id": "L107",
    "name": "Fetch Debt to the Penny",
    "stage": "L",
    "description": "Pull daily total public debt outstanding from FiscalData API",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/raw/treasury/debt_to_penny.csv"}],
    "timeout": 600,
    "parallel_safe": True,
}


def fetch_paginated(url, page_size=10000):
    """Fetch all records from a FiscalData endpoint with pagination."""
    all_records = []
    page = 1

    while True:
        params = {'page[number]': page, 'page[size]': page_size, 'sort': 'record_date'}
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code != 200:
                logger.warning(f"HTTP {r.status_code}")
                break
            data = r.json()
            records = data.get('data', [])
            total = data.get('meta', {}).get('total-count', 0)
            all_records.extend(records)
            logger.info(f"  Page {page}: {len(all_records)}/{total}")
            if len(all_records) >= total or not records:
                break
            page += 1
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error on page {page}: {e}")
            break

    return all_records


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    raw_dir = project_root() / "Technical" / "data" / "raw" / "treasury"
    raw_dir.mkdir(parents=True, exist_ok=True)

    url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny"
    all_records = fetch_paginated(url)

    if all_records:
        df = pd.DataFrame(all_records)
        out = raw_dir / "debt_to_penny.csv"
        df.to_csv(out, index=False)
        logger.info(f"Saved {out.name}: {len(df)} records")
        if 'record_date' in df.columns:
            logger.info(f"  Date range: {df['record_date'].min()} to {df['record_date'].max()}")
    else:
        logger.warning("No debt-to-penny data retrieved")

    logger.info(f"[L107] Done.")


if __name__ == "__main__":
    run()
