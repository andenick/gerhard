#!/usr/bin/env python3
"""
L55: Extract WDI Fiscal Detail
Tax revenue, expenditure, and fiscal balance indicators from WDI.
Stage: L | ID: L55
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
    "id": "L55",
    "name": "Extract WDI Fiscal Detail",
    "stage": "L",
    "description": "Tax revenue, expenditure, and fiscal balance from WDI",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/processed/wdi_fiscal_detail.xlsx"}],
    "timeout": 180,
    "parallel_safe": True,
}

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
WDI_CSV = DATA_ROOT / "WorldBank" / "WDI_CSV" / "[2025.10.10] WDICSV.csv"

INDICATORS = {
    'GC.TAX.TOTL.GD.ZS': 'tax_revenue_pct_gdp',
    'GC.TAX.YPKG.ZS': 'income_tax_pct_gdp',
    'GC.TAX.YPKG.RV.ZS': 'income_tax_pct_revenue',
    'GC.TAX.GSRV.VA.ZS': 'goods_services_tax_pct_va',
    'GC.TAX.GSRV.RV.ZS': 'goods_services_tax_pct_revenue',
    'GC.TAX.INTT.RV.ZS': 'trade_tax_pct_revenue',
    'GC.TAX.EXPT.ZS': 'export_tax_pct_tax_revenue',
    'GC.TAX.OTHR.RV.ZS': 'other_tax_pct_revenue',
    'GC.REV.XGRT.GD.ZS': 'revenue_excl_grants_pct_gdp',
    'GC.REV.SOCL.ZS': 'social_contributions_pct_revenue',
    'GC.REV.GOTR.ZS': 'grants_other_pct_revenue',
    'GC.XPN.TOTL.GD.ZS': 'total_expense_pct_gdp',
    'GC.XPN.COMP.ZS': 'compensation_pct_expense',
    'GC.XPN.GSRV.ZS': 'goods_services_pct_expense',
    'GC.XPN.INTP.ZS': 'interest_pct_expense',
    'GC.XPN.INTP.RV.ZS': 'interest_pct_revenue',
    'GC.XPN.TRFT.ZS': 'transfers_pct_expense',
    'GC.XPN.OTHR.ZS': 'other_expense_pct_expense',
    'GC.NLD.TOTL.GD.ZS': 'net_lending_borrowing_pct_gdp',
}

OUTPUT_FILENAME = 'wdi_fiscal_detail.xlsx'


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    if not WDI_CSV.exists():
        logger.error(f"WDI CSV not found at {WDI_CSV}")
        return

    logger.info(f"Reading WDI CSV ({WDI_CSV.stat().st_size / 1e6:.0f} MB)...")
    wdi = pd.read_csv(WDI_CSV, low_memory=False)
    filtered = wdi[wdi['Indicator Code'].isin(INDICATORS.keys())]
    logger.info(f"Filtered to {len(filtered)} rows ({filtered['Indicator Code'].nunique()} indicators)")

    # Melt year columns
    year_cols = [c for c in filtered.columns if c.isdigit()]
    melted = filtered.melt(
        id_vars=['Country Name', 'Country Code', 'Indicator Code'],
        value_vars=year_cols,
        var_name='year', value_name='value'
    )
    melted['year'] = melted['year'].astype(int)
    melted = melted.dropna(subset=['value'])

    # Pivot indicators to columns
    pivoted = melted.pivot_table(
        index=['Country Code', 'Country Name', 'year'],
        columns='Indicator Code',
        values='value'
    ).reset_index()
    pivoted.columns.name = None

    # Rename
    rename_map = {'Country Code': 'country_code', 'Country Name': 'country_name'}
    rename_map.update(INDICATORS)
    pivoted = pivoted.rename(columns=rename_map)

    # Filter to real countries (3-char codes, exclude aggregates)
    pivoted = pivoted[pivoted['country_code'].str.len() == 3]
    pivoted = pivoted.sort_values(['country_code', 'year']).reset_index(drop=True)

    # Save
    output_dir = ensure_dir(project_root() / "Technical" / "data" / "processed")
    output_path = output_dir / OUTPUT_FILENAME
    write_single_sheet_excel(pivoted, output_path)
    logger.info(f"Saved {output_path.name}: {len(pivoted)} rows, {pivoted['country_code'].nunique()} countries")

    # Report coverage
    for code, col in INDICATORS.items():
        if col in pivoted.columns:
            n = pivoted[col].notna().sum()
            logger.info(f"  {col}: {n} observations")


if __name__ == "__main__":
    run()
