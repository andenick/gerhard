#!/usr/bin/env python3
"""
A130: Aggregate Trends Analysis
Analyze global trends, regional divergence, income group trajectories, and OECD gap.
Stage: A | ID: A130
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
    "id": "A130",
    "name": "Aggregate Trends",
    "stage": "A",
    "description": "Analyze global trends, regional divergence, income group trajectories, and OECD gap",
    "depends_on": ["P98"],
    "inputs": [
        {"path": "Output/Data/aggregates_panel.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/aggregate_trends_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    agg = read_excel_safe(out / "aggregates_panel.xlsx")

    if agg.empty:
        logger.error("Cannot load aggregates_panel.xlsx; aborting.")
        return

    logger.info(f"Aggregates panel: {len(agg)} rows, types: {agg['aggregate_type'].unique().tolist()}")

    # ── 1. Global Trends ──
    global_agg = agg[agg["aggregate_type"] == "global"].copy()
    key_vars = ["tax_revenue_pct_gdp", "expenditure_pct_gdp", "debt_pct_gdp"]
    global_trends = []
    for var in key_vars:
        vdata = global_agg[global_agg["variable"] == var].sort_values("year")
        if not vdata.empty:
            for _, row in vdata.iterrows():
                global_trends.append({
                    "aggregate_type": "global",
                    "aggregate_name": row.get("aggregate_name", "Global"),
                    "variable": var,
                    "year": row["year"],
                    "mean": row.get("mean"),
                    "weighted_mean": row.get("weighted_mean"),
                    "median": row.get("median"),
                    "n_countries": row.get("n_countries"),
                })
            # Log start/end
            first = vdata.iloc[0]
            last = vdata.iloc[-1]
            logger.info(f"Global {var}: {first.get('mean', 'N/A'):.2f} ({int(first['year'])}) -> "
                        f"{last.get('mean', 'N/A'):.2f} ({int(last['year'])})")

    # ── 2. Regional Divergence (sigma convergence) ──
    regional_agg = agg[agg["aggregate_type"] == "region"].copy()
    tax_regional = regional_agg[regional_agg["variable"] == "tax_revenue_pct_gdp"].copy()

    sigma_by_year = []
    if not tax_regional.empty:
        for yr, grp in tax_regional.groupby("year"):
            means = grp["mean"].dropna()
            if len(means) >= 3:
                sigma_by_year.append({
                    "year": yr,
                    "sigma_tax_across_regions": round(means.std(), 4),
                    "n_regions": len(means),
                    "min_regional_mean": round(means.min(), 2),
                    "max_regional_mean": round(means.max(), 2),
                    "range": round(means.max() - means.min(), 2),
                })

    sigma_df = pd.DataFrame(sigma_by_year).sort_values("year")
    if len(sigma_df) >= 2:
        first_sigma = sigma_df.iloc[0]["sigma_tax_across_regions"]
        last_sigma = sigma_df.iloc[-1]["sigma_tax_across_regions"]
        trend = "converging (sigma falling)" if last_sigma < first_sigma else "diverging (sigma rising)"
        logger.info(f"Regional divergence: sigma {first_sigma:.3f} -> {last_sigma:.3f} = {trend}")

    # ── 3. Income Group Trajectories ──
    ig_agg = agg[agg["aggregate_type"] == "income_group"].copy()
    ig_tax = ig_agg[ig_agg["variable"] == "tax_revenue_pct_gdp"].copy()
    ig_trajectories = []
    if not ig_tax.empty:
        for ig, grp in ig_tax.groupby("aggregate_name"):
            grp = grp.sort_values("year")
            if len(grp) >= 5:
                first_val = grp["mean"].iloc[0]
                last_val = grp["mean"].iloc[-1]
                growth = last_val - first_val
                annual_growth = growth / (grp["year"].iloc[-1] - grp["year"].iloc[0]) if len(grp) > 1 else 0
                ig_trajectories.append({
                    "income_group": ig,
                    "first_year": int(grp["year"].iloc[0]),
                    "last_year": int(grp["year"].iloc[-1]),
                    "first_mean_tax": round(first_val, 2),
                    "last_mean_tax": round(last_val, 2),
                    "total_change_pp": round(growth, 2),
                    "annual_change_pp": round(annual_growth, 3),
                    "n_years": len(grp),
                })
        ig_traj_df = pd.DataFrame(ig_trajectories)
        if not ig_traj_df.empty:
            logger.info(f"Income group tax trajectories:\n{ig_traj_df.to_string(index=False)}")

    # ── 4. OECD vs Non-OECD Gap ──
    # Look for OECD-related aggregates (might be aggregate_name containing "OECD")
    oecd_related = agg[agg["aggregate_name"].str.contains("OECD|High income", case=False, na=False)]
    non_oecd = agg[agg["aggregate_name"].str.contains("Low income|Lower middle", case=False, na=False)]

    oecd_gap = []
    # Use High income as OECD proxy, Low income as non-OECD proxy
    hi_tax = ig_tax[ig_tax["aggregate_name"].str.contains("High", case=False, na=False)].sort_values("year")
    lo_tax = ig_tax[ig_tax["aggregate_name"].str.contains("Low income", case=False, na=False)]
    # If "Low income" is exact, use it; otherwise try lower-middle
    if lo_tax.empty:
        lo_tax = ig_tax[ig_tax["aggregate_name"].str.contains("Lower", case=False, na=False)]
    lo_tax = lo_tax.sort_values("year")

    if not hi_tax.empty and not lo_tax.empty:
        hi_dict = hi_tax.set_index("year")["mean"].to_dict()
        lo_dict = lo_tax.set_index("year")["mean"].to_dict()
        common_years = sorted(set(hi_dict.keys()) & set(lo_dict.keys()))
        for yr in common_years:
            oecd_gap.append({
                "year": yr,
                "high_income_mean_tax": round(hi_dict[yr], 2),
                "low_income_mean_tax": round(lo_dict[yr], 2),
                "gap_pp": round(hi_dict[yr] - lo_dict[yr], 2),
            })
        gap_df = pd.DataFrame(oecd_gap)
        if len(gap_df) >= 2:
            first_gap = gap_df.iloc[0]["gap_pp"]
            last_gap = gap_df.iloc[-1]["gap_pp"]
            narrowing = "narrowing" if last_gap < first_gap else "widening"
            logger.info(f"High-Low income tax gap: {first_gap:.1f}pp -> {last_gap:.1f}pp ({narrowing})")

    # ── Build comprehensive output ──
    # Combine global trends + sigma + trajectories into one sheet
    rows = []

    # Global trends
    for item in global_trends:
        rows.append({
            "analysis": "global_trend",
            "group": item["aggregate_name"],
            "variable": item["variable"],
            "year": item["year"],
            "value_mean": item["mean"],
            "value_weighted_mean": item["weighted_mean"],
            "value_median": item["median"],
            "n_countries": item["n_countries"],
            "sigma": np.nan,
            "gap_pp": np.nan,
        })

    # Sigma convergence
    for _, row in sigma_df.iterrows():
        rows.append({
            "analysis": "regional_divergence",
            "group": "all_regions",
            "variable": "tax_revenue_pct_gdp",
            "year": row["year"],
            "value_mean": np.nan,
            "value_weighted_mean": np.nan,
            "value_median": np.nan,
            "n_countries": row["n_regions"],
            "sigma": row["sigma_tax_across_regions"],
            "gap_pp": row["range"],
        })

    # OECD gap
    for item in oecd_gap:
        rows.append({
            "analysis": "income_gap",
            "group": "high_vs_low",
            "variable": "tax_revenue_pct_gdp",
            "year": item["year"],
            "value_mean": item["high_income_mean_tax"],
            "value_weighted_mean": item["low_income_mean_tax"],
            "value_median": np.nan,
            "n_countries": np.nan,
            "sigma": np.nan,
            "gap_pp": item["gap_pp"],
        })

    result = pd.DataFrame(rows)
    if result.empty:
        logger.warning("No aggregate trend results produced.")
        result = pd.DataFrame(columns=["analysis", "group", "variable", "year",
                                        "value_mean", "sigma", "gap_pp"])

    out_path = out / "aggregate_trends_analysis.xlsx"
    write_single_sheet_excel(result, out_path, sheet_name="Aggregate Trends")
    logger.info(f"[{MANIFEST['id']}] Saved {len(result)} rows to {out_path}")


if __name__ == "__main__":
    run()
