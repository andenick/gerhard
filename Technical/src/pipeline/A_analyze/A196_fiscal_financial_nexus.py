#!/usr/bin/env python3
"""
A196: Fiscal-Financial Nexus
Analyze credit gaps, bank exposure to government, financial depth vs tax capacity,
NPL-deficit correlation, and reserve adequacy.
Stage: A | ID: A196
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

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A196",
    "name": "Fiscal-Financial Nexus",
    "stage": "A",
    "description": "Credit gaps, crowding out, financial depth vs tax capacity, NPL-deficit link",
    "depends_on": ["P76"],
    "inputs": [
        {"path": "Output/Data/financial_sector_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/fiscal_financial_nexus.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    fin = read_excel_safe(out / "financial_sector_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if fin.empty or master.empty:
        logger.error("Required panels missing; aborting.")
        return

    # Merge financial with fiscal
    merge_key = ["country_code", "year"]
    fiscal_cols = ["country_code", "year", "tax_revenue_pct_gdp", "expenditure_pct_gdp",
                   "fiscal_balance_pct_gdp", "debt_pct_gdp", "income_group", "region"]
    fiscal_avail = [c for c in fiscal_cols if c in master.columns]
    df = fin.merge(master[fiscal_avail].drop_duplicates(merge_key), on=merge_key, how="left")

    logger.info(f"Merged panel: {len(df)} rows, {df['country_code'].nunique()} countries")

    sheets = {}

    # ── 1. Credit-to-GDP gap: deviation from 10-year moving average ──
    logger.info("1. Credit-to-GDP gap (early warning)...")
    credit_col = None
    for c in ["domestic_credit_financial_pct_gdp", "domestic_credit_private_pct_gdp"]:
        if c in df.columns:
            credit_col = c
            break

    if credit_col:
        df = df.sort_values(["country_code", "year"])
        df["credit_10y_ma"] = (
            df.groupby("country_code")[credit_col]
            .transform(lambda x: x.rolling(10, min_periods=5).mean())
        )
        mask = df[credit_col].notna() & df["credit_10y_ma"].notna()
        df.loc[mask, "credit_gap"] = df.loc[mask, credit_col] - df.loc[mask, "credit_10y_ma"]

        # Country-level credit gap summary (latest available)
        gap_latest = (
            df.dropna(subset=["credit_gap"])
            .sort_values("year")
            .groupby("country_code")
            .last()
            .reset_index()
        )
        gap_summary = gap_latest[["country_code", "year", credit_col, "credit_10y_ma",
                                   "credit_gap", "income_group"]].copy()
        gap_summary = gap_summary.sort_values("credit_gap", ascending=False)
        sheets["credit_gap"] = gap_summary
        logger.info(f"  Credit gap: {len(gap_summary)} countries, "
                    f"top gap: {gap_summary['credit_gap'].max():.1f}pp")

    # ── 2. Bank exposure to government: crowding_out_ratio by income group ──
    logger.info("2. Bank exposure to government...")
    if "crowding_out_ratio" in df.columns and "income_group" in df.columns:
        crowding = (
            df.dropna(subset=["crowding_out_ratio", "income_group"])
            .groupby(["income_group", "year"])
            .agg(
                mean_crowding=("crowding_out_ratio", "mean"),
                median_crowding=("crowding_out_ratio", "median"),
                n_countries=("country_code", "nunique"),
            )
            .reset_index()
        )
        sheets["crowding_out"] = crowding
        logger.info(f"  Crowding out: {len(crowding)} group-year obs")

    # ── 3. Financial depth vs tax capacity ──
    logger.info("3. Financial depth vs tax capacity...")
    if "financial_depth_index" in df.columns and "tax_revenue_pct_gdp" in df.columns:
        valid = df.dropna(subset=["financial_depth_index", "tax_revenue_pct_gdp"])
        if len(valid) > 10:
            # Cross-sectional regression (latest year per country)
            latest = valid.sort_values("year").groupby("country_code").last().reset_index()
            corr = latest["financial_depth_index"].corr(latest["tax_revenue_pct_gdp"])

            # Simple OLS
            x = latest["financial_depth_index"]
            y = latest["tax_revenue_pct_gdp"]
            x_dm = x - x.mean()
            beta = (x_dm * (y - y.mean())).sum() / (x_dm ** 2).sum()
            alpha = y.mean() - beta * x.mean()

            depth_tax = latest[["country_code", "income_group", "year",
                                "financial_depth_index", "tax_revenue_pct_gdp"]].copy()
            depth_tax["predicted_tax"] = alpha + beta * depth_tax["financial_depth_index"]
            depth_tax["residual"] = depth_tax["tax_revenue_pct_gdp"] - depth_tax["predicted_tax"]
            depth_tax = depth_tax.sort_values("residual", ascending=False)
            sheets["depth_vs_tax"] = depth_tax
            logger.info(f"  Depth-tax correlation: {corr:.3f}, beta={beta:.4f}, "
                        f"n={len(latest)} countries")

    # ── 4. NPL-deficit correlation ──
    logger.info("4. NPL-deficit correlation...")
    npl_col = None
    for c in ["bank_npl_pct", "npl_pct_gross_loans"]:
        if c in df.columns:
            npl_col = c
            break

    if npl_col and "fiscal_balance_pct_gdp" in df.columns:
        valid = df.dropna(subset=[npl_col, "fiscal_balance_pct_gdp"])
        if len(valid) > 10:
            corr = valid[npl_col].corr(valid["fiscal_balance_pct_gdp"])
            logger.info(f"  NPL-fiscal balance correlation: {corr:.3f} (n={len(valid)})")

            # By income group
            npl_deficit = (
                valid.dropna(subset=["income_group"])
                .groupby("income_group")
                .apply(
                    lambda g: pd.Series({
                        "npl_deficit_corr": g[npl_col].corr(g["fiscal_balance_pct_gdp"]),
                        "mean_npl": g[npl_col].mean(),
                        "mean_deficit": g["fiscal_balance_pct_gdp"].mean(),
                        "n_obs": len(g),
                    })
                )
                .reset_index()
            )
            sheets["npl_deficit"] = npl_deficit

    # ── 5. Reserve adequacy by income group ──
    logger.info("5. Reserve adequacy...")
    reserve_col = None
    for c in ["reserves_months_imports", "total_reserves_months_imports"]:
        if c in df.columns:
            reserve_col = c
            break

    if reserve_col and "income_group" in df.columns:
        reserves = (
            df.dropna(subset=[reserve_col, "income_group"])
            .groupby(["income_group", "year"])
            .agg(
                mean_reserves_months=pd.NamedAgg(column=reserve_col, aggfunc="mean"),
                median_reserves_months=pd.NamedAgg(column=reserve_col, aggfunc="median"),
                pct_below_3m=pd.NamedAgg(
                    column=reserve_col,
                    aggfunc=lambda x: (x < 3).mean() * 100,
                ),
                n_countries=pd.NamedAgg(column="country_code", aggfunc="nunique"),
            )
            .reset_index()
        )
        sheets["reserve_adequacy"] = reserves
        logger.info(f"  Reserve adequacy: {len(reserves)} group-year obs")

    # --- Write output ---
    if not sheets:
        logger.error("No analysis sheets produced; aborting.")
        return

    filepath = out / "fiscal_financial_nexus.xlsx"
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
