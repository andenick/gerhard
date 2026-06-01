#!/usr/bin/env python3
"""
A194: Expenditure Structure Analysis
Analyze mandatory vs discretionary proxies, wage bill shares, social spending vs
outcomes, and interest crowding of expenditure.
Stage: A | ID: A194
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
    "id": "A194",
    "name": "Expenditure Structure Analysis",
    "stage": "A",
    "description": "Mandatory vs discretionary, wage bill, social spending vs outcomes, interest crowding",
    "depends_on": ["P77", "P70"],
    "inputs": [
        {"path": "Output/Data/expenditure_functions_panel.xlsx", "required": True},
        {"path": "Output/Data/expenditure_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/social_outcomes_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/expenditure_structure_deep.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    exp_func = read_excel_safe(out / "expenditure_functions_panel.xlsx")
    exp_comp = read_excel_safe(out / "expenditure_composition_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    social = read_excel_safe(out / "social_outcomes_panel.xlsx")

    if exp_func.empty or exp_comp.empty or master.empty:
        logger.error("Required panels missing; aborting.")
        return

    ig_map = master.drop_duplicates("country_code")[["country_code", "income_group"]].dropna(subset=["income_group"])

    sheets = {}

    # ── 1. Mandatory vs discretionary proxy ──
    logger.info("1. Mandatory vs discretionary proxy...")
    ec = exp_comp.merge(ig_map, on="country_code", how="left")
    if "transfers_pct_expense" in ec.columns and "interest_pct_expense" in ec.columns:
        mask = ec["transfers_pct_expense"].notna() & ec["interest_pct_expense"].notna()
        ec.loc[mask, "mandatory_proxy_pct"] = (
            ec.loc[mask, "transfers_pct_expense"] + ec.loc[mask, "interest_pct_expense"]
        )
        mandatory = (
            ec.dropna(subset=["mandatory_proxy_pct", "income_group"])
            .groupby(["income_group", "year"])
            .agg(
                mean_mandatory=("mandatory_proxy_pct", "mean"),
                median_mandatory=("mandatory_proxy_pct", "median"),
                n_countries=("country_code", "nunique"),
            )
            .reset_index()
        )
        sheets["mandatory_proxy"] = mandatory
        logger.info(f"  Mandatory proxy: {len(mandatory)} group-year obs")

    # ── 2. Wage bill share by income group ──
    logger.info("2. Wage bill share by income group...")
    if "compensation_pct_expense" in ec.columns:
        wage_bill = (
            ec.dropna(subset=["compensation_pct_expense", "income_group"])
            .groupby(["income_group", "year"])
            .agg(
                mean_wage_bill=("compensation_pct_expense", "mean"),
                median_wage_bill=("compensation_pct_expense", "median"),
                n_countries=("country_code", "nunique"),
            )
            .reset_index()
        )
        sheets["wage_bill"] = wage_bill
        logger.info(f"  Wage bill: {len(wage_bill)} group-year obs")

    # ── 3. Social spending vs outcomes ──
    logger.info("3. Social spending vs outcomes...")
    if not social.empty:
        ef_ig = exp_func.merge(ig_map, on="country_code", how="left")
        # Merge education spending with enrollment
        social_cols = ["country_code", "year"]
        for c in ["life_expectancy", "primary_enrollment_gross", "secondary_enrollment_gross"]:
            if c in social.columns:
                social_cols.append(c)
        if len(social_cols) > 2:
            merged = ef_ig.merge(social[social_cols], on=["country_code", "year"], how="inner")

            records = []
            for cc, grp in merged.groupby("country_code"):
                row = {"country_code": cc, "income_group": grp["income_group"].iloc[0]}
                if "education_pct_gdp" in grp.columns and "secondary_enrollment_gross" in grp.columns:
                    valid = grp.dropna(subset=["education_pct_gdp", "secondary_enrollment_gross"])
                    if len(valid) >= 3:
                        row["edu_enrollment_corr"] = valid["education_pct_gdp"].corr(valid["secondary_enrollment_gross"])
                        row["mean_edu_spend"] = valid["education_pct_gdp"].mean()
                        row["mean_enrollment"] = valid["secondary_enrollment_gross"].mean()
                if "health_govt_pct_gdp" in grp.columns and "life_expectancy" in grp.columns:
                    valid = grp.dropna(subset=["health_govt_pct_gdp", "life_expectancy"])
                    if len(valid) >= 3:
                        row["health_lifeexp_corr"] = valid["health_govt_pct_gdp"].corr(valid["life_expectancy"])
                        row["mean_health_spend"] = valid["health_govt_pct_gdp"].mean()
                        row["mean_life_exp"] = valid["life_expectancy"].mean()
                if len(row) > 2:
                    records.append(row)

            if records:
                spending_vs_outcomes = pd.DataFrame(records)
                sheets["spending_vs_outcomes"] = spending_vs_outcomes
                logger.info(f"  Spending vs outcomes: {len(spending_vs_outcomes)} countries")
    else:
        logger.warning("  Social outcomes panel not available")

    # ── 4. Interest crowding ──
    logger.info("4. Interest crowding analysis...")
    if "interest_pct_expense" in ec.columns and "total_expense_pct_gdp" in ec.columns:
        # For each country, compute how much of expenditure growth went to interest
        records = []
        for cc, grp in ec.groupby("country_code"):
            grp = grp.sort_values("year").dropna(subset=["interest_pct_expense", "total_expense_pct_gdp"])
            if len(grp) < 5:
                continue
            first_half = grp.head(len(grp) // 2)
            second_half = grp.tail(len(grp) // 2)
            interest_early = first_half["interest_pct_expense"].mean()
            interest_late = second_half["interest_pct_expense"].mean()
            expense_early = first_half["total_expense_pct_gdp"].mean()
            expense_late = second_half["total_expense_pct_gdp"].mean()

            records.append({
                "country_code": cc,
                "income_group": grp["income_group"].iloc[0] if "income_group" in grp.columns else None,
                "interest_share_early": interest_early,
                "interest_share_late": interest_late,
                "interest_share_change": interest_late - interest_early,
                "expense_gdp_early": expense_early,
                "expense_gdp_late": expense_late,
                "expense_gdp_change": expense_late - expense_early,
                "n_years": len(grp),
            })

        if records:
            crowding = pd.DataFrame(records)
            sheets["interest_crowding"] = crowding
            # Countries where interest rose while spending grew
            squeezed = crowding[
                (crowding["interest_share_change"] > 2) & (crowding["expense_gdp_change"] > 0)
            ]
            logger.info(f"  Interest crowding: {len(crowding)} countries, "
                        f"{len(squeezed)} squeezed (interest +2pp while spending grew)")

    # --- Write output ---
    if not sheets:
        logger.error("No analysis sheets produced; aborting.")
        return

    filepath = out / "expenditure_structure_deep.xlsx"
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
