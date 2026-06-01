#!/usr/bin/env python3
"""
P50: Disaggregate Debt Data
Create country-year debt panel from World Bank data.
Stage: P | ID: P50
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
    "id": "P50",
    "name": "Disaggregate Debt",
    "stage": "P",
    "description": "Create country-year debt panel from World Bank data",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Output/Data/debt_panel.xlsx"}],
    "timeout": 300,
    "parallel_safe": True,
}

# World Bank debt indicators
WB_DEBT_INDICATORS = {
    'GC.DOD.TOTL.GD.ZS': 'central_govt_debt_pct_gdp',
    'DT.DOD.DECT.GN.ZS': 'external_debt_pct_gni',
}


def fetch_wb_indicator(indicator_code: str, per_page: int = 10000) -> pd.DataFrame:
    """Fetch a World Bank indicator for all countries."""
    import requests

    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator_code}"
    params = {'format': 'json', 'per_page': per_page, 'date': '1990:2024'}

    try:
        response = requests.get(url, params=params, timeout=45)
        if response.status_code != 200:
            return pd.DataFrame()

        data = response.json()
        if len(data) < 2 or not data[1]:
            return pd.DataFrame()

        records = []
        for entry in data[1]:
            if entry.get('value') is not None:
                iso3 = entry.get('countryiso3code', '') or entry['country']['id']
                records.append({
                    'country_code': iso3,
                    'country_name': entry['country']['value'],
                    'year': int(entry['date']),
                    'value': float(entry['value']),
                })
        return pd.DataFrame(records)
    except Exception as e:
        logger.error(f"Error: {e}")
        return pd.DataFrame()


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    logger.info("Fetching debt data from World Bank API...")

    panels = {}
    for indicator, col_name in WB_DEBT_INDICATORS.items():
        logger.info(f"  Fetching {indicator} ({col_name})...")
        df = fetch_wb_indicator(indicator)
        if len(df) > 0:
            df = df.rename(columns={'value': col_name})
            panels[col_name] = df[['country_code', 'country_name', 'year', col_name]]
            logger.info(f"    Got {len(df)} observations, {df['country_code'].nunique()} countries")

    if not panels:
        logger.error("No debt data retrieved.")
        return

    # Merge indicators
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

    # Create consolidated debt column (prefer central govt debt, fallback to external)
    result['debt_pct_gdp'] = np.nan
    result['debt_source'] = None

    if 'central_govt_debt_pct_gdp' in result.columns:
        mask_cg = result['central_govt_debt_pct_gdp'].notna()
        result.loc[mask_cg, 'debt_pct_gdp'] = result.loc[mask_cg, 'central_govt_debt_pct_gdp']
        result.loc[mask_cg, 'debt_source'] = 'central_govt'

    if 'external_debt_pct_gni' in result.columns:
        # Fill gaps with external debt where central govt is missing
        mask = result['debt_pct_gdp'].isna() & result['external_debt_pct_gni'].notna()
        result.loc[mask, 'debt_pct_gdp'] = result.loc[mask, 'external_debt_pct_gni']
        result.loc[mask, 'debt_source'] = 'external_debt'

    # Filter to real countries (exclude aggregates)
    import requests as _requests
    try:
        resp = _requests.get('https://api.worldbank.org/v2/country',
                            params={'format': 'json', 'per_page': 500}, timeout=30)
        wb_countries = {e['id'] for e in resp.json()[1] if e.get('region', {}).get('id') != 'NA'}
        result = result[result['country_code'].isin(wb_countries)].copy()
        logger.info(f"Filtered to {result['country_code'].nunique()} real countries")
    except Exception as e:
        logger.warning(f"Could not fetch country list: {e}")
        result = result.copy()
    result = result.sort_values(['country_code', 'year']).reset_index(drop=True)

    # Fill country names
    name_map = result.dropna(subset=['country_name']).drop_duplicates('country_code').set_index('country_code')['country_name']
    result['country_name'] = result['country_code'].map(name_map)

    # Keep key columns
    keep_cols = ['country_code', 'country_name', 'year', 'debt_pct_gdp', 'debt_source']
    extra_cols = [c for c in result.columns if c not in keep_cols and c.endswith('_gdp') or c.endswith('_gni')]

    write_single_sheet_excel(result[keep_cols + extra_cols], out / "debt_panel.xlsx")
    logger.info(f"Saved debt_panel.xlsx: {len(result)} rows, {result['country_code'].nunique()} countries")


if __name__ == "__main__":
    run()
