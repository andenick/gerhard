#!/usr/bin/env python3
"""
L115: Fetch Treasury Auctions
Pull Treasury auction results from FiscalData API.
Stage: L | ID: L115
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
    "id": "L115",
    "name": "Fetch Treasury Auctions",
    "stage": "L",
    "description": "Pull Treasury security auction results from FiscalData API",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/raw/treasury/auction_results.csv"}],
    "timeout": 300,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    raw_dir = project_root() / "Technical" / "data" / "raw" / "treasury"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Treasury auction data endpoint
    url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/auctions_query"

    all_records = []
    page = 1

    while True:
        params = {
            'page[number]': page,
            'page[size]': 10000,
            'sort': '-auction_date',
        }

        try:
            response = requests.get(url, params=params, timeout=60)
            if response.status_code != 200:
                logger.warning(f"Auctions HTTP {response.status_code}")
                # Try alternative endpoint
                url_alt = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
                response = requests.get(url_alt, params=params, timeout=60)
                if response.status_code != 200:
                    logger.error(f"Both auction endpoints failed. Skipping.")
                    break

            data = response.json()
            records = data.get('data', [])
            total = data.get('meta', {}).get('total-count', 0)

            all_records.extend(records)
            logger.info(f"  Page {page}: {len(all_records)}/{total} records")

            if len(all_records) >= total or not records:
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error: {e}")
            break

    if all_records:
        df = pd.DataFrame(all_records)
        output_path = raw_dir / "auction_results.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {output_path.name}: {len(df)} auctions")

        if 'auction_date' in df.columns:
            logger.info(f"  Date range: {df['auction_date'].min()} to {df['auction_date'].max()}")
    else:
        logger.warning("No auction data retrieved")

    logger.info(f"[L115] Done.")


if __name__ == "__main__":
    run()
