#!/usr/bin/env python3
"""
P108: Build Treasury Interest Rates Panel
Pivot avg interest rates by security type into analytical panel.
Stage: P | ID: P108
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
    "id": "P108",
    "name": "Build Treasury Interest Rates Panel",
    "stage": "P",
    "description": "Weighted average interest rates by security type, pivoted monthly",
    "depends_on": ["L108"],
    "inputs": [
        {"path": "Technical/data/raw/treasury/avg_interest_rates.csv", "required": True},
    ],
    "outputs": [{"path": "Output/Data/treasury_interest_rates_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}

# Map security descriptions to clean column names
SECURITY_MAP = {
    "Treasury Bills": "bills",
    "Treasury Notes": "notes",
    "Treasury Bonds": "bonds",
    "Treasury Inflation-Indexed Notes": "tips_notes",
    "Treasury Inflation-Indexed Bonds": "tips_bonds",
    "Treasury Inflation-Protected Securities (TIPS)": "tips",
    "Treasury Floating Rate Notes (FRN)": "frn",
    "Federal Financing Bank": "ffb",
    "Total Marketable": "total_marketable",
    "Domestic Series": "domestic_series",
    "Foreign Series": "foreign_series",
    "State and Local Government Series": "slgs",
    "United States Savings Securities": "savings_securities",
    "United States Savings Inflation Securities": "savings_inflation",
    "Government Account Series": "govt_account",
    "Government Account Series Inflation Securities": "govt_account_inflation",
    "Total Non-marketable": "total_nonmarketable",
    "Total Interest-bearing Debt": "total_interest_bearing",
    "Hope Bonds": "hope_bonds",
    "R.E.A. Series": "rea_series",
    "Special Purpose Vehicle": "spv",
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    raw = raw_data_dir() / "treasury"
    out = output_data_dir()

    # --- Load ---
    df = pd.read_csv(raw / "avg_interest_rates.csv")
    logger.info(f"Loaded avg_interest_rates: {len(df)} rows")
    logger.info(f"  Columns: {list(df.columns)}")
    logger.info(f"  Security types: {df['security_desc'].unique()}")

    # Parse date
    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
    df["avg_interest_rate_amt"] = pd.to_numeric(df["avg_interest_rate_amt"], errors="coerce")

    # Map to clean names
    df["security_clean"] = df["security_desc"].map(SECURITY_MAP)
    unmapped = df[df["security_clean"].isna()]["security_desc"].unique()
    if len(unmapped) > 0:
        logger.warning(f"  Unmapped security types: {unmapped}")
        # Use cleaned version of desc for unmapped
        df.loc[df["security_clean"].isna(), "security_clean"] = (
            df.loc[df["security_clean"].isna(), "security_desc"]
            .str.lower()
            .str.replace(r"[^a-z0-9]+", "_", regex=True)
            .str.strip("_")
        )

    # --- Pivot: one row per date, columns = security type rates ---
    pivot = df.pivot_table(
        index="record_date",
        columns="security_clean",
        values="avg_interest_rate_amt",
        aggfunc="mean",
    )

    # Prefix columns
    pivot.columns = [f"rate_{c}" for c in pivot.columns]
    panel = pivot.reset_index().sort_values("record_date").reset_index(drop=True)

    # Add calendar fields
    panel["year"] = panel["record_date"].dt.year
    panel["month"] = panel["record_date"].dt.month
    panel["country_code"] = "USA"

    # --- Compute spread metrics ---
    if "rate_notes" in panel.columns and "rate_bills" in panel.columns:
        panel["term_spread_notes_bills"] = panel["rate_notes"] - panel["rate_bills"]
    if "rate_bonds" in panel.columns and "rate_bills" in panel.columns:
        panel["term_spread_bonds_bills"] = panel["rate_bonds"] - panel["rate_bills"]

    logger.info(f"Panel: {len(panel)} rows, {len(panel.columns)} cols")
    logger.info(f"  Date range: {panel['record_date'].min().date()} to {panel['record_date'].max().date()}")

    # --- Save ---
    write_single_sheet_excel(panel, out / "treasury_interest_rates_panel.xlsx")
    logger.info(
        f"Saved treasury_interest_rates_panel.xlsx: {len(panel)} rows, {len(panel.columns)} cols"
    )

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
