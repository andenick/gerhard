#!/usr/bin/env python3
"""
A120: Debt Dynamics Deep Analysis
Analyze interest-growth differential, debt composition risk, primary balance needs, and rapid accumulation.
Stage: A | ID: A120
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
    "id": "A120",
    "name": "Debt Dynamics Deep",
    "stage": "A",
    "description": "Analyze r-g differential, debt composition risk, primary balance needs, rapid accumulation",
    "depends_on": ["P90"],
    "inputs": [
        {"path": "Output/Data/debt_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/debt_dynamics_deep.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    debt = read_excel_safe(out / "debt_composition_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if debt.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    logger.info(f"Debt panel: {len(debt)} rows, {debt['country_code'].nunique()} countries")

    # Merge GDP growth + income_group + debt_pct_gdp from master
    master = master.sort_values(["country_code", "year"])
    master["gdp_growth"] = master.groupby("country_code")["gdp_constant_2015_usd"].pct_change(fill_method=None)

    fiscal_cols = ["country_code", "year", "income_group", "gdp_growth", "debt_pct_gdp",
                   "fiscal_balance_pct_gdp", "country_name"]
    master_sub = master[[c for c in fiscal_cols if c in master.columns]].drop_duplicates(
        subset=["country_code", "year"])
    merged = debt.merge(master_sub, on=["country_code", "year"], how="left",
                        suffixes=("", "_master"))
    if "country_name_master" in merged.columns:
        merged["country_name"] = merged["country_name"].fillna(merged["country_name_master"])
        merged.drop(columns=["country_name_master"], inplace=True)

    # ── 1. Interest-Growth Differential (r - g) ──
    # Proxy r = debt_service_pct_gni (rough proxy for effective interest rate)
    rg = merged.dropna(subset=["debt_service_pct_gni", "gdp_growth"]).copy()
    rg["r_proxy"] = rg["debt_service_pct_gni"] / 100  # convert to fraction
    rg["g"] = rg["gdp_growth"]
    rg["r_minus_g"] = rg["r_proxy"] - rg["g"]
    rg["unfavorable"] = rg["r_minus_g"] > 0

    rg_summary = rg.groupby("income_group").agg(
        mean_r_proxy=("r_proxy", "mean"),
        mean_g=("g", "mean"),
        mean_r_minus_g=("r_minus_g", "mean"),
        pct_unfavorable=("unfavorable", "mean"),
        n_obs=("r_minus_g", "count"),
    ).round(4).reset_index()
    logger.info(f"r-g differential by income group:\n{rg_summary.to_string(index=False)}")

    # ── 2. Debt Composition Risk ──
    risk_by_ig = (merged.dropna(subset=["debt_risk_score", "income_group"])
                  .groupby("income_group")["debt_risk_score"]
                  .agg(["mean", "median", "max", "count"])
                  .round(2)
                  .reset_index())
    risk_by_ig.columns = ["income_group", "mean_risk", "median_risk", "max_risk", "n_obs"]
    logger.info(f"Debt risk by income group:\n{risk_by_ig.to_string(index=False)}")

    # Top 20 riskiest (latest observation)
    latest = merged.sort_values("year").groupby("country_code").last().reset_index()
    top20_risk = (latest.dropna(subset=["debt_risk_score"])
                  .nlargest(20, "debt_risk_score")[
                      ["country_code", "country_name", "year", "income_group",
                       "debt_risk_score", "external_debt_pct_gni", "short_term_pct_total"]]
                  .reset_index(drop=True))
    logger.info(f"Top 20 riskiest countries (latest year):")
    for _, r in top20_risk.head(10).iterrows():
        logger.info(f"  {r['country_name']:30s} risk={r['debt_risk_score']:.1f}")

    # ── 3. Primary Balance Needed to Stabilize Debt ──
    # pb* = (r-g)/(1+g) * d, where d = debt/GDP
    stab = rg.dropna(subset=["debt_pct_gdp"]).copy()
    stab["d"] = stab["debt_pct_gdp"] / 100  # fraction
    stab["pb_star"] = (stab["r_minus_g"] / (1 + stab["g"])) * stab["d"] * 100  # back to % GDP

    # Latest per country
    pb_latest = stab.sort_values("year").groupby("country_code").last().reset_index()
    pb_summary = pb_latest[["country_code", "country_name", "year", "income_group",
                             "debt_pct_gdp", "r_proxy", "g", "r_minus_g", "pb_star"]].copy()
    pb_summary = pb_summary.round(4)
    logger.info(f"Primary balance needed: computed for {len(pb_summary)} countries")
    big_adj = pb_summary[pb_summary["pb_star"] > 3].sort_values("pb_star", ascending=False)
    if len(big_adj) > 0:
        logger.info(f"Countries needing primary surplus > 3% GDP to stabilize debt: {len(big_adj)}")

    # ── 4. Rapid Debt Accumulation Episodes ──
    merged = merged.sort_values(["country_code", "year"])
    merged["debt_change_yoy"] = merged.groupby("country_code")["external_debt_pct_gni"].diff()
    rapid = merged[merged["debt_change_yoy"] > 10].copy()
    rapid["decade"] = (rapid["year"] // 10 * 10).astype(int)
    rapid_by_decade = rapid.groupby("decade").agg(
        n_episodes=("country_code", "count"),
        n_countries=("country_code", "nunique"),
        mean_increase=("debt_change_yoy", "mean"),
    ).round(1).reset_index()
    logger.info(f"Rapid accumulation episodes (>10pp YoY):\n{rapid_by_decade.to_string(index=False)}")

    # ── Build output ──
    # Comprehensive per-country sheet
    result = latest[["country_code", "country_name", "year", "income_group"]].copy()
    for col in ["external_debt_pct_gni", "debt_risk_score", "debt_service_pct_gni",
                "short_term_pct_total", "ppg_pct_total"]:
        if col in latest.columns:
            result[col] = latest[col]

    # Merge r-g and pb_star
    rg_country = pb_summary[["country_code", "r_minus_g", "pb_star"]].copy()
    result = result.merge(rg_country, on="country_code", how="left")

    # Count rapid accumulation episodes
    rapid_count = rapid.groupby("country_code").size().reset_index(name="n_rapid_debt_episodes")
    result = result.merge(rapid_count, on="country_code", how="left")
    result["n_rapid_debt_episodes"] = result["n_rapid_debt_episodes"].fillna(0).astype(int)

    # Add risk group summary
    result = result.merge(
        risk_by_ig[["income_group", "mean_risk"]].rename(columns={"mean_risk": "ig_mean_risk_score"}),
        on="income_group", how="left"
    )

    out_path = out / "debt_dynamics_deep.xlsx"
    write_single_sheet_excel(result, out_path, sheet_name="Debt Dynamics")
    logger.info(f"[{MANIFEST['id']}] Saved {len(result)} rows to {out_path}")


if __name__ == "__main__":
    run()
