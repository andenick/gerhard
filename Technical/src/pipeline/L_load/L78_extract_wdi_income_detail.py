#!/usr/bin/env python3
"""
L78: Extract WDI Income Detail
GNI, adjusted net national income, savings, and consumption from WDI.
Stage: L | ID: L78
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
    "id": "L78",
    "name": "Extract WDI Income Detail",
    "stage": "L",
    "description": "GNI, adjusted net national income, savings, and consumption from WDI",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/processed/wdi_income_detail.xlsx"}],
    "timeout": 180,
    "parallel_safe": True,
}

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
WDI_CSV = DATA_ROOT / "WorldBank" / "WDI_CSV" / "[2025.10.10] WDICSV.csv"

INDICATORS = {
    'NY.GNP.MKTP.CD': 'gni_current_usd',
    'NY.GNP.MKTP.KD': 'gni_constant_2015_usd',
    'NY.GNP.PCAP.CD': 'gni_per_capita_usd',
    'NY.GNP.PCAP.PP.CD': 'gni_per_capita_ppp',
    'NY.ADJ.NNTY.PC.CD': 'adj_net_national_income_pc',
    'NY.ADJ.SVNG.GN.ZS': 'adj_net_savings_pct_gni',
    'NY.GSR.NFCY.CD': 'net_income_from_abroad_usd',
    'NE.CON.TOTL.ZS': 'final_consumption_pct_gdp',
    'NY.GNS.ICTR.ZS': 'gross_savings_pct_gdp',
}

OUTPUT_FILENAME = 'wdi_income_detail.xlsx'


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
