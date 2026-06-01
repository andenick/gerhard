#!/usr/bin/env python3
"""
L77: Extract WDI Expenditure Functions
Military, education, health, R&D expenditure and fiscal balance from WDI.
Stage: L | ID: L77
Project: Gerhard
"""
import os
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import ensure_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "L77",
    "name": "Extract WDI Expenditure Functions",
    "stage": "L",
    "description": "Military, education, health, R&D expenditure and fiscal balance from WDI",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/processed/wdi_expenditure_functions.xlsx"}],
    "timeout": 180,
    "parallel_safe": True,
}

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
WDI_CSV = DATA_ROOT / "WorldBank" / "WDI_CSV" / "[2025.10.10] WDICSV.csv"

INDICATORS = {
    'MS.MIL.XPND.GD.ZS': 'military_pct_gdp',
    'MS.MIL.XPND.ZS': 'military_pct_govt_expenditure',
    'SE.XPD.TOTL.GD.ZS': 'education_pct_gdp',
    'SE.XPD.TOTL.GB.ZS': 'education_pct_govt_expenditure',
    'SH.XPD.GHED.GD.ZS': 'health_govt_pct_gdp',
    'SH.XPD.GHED.GE.ZS': 'health_pct_govt_expenditure',
    'SH.XPD.CHEX.GD.ZS': 'health_total_pct_gdp',
    'GB.XPD.RSDV.GD.ZS': 'rnd_pct_gdp',
    'GC.DOD.TOTL.GD.ZS': 'central_govt_debt_pct_gdp',
    'GC.BAL.CASH.GD.ZS': 'cash_surplus_deficit_pct_gdp',
}

OUTPUT_FILENAME = 'wdi_expenditure_functions.xlsx'


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    if not WDI_CSV.exists():
        logger.error(f"WDI CSV not found at {WDI_CSV}")
        return

    logger.info(f"Reading WDI CSV ({WDI_CSV.stat().st_size / 1e6:.0f} MB)...")
    wdi = pd.read_csv(WDI_CSV, low_memory=False)
    filtered = wdi[wdi['Indicator Code'].isin(INDICATORS.keys())]
    logger.info(f"Filtered to {len(filtered)} rows ({filtered['Indicator Code'].nunique()} indicators)")

    year_cols = [c for c in filtered.columns if c.isdigit()]
    melted = filtered.melt(
        id_vars=['Country Name', 'Country Code', 'Indicator Code'],
        value_vars=year_cols,
        var_name='year', value_name='value'
    )
    melted['year'] = melted['year'].astype(int)
    melted = melted.dropna(subset=['value'])

    pivoted = melted.pivot_table(
        index=['Country Code', 'Country Name', 'year'],
        columns='Indicator Code',
        values='value'
    ).reset_index()
    pivoted.columns.name = None

    rename_map = {'Country Code': 'country_code', 'Country Name': 'country_name'}
    rename_map.update(INDICATORS)
    pivoted = pivoted.rename(columns=rename_map)

    pivoted = pivoted[pivoted['country_code'].str.len() == 3]
    pivoted = pivoted.sort_values(['country_code', 'year']).reset_index(drop=True)

    output_dir = ensure_dir(project_root() / "Technical" / "data" / "processed")
    output_path = output_dir / OUTPUT_FILENAME
    write_single_sheet_excel(pivoted, output_path)
    logger.info(f"Saved {output_path.name}: {len(pivoted)} rows, {pivoted['country_code'].nunique()} countries")

    for code, col in INDICATORS.items():
        if col in pivoted.columns:
            n = pivoted[col].notna().sum()
            logger.info(f"  {col}: {n} observations")


if __name__ == "__main__":
    run()
