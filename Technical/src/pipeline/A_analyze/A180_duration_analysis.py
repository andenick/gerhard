#!/usr/bin/env python3
"""
A180: Duration Analysis
Compute Macaulay duration for each Treasury security and track portfolio duration.
Stage: A | ID: A180
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
    "id": "A180",
    "name": "Duration Analysis",
    "stage": "A",
    "description": "Compute Macaulay duration for Treasury securities and track portfolio duration",
    "depends_on": ["P115"],
    "inputs": [
        {"path": "Technical/data/raw/treasury/mspd_table_3_market.csv", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/treasury_duration_analysis.xlsx"},
    ],
    "timeout": 300,
    "parallel_safe": True,
}

# Map security_class1_desc to standardized type
SECURITY_TYPE_MAP = {
    "Bills Maturity Value": "Bills",
    "Notes": "Notes",
    "Bonds": "Bonds",
    "Inflation-Protected Securities": "TIPS",
    "Inflation-Indexed Notes": "TIPS",
    "Inflation-Indexed Bonds": "TIPS",
    "Floating Rate Notes": "FRN",
}


def macaulay_duration(coupon_rate, remaining_years, yield_rate, face=100):
    """Simplified Macaulay duration for a coupon bond.

    Args:
        coupon_rate: Annual coupon rate (decimal, e.g. 0.05 for 5%)
        remaining_years: Years to maturity
        yield_rate: Annual yield (decimal)
        face: Face value

    Returns:
        Duration in years
    """
    if remaining_years is None or np.isnan(remaining_years) or remaining_years <= 0:
        return 0.0
    if coupon_rate is None or np.isnan(coupon_rate) or coupon_rate == 0:
        # Zero-coupon (bills, zero-coupon STRIPS)
        return remaining_years

    if yield_rate is None or np.isnan(yield_rate) or yield_rate <= 0:
        # If no yield, approximate with coupon rate
        yield_rate = coupon_rate
    if yield_rate <= 0:
        return remaining_years

    coupon = face * coupon_rate / 2  # Semi-annual
    n_periods = max(1, int(remaining_years * 2))
    y = yield_rate / 2  # Semi-annual yield

    pv_weighted_sum = 0.0
    pv_sum = 0.0
    for t in range(1, n_periods + 1):
        discount = (1 + y) ** t
        pv = coupon / discount
        pv_weighted_sum += t * pv
        pv_sum += pv

    # Add principal
    discount_n = (1 + y) ** n_periods
    pv_principal = face / discount_n
    pv_weighted_sum += n_periods * pv_principal
    pv_sum += pv_principal

    if pv_sum <= 0:
        return remaining_years

    duration_periods = pv_weighted_sum / pv_sum
    return duration_periods / 2  # Convert to years


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    raw = raw_data_dir() / "treasury"

    # --- Load raw security data ---
    logger.info("Loading mspd_table_3_market.csv...")
    df = pd.read_csv(raw / "mspd_table_3_market.csv", low_memory=False)

    # Parse and convert
    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
    df["maturity_date"] = pd.to_datetime(df["maturity_date"], errors="coerce")
    df["interest_rate_pct"] = pd.to_numeric(df["interest_rate_pct"], errors="coerce")
    df["yield_pct"] = pd.to_numeric(df["yield_pct"], errors="coerce")
    df["outstanding_amt"] = pd.to_numeric(df["outstanding_amt"], errors="coerce")

    # Classify
    df["security_type"] = df["security_class1_desc"].map(SECURITY_TYPE_MAP)
    df = df[df["security_type"].notna()].copy()

    # Remaining maturity
    df["remaining_years"] = (df["maturity_date"] - df["record_date"]).dt.days / 365.25

    # Convert rates to decimals
    df["coupon_decimal"] = df["interest_rate_pct"] / 100.0
    df["yield_decimal"] = df["yield_pct"] / 100.0

    # Filter to securities with positive outstanding and maturity
    df = df[df["outstanding_amt"].notna() & (df["outstanding_amt"] > 0)].copy()
    df = df[df["remaining_years"].notna() & (df["remaining_years"] > 0)].copy()
    logger.info(f"Computing duration for {len(df)} security-date observations...")

    # --- Compute Macaulay duration ---
    df["duration_years"] = df.apply(
        lambda r: macaulay_duration(
            r["coupon_decimal"],
            r["remaining_years"],
            r["yield_decimal"],
        ),
        axis=1,
    )

    logger.info(f"Duration computed. Mean: {df['duration_years'].mean():.2f} years")

    # --- Aggregate: weighted average duration per month by type ---
    logger.info("Aggregating portfolio duration by month...")
    records = []
    for rd, grp in df.groupby("record_date"):
        row = {"record_date": rd}

        # Overall portfolio duration (weighted by outstanding)
        total_out = grp["outstanding_amt"].sum()
        if total_out > 0:
            row["portfolio_duration_years"] = np.average(
                grp["duration_years"], weights=grp["outstanding_amt"]
            )
        else:
            row["portfolio_duration_years"] = np.nan

        row["total_outstanding_bil"] = total_out / 1000.0

        # Duration by type
        for stype in ["Bills", "Notes", "Bonds", "TIPS", "FRN"]:
            sub = grp[grp["security_type"] == stype]
            if len(sub) > 0 and sub["outstanding_amt"].sum() > 0:
                row[f"{stype.lower()}_duration"] = np.average(
                    sub["duration_years"], weights=sub["outstanding_amt"]
                )
                row[f"{stype.lower()}_outstanding_bil"] = sub["outstanding_amt"].sum() / 1000.0
            else:
                row[f"{stype.lower()}_duration"] = np.nan
                row[f"{stype.lower()}_outstanding_bil"] = 0.0

        # Duration-weighted outstanding (dollar-duration)
        row["duration_times_outstanding"] = (
            row["portfolio_duration_years"] * row["total_outstanding_bil"]
            if pd.notna(row.get("portfolio_duration_years")) else np.nan
        )

        records.append(row)

    panel = pd.DataFrame(records).sort_values("record_date").reset_index(drop=True)

    logger.info(f"Duration panel: {len(panel)} rows")
    logger.info(f"Latest portfolio duration: {panel['portfolio_duration_years'].iloc[-1]:.2f} years")
    logger.info(f"Latest total outstanding: ${panel['total_outstanding_bil'].iloc[-1]:,.1f}B")

    write_single_sheet_excel(panel, out / "treasury_duration_analysis.xlsx", sheet_name="DurationAnalysis")

    logger.info(f"[{MANIFEST['id']}] Done. {len(panel)} rows")


if __name__ == "__main__":
    run()
