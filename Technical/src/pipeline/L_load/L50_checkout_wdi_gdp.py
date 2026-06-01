#!/usr/bin/env python3
"""
L50: Checkout WDI GDP
Extract GDP, population, trade from World Bank WDI data.
Stage: L | ID: L50
Project: Gerhard
"""
import os
import sys
import shutil
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import ensure_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "L50",
    "name": "Checkout WDI GDP",
    "stage": "L",
    "description": "Extract GDP, population, trade from World Bank WDI data",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Inputs/WDI/wdi_macro_panel.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}

# WDI source directory (set DATA_ROOT to your World Bank WDI bulk-CSV folder)
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
WDI_DIR = DATA_ROOT / "WorldBank" / "WDI_CSV"
WDI_CSV = WDI_DIR / "[2025.10.10] WDICSV.csv"
WDI_COUNTRY_CSV = WDI_DIR / "[2025.10.10] WDICountry.csv"

# Indicators to extract
INDICATORS = {
    'NY.GDP.MKTP.CD': 'gdp_current_usd',
    'NY.GDP.MKTP.KD': 'gdp_constant_2015_usd',
    'NY.GDP.PCAP.CD': 'gdp_per_capita_usd',
    'NY.GDP.PCAP.PP.CD': 'gdp_per_capita_ppp',
    'SP.POP.TOTL': 'population',
    'NE.TRD.GNFS.ZS': 'trade_pct_gdp',
    'SP.URB.TOTL.IN.ZS': 'urban_pct',
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    root = project_root()
    out_dir = ensure_dir(root / "Inputs" / "WDI")

    # --- Step 1: Read WDI CSV and extract indicators ---
    if not WDI_CSV.exists():
        logger.error(f"WDI CSV not found: {WDI_CSV}")
        return

    logger.info(f"Reading WDI CSV: {WDI_CSV}")
    logger.info(f"  File size: {WDI_CSV.stat().st_size / 1e6:.1f} MB")

    # Read the full CSV (wide format: Country Name, Country Code, Indicator Name, Indicator Code, 1960..2024)
    wdi = pd.read_csv(WDI_CSV, low_memory=False)
    logger.info(f"  Raw WDI: {len(wdi)} rows, {len(wdi.columns)} columns")

    # Filter to our indicators
    indicator_codes = list(INDICATORS.keys())
    wdi_filtered = wdi[wdi['Indicator Code'].isin(indicator_codes)].copy()
    logger.info(f"  Filtered to {len(wdi_filtered)} rows for {len(indicator_codes)} indicators")

    # --- Step 2: Melt year columns to long format ---
    year_cols = [c for c in wdi_filtered.columns if c.isdigit()]
    logger.info(f"  Year columns: {year_cols[0]}..{year_cols[-1]} ({len(year_cols)} years)")

    melted = wdi_filtered.melt(
        id_vars=['Country Name', 'Country Code', 'Indicator Code'],
        value_vars=year_cols,
        var_name='year',
        value_name='value',
    )
    melted['year'] = melted['year'].astype(int)
    melted = melted.dropna(subset=['value'])
    logger.info(f"  After melt + dropna: {len(melted)} observations")

    # --- Step 3: Pivot indicators to columns ---
    pivoted = melted.pivot_table(
        index=['Country Code', 'Country Name', 'year'],
        columns='Indicator Code',
        values='value',
    ).reset_index()

    pivoted.columns.name = None

    # Rename columns
    col_map = {
        'Country Code': 'country_code',
        'Country Name': 'country_name',
    }
    col_map.update(INDICATORS)
    pivoted = pivoted.rename(columns=col_map)

    pivoted = pivoted.sort_values(['country_code', 'year']).reset_index(drop=True)

    logger.info(f"  Pivoted panel: {len(pivoted)} rows, {pivoted['country_code'].nunique()} entities")
    logger.info(f"  Year range: {pivoted['year'].min()}-{pivoted['year'].max()}")
    logger.info(f"  Columns: {list(pivoted.columns)}")

    # Report coverage per indicator
    for code, col in INDICATORS.items():
        if col in pivoted.columns:
            n = pivoted[col].notna().sum()
            logger.info(f"    {col}: {n} observations")

    # --- Step 4: Save macro panel ---
    write_single_sheet_excel(pivoted, out_dir / "wdi_macro_panel.xlsx")
    logger.info(f"Saved wdi_macro_panel.xlsx: {len(pivoted)} rows")

    # --- Step 5: Copy country metadata ---
    if WDI_COUNTRY_CSV.exists():
        country_meta = pd.read_csv(WDI_COUNTRY_CSV)
        logger.info(f"  Country metadata: {len(country_meta)} entries")

        # Keep useful columns
        keep_cols = ['Country Code', 'Short Name', 'Region', 'Income Group']
        available = [c for c in keep_cols if c in country_meta.columns]
        country_slim = country_meta[available].copy()
        country_slim = country_slim.rename(columns={
            'Country Code': 'country_code',
            'Short Name': 'short_name',
            'Region': 'region',
            'Income Group': 'income_group',
        })

        # Drop rows with empty region (these are aggregates)
        country_slim = country_slim[country_slim['region'].notna() & (country_slim['region'] != '')]
        logger.info(f"  Real countries with region: {len(country_slim)}")

        write_single_sheet_excel(country_slim, out_dir / "wdi_country_metadata.xlsx")
        logger.info(f"Saved wdi_country_metadata.xlsx")

        # Also copy the raw file for reference
        dest = out_dir / "[2025.10.10] WDICountry.csv"
        if not dest.exists():
            shutil.copy2(WDI_COUNTRY_CSV, dest)
            logger.info(f"Copied WDICountry.csv to {dest}")
    else:
        logger.warning(f"Country metadata not found: {WDI_COUNTRY_CSV}")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
