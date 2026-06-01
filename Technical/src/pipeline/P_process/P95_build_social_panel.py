#!/usr/bin/env python3
"""
P95: Build Social Outcomes Panel
Pass through WDI social indicators as a clean panel.
Stage: P | ID: P95
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
    "id": "P95",
    "name": "Build Social Outcomes Panel",
    "stage": "P",
    "description": "Social indicators panel from WDI social data",
    "depends_on": ["L80"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_social.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/social_outcomes_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_social.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_social.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_social: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "social_outcomes_panel.xlsx")
    logger.info(f"Saved social_outcomes_panel.xlsx: {len(panel)} rows, "
                f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
