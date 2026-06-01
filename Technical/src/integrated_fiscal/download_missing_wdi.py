"""
Download missing WDI indicators needed by A09 and A10.
- GDP growth (annual %) — NY.GDP.MKTP.KD.ZG
- Central government debt (% GDP) — GC.DOD.TOTL.GD.ZS
- Inflation (CPI, annual %) — FP.CPI.TOTL.ZG
- GDP per capita (current US$) — NY.GDP.PCAP.CD

Uses World Bank API v2 (same approach as existing download scripts).
"""

import requests
import pandas as pd
import time
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

OUTPUT_DIR = raw_data_dir() / "worldbank" / "macro"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.worldbank.org/v2"

INDICATORS = {
    'gdp_growth': {
        'code': 'NY.GDP.MKTP.KD.ZG',
        'name': 'GDP growth (annual %)',
    },
    'central_gov_debt_gdp': {
        'code': 'GC.DOD.TOTL.GD.ZS',
        'name': 'Central government debt, total (% of GDP)',
        'alt_code': 'GC.XPN.TOTL.GD.ZS',  # fallback: expense (% GDP)
    },
    'inflation_cpi': {
        'code': 'FP.CPI.TOTL.ZG',
        'name': 'Inflation, consumer prices (annual %)',
    },
    'gdp_per_capita': {
        'code': 'NY.GDP.PCAP.CD',
        'name': 'GDP per capita (current US$)',
    },
}


def download_indicator(code: str, name: str) -> pd.DataFrame:
    """Download a single WDI indicator for all countries, all years."""
    all_data = []
    page = 1
    per_page = 1000
    total_pages = 1

    while page <= total_pages:
        url = f"{BASE_URL}/country/all/indicator/{code}"
        params = {
            'format': 'json',
            'per_page': per_page,
            'page': page,
            'date': '1960:2024',
        }

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"API error for {code} page {page}: {e}")
            break

        if not data or len(data) < 2:
            break

        meta = data[0]
        total_pages = meta.get('pages', 1)
        records = data[1]

        if not records:
            break

        for rec in records:
            if rec.get('value') is not None:
                all_data.append({
                    'country_name': rec['country']['value'],
                    'country_code': rec['countryiso3code'],
                    'year': int(rec['date']),
                    'value': float(rec['value']),
                })

        page += 1
        if page <= total_pages:
            time.sleep(0.1)

    df = pd.DataFrame(all_data)
    if not df.empty:
        logger.info(f"Downloaded {code} ({name}): {len(df):,} observations, "
                   f"{df['country_code'].nunique()} countries")
    else:
        logger.warning(f"No data returned for {code} ({name})")
    return df


def run():
    """Download all missing indicators."""
    logger.info("=" * 80)
    logger.info("DOWNLOADING MISSING WDI INDICATORS")
    logger.info("=" * 80)

    results = {}
    for key, info in INDICATORS.items():
        code = info['code']
        logger.info(f"Downloading: {info['name']} ({code})")
        df = download_indicator(code, info['name'])

        # Try alternate code if primary failed
        if df.empty and 'alt_code' in info:
            code = info['alt_code']
            logger.info(f"Trying alternate: {code}")
            df = download_indicator(code, info['name'])

        if not df.empty:
            # Save as CSV (consistent with other WB downloads)
            csv_path = OUTPUT_DIR / f"wb_{key}.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"Saved: {csv_path} ({len(df):,} rows)")
            results[key] = len(df)
        else:
            logger.warning(f"No data for {key}")

    # Also save combined panel
    all_dfs = []
    for key, info in INDICATORS.items():
        csv_path = OUTPUT_DIR / f"wb_{key}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df = df.rename(columns={'value': key})
            all_dfs.append(df[['country_code', 'year', key]])

    if all_dfs:
        combined = all_dfs[0]
        for df in all_dfs[1:]:
            combined = combined.merge(df, on=['country_code', 'year'], how='outer')
        combined = combined.sort_values(['country_code', 'year']).reset_index(drop=True)
        combined.to_csv(OUTPUT_DIR / "wb_macro_combined.csv", index=False)
        logger.info(f"Combined panel: {len(combined):,} rows, {combined['country_code'].nunique()} countries")

    # Write download log
    log = {
        'downloaded_at': pd.Timestamp.now().isoformat(),
        'indicators': {k: {'code': v['code'], 'rows': results.get(k, 0)} for k, v in INDICATORS.items()},
    }
    with open(OUTPUT_DIR / "download_log.json", 'w') as f:
        json.dump(log, f, indent=2)

    logger.info("DOWNLOAD COMPLETE")
    return results


if __name__ == "__main__":
    run()
