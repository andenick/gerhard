#!/usr/bin/env python3
"""
P111: Build US Monetary Panel
Resample FRED monetary series to monthly, compute growth rates and Fed balance sheet ratios.
Stage: P | ID: P111
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
    "id": "P111",
    "name": "Build US Monetary Panel",
    "stage": "P",
    "description": "Monthly monetary panel with growth rates and Fed balance sheet ratios",
    "depends_on": ["L111"],
    "inputs": [
        {"path": "Technical/data/raw/treasury/fred_monetary.csv", "required": True},
    ],
    "outputs": [{"path": "Output/Data/us_monetary_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}

# Series metadata (all in billions USD unless noted)
# M1SL: M1 money stock (billions)
# M2SL: M2 money stock (billions)
# BOGMBASE: Monetary base (billions)
# WALCL: Fed total assets (millions -> convert to billions)
# WTREGEN: Fed treasury holdings (millions -> convert to billions)
# FEDFUNDS: Federal funds rate (%)
# SOFR: Secured Overnight Financing Rate (%)
# DPRIME: Bank prime loan rate (%)
# TOTRESNS: Total reserves (millions -> convert to billions)
# EXCSRESNS: Excess reserves (millions -> convert to billions)

MILLIONS_TO_BILLIONS = ["WALCL", "WTREGEN", "TOTRESNS", "EXCSRESNS"]


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    raw = raw_data_dir() / "treasury"
    out = output_data_dir()

    # --- Load ---
    df = pd.read_csv(raw / "fred_monetary.csv")
    logger.info(f"Loaded fred_monetary: {len(df)} rows, columns: {list(df.columns)}")

    # Parse date and set as index
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()

    # Convert millions to billions where needed
    for col in MILLIONS_TO_BILLIONS:
        if col in df.columns:
            df[col] = df[col] / 1000.0
            logger.info(f"  Converted {col} from millions to billions")

    # --- Resample to monthly (end of month, last observation) ---
    panel = df.resample("ME").last()
    logger.info(f"Resampled to monthly: {len(panel)} rows")

    # --- Compute year-over-year growth rates ---
    growth_series = {"M1SL": "M1_growth", "M2SL": "M2_growth", "BOGMBASE": "base_growth"}
    for src, dest in growth_series.items():
        if src in panel.columns:
            panel[dest] = panel[src].pct_change(periods=12) * 100
            computed = panel[dest].notna().sum()
            logger.info(f"  {dest} computed for {computed} rows")

    # --- Fed treasury holdings as % of total assets ---
    if "WALCL" in panel.columns and "WTREGEN" in panel.columns:
        mask = panel["WALCL"].notna() & panel["WTREGEN"].notna() & (panel["WALCL"] > 0)
        panel["Fed_treasury_pct"] = np.where(
            mask, panel["WTREGEN"] / panel["WALCL"] * 100, np.nan
        )
        logger.info(f"  Fed_treasury_pct computed for {mask.sum()} rows")

    # --- Excess reserves as % of total reserves ---
    if "TOTRESNS" in panel.columns and "EXCSRESNS" in panel.columns:
        mask = panel["TOTRESNS"].notna() & panel["EXCSRESNS"].notna() & (panel["TOTRESNS"] > 0)
        panel["excess_reserves_pct"] = np.where(
            mask, panel["EXCSRESNS"] / panel["TOTRESNS"] * 100, np.nan
        )
        logger.info(f"  excess_reserves_pct computed for {mask.sum()} rows")

    # Reset index
    panel = panel.reset_index()
    panel["year"] = panel["date"].dt.year
    panel["month"] = panel["date"].dt.month
    panel["country_code"] = "USA"

    logger.info(f"Panel: {len(panel)} rows, {len(panel.columns)} cols")
    logger.info(f"  Date range: {panel['date'].min().date()} to {panel['date'].max().date()}")

    # --- Save ---
    write_single_sheet_excel(panel, out / "us_monetary_panel.xlsx")
    logger.info(
        f"Saved us_monetary_panel.xlsx: {len(panel)} rows, {len(panel.columns)} cols"
    )

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
