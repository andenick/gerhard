#!/usr/bin/env python3
"""
P80: Build Exchange Rate Panel
Compute REER changes and real depreciation from WDI exchange rate data.
Stage: P | ID: P80
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
    "id": "P80",
    "name": "Build Exchange Rate Panel",
    "stage": "P",
    "description": "Exchange rate panel with REER changes and real depreciation",
    "depends_on": ["L70"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_exchange_rates.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/exchange_rate_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_exchange_rates.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_exchange_rates.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_exchange_rates: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.sort_values(["country_code", "year"]).copy()

    # --- Compute REER year-over-year % change per country ---
    if "reer_index" in panel.columns:
        panel["reer_change_pct"] = (
            panel.groupby("country_code")["reer_index"]
            .pct_change() * 100
        )
        # Real depreciation = negative REER change (appreciation is negative depreciation)
        panel["real_depreciation"] = -panel["reer_change_pct"]

        n_reer = panel["reer_change_pct"].notna().sum()
        logger.info(f"  reer_change_pct computed for {n_reer} rows")
        logger.info(f"  real_depreciation computed for {n_reer} rows")

    # --- Sort and save ---
    panel = panel.reset_index(drop=True)
    write_single_sheet_excel(panel, out / "exchange_rate_panel.xlsx")
    logger.info(f"Saved exchange_rate_panel.xlsx: {len(panel)} rows, "
                f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
