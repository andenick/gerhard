#!/usr/bin/env python3
"""
A170: Treasury Market Structure
Analyze composition, size, and maturity trends in the Treasury market.
Uses Table 1 summary (known units: millions) for reliable outstanding amounts,
and security panel for maturity-weighted metrics.
Stage: A | ID: A170
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
    "id": "A170",
    "name": "Treasury Market Structure",
    "stage": "A",
    "description": "Analyze Treasury market size, composition, and maturity trends",
    "depends_on": ["P115"],
    "inputs": [
        {"path": "Output/Data/treasury_security_panel.xlsx", "required": True},
        {"path": "Output/Data/treasury_summary_panel.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/treasury_market_structure.xlsx"},
    ],
    "timeout": 60,
    "parallel_safe": True,
}

# Map Table 1 column prefixes to standardized names
TABLE1_TYPE_MAP = {
    "bills": "bills",
    "notes": "notes",
    "bonds": "bonds",
    "inflation_indexed_notes": "tips_notes",
    "inflation_indexed_bonds": "tips_bonds",
    "treasury_inflation_protected_securities": "tips",
    "floating_rate_notes": "frn",
    "federal_financing_bank": "ffb",
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    # --- Load panels ---
    sec = read_excel_safe(out / "treasury_security_panel.xlsx")
    summary = read_excel_safe(out / "treasury_summary_panel.xlsx")

    if summary.empty:
        logger.error("Summary panel is empty, cannot proceed")
        return

    summary["record_date"] = pd.to_datetime(summary["record_date"])
    summary = summary.sort_values("record_date").reset_index(drop=True)
    logger.info(f"Summary panel: {len(summary)} rows, {len(summary.columns)} columns")
    logger.info(f"Summary columns: {list(summary.columns)}")

    # --- Build market structure from Table 1 summary (reliable units: millions) ---
    result = pd.DataFrame()
    result["record_date"] = summary["record_date"]

    # Find columns for each security type
    total_mil_cols = [c for c in summary.columns if c.endswith("_total_mil")]
    logger.info(f"Found total_mil columns: {total_mil_cols}")

    # Map to standardized types
    for col in total_mil_cols:
        prefix = col.replace("_total_mil", "")
        # Convert to billions
        result[f"{prefix}_outstanding_bil"] = summary[col] / 1000.0

    # TIPS = sum of all inflation-related columns (names changed over time)
    tips_cols = [c for c in result.columns if "inflation" in c and "outstanding" in c]
    if tips_cols:
        result["tips_outstanding_bil"] = result[tips_cols].sum(axis=1, min_count=1)
        # Fill NaN where all components are NaN but keep zeros
        result["tips_outstanding_bil"] = result["tips_outstanding_bil"].fillna(0)

    # Total marketable from Table 1
    if "total_marketable_mil" in summary.columns:
        result["total_outstanding_bil"] = summary["total_marketable_mil"] / 1000.0
    else:
        # Sum components
        out_cols = [c for c in result.columns if c.endswith("_outstanding_bil")
                    and "ffb" not in c and "federal" not in c and "tips_outstanding" not in c
                    and "inflation" not in c]
        if "tips_outstanding_bil" in result.columns:
            out_cols.append("tips_outstanding_bil")
        result["total_outstanding_bil"] = result[out_cols].sum(axis=1)

    # Composition percentages (use standardized names)
    for stype_col in ["bills", "notes", "bonds"]:
        col = f"{stype_col}_outstanding_bil"
        if col in result.columns and "total_outstanding_bil" in result.columns:
            result[f"{stype_col}_pct"] = (
                result[col] / result["total_outstanding_bil"] * 100
            ).round(2)

    if "tips_outstanding_bil" in result.columns:
        result["tips_pct"] = (
            result["tips_outstanding_bil"] / result["total_outstanding_bil"] * 100
        ).round(2)

    frn_col = [c for c in result.columns if "floating" in c and "outstanding" in c]
    if frn_col:
        result["frn_pct"] = (
            result[frn_col[0]] / result["total_outstanding_bil"] * 100
        ).round(2)

    # Weighted average maturity from security panel
    if not sec.empty:
        sec["record_date"] = pd.to_datetime(sec["record_date"])
        mat_data = sec.groupby("record_date").apply(
            lambda g: np.average(
                g["weighted_avg_maturity_years"].dropna(),
                weights=g.loc[g["weighted_avg_maturity_years"].notna(), "total_outstanding_bil"].clip(lower=0)
            ) if g["weighted_avg_maturity_years"].notna().any()
            and (g.loc[g["weighted_avg_maturity_years"].notna(), "total_outstanding_bil"] > 0).any()
            else np.nan,
            include_groups=False,
        )
        mat_df = mat_data.reset_index()
        mat_df.columns = ["record_date", "weighted_avg_maturity_years"]
        result = pd.merge(result, mat_df, on="record_date", how="left")

    # Month-over-month change
    result = result.sort_values("record_date").reset_index(drop=True)
    result["mom_change_bil"] = result["total_outstanding_bil"].diff()
    result["yoy_change_bil"] = result["total_outstanding_bil"].diff(12)

    logger.info(f"Market structure: {len(result)} rows")
    if "total_outstanding_bil" in result.columns:
        latest_total = result["total_outstanding_bil"].iloc[-1]
        logger.info(f"Latest total outstanding: ${latest_total:,.1f}B (${latest_total/1000:.1f}T)")
    logger.info(f"Date range: {result['record_date'].min().date()} to {result['record_date'].max().date()}")

    # Log composition at latest date
    latest = result.iloc[-1]
    for stype in ["bills", "notes", "bonds", "tips", "frn"]:
        pct_col = f"{stype}_pct"
        if pct_col in latest.index and pd.notna(latest[pct_col]):
            logger.info(f"  {stype.upper()}: {latest[pct_col]:.1f}%")

    write_single_sheet_excel(result, out / "treasury_market_structure.xlsx", sheet_name="MarketStructure")

    logger.info(f"[{MANIFEST['id']}] Done. {len(result)} rows")


if __name__ == "__main__":
    run()
