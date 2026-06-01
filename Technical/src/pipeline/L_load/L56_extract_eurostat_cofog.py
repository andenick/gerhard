#!/usr/bin/env python3
"""
L56: Extract Eurostat COFOG
Parse Eurostat government expenditure by function (COFOG) for EU countries.
Stage: L | ID: L56
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import ensure_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "L56",
    "name": "Extract Eurostat COFOG",
    "stage": "L",
    "description": "Parse Eurostat COFOG expenditure by function for EU-27",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/processed/eurostat_cofog_panel.xlsx"}],
    "timeout": 180,
    "parallel_safe": True,
}

EUROSTAT_TSV = project_root() / "Technical" / "data" / "raw" / "eurostat" / "gfs" / "eurostat_gov_10a_exp.tsv"

# Map COFOG codes to readable names
COFOG_MAP = {
    'GF01': 'general_public_services',
    'GF02': 'defense',
    'GF03': 'public_order_safety',
    'GF04': 'economic_affairs',
    'GF05': 'environment_protection',
    'GF06': 'housing_community',
    'GF07': 'health',
    'GF08': 'recreation_culture',
    'GF09': 'education',
    'GF10': 'social_protection',
    'TOTAL': 'total_expenditure',
}

# ISO2 to ISO3 mapping for EU countries
EU_ISO2_TO_ISO3 = {
    'AT': 'AUT', 'BE': 'BEL', 'BG': 'BGR', 'CY': 'CYP', 'CZ': 'CZE',
    'DE': 'DEU', 'DK': 'DNK', 'EE': 'EST', 'EL': 'GRC', 'ES': 'ESP',
    'FI': 'FIN', 'FR': 'FRA', 'HR': 'HRV', 'HU': 'HUN', 'IE': 'IRL',
    'IT': 'ITA', 'LT': 'LTU', 'LU': 'LUX', 'LV': 'LVA', 'MT': 'MLT',
    'NL': 'NLD', 'PL': 'POL', 'PT': 'PRT', 'RO': 'ROU', 'SE': 'SWE',
    'SI': 'SVN', 'SK': 'SVK', 'NO': 'NOR', 'IS': 'ISL', 'CH': 'CHE',
    'UK': 'GBR', 'ME': 'MNE', 'MK': 'MKD', 'RS': 'SRB', 'TR': 'TUR',
    'BA': 'BIH', 'AL': 'ALB', 'XK': 'XKX',
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    if not EUROSTAT_TSV.exists():
        logger.error(f"Eurostat TSV not found at {EUROSTAT_TSV}")
        return

    logger.info(f"Reading Eurostat TSV ({EUROSTAT_TSV.stat().st_size / 1e6:.0f} MB)...")

    # Read TSV — first column is composite key
    df = pd.read_csv(EUROSTAT_TSV, sep='\t', low_memory=False)
    logger.info(f"Raw shape: {df.shape}")

    # First column contains: freq,unit,sector,cofog99,na_item,geo\TIME_PERIOD
    first_col = df.columns[0]

    # Split the composite key
    key_parts = df[first_col].str.split(',', expand=True)
    if key_parts.shape[1] >= 6:
        df['freq'] = key_parts[0]
        df['unit'] = key_parts[1]
        df['sector'] = key_parts[2]
        df['cofog99'] = key_parts[3]
        df['na_item'] = key_parts[4]
        df['geo'] = key_parts[5]
    else:
        logger.error(f"Unexpected key format. First column has {key_parts.shape[1]} parts")
        logger.info(f"Sample: {df[first_col].head(3).tolist()}")
        return

    # Filter: unit=PC_GDP (percent of GDP), sector=S13 (general government)
    filtered = df[(df['unit'] == 'PC_GDP') & (df['sector'] == 'S13')]
    logger.info(f"Filtered to PC_GDP + S13: {len(filtered)} rows")

    # Filter to COFOG codes we want
    cofog_codes = list(COFOG_MAP.keys())
    filtered = filtered[filtered['cofog99'].isin(cofog_codes)]
    logger.info(f"Filtered to {len(cofog_codes)} COFOG codes: {len(filtered)} rows")

    # Get year columns (everything after the composite key)
    year_cols = [c for c in df.columns if c != first_col and c not in ['freq', 'unit', 'sector', 'cofog99', 'na_item', 'geo']]

    # Melt to long format
    melted = filtered.melt(
        id_vars=['geo', 'cofog99'],
        value_vars=year_cols,
        var_name='year_raw',
        value_name='value'
    )

    # Clean year (may have trailing spaces or flags like 'p', 'e', 'b')
    melted['year'] = melted['year_raw'].str.strip().str.extract(r'(\d{4})')[0]
    melted = melted.dropna(subset=['year'])
    melted['year'] = melted['year'].astype(int)

    # Clean value (may have flags like ': ' for missing, 'p' for provisional)
    melted['value'] = pd.to_numeric(
        melted['value'].astype(str).str.strip().str.replace(r'[^0-9.\-]', '', regex=True),
        errors='coerce'
    )
    melted = melted.dropna(subset=['value'])

    # Map COFOG codes to column names
    melted['cofog_name'] = melted['cofog99'].map(COFOG_MAP)

    # Map geo codes to ISO3
    melted['country_code'] = melted['geo'].str.strip().map(EU_ISO2_TO_ISO3)
    melted = melted.dropna(subset=['country_code'])

    # Pivot COFOG functions to columns
    pivoted = melted.pivot_table(
        index=['country_code', 'year'],
        columns='cofog_name',
        values='value'
    ).reset_index()
    pivoted.columns.name = None

    pivoted = pivoted.sort_values(['country_code', 'year']).reset_index(drop=True)

    # Save
    output_dir = ensure_dir(project_root() / "Technical" / "data" / "processed")
    output_path = output_dir / "eurostat_cofog_panel.xlsx"
    write_single_sheet_excel(pivoted, output_path)

    logger.info(f"Saved {output_path.name}: {len(pivoted)} rows, {pivoted['country_code'].nunique()} countries")
    for col in sorted(pivoted.columns):
        if col not in ['country_code', 'year']:
            n = pivoted[col].notna().sum()
            logger.info(f"  {col}: {n} observations")


if __name__ == "__main__":
    run()
