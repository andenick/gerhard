"""Download OECD Revenue Statistics via SDMX REST API.
Tax structure data for 38+ countries, 1965-2024.

Uses the OECD SDMX JSON endpoint.
"""

import requests
import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

OUTPUT_DIR = raw_data_dir() / "oecd" / "revenue_stats"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OECD SDMX endpoints
OECD_SDMX_BASE = "https://stats.oecd.org/sdmx-json/data"
OECD_NEW_API = "https://sdmx.oecd.org/public/rest/data"

# Revenue Statistics dataset ID
REV_DATASET = "REV"

# Key OECD countries
OECD_COUNTRIES = "AUS+AUT+BEL+CAN+CHL+COL+CRI+CZE+DNK+EST+FIN+FRA+DEU+GRC+HUN+ISL+IRL+ISR+ITA+JPN+KOR+LVA+LTU+LUX+MEX+NLD+NZL+NOR+POL+PRT+SVK+SVN+ESP+SWE+CHE+TUR+GBR+USA"


def try_oecd_sdmx():
    """Try the classic OECD.Stat SDMX endpoint."""
    # Revenue Statistics: total tax revenue as % GDP for all countries
    # Format: dataset/filter/agency?startTime=1965&endTime=2024
    url = f"{OECD_SDMX_BASE}/{REV_DATASET}/{OECD_COUNTRIES}.TOTALTAX.TAXGDP/all"
    params = {'startTime': '1965', 'endTime': '2024'}

    logger.info(f"Trying OECD.Stat SDMX: {url}")
    try:
        resp = requests.get(url, params=params, timeout=60,
                          headers={'Accept': 'application/vnd.sdmx.data+json;version=1.0.0-wd'})
        logger.info(f"Response status: {resp.status_code}")
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"OECD SDMX returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"OECD SDMX failed: {e}")
    return None


def try_oecd_new_api():
    """Try the new OECD SDMX API (post-2024 migration)."""
    # New endpoint format
    url = f"{OECD_NEW_API}/OECD.SDD.TPS,DSD_REV@DF_REV,1.0/all"
    params = {'startPeriod': '1965', 'endPeriod': '2024', 'dimensionAtObservation': 'AllDimensions'}

    logger.info(f"Trying new OECD API: {url}")
    try:
        resp = requests.get(url, params=params, timeout=60)
        logger.info(f"Response status: {resp.status_code}")
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.info(f"New API response: {resp.text[:300]}")
    except Exception as e:
        logger.warning(f"New OECD API failed: {e}")
    return None


def try_oecd_csv_endpoint():
    """Try OECD CSV download (simpler format)."""
    # CSV endpoint for Revenue Statistics
    url = "https://stats.oecd.org/sdmx-json/data/REV/.TOTALTAX.TAXGDP/all"
    params = {'startTime': '1990', 'endTime': '2022', 'contentType': 'csv'}

    logger.info("Trying OECD CSV endpoint...")
    try:
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code == 200 and 'csv' in resp.headers.get('content-type', '').lower():
            return resp.text
        # Try alternate CSV format
        url2 = "https://stats.oecd.org/restsdmx/sdmx.ashx/GetData/REV/all/all?format=csv"
        resp2 = requests.get(url2, timeout=60)
        if resp2.status_code == 200:
            logger.info(f"Got response ({len(resp2.content)} bytes)")
            return resp2
    except Exception as e:
        logger.warning(f"CSV endpoint failed: {e}")
    return None


def parse_sdmx_json(data: dict) -> pd.DataFrame:
    """Parse OECD SDMX-JSON response into DataFrame."""
    if not data:
        return pd.DataFrame()

    try:
        # SDMX-JSON 1.0 structure
        datasets = data.get('dataSets', [])
        structure = data.get('structure', {})

        if not datasets:
            logger.warning("No datasets in SDMX response")
            return pd.DataFrame()

        # Get dimension values
        dimensions = structure.get('dimensions', {}).get('observation', [])
        dim_values = {}
        for dim in dimensions:
            dim_id = dim.get('id', '')
            values = dim.get('values', [])
            dim_values[dim_id] = [v.get('id', v.get('name', '')) for v in values]

        # Parse observations
        observations = datasets[0].get('observations', {})
        rows = []
        for key, obs in observations.items():
            indices = key.split(':')
            row = {}
            for i, dim in enumerate(dimensions):
                if i < len(indices):
                    dim_id = dim.get('id', f'dim{i}')
                    idx = int(indices[i])
                    values = dim.get('values', [])
                    if idx < len(values):
                        row[dim_id] = values[idx].get('id', values[idx].get('name', ''))
            if obs:
                row['value'] = obs[0] if isinstance(obs, list) else obs
            rows.append(row)

        df = pd.DataFrame(rows)
        logger.info(f"Parsed {len(df)} observations from SDMX-JSON")
        return df

    except Exception as e:
        logger.error(f"Error parsing SDMX-JSON: {e}")
        return pd.DataFrame()


def run():
    logger.info("=" * 80)
    logger.info("DOWNLOADING OECD REVENUE STATISTICS")
    logger.info("=" * 80)

    # Try multiple endpoints
    data = None

    # Method 1: Classic OECD.Stat SDMX
    data = try_oecd_sdmx()
    if data:
        df = parse_sdmx_json(data)
        if not df.empty:
            df.to_parquet(OUTPUT_DIR / "oecd_revenue_sdmx.parquet", index=False)
            logger.info(f"Saved OECD Revenue: {len(df)} rows")

            log = {
                'downloaded_at': pd.Timestamp.now().isoformat(),
                'source': 'OECD.Stat SDMX',
                'rows': len(df),
                'columns': df.columns.tolist(),
            }
            with open(OUTPUT_DIR / "download_log.json", 'w') as f:
                json.dump(log, f, indent=2)
            logger.info("OECD REVENUE DOWNLOAD COMPLETE")
            return

    # Method 2: New OECD API
    data = try_oecd_new_api()
    if data:
        df = parse_sdmx_json(data)
        if not df.empty:
            df.to_parquet(OUTPUT_DIR / "oecd_revenue_new_api.parquet", index=False)
            logger.info(f"Saved OECD Revenue (new API): {len(df)} rows")
            return

    # Method 3: CSV
    csv_data = try_oecd_csv_endpoint()
    if csv_data:
        logger.info("Got CSV response — saving raw")
        if isinstance(csv_data, str):
            (OUTPUT_DIR / "oecd_revenue_raw.csv").write_text(csv_data)
        elif hasattr(csv_data, 'content'):
            (OUTPUT_DIR / "oecd_revenue_raw.bin").write_bytes(csv_data.content)

    # If all fail, log what we know
    logger.warning("All OECD endpoints attempted. Status:")
    logger.warning("  - OECD.Stat SDMX: may require specific dataset format")
    logger.warning("  - New OECD API: may have different dataset naming")
    logger.warning("  - Manual: https://stats.oecd.org/Index.aspx?DataSetCode=REV")

    log = {
        'status': 'PARTIAL_OR_FAILED',
        'attempted_at': pd.Timestamp.now().isoformat(),
        'note': 'OECD Revenue Stats requires specific SDMX query format',
        'manual_url': 'https://stats.oecd.org/Index.aspx?DataSetCode=REV',
        'source': 'OECD Revenue Statistics (SDMX)',
    }
    with open(OUTPUT_DIR / "download_log.json", 'w') as f:
        json.dump(log, f, indent=2)


if __name__ == "__main__":
    run()
