#!/usr/bin/env python3
"""
A200: Comprehensive Fiscal Dashboard Data
Build country fiscal health scorecard (0-100), traffic lights, and global
fiscal pulse (GDP-weighted averages).
Stage: A | ID: A200
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
    "id": "A200",
    "name": "Comprehensive Fiscal Dashboard Data",
    "stage": "A",
    "description": "Country fiscal health scores (0-100), traffic lights, global fiscal pulse",
    "depends_on": ["A190", "A196", "A198"],
    "inputs": [
        {"path": "Output/Data/fiscal_ratios_panel.xlsx", "required": True},
        {"path": "Output/Data/fiscal_financial_nexus.xlsx", "required": False},
        {"path": "Output/Data/monetary_fiscal_coordination.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/comprehensive_fiscal_dashboard.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def percentile_score(series, higher_is_better=True):
    """Convert a series to 0-100 percentile score."""
    ranks = series.rank(pct=True, na_option="keep")
    if not higher_is_better:
        ranks = 1 - ranks
    return ranks * 100


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    ratios = read_excel_safe(out / "fiscal_ratios_panel.xlsx")
    if ratios.empty:
        logger.error("Cannot load fiscal_ratios_panel.xlsx; aborting.")
        return

    logger.info(f"Fiscal ratios: {len(ratios)} rows, {ratios['country_code'].nunique()} countries")

    sheets = {}

    # ── 1. Country fiscal health score ──
    logger.info("1. Computing fiscal health scores...")

    # Use latest available year per country
    latest = ratios.sort_values("year").groupby("country_code").last().reset_index()
    logger.info(f"  Latest data for {len(latest)} countries")

    # Component scores (each 0-100)
    score_components = {}

    # Revenue adequacy: higher tax_burden = better
    if "tax_burden" in latest.columns:
        score_components["revenue_adequacy"] = percentile_score(latest["tax_burden"], higher_is_better=True)

    # Spending efficiency proxy: social_spending_pct_gdp (higher = better, with caveats)
    if "social_spending_pct_gdp" in latest.columns:
        score_components["spending_efficiency"] = percentile_score(latest["social_spending_pct_gdp"], higher_is_better=True)

    # Debt sustainability: lower debt_pct_gdp = better
    if "debt_pct_gdp" in latest.columns:
        score_components["debt_sustainability"] = percentile_score(latest["debt_pct_gdp"], higher_is_better=False)

    # Financial stability: lower NPLs = better
    npl_col = None
    for c in ["bank_npl_pct", "npl_pct_gross_loans"]:
        if c in latest.columns:
            npl_col = c
            break
    if npl_col:
        score_components["financial_stability"] = percentile_score(latest[npl_col], higher_is_better=False)

    # External position: higher reserves = better
    reserve_col = None
    for c in ["reserves_months_imports", "total_reserves_months_imports"]:
        if c in latest.columns:
            reserve_col = c
            break
    if reserve_col:
        score_components["reserve_position"] = percentile_score(latest[reserve_col], higher_is_better=True)

    if not score_components:
        logger.error("No score components available")
        return

    # Weighted average
    weights = {
        "revenue_adequacy": 0.25,
        "spending_efficiency": 0.15,
        "debt_sustainability": 0.30,
        "financial_stability": 0.15,
        "reserve_position": 0.15,
    }

    score_df = pd.DataFrame(score_components, index=latest.index)
    available_weights = {k: v for k, v in weights.items() if k in score_df.columns}
    # Renormalize weights
    total_w = sum(available_weights.values())
    norm_weights = {k: v / total_w for k, v in available_weights.items()}

    latest["fiscal_health_score"] = 0.0
    for comp, w in norm_weights.items():
        latest["fiscal_health_score"] += score_df[comp].fillna(50) * w

    # Traffic light
    latest["traffic_light"] = "Yellow"
    latest.loc[latest["fiscal_health_score"] > 70, "traffic_light"] = "Green"
    latest.loc[latest["fiscal_health_score"] < 40, "traffic_light"] = "Red"

    # Add component scores
    for comp in score_components:
        latest[f"score_{comp}"] = score_df[comp]

    scorecard_cols = ["country_code", "country_name", "year", "income_group",
                      "fiscal_health_score", "traffic_light"]
    scorecard_cols += [f"score_{c}" for c in score_components]
    scorecard_cols += ["tax_burden", "debt_pct_gdp", "fiscal_balance",
                       "social_spending_pct_gdp"]
    scorecard_cols = [c for c in scorecard_cols if c in latest.columns]

    scorecard = latest[scorecard_cols].sort_values("fiscal_health_score", ascending=False)
    sheets["scorecard"] = scorecard

    # Summary
    for light in ["Green", "Yellow", "Red"]:
        n = (scorecard["traffic_light"] == light).sum()
        logger.info(f"  {light}: {n} countries")

    # ── 2. Global fiscal pulse: GDP-weighted averages by year ──
    logger.info("2. Global fiscal pulse...")
    pulse_cols = ["tax_burden", "spending_intensity", "fiscal_balance", "debt_pct_gdp",
                  "interest_pct_gdp", "social_spending_pct_gdp"]
    pulse_available = [c for c in pulse_cols if c in ratios.columns]

    if "gdp_current_usd" in ratios.columns and pulse_available:
        pulse_records = []
        for yr, grp in ratios.groupby("year"):
            row = {"year": yr, "n_countries": grp["country_code"].nunique()}
            gdp_total = grp["gdp_current_usd"].sum()

            for col in pulse_available:
                valid = grp.dropna(subset=[col, "gdp_current_usd"])
                if len(valid) > 0 and valid["gdp_current_usd"].sum() > 0:
                    w = valid["gdp_current_usd"] / valid["gdp_current_usd"].sum()
                    row[f"gdp_wtd_{col}"] = (valid[col] * w).sum()
                    row[f"simple_avg_{col}"] = valid[col].mean()
            pulse_records.append(row)

        pulse = pd.DataFrame(pulse_records).sort_values("year")
        sheets["global_pulse"] = pulse
        logger.info(f"  Global pulse: {len(pulse)} years")

    # ── 3. Income group summary ──
    logger.info("3. Income group summary...")
    if "income_group" in scorecard.columns:
        ig_summary = (
            scorecard.dropna(subset=["income_group"])
            .groupby("income_group")
            .agg(
                n_countries=("country_code", "count"),
                mean_score=("fiscal_health_score", "mean"),
                median_score=("fiscal_health_score", "median"),
                pct_green=("traffic_light", lambda x: (x == "Green").mean() * 100),
                pct_red=("traffic_light", lambda x: (x == "Red").mean() * 100),
            )
            .reset_index()
        )
        sheets["income_group_summary"] = ig_summary
        logger.info(f"  Income groups: {len(ig_summary)}")

    # --- Write output ---
    filepath = out / "comprehensive_fiscal_dashboard.xlsx"
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
