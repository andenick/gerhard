#!/usr/bin/env python3
"""
P76: Build Financial Sector Panel
Derive lending spread, financial depth index, and crowding-out ratio from WDI financial sector data.
Stage: P | ID: P76
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
    "id": "P76",
    "name": "Build Financial Sector Panel",
    "stage": "P",
    "description": "Financial sector panel with lending spread, depth index, crowding-out ratio",
    "depends_on": ["L76"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_financial_sector.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/financial_sector_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_financial_sector.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_financial_sector.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_financial_sector: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- Derived: lending spread ---
    if "lending_interest_rate" in panel.columns and "deposit_interest_rate" in panel.columns:
        mask = panel["lending_interest_rate"].notna() & panel["deposit_interest_rate"].notna()
        panel["lending_spread"] = np.where(
            mask,
            panel["lending_interest_rate"] - panel["deposit_interest_rate"],
            np.nan,
        )
        logger.info(f"  lending_spread computed for {mask.sum()} rows")

    # --- Derived: financial depth index (nanmean of 3 indicators) ---
    depth_cols = ["broad_money_pct_gdp", "domestic_credit_financial_pct_gdp", "market_cap_pct_gdp"]
    available = [c for c in depth_cols if c in panel.columns]
    if available:
        panel["financial_depth_index"] = panel[available].apply(
            lambda row: np.nanmean(row.values) if row.notna().any() else np.nan, axis=1
        )
        computed = panel["financial_depth_index"].notna().sum()
        logger.info(f"  financial_depth_index computed for {computed} rows (from {len(available)} indicators)")

    # --- Derived: crowding-out ratio ---
    if "claims_on_central_govt_pct_gdp" in panel.columns and "domestic_credit_financial_pct_gdp" in panel.columns:
        mask = (
            panel["claims_on_central_govt_pct_gdp"].notna()
            & panel["domestic_credit_financial_pct_gdp"].notna()
            & (panel["domestic_credit_financial_pct_gdp"] != 0)
        )
        panel["crowding_out_ratio"] = np.where(
            mask,
            panel["claims_on_central_govt_pct_gdp"] / panel["domestic_credit_financial_pct_gdp"] * 100,
            np.nan,
        )
        logger.info(f"  crowding_out_ratio computed for {mask.sum()} rows")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "financial_sector_panel.xlsx")
    logger.info(
        f"Saved financial_sector_panel.xlsx: {len(panel)} rows, "
        f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols"
    )

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
