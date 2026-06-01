#!/usr/bin/env python3
"""
A192: Income Structure Analysis
Deep analysis of tax-to-GNI vs GDP, revenue diversification, social contributions,
and non-tax revenue importance by income group.
Stage: A | ID: A192
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
    "id": "A192",
    "name": "Income Structure Analysis",
    "stage": "A",
    "description": "Deep analysis of revenue structure by income group and over time",
    "depends_on": ["P78", "P65"],
    "inputs": [
        {"path": "Output/Data/income_panel.xlsx", "required": True},
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/income_structure_deep.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    income = read_excel_safe(out / "income_panel.xlsx")
    rev = read_excel_safe(out / "revenue_composition_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if income.empty or rev.empty or master.empty:
        logger.error("Required panels missing; aborting.")
        return

    # Get income_group mapping from master
    ig_map = master.drop_duplicates("country_code")[["country_code", "income_group"]].dropna(subset=["income_group"])

    sheets = {}

    # ── 1. Tax-to-GNI vs Tax-to-GDP comparison ──
    logger.info("1. Tax-to-GNI vs Tax-to-GDP comparison...")
    merged = rev.merge(income[["country_code", "year", "gni_current_usd", "gni_gdp_ratio"]].dropna(subset=["gni_gdp_ratio"]),
                       on=["country_code", "year"], how="inner")
    if not merged.empty and "tax_revenue_pct_gdp" in merged.columns:
        merged["tax_to_gni"] = merged["tax_revenue_pct_gdp"] / merged["gni_gdp_ratio"]
        merged["gni_gdp_gap"] = merged["tax_to_gni"] - merged["tax_revenue_pct_gdp"]
        merged = merged.merge(ig_map, on="country_code", how="left")

        tax_comparison = merged.groupby("income_group").agg(
            n_obs=("gni_gdp_gap", "count"),
            mean_tax_gdp=("tax_revenue_pct_gdp", "mean"),
            mean_tax_gni=("tax_to_gni", "mean"),
            mean_gap=("gni_gdp_gap", "mean"),
        ).reset_index()
        sheets["tax_gni_vs_gdp"] = tax_comparison
        logger.info(f"  Tax-GNI vs GDP: {len(merged)} obs, gap range "
                    f"{merged['gni_gdp_gap'].min():.2f} to {merged['gni_gdp_gap'].max():.2f}")
    else:
        logger.warning("  Cannot compute tax-GNI comparison")

    # ── 2. Revenue diversification trends by income group ──
    logger.info("2. Revenue diversification trends...")
    rev_ig = rev.merge(ig_map, on="country_code", how="left")
    if "tax_diversification_index" in rev_ig.columns:
        div_trends = (
            rev_ig.dropna(subset=["tax_diversification_index", "income_group"])
            .groupby(["income_group", "year"])
            .agg(
                mean_diversification=("tax_diversification_index", "mean"),
                median_diversification=("tax_diversification_index", "median"),
                n_countries=("country_code", "nunique"),
            )
            .reset_index()
        )
        sheets["diversification_trends"] = div_trends
        logger.info(f"  Diversification trends: {len(div_trends)} group-year obs")

    # ── 3. Social contribution importance by income group ──
    logger.info("3. Social contribution importance...")
    if "social_contributions_pct_revenue" in rev_ig.columns:
        social_by_ig = (
            rev_ig.dropna(subset=["social_contributions_pct_revenue", "income_group"])
            .groupby(["income_group", "year"])
            .agg(
                mean_social_contrib=("social_contributions_pct_revenue", "mean"),
                n_countries=("country_code", "nunique"),
            )
            .reset_index()
        )
        sheets["social_contributions"] = social_by_ig
        logger.info(f"  Social contributions: {len(social_by_ig)} group-year obs")
    else:
        logger.warning("  social_contributions_pct_revenue not available")

    # ── 4. Non-tax revenue importance ──
    logger.info("4. Non-tax revenue importance...")
    if "revenue_excl_grants_pct_gdp" in rev_ig.columns and "tax_revenue_pct_gdp" in rev_ig.columns:
        mask = (
            rev_ig["revenue_excl_grants_pct_gdp"].notna()
            & rev_ig["tax_revenue_pct_gdp"].notna()
            & (rev_ig["revenue_excl_grants_pct_gdp"] > 0)
        )
        rev_ig.loc[mask, "non_tax_pct_revenue"] = (
            (rev_ig.loc[mask, "revenue_excl_grants_pct_gdp"] - rev_ig.loc[mask, "tax_revenue_pct_gdp"])
            / rev_ig.loc[mask, "revenue_excl_grants_pct_gdp"] * 100
        )
        nontax_by_ig = (
            rev_ig.dropna(subset=["non_tax_pct_revenue", "income_group"])
            .groupby(["income_group", "year"])
            .agg(
                mean_nontax_share=("non_tax_pct_revenue", "mean"),
                n_countries=("country_code", "nunique"),
            )
            .reset_index()
        )
        sheets["non_tax_revenue"] = nontax_by_ig
        logger.info(f"  Non-tax revenue: {len(nontax_by_ig)} group-year obs")

    # --- Build combined output ---
    if not sheets:
        logger.error("No analysis sheets produced; aborting.")
        return

    # Use the largest sheet as the primary output
    primary_key = max(sheets, key=lambda k: len(sheets[k]))
    result = sheets[primary_key]

    # Write all sheets into one file
    filepath = out / "income_structure_deep.xlsx"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    total_rows = sum(len(s) for s in sheets.values())
    logger.info(f"[{MANIFEST['id']}] Done. {len(sheets)} sheets, {total_rows} total rows")


if __name__ == "__main__":
    run()
