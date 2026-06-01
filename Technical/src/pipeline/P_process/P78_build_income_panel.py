#!/usr/bin/env python3
"""
P78: Build Income Panel
Derive GNI/GDP ratio and savings-investment gap from WDI income detail + cross-panel merges.
Stage: P | ID: P78
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
    "id": "P78",
    "name": "Build Income Panel",
    "stage": "P",
    "description": "Income panel with GNI/GDP ratio and savings-investment gap",
    "depends_on": ["L78"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_income_detail.xlsx", "required": True},
        {"path": "Output/Data/enriched_tax_panel.xlsx", "required": False},
        {"path": "Output/Data/national_accounts_panel.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/income_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load income detail ---
    df = read_excel_safe(processed / "wdi_income_detail.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_income_detail.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_income_detail: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- Merge GDP from enriched_tax_panel for GNI/GDP ratio ---
    tax_panel = read_excel_safe(out / "enriched_tax_panel.xlsx")
    if not tax_panel.empty and "gdp_current_usd" in tax_panel.columns:
        gdp_lookup = tax_panel[["country_code", "year", "gdp_current_usd"]].dropna(
            subset=["gdp_current_usd"]
        )
        before = len(panel)
        panel = panel.merge(gdp_lookup, on=["country_code", "year"], how="left")
        logger.info(f"  Merged GDP from enriched_tax_panel: {panel['gdp_current_usd'].notna().sum()} matches")

        # GNI/GDP ratio (>1 means net income from abroad is positive)
        mask = (
            panel["gni_current_usd"].notna()
            & panel["gdp_current_usd"].notna()
            & (panel["gdp_current_usd"] > 0)
        )
        panel["gni_gdp_ratio"] = np.where(
            mask, panel["gni_current_usd"] / panel["gdp_current_usd"], np.nan
        )
        logger.info(f"  gni_gdp_ratio computed for {mask.sum()} rows")
    else:
        logger.warning("  enriched_tax_panel not available or missing gdp_current_usd; skipping gni_gdp_ratio")

    # --- Merge GCF from national_accounts_panel for savings-investment gap ---
    na_panel = read_excel_safe(out / "national_accounts_panel.xlsx")
    if not na_panel.empty and "gross_capital_formation_pct_gdp" in na_panel.columns:
        gcf_lookup = na_panel[["country_code", "year", "gross_capital_formation_pct_gdp"]].dropna(
            subset=["gross_capital_formation_pct_gdp"]
        )
        panel = panel.merge(gcf_lookup, on=["country_code", "year"], how="left")
        logger.info(
            f"  Merged GCF from national_accounts_panel: "
            f"{panel['gross_capital_formation_pct_gdp'].notna().sum()} matches"
        )

        # Savings-investment gap
        if "gross_savings_pct_gdp" in panel.columns:
            mask = (
                panel["gross_savings_pct_gdp"].notna()
                & panel["gross_capital_formation_pct_gdp"].notna()
            )
            panel["savings_investment_gap"] = np.where(
                mask,
                panel["gross_savings_pct_gdp"] - panel["gross_capital_formation_pct_gdp"],
                np.nan,
            )
            logger.info(f"  savings_investment_gap computed for {mask.sum()} rows")
    else:
        logger.warning("  national_accounts_panel not available; skipping savings_investment_gap")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "income_panel.xlsx")
    logger.info(
        f"Saved income_panel.xlsx: {len(panel)} rows, "
        f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols"
    )

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
