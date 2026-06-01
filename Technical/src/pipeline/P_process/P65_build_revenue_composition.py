#!/usr/bin/env python3
"""
P65: Build Revenue Composition Panel
Extract revenue-side columns from WDI fiscal detail and compute tax diversification.
Stage: P | ID: P65
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
    "id": "P65",
    "name": "Build Revenue Composition Panel",
    "stage": "P",
    "description": "Revenue-side columns with tax diversification index",
    "depends_on": ["L55"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_fiscal_detail.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/revenue_composition_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}

REVENUE_COLS = [
    "country_code", "country_name", "year",
    "tax_revenue_pct_gdp",
    "income_tax_pct_gdp",
    "income_tax_pct_revenue",
    "goods_services_tax_pct_revenue",
    "trade_tax_pct_revenue",
    "social_contributions_pct_revenue",
    "other_tax_pct_revenue",
    "revenue_excl_grants_pct_gdp",
    "grants_other_pct_revenue",
]

# Shares used for diversification index (as % of revenue)
SHARE_COLS = [
    "income_tax_pct_revenue",
    "goods_services_tax_pct_revenue",
    "trade_tax_pct_revenue",
    "other_tax_pct_revenue",
]


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_fiscal_detail.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_fiscal_detail.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_fiscal_detail: {len(df)} rows, {df['country_code'].nunique()} countries")

    # --- Filter to rows with at least tax_revenue_pct_gdp ---
    available = [c for c in REVENUE_COLS if c in df.columns]
    panel = df[available].copy()
    panel = panel[panel["tax_revenue_pct_gdp"].notna()].reset_index(drop=True)
    logger.info(f"After filtering (tax_revenue_pct_gdp non-null): {len(panel)} rows")

    # --- Compute tax diversification index ---
    # HHI-complement: 1 - sum(share_i^2) where shares are fractions (0-1)
    share_df = panel[SHARE_COLS].div(100)  # convert pct to fraction
    hhi = (share_df ** 2).sum(axis=1, min_count=1)
    panel["tax_diversification_index"] = np.where(hhi.notna(), 1 - hhi, np.nan)

    n_div = panel["tax_diversification_index"].notna().sum()
    logger.info(f"  tax_diversification_index computed for {n_div} rows")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "revenue_composition_panel.xlsx")
    logger.info(f"Saved revenue_composition_panel.xlsx: {len(panel)} rows, "
                f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
