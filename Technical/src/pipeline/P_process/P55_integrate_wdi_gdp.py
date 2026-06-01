#!/usr/bin/env python3
"""
P55: Integrate WDI GDP
Merge GDP, population, trade data from World Bank WDI into tax panel.
Stage: P | ID: P55
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "P55",
    "name": "Integrate WDI GDP",
    "stage": "P",
    "description": "Merge GDP, population, trade data from World Bank WDI into tax panel",
    "depends_on": ["L50", "P40"],
    "inputs": [
        {"path": "Output/Data/clean_tax_panel.xlsx", "required": True},
        {"path": "Inputs/WDI/wdi_macro_panel.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/enriched_tax_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}

# GDP columns expected from WDI macro panel
GDP_COLS = [
    'gdp_current_usd',
    'gdp_constant_2015_usd',
    'gdp_per_capita_usd',
    'gdp_per_capita_ppp',
    'population',
    'trade_pct_gdp',
    'urban_pct',
]


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    root = project_root()
    out = output_data_dir()

    # --- Load tax panel ---
    tax_path = out / "clean_tax_panel.xlsx"
    tax = read_excel_safe(tax_path)
    if tax.empty:
        logger.error(f"Cannot load tax panel: {tax_path}")
        return
    logger.info(f"Tax panel: {len(tax)} rows, {tax['country_code'].nunique()} countries")

    # --- Load WDI macro panel ---
    wdi_path = root / "Inputs" / "WDI" / "wdi_macro_panel.xlsx"
    wdi = read_excel_safe(wdi_path)
    if wdi.empty:
        logger.error(f"Cannot load WDI macro panel: {wdi_path}")
        return
    logger.info(f"WDI macro panel: {len(wdi)} rows, {wdi['country_code'].nunique()} entities")

    # Select only the merge key + GDP columns from WDI
    wdi_merge_cols = ['country_code', 'year'] + [c for c in GDP_COLS if c in wdi.columns]
    wdi_slim = wdi[wdi_merge_cols].copy()

    # --- Load country metadata (region, income_group) ---
    meta_path = root / "Inputs" / "WDI" / "wdi_country_metadata.xlsx"
    meta = read_excel_safe(meta_path)
    if not meta.empty and 'country_code' in meta.columns:
        logger.info(f"Country metadata: {len(meta)} countries")
        meta_cols = ['country_code']
        if 'region' in meta.columns:
            meta_cols.append('region')
        if 'income_group' in meta.columns:
            meta_cols.append('income_group')
        meta_slim = meta[meta_cols].drop_duplicates('country_code')
    else:
        logger.warning("No country metadata available; skipping region/income_group")
        meta_slim = pd.DataFrame()

    # --- Merge GDP data into tax panel ---
    pre_merge = len(tax)
    enriched = tax.merge(wdi_slim, on=['country_code', 'year'], how='left')
    logger.info(f"After GDP merge: {len(enriched)} rows (was {pre_merge})")

    # Count GDP coverage
    gdp_matched = enriched['gdp_current_usd'].notna().sum()
    logger.info(f"  GDP data matched: {gdp_matched}/{len(enriched)} rows ({100*gdp_matched/len(enriched):.1f}%)")

    # --- Merge country metadata ---
    if not meta_slim.empty:
        enriched = enriched.merge(meta_slim, on='country_code', how='left')
        region_matched = enriched['region'].notna().sum() if 'region' in enriched.columns else 0
        logger.info(f"  Region matched: {region_matched}/{len(enriched)} rows")

    # --- Report coverage by region ---
    if 'region' in enriched.columns:
        logger.info("\n  Coverage by region:")
        region_stats = enriched.groupby('region').agg(
            rows=('country_code', 'size'),
            countries=('country_code', 'nunique'),
            gdp_coverage=('gdp_current_usd', lambda x: x.notna().mean()),
        ).sort_values('rows', ascending=False)
        for region, row in region_stats.iterrows():
            logger.info(f"    {region}: {row['countries']} countries, "
                       f"{row['rows']} rows, GDP coverage {100*row['gdp_coverage']:.0f}%")

    # --- Ensure column order ---
    priority_cols = [
        'country_code', 'country_name', 'year', 'tax_revenue_pct_gdp',
        'is_outlier', 'quality_tier',
    ]
    gdp_cols_present = [c for c in GDP_COLS if c in enriched.columns]
    meta_cols_present = [c for c in ['region', 'income_group'] if c in enriched.columns]
    other_cols = [c for c in enriched.columns
                  if c not in priority_cols + gdp_cols_present + meta_cols_present]

    final_order = priority_cols + gdp_cols_present + meta_cols_present + other_cols
    final_order = [c for c in final_order if c in enriched.columns]
    enriched = enriched[final_order]

    enriched = enriched.sort_values(['country_code', 'year']).reset_index(drop=True)

    # --- Save ---
    write_single_sheet_excel(enriched, out / "enriched_tax_panel.xlsx")
    logger.info(f"Saved enriched_tax_panel.xlsx: {len(enriched)} rows, "
               f"{enriched['country_code'].nunique()} countries, {len(enriched.columns)} columns")
    logger.info(f"  Columns: {list(enriched.columns)}")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
