#!/usr/bin/env python3
"""
A105: Expenditure Structure Analysis
Analyze interest burden, wage bill, social protection adequacy, and spending structure.
Stage: A | ID: A105
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
    "id": "A105",
    "name": "Expenditure Structure Analysis",
    "stage": "A",
    "description": "Analyze interest burden, wage bill, social protection adequacy, and spending structure",
    "depends_on": ["P70"],
    "inputs": [
        {"path": "Output/Data/expenditure_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/social_outcomes_panel.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/expenditure_structure_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    exp = read_excel_safe(out / "expenditure_composition_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    social = read_excel_safe(out / "social_outcomes_panel.xlsx")

    if exp.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    logger.info(f"Expenditure panel: {len(exp)} rows, {exp['country_code'].nunique()} countries")

    # Merge income_group + debt_pct_gdp from master
    master_cols = master[["country_code", "year", "income_group", "debt_pct_gdp"]].drop_duplicates()
    exp = exp.merge(master_cols, on=["country_code", "year"], how="left")

    # ── 1. Interest Burden for High-Debt Countries ──
    # High-debt = debt_pct_gdp > 60 at any point
    high_debt_countries = (master[master["debt_pct_gdp"] > 60]["country_code"].unique()
                           if "debt_pct_gdp" in master.columns else [])
    interest_trend = (exp[exp["country_code"].isin(high_debt_countries)]
                      .dropna(subset=["interest_pct_gdp"])
                      .groupby("year")["interest_pct_gdp"]
                      .agg(["mean", "median", "count"])
                      .reset_index())
    interest_trend.columns = ["year", "mean_interest_pct_gdp", "median_interest_pct_gdp", "n_countries"]
    logger.info(f"Interest burden trend: {len(interest_trend)} year-obs for {len(high_debt_countries)} high-debt countries")

    # ── 2. Wage Bill (compensation) by Income Group ──
    wage_by_ig = (exp.dropna(subset=["compensation_pct_expense", "income_group"])
                  .groupby("income_group")["compensation_pct_expense"]
                  .agg(["mean", "median", "std", "count"])
                  .round(2)
                  .reset_index())
    wage_by_ig.columns = ["income_group", "mean_comp_pct", "median_comp_pct", "std_comp_pct", "n_obs"]
    logger.info(f"Wage bill by income group:\n{wage_by_ig.to_string(index=False)}")

    # ── 3. Social Protection Adequacy ──
    sp_poverty = None
    if not social.empty and "cofog_social_protection" in exp.columns:
        sp = exp[["country_code", "year", "cofog_social_protection"]].dropna()
        pov = social[["country_code", "year", "poverty_headcount_215"]].dropna()
        merged = sp.merge(pov, on=["country_code", "year"], how="inner")
        if len(merged) >= 10:
            slope, intercept, r_val, p_val, se = stats.linregress(
                merged["cofog_social_protection"].values,
                merged["poverty_headcount_215"].values
            )
            logger.info(f"Social protection vs poverty: slope={slope:.3f}, R2={r_val**2:.3f}, p={p_val:.4f}")
            sp_poverty = {
                "relationship": "cofog_social_protection -> poverty_headcount_215",
                "slope": round(slope, 4),
                "intercept": round(intercept, 4),
                "r_squared": round(r_val ** 2, 4),
                "p_value": round(p_val, 6),
                "n_obs": len(merged),
            }
        else:
            logger.warning(f"Insufficient overlap for social protection regression: {len(merged)} obs")
    else:
        logger.warning("Social outcomes or COFOG social_protection not available for regression")

    # ── 4. Spending Structure by Income Group ──
    cofog_cols = [c for c in exp.columns if c.startswith("cofog_") and c != "cofog_total"]
    expense_cats = ["compensation_pct_expense", "goods_services_pct_expense",
                    "interest_pct_expense", "transfers_pct_expense", "other_expense_pct_expense"]
    struct_cols = [c for c in expense_cats + cofog_cols if c in exp.columns]

    spending_struct = (exp.dropna(subset=["income_group"])
                       .groupby("income_group")[struct_cols]
                       .mean()
                       .round(2)
                       .reset_index())
    logger.info(f"Spending structure: {len(spending_struct)} income groups, {len(struct_cols)} categories")

    # ── Combine into comprehensive output ──
    # Build per-country summary as main sheet
    latest = exp.sort_values("year").groupby("country_code").last().reset_index()
    result = latest[["country_code", "country_name", "year", "income_group",
                      "total_expense_pct_gdp", "compensation_pct_expense",
                      "interest_pct_gdp", "interest_pct_expense"]].copy()

    # Add COFOG columns if present
    for c in cofog_cols:
        if c in latest.columns:
            result[c] = latest[c]

    # Add income-group wage bill context
    result = result.merge(
        wage_by_ig[["income_group", "mean_comp_pct"]].rename(
            columns={"mean_comp_pct": "ig_mean_compensation_pct"}),
        on="income_group", how="left"
    )

    # Add SP regression result as metadata columns
    if sp_poverty:
        result["sp_poverty_slope"] = sp_poverty["slope"]
        result["sp_poverty_r2"] = sp_poverty["r_squared"]
        result["sp_poverty_p"] = sp_poverty["p_value"]

    out_path = out / "expenditure_structure_analysis.xlsx"
    write_single_sheet_excel(result, out_path, sheet_name="Expenditure Structure")
    logger.info(f"[{MANIFEST['id']}] Saved {len(result)} rows to {out_path}")


if __name__ == "__main__":
    run()
