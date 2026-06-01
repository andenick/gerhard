#!/usr/bin/env python3
"""
P45: Disaggregate Expenditure Data
Create country-year expenditure panel from raw World Bank data.
Stage: P | ID: P45
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, raw_data_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "P45",
    "name": "Disaggregate Expenditure",
    "stage": "P",
    "description": "Create country-year expenditure panel from World Bank data",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Output/Data/expenditure_panel.xlsx"}],
    "timeout": 300,
    "parallel_safe": True,
}

# World Bank indicators for expenditure
WB_INDICATORS = {
    'GC.XPN.TOTL.GD.ZS': 'expenditure_pct_gdp',
    'SE.XPD.TOTL.GD.ZS': 'education_pct_gdp',
    'SH.XPD.GHED.GD.ZS': 'health_pct_gdp',
    'MS.MIL.XPND.GD.ZS': 'military_pct_gdp',
}


def fetch_wb_indicator(indicator_code: str, per_page: int = 10000) -> pd.DataFrame:
    """Fetch a World Bank indicator for all countries."""
    import requests

    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator_code}"
    params = {
        'format': 'json',
        'per_page': per_page,
        'date': '1990:2024',
    }

    try:
        response = requests.get(url, params=params, timeout=45)
        if response.status_code != 200:
            logger.warning(f"WB API returned {response.status_code} for {indicator_code}")
            return pd.DataFrame()

        data = response.json()
        if len(data) < 2 or not data[1]:
            logger.warning(f"No data returned for {indicator_code}")
            return pd.DataFrame()

        records = []
        for entry in data[1]:
            if entry.get('value') is not None:
                # Use countryiso3code for consistent 3-char ISO codes
                iso3 = entry.get('countryiso3code', '') or entry['country']['id']
                records.append({
                    'country_code': iso3,
                    'country_name': entry['country']['value'],
                    'year': int(entry['date']),
                    'value': float(entry['value']),
                })

        return pd.DataFrame(records)

    except Exception as e:
        logger.error(f"Error fetching {indicator_code}: {e}")
        return pd.DataFrame()


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    # Try to load from existing raw data first
    raw_exp = raw_data_dir() / "worldbank" / "expenditure"

    # Check if we already have a wide-format expenditure file
    existing_files = list(raw_exp.glob("*.csv")) if raw_exp.exists() else []

    if existing_files:
        logger.info(f"Found {len(existing_files)} existing expenditure files in raw/")
        # Try to parse existing data
        all_dfs = []
        for f in existing_files:
            try:
                df = pd.read_csv(f)
                if 'country' in str(df.columns).lower() and len(df) > 10:
                    all_dfs.append(df)
                    logger.info(f"  Loaded {f.name}: {len(df)} rows")
            except Exception as e:
                logger.warning(f"  Could not read {f.name}: {e}")

        if all_dfs:
            # Check if any have country-year structure
            for adf in all_dfs:
                cols_lower = [c.lower() for c in adf.columns]
                if any('country' in c for c in cols_lower) and len(adf) > 100:
                    logger.info(f"Using existing data with {len(adf)} rows")

    # Fetch fresh data from World Bank API
    logger.info("Fetching expenditure data from World Bank API...")

    panels = {}
    for indicator, col_name in WB_INDICATORS.items():
        logger.info(f"  Fetching {indicator} ({col_name})...")
        df = fetch_wb_indicator(indicator)
        if len(df) > 0:
            df = df.rename(columns={'value': col_name})
            panels[col_name] = df[['country_code', 'country_name', 'year', col_name]]
            logger.info(f"    Got {len(df)} observations, {df['country_code'].nunique()} countries")
        else:
            logger.warning(f"    No data for {indicator}")

    if not panels:
        logger.error("No expenditure data retrieved. Cannot create panel.")
        return

    # Merge all indicators into one panel
    base_col = list(panels.keys())[0]
    result = panels[base_col]

    for col_name, df in panels.items():
        if col_name == base_col:
            continue
        result = result.merge(
            df[['country_code', 'year', col_name]],
            on=['country_code', 'year'],
            how='outer'
        )

    # Filter to real countries (exclude aggregates like "World", "High income", etc.)
    # Use World Bank country API: real countries have region != 'NA'
    import requests
    try:
        resp = requests.get('https://api.worldbank.org/v2/country',
                           params={'format': 'json', 'per_page': 500}, timeout=30)
        wb_countries = {e['id'] for e in resp.json()[1] if e.get('region', {}).get('id') != 'NA'}
        result = result[result['country_code'].isin(wb_countries)].copy()
        logger.info(f"Filtered to {result['country_code'].nunique()} real countries (excluded aggregates)")
    except Exception as e:
        logger.warning(f"Could not fetch country list, keeping all: {e}")
        result = result.copy()
    result = result.sort_values(['country_code', 'year']).reset_index(drop=True)

    # Fill country names for rows that came from outer join
    name_map = result.dropna(subset=['country_name']).drop_duplicates('country_code').set_index('country_code')['country_name']
    result['country_name'] = result['country_code'].map(name_map)

    write_single_sheet_excel(result, out / "expenditure_panel.xlsx")
    logger.info(f"Saved expenditure_panel.xlsx: {len(result)} rows, {result['country_code'].nunique()} countries")

    # Report coverage
    for col in WB_INDICATORS.values():
        if col in result.columns:
            non_null = result[col].notna().sum()
            logger.info(f"  {col}: {non_null} observations")


if __name__ == "__main__":
    run()
