#!/usr/bin/env python3
"""
P125: Build Auction Panel
Parse treasury auction results into a monthly panel by security type.
Stage: P | ID: P125
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
    "id": "P125",
    "name": "Build Auction Panel",
    "stage": "P",
    "description": "Build monthly treasury auction panel from auction results",
    "depends_on": ["L115"],
    "inputs": [
        {"path": "Technical/data/raw/treasury/auction_results.csv", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/treasury_auction_panel.xlsx"},
    ],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    raw = raw_data_dir() / "treasury"

    # --- Load auction results ---
    logger.info("Loading auction_results.csv...")
    df = pd.read_csv(raw / "auction_results.csv", low_memory=False)
    logger.info(f"Auction raw: {len(df)} rows, security_types: {df['security_type'].unique()}")

    # Parse dates
    for col in ["auction_date", "issue_date", "maturity_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert key numerics
    for col in ["bid_to_cover_ratio", "offering_amt", "total_accepted", "total_tendered",
                 "high_yield", "high_discnt_rate", "price_per100", "int_rate",
                 "comp_accepted", "noncomp_accepted",
                 "direct_bidder_accepted", "indirect_bidder_accepted",
                 "primary_dealer_accepted"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Extract auction month
    df["auction_month"] = df["auction_date"].dt.to_period("M").dt.to_timestamp()

    # --- Aggregate by month x security_type ---
    logger.info("Aggregating by month x security_type...")
    records = []
    for (month, stype), grp in df.groupby(["auction_month", "security_type"]):
        rec = {
            "auction_month": month,
            "security_type": stype,
            "auction_count": len(grp),
            "total_offering_bil": grp["offering_amt"].sum() / 1e9 if grp["offering_amt"].notna().any() else np.nan,
            "total_accepted_bil": grp["total_accepted"].sum() / 1e9 if grp["total_accepted"].notna().any() else np.nan,
            "total_tendered_bil": grp["total_tendered"].sum() / 1e9 if grp["total_tendered"].notna().any() else np.nan,
            "avg_bid_to_cover": grp["bid_to_cover_ratio"].mean() if grp["bid_to_cover_ratio"].notna().any() else np.nan,
            "avg_high_yield": grp["high_yield"].mean() if grp["high_yield"].notna().any() else np.nan,
            "avg_high_discount_rate": grp["high_discnt_rate"].mean() if grp["high_discnt_rate"].notna().any() else np.nan,
        }

        # Bidder composition (where available)
        for bidder_col in ["direct_bidder_accepted", "indirect_bidder_accepted", "primary_dealer_accepted"]:
            if bidder_col in grp.columns and grp[bidder_col].notna().any():
                rec[f"avg_{bidder_col}"] = grp[bidder_col].mean()

        records.append(rec)

    panel = pd.DataFrame(records)
    panel = panel.sort_values(["auction_month", "security_type"]).reset_index(drop=True)

    # Compute aggregate bid-to-cover where total_tendered and total_accepted available
    mask = panel["total_tendered_bil"].notna() & panel["total_accepted_bil"].notna() & (panel["total_accepted_bil"] > 0)
    panel.loc[mask, "implied_bid_to_cover"] = panel.loc[mask, "total_tendered_bil"] / panel.loc[mask, "total_accepted_bil"]

    logger.info(f"Auction panel: {len(panel)} rows, "
                f"months: {panel['auction_month'].min()} to {panel['auction_month'].max()}")
    logger.info(f"Security types: {panel['security_type'].unique().tolist()}")

    write_single_sheet_excel(panel, out / "treasury_auction_panel.xlsx", sheet_name="AuctionPanel")

    logger.info(f"[{MANIFEST['id']}] Done. {len(panel)} rows")


if __name__ == "__main__":
    run()
