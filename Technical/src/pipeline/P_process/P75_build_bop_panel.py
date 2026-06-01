#!/usr/bin/env python3
"""
P75: Build Balance of Payments Panel
Compute derived BoP balances from WDI BoP detail.
Stage: P | ID: P75
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
    "id": "P75",
    "name": "Build Balance of Payments Panel",
    "stage": "P",
    "description": "BoP panel with derived goods/services/income balances",
    "depends_on": ["L60"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_bop_detail.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/bop_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_bop_detail.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_bop_detail.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_bop_detail: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- Derived columns ---
    # Goods balance
    if "goods_exports_usd" in panel.columns and "goods_imports_usd" in panel.columns:
        mask = panel["goods_exports_usd"].notna() & panel["goods_imports_usd"].notna()
        panel["goods_balance_usd"] = np.where(
            mask, panel["goods_exports_usd"] - panel["goods_imports_usd"], np.nan
        )
        logger.info(f"  goods_balance_usd computed for {mask.sum()} rows")

    # Services balance
    if "services_exports_usd" in panel.columns and "services_imports_usd" in panel.columns:
        mask = panel["services_exports_usd"].notna() & panel["services_imports_usd"].notna()
        panel["services_balance_usd"] = np.where(
            mask, panel["services_exports_usd"] - panel["services_imports_usd"], np.nan
        )
        logger.info(f"  services_balance_usd computed for {mask.sum()} rows")

    # Primary income net
    if "primary_income_receipts_usd" in panel.columns and "primary_income_payments_usd" in panel.columns:
        mask = panel["primary_income_receipts_usd"].notna() & panel["primary_income_payments_usd"].notna()
        panel["primary_income_net_usd"] = np.where(
            mask, panel["primary_income_receipts_usd"] - panel["primary_income_payments_usd"], np.nan
        )
        logger.info(f"  primary_income_net_usd computed for {mask.sum()} rows")

    # --- Filter: keep rows where at least current_account_pct_gdp or goods_exports_usd is non-null ---
    keep_mask = panel["current_account_pct_gdp"].notna() | panel["goods_exports_usd"].notna()
    panel = panel[keep_mask].reset_index(drop=True)
    logger.info(f"After filtering: {len(panel)} rows")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "bop_panel.xlsx")
    logger.info(f"Saved bop_panel.xlsx: {len(panel)} rows, "
                f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
