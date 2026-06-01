#!/usr/bin/env python3
"""
P110: Integrate Governance
Create governance panel with composite score from WGI indicators.
Stage: P | ID: P110
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "P110",
    "name": "Integrate Governance",
    "stage": "P",
    "description": "Create governance panel with composite score from WGI",
    "depends_on": ["L100"],
    "inputs": [
        {"path": "Technical/data/processed/wgi_governance.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/governance_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}

# The 6 WGI dimensions (column names from L100 extraction)
GOVERNANCE_DIMS = [
    "govt_effectiveness",
    "regulatory_quality",
    "rule_of_law",
    "control_of_corruption",
    "voice_accountability",
    "political_stability",
]


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    root = project_root()

    # Load WGI extraction
    wgi_path = root / "Technical" / "data" / "processed" / "wgi_governance.xlsx"
    wgi = pd.read_excel(wgi_path)
    logger.info(f"WGI data: {len(wgi)} rows, {wgi['country_code'].nunique() if len(wgi) > 0 else 0} countries")

    if len(wgi) == 0:
        logger.warning("WGI data is empty; creating placeholder governance_panel.xlsx")
        placeholder = pd.DataFrame(columns=["country_code", "country_name", "year"] +
                                   GOVERNANCE_DIMS + ["governance_composite"])
        write_single_sheet_excel(placeholder, out / "governance_panel.xlsx")
        logger.info("Saved governance_panel.xlsx (empty)")
        return

    # Ensure all dimension columns exist
    for dim in GOVERNANCE_DIMS:
        if dim not in wgi.columns:
            wgi[dim] = np.nan
            logger.warning(f"Missing dimension: {dim}")

    # Compute governance composite = mean of available dimensions per row
    wgi["governance_composite"] = wgi[GOVERNANCE_DIMS].mean(axis=1)

    # Count how many dimensions are non-null per row
    wgi["n_dimensions"] = wgi[GOVERNANCE_DIMS].notna().sum(axis=1)

    # Order columns
    ordered_cols = ["country_code", "country_name", "year"] + GOVERNANCE_DIMS + [
        "governance_composite", "n_dimensions"
    ]
    existing_cols = [c for c in ordered_cols if c in wgi.columns]
    result = wgi[existing_cols].copy()

    # Filter rows with at least 1 governance dimension
    result = result[result["n_dimensions"] > 0].copy()

    result = result.sort_values(["country_code", "year"]).reset_index(drop=True)

    # Summary statistics
    n_countries = result["country_code"].nunique()
    yr_range = f"{result['year'].min()}-{result['year'].max()}"
    logger.info(f"Governance panel: {len(result)} rows, {n_countries} countries, {yr_range}")

    for dim in GOVERNANCE_DIMS:
        if dim in result.columns:
            n = result[dim].notna().sum()
            mean_val = result[dim].mean()
            logger.info(f"  {dim}: {n} obs, mean={mean_val:.3f}")

    composite_mean = result["governance_composite"].mean()
    logger.info(f"  governance_composite: mean={composite_mean:.3f}")

    # Distribution of dimension coverage
    coverage = result["n_dimensions"].value_counts().sort_index()
    for dims, count in coverage.items():
        logger.info(f"  Rows with {dims}/6 dimensions: {count}")

    write_single_sheet_excel(result, out / "governance_panel.xlsx")
    logger.info("Saved governance_panel.xlsx")


if __name__ == "__main__":
    run()
