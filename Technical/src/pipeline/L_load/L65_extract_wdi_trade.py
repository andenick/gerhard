#!/usr/bin/env python3
"""
L65: Extract WDI Trade Detail
Trade composition, terms of trade, and trade openness from WDI.
Stage: L | ID: L65
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
    "id": "L65",
    "name": "Extract WDI Trade Detail",
    "stage": "L",
    "description": "Trade composition, terms of trade, and trade openness from WDI",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/processed/wdi_trade_detail.xlsx"}],
    "timeout": 180,
    "parallel_safe": True,
}

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
WDI_CSV = DATA_ROOT / "WorldBank" / "WDI_CSV" / "[2025.10.10] WDICSV.csv"

INDICATORS = {
    'TX.VAL.FOOD.ZS.UN': 'food_exports_pct',
    'TX.VAL.FUEL.ZS.UN': 'fuel_exports_pct',
    'TX.VAL.MANF.ZS.UN': 'manufactures_exports_pct',
    'TX.VAL.MMTL.ZS.UN': 'ores_metals_exports_pct',
    'TX.VAL.AGRI.ZS.UN': 'agri_raw_exports_pct',
    'TM.VAL.FOOD.ZS.UN': 'food_imports_pct',
    'TM.VAL.FUEL.ZS.UN': 'fuel_imports_pct',
    'TM.VAL.MANF.ZS.UN': 'manufactures_imports_pct',
    'TT.PRI.MRCH.XD.WD': 'terms_of_trade_index',
    'TX.QTY.MRCH.XD.WD': 'export_volume_index',
    'TM.QTY.MRCH.XD.WD': 'import_volume_index',
    'NE.TRD.GNFS.ZS': 'trade_pct_gdp',
    'NE.EXP.GNFS.ZS': 'exports_pct_gdp',
    'NE.IMP.GNFS.ZS': 'imports_pct_gdp',
    'NE.RSB.GNFS.ZS': 'external_balance_pct_gdp',
}

OUTPUT_FILENAME = 'wdi_trade_detail.xlsx'


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
