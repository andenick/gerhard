#!/usr/bin/env python3
"""
A202: US Fiscal Deep Dive
Comprehensive US-only analysis: income statement, interest cost, yield curve
vs deficit, refinancing risk, and Fed balance sheet impact.
Stage: A | ID: A202
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

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A202",
    "name": "US Fiscal Deep Dive",
    "stage": "A",
    "description": "Full US income statement, interest cost, yield-deficit, refinancing risk",
    "depends_on": ["P106", "P108", "P111"],
    "inputs": [
        {"path": "Output/Data/us_mts_panel.xlsx", "required": True},
        {"path": "Output/Data/treasury_interest_rates_panel.xlsx", "required": False},
        {"path": "Output/Data/us_monetary_panel.xlsx", "required": False},
        {"path": "Output/Data/treasury_security_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/us_fiscal_deep_dive.xlsx"},
    ],
    "timeout": 180,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    raw = raw_data_dir() / "treasury"

    mts = read_excel_safe(out / "us_mts_panel.xlsx")
    rates = read_excel_safe(out / "treasury_interest_rates_panel.xlsx")
    monetary = read_excel_safe(out / "us_monetary_panel.xlsx")
    treasury = read_excel_safe(out / "treasury_security_panel.xlsx")

    if mts.empty:
        logger.error("Cannot load us_mts_panel.xlsx; aborting.")
        return

    mts["record_date"] = pd.to_datetime(mts["record_date"])

    sheets = {}

    # ── 1. Full income statement: monthly receipts/outlays ──
    logger.info("1. US fiscal income statement...")
    receipt_cols = [c for c in mts.columns if c.startswith("monthly_") and "receipt" in c.lower()]
    outlay_cols = [c for c in mts.columns if c.startswith("monthly_") and "outlay" in c.lower()]

    # Also check for generic monthly_ columns
    if not receipt_cols and not outlay_cols:
        all_monthly = [c for c in mts.columns if c.startswith("monthly_")]
        logger.info(f"  Found {len(all_monthly)} monthly columns")
        receipt_cols = all_monthly[:len(all_monthly)//2]
        outlay_cols = all_monthly[len(all_monthly)//2:]

    income_stmt = mts[["record_date", "year", "month"] +
                      [c for c in receipt_cols + outlay_cols if c in mts.columns]].copy()

    # Add total receipts and outlays if available
    if "fytd_net_receipts" in mts.columns:
        income_stmt["fytd_net_receipts"] = mts["fytd_net_receipts"]

    sheets["income_statement"] = income_stmt
    logger.info(f"  Income statement: {len(income_stmt)} months, "
                f"{len(income_stmt.columns)} columns")

    # ── 2. Interest cost as % of receipts ──
    logger.info("2. Interest cost analysis...")
    # Look for interest-related columns in MTS
    interest_cols = [c for c in mts.columns if "interest" in c.lower()]
    receipt_total_cols = [c for c in mts.columns if "total" in c.lower() and "receipt" in c.lower()]

    # If we have interest rate panel, merge with MTS
    if not rates.empty:
        rates["record_date"] = pd.to_datetime(rates["record_date"])
        rates_slim = rates[["record_date"] + [c for c in rates.columns
                            if c.startswith("rate_") or c.endswith("_spread")]].copy()
        rates_slim["year_month"] = rates_slim["record_date"].dt.to_period("M")
        mts_r = mts.copy()
        mts_r["year_month"] = mts_r["record_date"].dt.to_period("M")
        merged = mts_r.merge(rates_slim.drop(columns=["record_date"]), on="year_month", how="left")

        interest_cost = merged[["record_date", "year", "month"] +
                               [c for c in merged.columns if c.startswith("rate_") or
                                "interest" in c.lower() or c.endswith("_spread")]].copy()
        sheets["interest_cost"] = interest_cost
        logger.info(f"  Interest cost: {len(interest_cost)} rows")

    # ── 3. Yield curve shape vs fiscal deficit correlation ──
    logger.info("3. Yield curve vs deficit...")
    yc = read_excel_safe(out / "yield_curve_monthly.xlsx")
    if not yc.empty:
        yc["month_end"] = pd.to_datetime(yc["month_end"])
        master = read_excel_safe(out / "master_fiscal_panel.xlsx")
        if not master.empty:
            us_fiscal = master[master["country_code"] == "USA"][
                ["year", "fiscal_balance_pct_gdp", "debt_pct_gdp"]
            ].dropna(subset=["fiscal_balance_pct_gdp"])

            yc_annual = yc.copy()
            yc_annual["year"] = yc_annual["month_end"].dt.year
            yc_agg = yc_annual.groupby("year").agg({
                col: "mean" for col in yc_annual.columns
                if col in ["DGS2", "DGS5", "DGS10", "DGS30", "DFF",
                           "term_spread_10y2y", "term_spread_10y3m"]
            }).reset_index()

            yc_fiscal = yc_agg.merge(us_fiscal, on="year", how="inner")
            if len(yc_fiscal) > 5:
                if "term_spread_10y2y" in yc_fiscal.columns:
                    corr = yc_fiscal["term_spread_10y2y"].corr(yc_fiscal["fiscal_balance_pct_gdp"])
                    logger.info(f"  Term spread vs deficit corr: {corr:.3f}")
                if "DGS10" in yc_fiscal.columns:
                    corr10 = yc_fiscal["DGS10"].corr(yc_fiscal["fiscal_balance_pct_gdp"])
                    logger.info(f"  10Y yield vs deficit corr: {corr10:.3f}")
                sheets["yield_deficit"] = yc_fiscal

    # ── 4. Refinancing risk from MSPD ──
    logger.info("4. Refinancing risk...")
    mspd_file = raw / "mspd_table_3_market.csv"
    if mspd_file.exists():
        try:
            df_raw = pd.read_csv(mspd_file, low_memory=False)
            df_raw["record_date"] = pd.to_datetime(df_raw["record_date"], errors="coerce")
            df_raw["maturity_date"] = pd.to_datetime(df_raw["maturity_date"], errors="coerce")
            df_raw["outstanding_amt"] = pd.to_numeric(df_raw["outstanding_amt"], errors="coerce")

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
                    "total_outstanding_bil": total / 1000,
                    "pct_maturing_1yr": (mat_1y / total * 100) if total > 0 else np.nan,
                    "pct_maturing_2yr": (mat_2y / total * 100) if total > 0 else np.nan,
                    "pct_maturing_5yr": (mat_5y / total * 100) if total > 0 else np.nan,
                    "amount_maturing_1yr_bil": mat_1y / 1000,
                })

            refin = pd.DataFrame(refin_records).sort_values("record_date")
            sheets["refinancing_risk"] = refin
            if not refin.empty:
                latest = refin.iloc[-1]
                logger.info(f"  Refinancing: {latest['pct_maturing_1yr']:.1f}% within 1yr, "
                            f"${latest['amount_maturing_1yr_bil']:.0f}B")
        except Exception as e:
            logger.warning(f"  MSPD processing error: {e}")
    else:
        logger.warning("  MSPD raw data not found")

    # ── 5. Fed balance sheet impact on effective borrowing cost ──
    logger.info("5. Fed balance sheet impact...")
    if not monetary.empty and not rates.empty:
        mon = monetary.copy()
        if "date" in mon.columns:
            mon["date"] = pd.to_datetime(mon["date"])
            mon["year_month"] = mon["date"].dt.to_period("M")
        rates_m = rates.copy()
        rates_m["record_date"] = pd.to_datetime(rates_m["record_date"])
        rates_m["year_month"] = rates_m["record_date"].dt.to_period("M")

        fed_cols = ["year_month"]
        for c in ["WALCL", "WTREGEN", "Fed_treasury_pct"]:
            if c in mon.columns:
                fed_cols.append(c)

        rate_cols = ["year_month"]
        for c in rates_m.columns:
            if c.startswith("rate_") or c == "weighted_avg_rate":
                rate_cols.append(c)

        if len(fed_cols) > 1 and len(rate_cols) > 1:
            merged = mon[fed_cols].merge(rates_m[rate_cols], on="year_month", how="inner")
            if not merged.empty:
                sheets["fed_impact"] = merged
                logger.info(f"  Fed impact: {len(merged)} months")

    # --- Write output ---
    if not sheets:
        logger.error("No analysis sheets produced; aborting.")
        return

    filepath = out / "us_fiscal_deep_dive.xlsx"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets.items():
            for col in sheet_df.select_dtypes(include=[np.number]).columns:
                sheet_df[col] = sheet_df[col].round(4)
            sheet_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    total_rows = sum(len(s) for s in sheets.values())
    logger.info(f"[{MANIFEST['id']}] Done. {len(sheets)} sheets, {total_rows} total rows")


if __name__ == "__main__":
    run()
