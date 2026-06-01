#!/usr/bin/env python3
"""
P120: Build Yield Curve Panel
Convert daily yield curves to monthly with derived spread/regime metrics.
Stage: P | ID: P120
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
    "id": "P120",
    "name": "Build Yield Curve Panel",
    "stage": "P",
    "description": "Build daily and monthly yield curve panels with derived metrics",
    "depends_on": ["L110"],
    "inputs": [
        {"path": "Technical/data/raw/treasury/yield_curves_daily.csv", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/yield_curve_daily.xlsx"},
        {"path": "Output/Data/yield_curve_monthly.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}

# Key yield series
YIELD_COLS = [
    "DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS3",
    "DGS5", "DGS7", "DGS10", "DGS20", "DGS30",
]
TIPS_COLS = ["DFII5", "DFII10", "DFII20", "DFII30"]
SPREAD_COLS = ["T10Y2Y", "T10Y3M", "T10YIE"]
ALL_SERIES = YIELD_COLS + TIPS_COLS + SPREAD_COLS + ["DFF"]


def classify_regime(spread_10y2y):
    """Classify yield curve regime based on 10Y-2Y spread."""
    if pd.isna(spread_10y2y):
        return np.nan
    if spread_10y2y < -0.10:
        return "Inverted"
    elif spread_10y2y < 0.50:
        return "Flat"
    else:
        return "Normal"


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    raw = raw_data_dir() / "treasury"

    # --- Load daily yield curves ---
    logger.info("Loading yield_curves_daily.csv...")
    df = pd.read_csv(raw / "yield_curves_daily.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Convert all series to numeric
    for col in ALL_SERIES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(f"Daily data: {len(df)} rows, "
                f"{df['date'].min().date()} to {df['date'].max().date()}")

    # Write daily (full)
    write_single_sheet_excel(df, out / "yield_curve_daily.xlsx", sheet_name="DailyYields")

    # --- Resample to monthly (last business day) ---
    logger.info("Resampling to monthly...")
    df_indexed = df.set_index("date")
    monthly = df_indexed[ALL_SERIES].resample("ME").last().reset_index()
    monthly = monthly.rename(columns={"date": "month_end"})

    # --- Compute derived metrics ---
    # Term spreads
    monthly["term_spread_10y2y"] = monthly["DGS10"] - monthly["DGS2"]

    # Use pre-computed T10Y3M if available, else compute
    if "T10Y3M" in monthly.columns:
        monthly["term_spread_10y3m"] = monthly["T10Y3M"]
    else:
        monthly["term_spread_10y3m"] = monthly["DGS10"] - monthly["DGS3MO"]

    # Real 10Y yield (10Y nominal - 10Y breakeven inflation)
    if "T10YIE" in monthly.columns:
        monthly["real_10y"] = monthly["DGS10"] - monthly["T10YIE"]

    # Curve slope: average bp per maturity year
    monthly["curve_slope"] = (monthly["DGS30"] - monthly["DGS1MO"]) / 29.0

    # Butterfly (curvature): 2*5Y - 2Y - 10Y
    monthly["curve_curvature"] = 2 * monthly["DGS5"] - monthly["DGS2"] - monthly["DGS10"]

    # Inversion flag
    monthly["inversion_flag"] = (monthly["DGS10"] < monthly["DGS2"]).astype(int)

    # Regime classification
    monthly["curve_regime"] = monthly["term_spread_10y2y"].apply(classify_regime)

    logger.info(f"Monthly panel: {len(monthly)} rows, "
                f"{len(monthly.columns)} columns")

    # Regime distribution
    regime_counts = monthly["curve_regime"].value_counts()
    for regime, count in regime_counts.items():
        logger.info(f"  Regime '{regime}': {count} months ({100*count/len(monthly):.1f}%)")

    write_single_sheet_excel(monthly, out / "yield_curve_monthly.xlsx", sheet_name="MonthlyYields")

    logger.info(f"[{MANIFEST['id']}] Done. Daily: {len(df)} rows, Monthly: {len(monthly)} rows")


if __name__ == "__main__":
    run()
