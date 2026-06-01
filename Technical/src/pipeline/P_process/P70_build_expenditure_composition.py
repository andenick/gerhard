#!/usr/bin/env python3
"""
P70: Build Expenditure Composition Panel
Merge WDI expenditure columns with Eurostat COFOG functional breakdown.
Stage: P | ID: P70
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
    "id": "P70",
    "name": "Build Expenditure Composition Panel",
    "stage": "P",
    "description": "WDI expenditure columns merged with Eurostat COFOG breakdown",
    "depends_on": ["L55", "L56"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_fiscal_detail.xlsx", "required": True},
        {"path": "Technical/data/processed/eurostat_cofog_panel.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/expenditure_composition_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}

WDI_EXPENSE_COLS = [
    "country_code", "country_name", "year",
    "total_expense_pct_gdp",
    "compensation_pct_expense",
    "goods_services_pct_expense",
    "interest_pct_expense",
    "interest_pct_revenue",
    "transfers_pct_expense",
    "other_expense_pct_expense",
]

# Mapping from actual COFOG column names to prefixed output names
COFOG_RENAME = {
    "general_public_services": "cofog_general_services",
    "defense": "cofog_defense",
    "public_order_safety": "cofog_public_order",
    "economic_affairs": "cofog_economic_affairs",
    "environment_protection": "cofog_environment",
    "housing_community": "cofog_housing",
    "health": "cofog_health",
    "recreation_culture": "cofog_recreation",
    "education": "cofog_education",
    "social_protection": "cofog_social_protection",
    "total_expenditure": "cofog_total",
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load WDI fiscal detail (expenditure side) ---
    wdi = read_excel_safe(processed / "wdi_fiscal_detail.xlsx")
    if wdi.empty:
        logger.error("Cannot load wdi_fiscal_detail.xlsx; aborting.")
        return

    available = [c for c in WDI_EXPENSE_COLS if c in wdi.columns]
    panel = wdi[available].copy()

    # Filter: keep rows where total_expense_pct_gdp is non-null
    panel = panel[panel["total_expense_pct_gdp"].notna()].reset_index(drop=True)
    logger.info(f"WDI expenditure rows (total_expense non-null): {len(panel)}")

    # --- Compute interest_pct_gdp ---
    if "interest_pct_expense" in panel.columns and "total_expense_pct_gdp" in panel.columns:
        mask = panel["interest_pct_expense"].notna() & panel["total_expense_pct_gdp"].notna()
        panel["interest_pct_gdp"] = np.where(
            mask,
            (panel["interest_pct_expense"] / 100) * panel["total_expense_pct_gdp"],
            np.nan,
        )
        logger.info(f"  interest_pct_gdp computed for {mask.sum()} rows")

    # --- Load and merge COFOG ---
    cofog = read_excel_safe(processed / "eurostat_cofog_panel.xlsx")
    if not cofog.empty:
        # Rename COFOG columns to prefixed names
        rename_available = {k: v for k, v in COFOG_RENAME.items() if k in cofog.columns}
        cofog = cofog.rename(columns=rename_available)
        cofog_cols = ["country_code", "year"] + list(rename_available.values())
        cofog_slim = cofog[[c for c in cofog_cols if c in cofog.columns]].copy()

        pre = len(panel)
        panel = panel.merge(cofog_slim, on=["country_code", "year"], how="left")
        n_matched = panel[[c for c in rename_available.values() if c in panel.columns]].notna().any(axis=1).sum()
        logger.info(f"  COFOG merge: {n_matched} rows matched, panel {pre} -> {len(panel)} rows")
    else:
        logger.warning("COFOG panel not found; proceeding without functional breakdown.")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "expenditure_composition_panel.xlsx")
    logger.info(f"Saved expenditure_composition_panel.xlsx: {len(panel)} rows, "
                f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
