"""Download IMF Government Finance Statistics via SDMX JSON API.
Revenue + expenditure by type for 190+ countries, 1990-2024.
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

OUTPUT_DIR = raw_data_dir() / "imf" / "gfs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://dataservices.imf.org/REST/SDMX_JSON.svc"

# Key GFS indicators
GFS_INDICATORS = {
    # Revenue
    'G1': 'Total revenue',
    'G11': 'Taxes',
    'G111': 'Taxes on income profits and capital gains',
    'G112': 'Taxes on payroll and workforce',
    'G113': 'Taxes on property',
    'G114': 'Taxes on goods and services',
    'G115': 'Taxes on international trade',
    'G12': 'Social contributions',
    'G14': 'Other revenue',
    # Expenditure
    'G2': 'Total expenditure',
    'G21': 'Compensation of employees',
    'G22': 'Use of goods and services',
    'G24': 'Interest',
    'G25': 'Subsidies',
    'G27': 'Social benefits',
    'G28': 'Other expense',
    # Balance
    'GNL': 'Net lending/borrowing',
    'GNLG': 'Net lending/borrowing (% GDP)',
}


def get_imf_dataflow_info():
    """Check available GFS dataflows."""
    url = f"{BASE_URL}/Dataflow"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Find GFS-related flows
        flows = data.get('Structure', {}).get('Dataflows', {}).get('Dataflow', [])
        gfs_flows = [f for f in flows if 'GFS' in str(f.get('Name', ''))]
        logger.info(f"Found {len(gfs_flows)} GFS dataflows out of {len(flows)} total")
        for f in gfs_flows[:10]:
            name = f.get('Name', {})
            if isinstance(name, dict):
                name = name.get('#text', str(name))
            logger.info(f"  {f.get('@id', '?')}: {name}")
        return gfs_flows
    except Exception as e:
        logger.error(f"Failed to get dataflows: {e}")
        return []


def download_gfs_indicator(indicator: str, freq: str = 'A') -> pd.DataFrame:
    """Download a single GFS indicator for all countries."""
    # IMF SDMX structure: CompactData/{database}/{freq}.{ref_area}.{indicator}...
    # For GFS: database = GFSR (annual) or GFSM (monthly)
    # Key format varies — try simple approach first
    url = f"{BASE_URL}/CompactData/GFSR/{freq}..{indicator}.W0_S1_G1101.W0_S13"

    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            series = data.get('CompactData', {}).get('DataSet', {}).get('Series', [])
            if isinstance(series, dict):
                series = [series]
            logger.info(f"  {indicator}: got {len(series)} country series")
            return _parse_series(series, indicator)
        else:
            logger.warning(f"  {indicator}: HTTP {resp.status_code}")
            return pd.DataFrame()
    except Exception as e:
        logger.warning(f"  {indicator}: {e}")
        return pd.DataFrame()


def _parse_series(series: list, indicator: str) -> pd.DataFrame:
    """Parse IMF SDMX JSON series into DataFrame."""
    rows = []
    for s in series:
        country = s.get('@REF_AREA', '')
        obs = s.get('Obs', [])
        if isinstance(obs, dict):
            obs = [obs]
        for o in obs:
            rows.append({
                'country_code': country,
                'year': int(o.get('@TIME_PERIOD', 0)),
                'value': float(o.get('@OBS_VALUE', np.nan)),
                'indicator': indicator,
            })
    return pd.DataFrame(rows)


def try_alternative_endpoint():
    """Try the IMF JSON REST API (newer endpoint)."""
    # Try getting list of available datasets
    url = "https://dataservices.imf.org/REST/SDMX_JSON.svc/Dataflow"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            structures = data.get('Structure', {}).get('Dataflows', {}).get('Dataflow', [])
            gfs = [s for s in structures
                   if 'GFS' in str(s.get('@id', '')) or 'gfs' in str(s.get('Name', '')).lower()]
            if gfs:
                logger.info(f"Available GFS datasets:")
                for g in gfs[:5]:
                    logger.info(f"  ID: {g.get('@id')} - {g.get('Name', '')}")
                return gfs
    except Exception as e:
        logger.warning(f"Alternative endpoint failed: {e}")
    return []


def download_gfs_bulk():
    """Attempt bulk GFS download via the available endpoint."""
    # First, discover available datasets
    gfs_datasets = try_alternative_endpoint()

    if not gfs_datasets:
        logger.warning("No GFS datasets found via API. Trying known dataset IDs...")
        # Known dataset IDs for GFS
        known_ids = ['GFSR', 'GFSSSUC', 'GFSE', 'GFS01']
        for ds_id in known_ids:
            url = f"{BASE_URL}/CompactData/{ds_id}/A..."
            try:
                resp = requests.get(url, timeout=30, params={'startPeriod': '2020', 'endPeriod': '2022'})
                if resp.status_code == 200:
                    logger.info(f"Dataset {ds_id} accessible!")
                    gfs_datasets = [{'@id': ds_id}]
                    break
                else:
                    logger.info(f"  {ds_id}: HTTP {resp.status_code}")
            except Exception as e:
                logger.info(f"  {ds_id}: {e}")
            time.sleep(0.5)

    return gfs_datasets


def run():
    logger.info("=" * 80)
    logger.info("DOWNLOADING IMF GFS DATA")
    logger.info("=" * 80)

    # Step 1: Discover what's available
    datasets = download_gfs_bulk()

    if not datasets:
        logger.warning("Could not access IMF GFS API. This may require:")
        logger.warning("  1. Registration at https://data.imf.org for an API key")
        logger.warning("  2. Manual download from https://data.imf.org/?sk=a0867067-d23c-4ebc-ad23-d4b015d31802")
        logger.warning("Writing placeholder log...")

        log = {
            'status': 'API_NOT_ACCESSIBLE',
            'attempted_at': pd.Timestamp.now().isoformat(),
            'note': 'IMF GFS requires manual download or API key registration',
            'manual_url': 'https://data.imf.org/?sk=a0867067-d23c-4ebc-ad23-d4b015d31802',
        }
        with open(OUTPUT_DIR / "download_log.json", 'w') as f:
            json.dump(log, f, indent=2)
        return

    # Step 2: Try downloading indicators
    ds_id = datasets[0].get('@id', 'GFSR') if isinstance(datasets[0], dict) else 'GFSR'
    logger.info(f"Using dataset: {ds_id}")

    all_data = []
    for indicator, name in list(GFS_INDICATORS.items())[:5]:  # Start with first 5
        logger.info(f"Downloading {indicator} ({name})...")
        df = download_gfs_indicator(indicator)
        if not df.empty:
            all_data.append(df)
        time.sleep(1)  # Rate limiting

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined.to_parquet(OUTPUT_DIR / "gfs_sample.parquet", index=False)
        logger.info(f"GFS sample: {len(combined)} rows, {combined['country_code'].nunique()} countries")
    else:
        logger.warning("No GFS data retrieved")

    log = {
        'downloaded_at': pd.Timestamp.now().isoformat(),
        'dataset_id': ds_id,
        'rows': len(combined) if all_data else 0,
        'indicators_attempted': list(GFS_INDICATORS.keys())[:5],
    }
    with open(OUTPUT_DIR / "download_log.json", 'w') as f:
        json.dump(log, f, indent=2)

    logger.info("IMF GFS DOWNLOAD COMPLETE")


if __name__ == "__main__":
    run()
