#!/usr/bin/env python3
"""
A190: Income-Expenditure Ratios
The core ratio engine: compute fiscal, interest, debt, revenue, spending, and
financial-fiscal ratios across all country-years.
Stage: A | ID: A190
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
    "id": "A190",
    "name": "Income-Expenditure Ratios",
    "stage": "A",
    "description": "Core ratio engine for fiscal, interest, debt, revenue, spending ratios",
    "depends_on": ["P76", "P77", "P78"],
    "inputs": [
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/financial_sector_panel.xlsx", "required": False},
        {"path": "Output/Data/expenditure_functions_panel.xlsx", "required": False},
        {"path": "Output/Data/income_panel.xlsx", "required": False},
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": False},
        {"path": "Output/Data/expenditure_composition_panel.xlsx", "required": False},
        {"path": "Output/Data/debt_composition_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/fiscal_ratios_panel.xlsx"},
    ],
    "timeout": 180,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    # --- Load all panels ---
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    if master.empty:
        logger.error("Cannot load master_fiscal_panel.xlsx; aborting.")
        return

    financial = read_excel_safe(out / "financial_sector_panel.xlsx")
    exp_func = read_excel_safe(out / "expenditure_functions_panel.xlsx")
    income = read_excel_safe(out / "income_panel.xlsx")
    rev_comp = read_excel_safe(out / "revenue_composition_panel.xlsx")
    exp_comp = read_excel_safe(out / "expenditure_composition_panel.xlsx")
    debt_comp = read_excel_safe(out / "debt_composition_panel.xlsx")

    logger.info(f"Master: {len(master)} rows, {master['country_code'].nunique()} countries")

    # --- Start with master as base ---
    df = master.copy()

    # --- Merge supplementary panels ---
    merge_key = ["country_code", "year"]
    skip_cols = {"country_code", "country_name", "year", "region", "income_group"}

    for name, panel in [
        ("financial_sector", financial),
        ("expenditure_functions", exp_func),
        ("income", income),
        ("revenue_composition", rev_comp),
        ("expenditure_composition", exp_comp),
        ("debt_composition", debt_comp),
    ]:
        if panel.empty:
            logger.warning(f"  {name} panel empty, skipping")
            continue
        # Only merge columns not already in df
        new_cols = [c for c in panel.columns if c not in df.columns and c not in skip_cols]
        if not new_cols:
            logger.info(f"  {name}: no new columns to merge")
            continue
        slim = panel[list(merge_key) + new_cols].copy()
        pre = len(df)
        df = df.merge(slim, on=merge_key, how="left")
        matched = df[new_cols[0]].notna().sum() if new_cols else 0
        logger.info(f"  Merged {name}: +{len(new_cols)} cols, {matched} matched rows")

    # --- Compute fiscal ratios ---
    logger.info("Computing fiscal ratios...")

    # Fiscal ratios (some already exist)
    df["tax_burden"] = df.get("tax_revenue_pct_gdp", pd.Series(np.nan, index=df.index))
    df["spending_intensity"] = df.get("expenditure_pct_gdp", pd.Series(np.nan, index=df.index))
    if "tax_revenue_pct_gdp" in df.columns and "expenditure_pct_gdp" in df.columns:
        mask = df["tax_revenue_pct_gdp"].notna() & df["expenditure_pct_gdp"].notna()
        df["fiscal_balance"] = np.where(
            mask, df["tax_revenue_pct_gdp"] - df["expenditure_pct_gdp"], np.nan
        )
        logger.info(f"  fiscal_balance: {mask.sum()} rows")

    # Interest burden (from expenditure_composition)
    if "interest_pct_expense" in df.columns and "total_expense_pct_gdp" in df.columns:
        mask = df["interest_pct_expense"].notna() & df["total_expense_pct_gdp"].notna()
        df["interest_pct_gdp"] = np.where(
            mask,
            df["interest_pct_expense"] / 100 * df["total_expense_pct_gdp"],
            np.nan,
        )
        logger.info(f"  interest_pct_gdp: {mask.sum()} rows")

        if "tax_revenue_pct_gdp" in df.columns:
            mask2 = df["interest_pct_gdp"].notna() & df["tax_revenue_pct_gdp"].notna() & (df["tax_revenue_pct_gdp"] > 0)
            df["interest_pct_revenue"] = np.where(
                mask2,
                df["interest_pct_gdp"] / df["tax_revenue_pct_gdp"] * 100,
                np.nan,
            )
            logger.info(f"  interest_pct_revenue: {mask2.sum()} rows")

    # Primary balance
    if "fiscal_balance" in df.columns:
        interest_gdp = df.get("interest_pct_gdp", pd.Series(0, index=df.index)).fillna(0)
        df["primary_balance_pct_gdp"] = np.where(
            df["fiscal_balance"].notna(),
            df["fiscal_balance"].astype(float) + interest_gdp.astype(float),
            np.nan,
        )
        n = df["primary_balance_pct_gdp"].notna().sum()
        logger.info(f"  primary_balance_pct_gdp: {n} rows")

    # Debt ratios
    if "debt_pct_gdp" in df.columns and "tax_revenue_pct_gdp" in df.columns:
        mask = df["debt_pct_gdp"].notna() & df["tax_revenue_pct_gdp"].notna() & (df["tax_revenue_pct_gdp"] > 0)
        df["debt_to_revenue"] = np.where(
            mask,
            df["debt_pct_gdp"] / df["tax_revenue_pct_gdp"],
            np.nan,
        )
        logger.info(f"  debt_to_revenue: {mask.sum()} rows")

    # Revenue structure
    df["direct_tax_share"] = df.get("income_tax_pct_revenue", pd.Series(np.nan, index=df.index))
    df["indirect_tax_share"] = df.get("goods_services_tax_pct_revenue", pd.Series(np.nan, index=df.index))

    # Spending priorities (from expenditure_functions)
    edu_gdp = df.get("education_pct_gdp", pd.Series(0, index=df.index)).fillna(0)
    health_gdp = df.get("health_govt_pct_gdp", pd.Series(0, index=df.index)).fillna(0)
    has_social = (
        df.get("education_pct_gdp", pd.Series(np.nan, index=df.index)).notna()
        | df.get("health_govt_pct_gdp", pd.Series(np.nan, index=df.index)).notna()
    )
    df["social_spending_pct_gdp"] = np.where(has_social, edu_gdp + health_gdp, np.nan)

    if "military_pct_gdp" in df.columns:
        social_safe = pd.to_numeric(df["social_spending_pct_gdp"], errors="coerce").replace(0, np.nan)
        mask = df["military_pct_gdp"].notna() & social_safe.notna()
        df["guns_butter"] = np.where(mask, df["military_pct_gdp"] / social_safe, np.nan)
        logger.info(f"  guns_butter: {mask.sum()} rows")

    # Financial-fiscal (from financial_sector)
    df["govt_crowding_pct"] = df.get("crowding_out_ratio", pd.Series(np.nan, index=df.index))
    df["financial_depth"] = df.get("financial_depth_index", pd.Series(np.nan, index=df.index))

    # Income (from income_panel)
    df["gni_gdp_ratio"] = df.get("gni_gdp_ratio", pd.Series(np.nan, index=df.index))
    df["savings_gap"] = df.get("savings_investment_gap", pd.Series(np.nan, index=df.index))

    # --- Summary statistics ---
    ratio_cols = [
        "tax_burden", "spending_intensity", "fiscal_balance", "interest_pct_gdp",
        "interest_pct_revenue", "primary_balance_pct_gdp", "debt_to_revenue",
        "direct_tax_share", "indirect_tax_share", "social_spending_pct_gdp",
        "guns_butter", "govt_crowding_pct", "financial_depth", "gni_gdp_ratio",
        "savings_gap",
    ]
    available_ratios = [c for c in ratio_cols if c in df.columns]
    logger.info(f"\nRatio coverage summary ({len(available_ratios)} ratios):")
    for col in available_ratios:
        n = df[col].notna().sum()
        if n > 0:
            logger.info(f"  {col}: {n} rows, mean={df[col].mean():.2f}, median={df[col].median():.2f}")

    # --- Round and save ---
    for col in df.select_dtypes(include=[np.number]).columns:
        df[col] = df[col].round(4)

    df = df.sort_values(["country_code", "year"]).reset_index(drop=True)

    write_single_sheet_excel(df, out / "fiscal_ratios_panel.xlsx", sheet_name="FiscalRatios")
    logger.info(f"[{MANIFEST['id']}] Done. {len(df)} rows, {len(df.columns)} cols, "
                f"{df['country_code'].nunique()} countries")


if __name__ == "__main__":
    run()
