#!/usr/bin/env python3
"""
A125: Inequality-Fiscal Nexus
Analyze tax-Gini, social spending-poverty, HDI-tax, and income group summary.
Stage: A | ID: A125
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A125",
    "name": "Inequality-Fiscal Nexus",
    "stage": "A",
    "description": "Analyze tax-Gini, social spending-poverty, HDI-tax, and income group summary",
    "depends_on": ["P95"],
    "inputs": [
        {"path": "Output/Data/social_outcomes_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/expenditure_composition_panel.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/inequality_fiscal_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    social = read_excel_safe(out / "social_outcomes_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    expenditure = read_excel_safe(out / "expenditure_composition_panel.xlsx")

    if social.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    logger.info(f"Social panel: {len(social)} rows, {social['country_code'].nunique()} countries")

    # Merge fiscal data with social
    fiscal_cols = ["country_code", "year", "tax_revenue_pct_gdp", "income_group",
                   "expenditure_pct_gdp", "country_name"]
    master_sub = master[[c for c in fiscal_cols if c in master.columns]].drop_duplicates(
        subset=["country_code", "year"])
    merged = social.merge(master_sub, on=["country_code", "year"], how="inner",
                          suffixes=("", "_master"))
    if "country_name_master" in merged.columns:
        merged["country_name"] = merged["country_name"].fillna(merged["country_name_master"])
        merged.drop(columns=["country_name_master"], inplace=True)

    logger.info(f"Merged social-fiscal: {len(merged)} rows, {merged['country_code'].nunique()} countries")

    # ── 1. Tax vs Gini (cross-section, latest year) ──
    gini_tax = merged.dropna(subset=["gini_coefficient", "tax_revenue_pct_gdp"])
    latest_gt = gini_tax.sort_values("year").groupby("country_code").last().reset_index()
    tax_gini_reg = {}
    if len(latest_gt) > 15:
        slope, intercept, r_val, p_val, se = stats.linregress(
            latest_gt["tax_revenue_pct_gdp"].values, latest_gt["gini_coefficient"].values
        )
        tax_gini_reg = {
            "slope": round(slope, 4),
            "intercept": round(intercept, 3),
            "r_squared": round(r_val ** 2, 4),
            "p_value": round(p_val, 6),
            "n_countries": len(latest_gt),
            "interpretation": ("higher-tax countries have lower inequality"
                               if slope < 0 else "no clear tax-inequality relationship"),
        }
        logger.info(f"Tax-Gini: slope={tax_gini_reg['slope']}, R2={tax_gini_reg['r_squared']}, "
                     f"p={tax_gini_reg['p_value']} -> {tax_gini_reg['interpretation']}")

    # ── 2. Social Spending vs Poverty ──
    sp_poverty_reg = {}
    if not expenditure.empty and "cofog_social_protection" in expenditure.columns:
        sp = expenditure[["country_code", "year", "cofog_social_protection"]].dropna()
        pov = social[["country_code", "year", "poverty_headcount_215"]].dropna()
        sp_pov = sp.merge(pov, on=["country_code", "year"], how="inner")
        if len(sp_pov) > 15:
            slope, intercept, r_val, p_val, se = stats.linregress(
                sp_pov["cofog_social_protection"].values, sp_pov["poverty_headcount_215"].values
            )
            sp_poverty_reg = {
                "slope": round(slope, 4),
                "intercept": round(intercept, 3),
                "r_squared": round(r_val ** 2, 4),
                "p_value": round(p_val, 6),
                "n_obs": len(sp_pov),
            }
            logger.info(f"Social protection-poverty: slope={sp_poverty_reg['slope']}, "
                         f"R2={sp_poverty_reg['r_squared']}")
        else:
            logger.warning(f"Insufficient SP-poverty overlap: {len(sp_pov)}")
    else:
        logger.warning("COFOG social_protection not available for poverty regression")

    # ── 3. Life Expectancy vs Tax (proxy for HDI-tax relationship) ──
    # Note: human_capital_index not in social panel, use life_expectancy as proxy
    le_tax = merged.dropna(subset=["life_expectancy", "tax_revenue_pct_gdp"])
    latest_le = le_tax.sort_values("year").groupby("country_code").last().reset_index()
    le_reg = {}
    if len(latest_le) > 15:
        slope, intercept, r_val, p_val, se = stats.linregress(
            latest_le["tax_revenue_pct_gdp"].values, latest_le["life_expectancy"].values
        )
        le_reg = {
            "slope": round(slope, 4),
            "intercept": round(intercept, 3),
            "r_squared": round(r_val ** 2, 4),
            "p_value": round(p_val, 6),
            "n_countries": len(latest_le),
        }
        logger.info(f"Life expectancy-tax: slope={le_reg['slope']}, R2={le_reg['r_squared']}")

    # ── 4. Summary Table by Income Group ──
    summary_cols = {
        "gini_coefficient": "mean_gini",
        "tax_revenue_pct_gdp": "mean_tax_pct_gdp",
        "poverty_headcount_215": "mean_poverty_215",
        "life_expectancy": "mean_life_expectancy",
    }
    available = {k: v for k, v in summary_cols.items() if k in merged.columns}
    ig_summary = (merged.dropna(subset=["income_group"])
                  .groupby("income_group")[list(available.keys())]
                  .mean()
                  .round(2)
                  .reset_index())
    ig_summary.columns = ["income_group"] + list(available.values())
    # Add count
    ig_count = merged.dropna(subset=["income_group"]).groupby("income_group")["country_code"].nunique()
    ig_summary["n_countries"] = ig_summary["income_group"].map(ig_count)
    logger.info(f"Income group summary:\n{ig_summary.to_string(index=False)}")

    # ── Build output ──
    # Per-country latest as main sheet
    country_latest = merged.sort_values("year").groupby("country_code").last().reset_index()
    result = country_latest[["country_code", "country_name", "year", "income_group"]].copy()

    for col in ["gini_coefficient", "tax_revenue_pct_gdp", "poverty_headcount_215",
                "life_expectancy", "expenditure_pct_gdp"]:
        if col in country_latest.columns:
            result[col] = country_latest[col]

    # Add regression metadata
    if tax_gini_reg:
        result["tax_gini_slope"] = tax_gini_reg["slope"]
        result["tax_gini_r2"] = tax_gini_reg["r_squared"]
        result["tax_gini_interpretation"] = tax_gini_reg["interpretation"]
    if sp_poverty_reg:
        result["sp_poverty_slope"] = sp_poverty_reg["slope"]
        result["sp_poverty_r2"] = sp_poverty_reg["r_squared"]
    if le_reg:
        result["life_exp_tax_slope"] = le_reg["slope"]
        result["life_exp_tax_r2"] = le_reg["r_squared"]

    # Add income group means for context
    result = result.merge(
        ig_summary[["income_group"] + [v for v in available.values()]].rename(
            columns={v: f"ig_{v}" for v in available.values()}),
        on="income_group", how="left"
    )

    out_path = out / "inequality_fiscal_analysis.xlsx"
    write_single_sheet_excel(result, out_path, sheet_name="Inequality Fiscal Nexus")
    logger.info(f"[{MANIFEST['id']}] Saved {len(result)} rows to {out_path}")


if __name__ == "__main__":
    run()
