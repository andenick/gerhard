#!/usr/bin/env python3
"""
P79: Build Labor Panel
Classify structural employment type from WDI labor data.
Stage: P | ID: P79
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
    "id": "P79",
    "name": "Build Labor Panel",
    "stage": "P",
    "description": "Labor panel with structural employment type classification",
    "depends_on": ["L79"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_labor.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/labor_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def classify_employment(row):
    """Classify structural employment type based on sectoral shares."""
    agr = row.get("employment_agriculture_pct", np.nan)
    ind = row.get("employment_industry_pct", np.nan)
    svc = row.get("employment_services_pct", np.nan)

    # Need at least one non-null to classify
    if pd.isna(agr) and pd.isna(ind) and pd.isna(svc):
        return np.nan

    # Apply classification rules in priority order
    if not pd.isna(agr) and agr > 30:
        return "agrarian"
    if not pd.isna(ind) and ind > 30:
        return "industrial"
    if not pd.isna(svc) and svc > 60:
        return "service-based"
    return "mixed"


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_labor.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_labor.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_labor: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- Derived: structural employment type ---
    panel["structural_employment_type"] = panel.apply(classify_employment, axis=1)
    classified = panel["structural_employment_type"].notna().sum()
    logger.info(f"  structural_employment_type classified for {classified} rows")

    # Log distribution
    dist = panel["structural_employment_type"].value_counts()
    for etype, count in dist.items():
        logger.info(f"    {etype}: {count}")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "labor_panel.xlsx")
    logger.info(
        f"Saved labor_panel.xlsx: {len(panel)} rows, "
        f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols"
    )

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
