#!/usr/bin/env python3
"""
P77: Build Expenditure Functions Panel
Derive social spending and guns/butter ratio from WDI expenditure-by-function data.
Stage: P | ID: P77
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
    "id": "P77",
    "name": "Build Expenditure Functions Panel",
    "stage": "P",
    "description": "Expenditure functions panel with social spending and guns/butter ratio",
    "depends_on": ["L77"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_expenditure_functions.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/expenditure_functions_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_expenditure_functions.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_expenditure_functions.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_expenditure_functions: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- Derived: social spending (education + health govt, % GDP) ---
    if "education_pct_gdp" in panel.columns and "health_govt_pct_gdp" in panel.columns:
        mask = panel["education_pct_gdp"].notna() & panel["health_govt_pct_gdp"].notna()
        panel["social_spending_pct_gdp"] = np.where(
            mask,
            panel["education_pct_gdp"] + panel["health_govt_pct_gdp"],
            np.nan,
        )
        logger.info(f"  social_spending_pct_gdp computed for {mask.sum()} rows")

    # --- Derived: guns/butter ratio ---
    if "military_pct_gdp" in panel.columns and "social_spending_pct_gdp" in panel.columns:
        mask = (
            panel["military_pct_gdp"].notna()
            & panel["social_spending_pct_gdp"].notna()
            & (panel["military_pct_gdp"] > 0)
            & (panel["social_spending_pct_gdp"] > 0)
        )
        panel["guns_butter_ratio"] = np.where(
            mask,
            panel["military_pct_gdp"] / panel["social_spending_pct_gdp"],
            np.nan,
        )
        logger.info(f"  guns_butter_ratio computed for {mask.sum()} rows")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "expenditure_functions_panel.xlsx")
    logger.info(
        f"Saved expenditure_functions_panel.xlsx: {len(panel)} rows, "
        f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols"
    )

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
