#!/usr/bin/env python3
"""
A100: Revenue Structure Analysis
Analyze tax structure typologies, diversification, temporal shifts, and tax mix.
Stage: A | ID: A100
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
    "id": "A100",
    "name": "Revenue Structure Analysis",
    "stage": "A",
    "description": "Analyze tax structure typologies, diversification, temporal shifts, and tax mix by income group",
    "depends_on": ["P65"],
    "inputs": [
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/revenue_structure_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    rev = read_excel_safe(out / "revenue_composition_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if rev.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    logger.info(f"Revenue panel: {len(rev)} rows, {rev['country_code'].nunique()} countries")

    # Merge income_group from master
    ig_map = master.drop_duplicates("country_code")[["country_code", "income_group"]].dropna()
    rev = rev.merge(ig_map, on="country_code", how="left")

    # ── 1. Tax Structure Typology (latest year per country) ──
    latest = rev.sort_values("year").groupby("country_code").last().reset_index()

    def classify_tax(row):
        inc = row.get("income_tax_pct_revenue", 0) or 0
        gs = row.get("goods_services_tax_pct_revenue", 0) or 0
        tr = row.get("trade_tax_pct_revenue", 0) or 0
        if inc > 50:
            return "direct-dominant"
        elif (gs + tr) > 50:
            return "indirect-dominant"
        else:
            return "balanced"

    latest["tax_structure_type"] = latest.apply(classify_tax, axis=1)
    typology = latest[["country_code", "country_name", "year", "income_group",
                        "income_tax_pct_revenue", "goods_services_tax_pct_revenue",
                        "trade_tax_pct_revenue", "tax_structure_type"]].copy()
    typology_counts = typology["tax_structure_type"].value_counts()
    logger.info(f"Tax structure typology distribution:\n{typology_counts.to_string()}")

    # ── 2. Revenue Diversification by Income Group ──
    div_by_ig = (rev.dropna(subset=["tax_diversification_index", "income_group"])
                 .groupby("income_group")["tax_diversification_index"]
                 .agg(["mean", "median", "std", "count"])
                 .round(4)
                 .reset_index())
    div_by_ig.columns = ["income_group", "mean_diversification", "median_diversification",
                         "std_diversification", "n_obs"]
    logger.info(f"Diversification by income group:\n{div_by_ig.to_string(index=False)}")

    # ── 3. Temporal Shift (trade tax modernization) ──
    country_years = rev.groupby("country_code")["year"].count()
    long_series = country_years[country_years >= 15].index

    shift_results = []
    for cc in long_series:
        cdf = rev[(rev["country_code"] == cc)].dropna(subset=["trade_tax_pct_revenue", "year"])
        if len(cdf) < 15:
            continue
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            cdf["year"].values, cdf["trade_tax_pct_revenue"].values
        )
        cname = cdf["country_name"].iloc[0]
        ig = cdf["income_group"].iloc[0] if "income_group" in cdf.columns else None
        shift_results.append({
            "country_code": cc,
            "country_name": cname,
            "income_group": ig,
            "n_years": len(cdf),
            "trade_tax_slope_per_year": round(slope, 5),
            "r_squared": round(r_value ** 2, 4),
            "p_value": round(p_value, 6),
            "modernizing": slope < 0 and p_value < 0.05,
        })
    shift_df = pd.DataFrame(shift_results).sort_values("trade_tax_slope_per_year")
    n_mod = shift_df["modernizing"].sum()
    logger.info(f"Temporal shift: {n_mod}/{len(shift_df)} countries significantly reducing trade taxes")

    # ── 4. Tax Mix Matrix: income_group x mean shares ──
    share_cols = ["income_tax_pct_revenue", "goods_services_tax_pct_revenue", "trade_tax_pct_revenue"]
    tax_mix = (rev.dropna(subset=share_cols + ["income_group"])
               .groupby("income_group")[share_cols]
               .mean()
               .round(2)
               .reset_index())
    tax_mix.columns = ["income_group", "mean_income_tax_share", "mean_goods_services_share",
                       "mean_trade_tax_share"]
    logger.info(f"Tax mix matrix:\n{tax_mix.to_string(index=False)}")

    # ── Combine into comprehensive output ──
    # Use typology as the main sheet (most comprehensive per-country result)
    # Add analysis_type column to distinguish sections when combined
    typology["analysis"] = "typology"
    typology["trade_tax_slope"] = typology["country_code"].map(
        shift_df.set_index("country_code")["trade_tax_slope_per_year"]
    )
    typology["modernizing"] = typology["country_code"].map(
        shift_df.set_index("country_code")["modernizing"]
    )

    # Merge diversification info
    typology = typology.merge(
        div_by_ig[["income_group", "mean_diversification"]],
        on="income_group", how="left"
    )
    # Merge tax mix info
    typology = typology.merge(tax_mix, on="income_group", how="left")

    out_path = out / "revenue_structure_analysis.xlsx"
    write_single_sheet_excel(typology, out_path, sheet_name="Revenue Structure")
    logger.info(f"[{MANIFEST['id']}] Saved {len(typology)} rows to {out_path}")


if __name__ == "__main__":
    run()
