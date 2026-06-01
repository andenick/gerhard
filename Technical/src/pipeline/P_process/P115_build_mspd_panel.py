#!/usr/bin/env python3
"""
P115: Build MSPD Panel
Parse MSPD Table 3 (market securities) and Table 1 (summary) into analytical panels.
Stage: P | ID: P115
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
    "id": "P115",
    "name": "Build MSPD Panel",
    "stage": "P",
    "description": "Build treasury security panel from MSPD Table 3 and summary from Table 1",
    "depends_on": ["L105"],
    "inputs": [
        {"path": "Technical/data/raw/treasury/mspd_table_3_market.csv", "required": True},
        {"path": "Technical/data/raw/treasury/mspd_table_1.csv", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/treasury_security_panel.xlsx"},
        {"path": "Output/Data/treasury_summary_panel.xlsx"},
    ],
    "timeout": 120,
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
    "Federal Financing Bank": "FFB",
    "Total Marketable": None,  # Exclude aggregates
}


def classify_security(class1_desc: str) -> str:
    """Map security_class1_desc to standardized type."""
    return SECURITY_TYPE_MAP.get(class1_desc, "Other")


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    raw = raw_data_dir() / "treasury"

    # --- Load Table 3 (security detail) ---
    logger.info("Loading mspd_table_3_market.csv...")
    df = pd.read_csv(raw / "mspd_table_3_market.csv", low_memory=False)
    logger.info(f"Table 3 raw: {len(df)} rows, columns: {list(df.columns)}")

    # Parse dates
    for col in ["record_date", "issue_date", "maturity_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Convert numerics
    for col in ["interest_rate_pct", "yield_pct", "outstanding_amt", "issued_amt"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Classify security type
    df["security_type"] = df["security_class1_desc"].map(classify_security)

    # Drop aggregate rows and FFB
    df = df[df["security_type"].notna() & (df["security_type"] != "FFB")].copy()
    logger.info(f"After classification filter: {len(df)} rows")

    # Compute remaining maturity
    df["remaining_maturity_years"] = (
        (df["maturity_date"] - df["record_date"]).dt.days / 365.25
    )

    # --- Aggregate by record_date x security_type ---
    logger.info("Aggregating by record_date x security_type...")

    def weighted_avg(group, value_col, weight_col):
        """Compute weighted average, handling NaNs."""
        mask = group[value_col].notna() & group[weight_col].notna() & (group[weight_col] > 0)
        if mask.sum() == 0:
            return np.nan
        vals = group.loc[mask, value_col]
        wts = group.loc[mask, weight_col]
        return np.average(vals, weights=wts)

    records = []
    for (rd, st), grp in df.groupby(["record_date", "security_type"]):
        records.append({
            "record_date": rd,
            "security_type": st,
            "count_securities": len(grp),
            "total_outstanding_mil": grp["outstanding_amt"].sum(),
            "weighted_avg_coupon": weighted_avg(grp, "interest_rate_pct", "outstanding_amt"),
            "weighted_avg_yield": weighted_avg(grp, "yield_pct", "outstanding_amt"),
            "weighted_avg_maturity_years": weighted_avg(grp, "remaining_maturity_years", "outstanding_amt"),
        })

    panel = pd.DataFrame(records)
    panel = panel.sort_values(["record_date", "security_type"]).reset_index(drop=True)

    # Convert outstanding to billions for readability
    panel["total_outstanding_bil"] = panel["total_outstanding_mil"] / 1000.0

    logger.info(f"Security panel: {len(panel)} rows, "
                f"dates: {panel['record_date'].min().date()} to {panel['record_date'].max().date()}")

    write_single_sheet_excel(panel, out / "treasury_security_panel.xlsx", sheet_name="SecurityPanel")

    # --- Load Table 1 (summary totals) ---
    logger.info("Loading mspd_table_1.csv...")
    t1 = pd.read_csv(raw / "mspd_table_1.csv")
    t1["record_date"] = pd.to_datetime(t1["record_date"], errors="coerce")
    for col in ["debt_held_public_mil_amt", "intragov_hold_mil_amt", "total_mil_amt"]:
        t1[col] = pd.to_numeric(t1[col], errors="coerce")

    # Pivot to wide: one row per record_date with columns for each security class
    # Focus on the marketable breakdown
    mkt = t1[t1["security_type_desc"] == "Marketable"].copy()
    summary_records = []
    for rd, grp in mkt.groupby("record_date"):
        row = {"record_date": rd}
        for _, r in grp.iterrows():
            cls = r["security_class_desc"]
            if cls == "_":
                continue
            prefix = cls.lower().replace(" ", "_").replace("-", "_")
            row[f"{prefix}_total_mil"] = r["total_mil_amt"]
            row[f"{prefix}_public_mil"] = r["debt_held_public_mil_amt"]
        summary_records.append(row)

    summary = pd.DataFrame(summary_records).sort_values("record_date").reset_index(drop=True)

    # Add total marketable row
    totals = t1[t1["security_class_desc"] == "_"].copy()
    totals = totals[totals["security_type_desc"] == "Total Marketable"]
    if not totals.empty:
        totals_map = totals.set_index("record_date")["total_mil_amt"].to_dict()
        summary["total_marketable_mil"] = summary["record_date"].map(totals_map)

    logger.info(f"Summary panel: {len(summary)} rows, "
                f"{len(summary.columns)} columns")

    write_single_sheet_excel(summary, out / "treasury_summary_panel.xlsx", sheet_name="SummaryPanel")

    logger.info(f"[{MANIFEST['id']}] Done. Security panel: {len(panel)} rows, Summary: {len(summary)} rows")


if __name__ == "__main__":
    run()
