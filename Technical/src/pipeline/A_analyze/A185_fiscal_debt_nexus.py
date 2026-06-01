#!/usr/bin/env python3
"""
A185: Fiscal-Debt Nexus
Analyze the relationship between fiscal policy, debt structure, and interest rates.
Stage: A | ID: A185
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, raw_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A185",
    "name": "Fiscal-Debt Nexus",
    "stage": "A",
    "description": "Analyze fiscal-debt-interest rate linkages",
    "depends_on": ["P115", "P120"],
    "inputs": [
        {"path": "Output/Data/treasury_summary_panel.xlsx", "required": True},
        {"path": "Output/Data/yield_curve_monthly.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/fiscal_debt_nexus.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    raw = raw_data_dir() / "treasury"

    # --- Load data ---
    summary = read_excel_safe(out / "treasury_summary_panel.xlsx")
    yc = read_excel_safe(out / "yield_curve_monthly.xlsx")
    fiscal = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if summary.empty or yc.empty:
        logger.error("Required panels are empty")
        return

    summary["record_date"] = pd.to_datetime(summary["record_date"])
    yc["month_end"] = pd.to_datetime(yc["month_end"])

    # --- Merge treasury summary with yield data by month ---
    summary["year_month"] = summary["record_date"].dt.to_period("M")
    yc["year_month"] = yc["month_end"].dt.to_period("M")

    merged = pd.merge(summary, yc, on="year_month", how="inner")
    merged["year"] = merged["record_date"].dt.year
    logger.info(f"Merged treasury-yield: {len(merged)} monthly observations")

    # --- Compute total marketable outstanding ---
    if "total_marketable_mil" in merged.columns:
        merged["total_outstanding_bil"] = merged["total_marketable_mil"] / 1000.0
    else:
        # Reconstruct from components
        out_cols = [c for c in merged.columns if c.endswith("_total_mil")]
        if out_cols:
            merged["total_outstanding_bil"] = merged[out_cols].sum(axis=1) / 1000.0
        else:
            merged["total_outstanding_bil"] = np.nan

    # --- Refinancing risk: load raw data for maturity distribution ---
    logger.info("Computing refinancing risk from raw MSPD data...")
    df_raw = pd.read_csv(raw / "mspd_table_3_market.csv", low_memory=False)
    df_raw["record_date"] = pd.to_datetime(df_raw["record_date"], errors="coerce")
    df_raw["maturity_date"] = pd.to_datetime(df_raw["maturity_date"], errors="coerce")
    df_raw["outstanding_amt"] = pd.to_numeric(df_raw["outstanding_amt"], errors="coerce")

    # For each record_date, compute % maturing within 1yr, 2yr, 5yr
    refin_records = []
    for rd, grp in df_raw.groupby("record_date"):
        grp = grp[grp["outstanding_amt"].notna() & (grp["outstanding_amt"] > 0)].copy()
        if grp.empty:
            continue
        total = grp["outstanding_amt"].sum()
        remaining = (grp["maturity_date"] - rd).dt.days / 365.25

        mat_1y = grp.loc[remaining <= 1, "outstanding_amt"].sum()
        mat_2y = grp.loc[remaining <= 2, "outstanding_amt"].sum()
        mat_5y = grp.loc[remaining <= 5, "outstanding_amt"].sum()

        refin_records.append({
            "record_date": rd,
            "pct_maturing_1yr": (mat_1y / total * 100) if total > 0 else np.nan,
            "pct_maturing_2yr": (mat_2y / total * 100) if total > 0 else np.nan,
            "pct_maturing_5yr": (mat_5y / total * 100) if total > 0 else np.nan,
        })

    refin = pd.DataFrame(refin_records)
    refin["record_date"] = pd.to_datetime(refin["record_date"])
    logger.info(f"Refinancing risk: {len(refin)} date observations")

    # Merge refinancing risk
    merged = pd.merge(merged, refin, on="record_date", how="left")

    # --- Interest rate sensitivity ---
    # Delta interest cost for 100bp shock
    merged["interest_cost_delta_100bp_bil"] = merged["total_outstanding_bil"] * 0.01

    # --- Merge fiscal data (annual, US only) ---
    if not fiscal.empty and "fiscal_balance_pct_gdp" in fiscal.columns:
        us_fiscal = fiscal[fiscal["country_code"] == "USA"][
            ["year", "fiscal_balance_pct_gdp", "debt_pct_gdp", "gdp_current_usd"]
        ].copy()
        us_fiscal["year"] = pd.to_numeric(us_fiscal["year"], errors="coerce")

        # Interest burden proxy: weighted_avg_coupon * total_outstanding / GDP
        merged = pd.merge(merged, us_fiscal, on="year", how="left")

        if "DGS10" in merged.columns and "gdp_current_usd" in merged.columns:
            # Interest burden = avg yield * total debt / GDP
            merged["interest_burden_pct_gdp"] = (
                merged["DGS10"] / 100.0 * merged["total_outstanding_bil"] * 1e9
                / merged["gdp_current_usd"]
                * 100  # as percentage
            )

        # Correlations
        annual = merged.groupby("year").agg({
            "DGS10": "mean",
            "DFF": "mean",
            "fiscal_balance_pct_gdp": "first",
            "total_outstanding_bil": "last",
        }).dropna(subset=["DGS10", "fiscal_balance_pct_gdp"])

        if len(annual) > 5:
            deficit_yield_corr = annual["fiscal_balance_pct_gdp"].corr(annual["DGS10"])
            ff_deficit_corr = annual["fiscal_balance_pct_gdp"].corr(annual["DFF"])
            logger.info(f"Deficit vs 10Y yield correlation: {deficit_yield_corr:.3f} (n={len(annual)})")
            logger.info(f"Fed funds vs fiscal balance correlation: {ff_deficit_corr:.3f}")
    else:
        logger.warning("No fiscal data available")

    # --- Build output ---
    output_cols = ["record_date", "year", "total_outstanding_bil"]

    # Add yield columns
    for yc_col in ["DGS2", "DGS5", "DGS10", "DGS30", "DFF", "term_spread_10y2y"]:
        if yc_col in merged.columns:
            output_cols.append(yc_col)

    # Add refinancing risk
    for rc in ["pct_maturing_1yr", "pct_maturing_2yr", "pct_maturing_5yr"]:
        if rc in merged.columns:
            output_cols.append(rc)

    output_cols.append("interest_cost_delta_100bp_bil")

    # Add fiscal
    for fc in ["fiscal_balance_pct_gdp", "debt_pct_gdp", "interest_burden_pct_gdp"]:
        if fc in merged.columns:
            output_cols.append(fc)

    # Filter to available columns
    output_cols = [c for c in output_cols if c in merged.columns]
    result = merged[output_cols].copy()
    result = result.sort_values("record_date").reset_index(drop=True)

    # Round numerics
    for col in result.select_dtypes(include=[np.number]).columns:
        result[col] = result[col].round(4)

    logger.info(f"Fiscal-debt nexus: {len(result)} rows, {len(result.columns)} columns")
    if "pct_maturing_1yr" in result.columns:
        latest = result.dropna(subset=["pct_maturing_1yr"]).iloc[-1] if result["pct_maturing_1yr"].notna().any() else None
        if latest is not None:
            logger.info(f"Latest refinancing risk: {latest['pct_maturing_1yr']:.1f}% within 1yr, "
                        f"{latest['pct_maturing_2yr']:.1f}% within 2yr")

    write_single_sheet_excel(result, out / "fiscal_debt_nexus.xlsx", sheet_name="FiscalDebtNexus")

    logger.info(f"[{MANIFEST['id']}] Done. {len(result)} rows")


if __name__ == "__main__":
    run()
