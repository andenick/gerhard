#!/usr/bin/env python3
"""
P97: Build National Accounts Panel
Pass through WDI national accounts as a clean panel.
Stage: P | ID: P97
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "P97",
    "name": "Build National Accounts Panel",
    "stage": "P",
    "description": "National accounts panel from WDI data",
    "depends_on": ["L85"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_national_accounts.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/national_accounts_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_national_accounts.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_national_accounts.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_national_accounts: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "national_accounts_panel.xlsx")
    logger.info(f"Saved national_accounts_panel.xlsx: {len(panel)} rows, "
                f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
