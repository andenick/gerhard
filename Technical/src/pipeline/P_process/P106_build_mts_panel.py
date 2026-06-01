#!/usr/bin/env python3
"""
P106: Build MTS Receipts & Outlays Panel
Pivot US monthly fiscal data into analytical panel with rolling averages.
Stage: P | ID: P106
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, raw_data_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "P106",
    "name": "Build MTS Panel",
    "stage": "P",
    "description": "US monthly fiscal receipts/outlays panel from MTS data",
    "depends_on": ["L106"],
    "inputs": [
        {"path": "Technical/data/raw/treasury/mts_receipts_outlays.csv", "required": True},
    ],
    "outputs": [{"path": "Output/Data/us_mts_panel.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}

# Top-level receipt categories to extract (sequence_level_nbr == 1, data_type_cd == 'T')
# We use the detail rows (data_type_cd == 'D') for granularity and totals for validation


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    raw = raw_data_dir() / "treasury"
    out = output_data_dir()

    # --- Load ---
    raw_path = raw / "mts_receipts_outlays.csv"
    df = pd.read_csv(raw_path, low_memory=False)
    logger.info(f"Loaded mts_receipts_outlays: {len(df)} rows")
    logger.info(f"  Columns: {list(df.columns)}")

    # Parse record_date
    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")

    # Log structure discovery
    logger.info(f"  data_type_cd values: {df['data_type_cd'].unique()}")
    logger.info(f"  record_type_cd values: {df['record_type_cd'].unique()}")
    top_level = df[df["sequence_level_nbr"] == 1]["classification_desc"].unique()
    logger.info(f"  Top-level classifications: {list(top_level)}")

    # --- Focus on top-level summary rows (sequence_level_nbr == 1) ---
    # These are the main receipt/outlay categories
    summary = df[df["sequence_level_nbr"] == 1].copy()

    # Clean classification names for column headers
    summary["clean_class"] = (
        summary["classification_desc"]
        .str.strip()
        .str.rstrip(":")
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    # --- Pivot: one row per month, columns = classification x amount type ---
    # Use current_month_net_rcpt_amt as the primary value
    pivot_data = summary.pivot_table(
        index="record_date",
        columns="clean_class",
        values="current_month_net_rcpt_amt",
        aggfunc="sum",
    )

    # Prefix columns
    pivot_data.columns = [f"monthly_{c}" for c in pivot_data.columns]

    # Also add FYTD net receipts for the total
    total_rows = df[df["classification_desc"].str.contains("Total", na=False, case=False)]
    total_rows = total_rows[total_rows["sequence_level_nbr"] == 1]
    if not total_rows.empty:
        fytd_totals = total_rows.groupby("record_date")["current_fytd_net_rcpt_amt"].sum()
        pivot_data["fytd_net_receipts"] = fytd_totals

    # Reset index
    panel = pivot_data.reset_index()
    panel = panel.sort_values("record_date").reset_index(drop=True)

    # Add calendar fields
    panel["year"] = panel["record_date"].dt.year
    panel["month"] = panel["record_date"].dt.month
    panel["country_code"] = "USA"

    # --- Compute 12-month rolling averages for seasonal adjustment ---
    numeric_cols = [c for c in panel.columns if c.startswith("monthly_")]
    for col in numeric_cols:
        roll_col = col.replace("monthly_", "rolling12m_")
        panel[roll_col] = panel[col].rolling(window=12, min_periods=6).mean()

    logger.info(f"Panel: {len(panel)} rows, {len(panel.columns)} cols")
    logger.info(f"  Date range: {panel['record_date'].min().date()} to {panel['record_date'].max().date()}")

    # --- Save ---
    write_single_sheet_excel(panel, out / "us_mts_panel.xlsx")
    logger.info(
        f"Saved us_mts_panel.xlsx: {len(panel)} rows, {len(panel.columns)} cols"
    )

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
