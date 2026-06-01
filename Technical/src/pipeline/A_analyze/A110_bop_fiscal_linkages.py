#!/usr/bin/env python3
"""
A110: Balance of Payments - Fiscal Linkages
Analyze twin deficits, FDI-tax, remittance-fiscal capacity, and trade openness-tax base.
Stage: A | ID: A110
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
    "id": "A110",
    "name": "BOP-Fiscal Linkages",
    "stage": "A",
    "description": "Analyze twin deficits, FDI-tax, remittance fiscal capacity, and trade openness tax base",
    "depends_on": ["P75"],
    "inputs": [
        {"path": "Output/Data/bop_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/bop_fiscal_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    bop = read_excel_safe(out / "bop_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if bop.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    logger.info(f"BOP panel: {len(bop)} rows, {bop['country_code'].nunique()} countries")

    # Merge fiscal data
    fiscal_cols = ["country_code", "year", "tax_revenue_pct_gdp", "fiscal_balance_pct_gdp",
                   "income_group", "gdp_per_capita_usd", "trade_pct_gdp", "country_name"]
    master_sub = master[[c for c in fiscal_cols if c in master.columns]].drop_duplicates(
        subset=["country_code", "year"])
    merged = bop.merge(master_sub, on=["country_code", "year"], how="inner",
                       suffixes=("", "_master"))
    # Use country_name from bop if present, else master
    if "country_name_master" in merged.columns:
        merged["country_name"] = merged["country_name"].fillna(merged["country_name_master"])
        merged.drop(columns=["country_name_master"], inplace=True)

    logger.info(f"Merged BOP-fiscal: {len(merged)} rows, {merged['country_code'].nunique()} countries")

    # ── 1. Twin Deficits ──
    td_cols = ["fiscal_balance_pct_gdp", "current_account_pct_gdp"]
    td_data = merged.dropna(subset=td_cols)

    # Panel correlation
    panel_corr = td_data[td_cols[0]].corr(td_data[td_cols[1]]) if len(td_data) > 10 else np.nan

    # Cross-section (latest year)
    latest = td_data.sort_values("year").groupby("country_code").last().reset_index()
    if len(latest) > 10:
        xs_corr, xs_p = stats.pearsonr(latest[td_cols[0]], latest[td_cols[1]])
    else:
        xs_corr, xs_p = np.nan, np.nan

    logger.info(f"Twin deficits: panel_corr={panel_corr:.3f}, "
                f"cross-section_corr={xs_corr:.3f} (p={xs_p:.4f}, n={len(latest)})")

    # ── 2. FDI-Tax Regression ──
    fdi_tax = merged.dropna(subset=["fdi_inflows_pct_gdp", "tax_revenue_pct_gdp", "gdp_per_capita_usd"])
    fdi_reg = {}
    if len(fdi_tax) > 20:
        # Simple OLS: fdi ~ tax + gdp_pc
        from numpy.linalg import lstsq
        X = np.column_stack([
            np.ones(len(fdi_tax)),
            fdi_tax["tax_revenue_pct_gdp"].values,
            np.log(fdi_tax["gdp_per_capita_usd"].values + 1)
        ])
        y = fdi_tax["fdi_inflows_pct_gdp"].values
        beta, residuals, rank, sv = lstsq(X, y, rcond=None)
        y_hat = X @ beta
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        fdi_reg = {
            "intercept": round(beta[0], 4),
            "beta_tax": round(beta[1], 4),
            "beta_log_gdppc": round(beta[2], 4),
            "r_squared": round(r2, 4),
            "n_obs": len(fdi_tax),
        }
        logger.info(f"FDI-tax regression: beta_tax={fdi_reg['beta_tax']}, R2={fdi_reg['r_squared']}")

    # ── 3. Remittance - Fiscal Capacity ──
    rem_data = merged.dropna(subset=["remittances_pct_gdp", "tax_revenue_pct_gdp"])
    rem_result = {}
    if len(rem_data) > 20:
        median_rem = rem_data["remittances_pct_gdp"].median()
        high_rem = rem_data[rem_data["remittances_pct_gdp"] >= median_rem]["tax_revenue_pct_gdp"]
        low_rem = rem_data[rem_data["remittances_pct_gdp"] < median_rem]["tax_revenue_pct_gdp"]
        t_stat, t_p = stats.ttest_ind(high_rem, low_rem, equal_var=False)
        rem_result = {
            "median_remittance_pct_gdp": round(median_rem, 3),
            "high_rem_mean_tax": round(high_rem.mean(), 2),
            "low_rem_mean_tax": round(low_rem.mean(), 2),
            "tax_gap": round(high_rem.mean() - low_rem.mean(), 2),
            "t_statistic": round(t_stat, 3),
            "p_value": round(t_p, 5),
        }
        logger.info(f"Remittance-tax gap: high_rem_tax={rem_result['high_rem_mean_tax']}%, "
                     f"low_rem_tax={rem_result['low_rem_mean_tax']}%, gap={rem_result['tax_gap']}pp")

    # ── 4. Trade Openness - Tax Base ──
    to_data = merged.dropna(subset=["trade_pct_gdp", "tax_revenue_pct_gdp"])
    to_reg = {}
    if len(to_data) > 20:
        slope, intercept, r_val, p_val, se = stats.linregress(
            to_data["trade_pct_gdp"].values, to_data["tax_revenue_pct_gdp"].values
        )
        to_reg = {
            "slope": round(slope, 5),
            "intercept": round(intercept, 3),
            "r_squared": round(r_val ** 2, 4),
            "p_value": round(p_val, 6),
            "n_obs": len(to_data),
        }
        logger.info(f"Trade-tax regression: slope={to_reg['slope']}, R2={to_reg['r_squared']}")

    # ── Build output ──
    # Per-country summary as main sheet
    country_latest = merged.sort_values("year").groupby("country_code").last().reset_index()
    result = country_latest[["country_code", "country_name", "year", "income_group"]].copy()

    for col in ["current_account_pct_gdp", "fiscal_balance_pct_gdp", "fdi_inflows_pct_gdp",
                "remittances_pct_gdp", "tax_revenue_pct_gdp", "trade_pct_gdp"]:
        if col in country_latest.columns:
            result[col] = country_latest[col]

    # Add analysis metadata
    result["twin_deficit_panel_corr"] = panel_corr
    result["twin_deficit_xs_corr"] = xs_corr
    if fdi_reg:
        result["fdi_tax_beta"] = fdi_reg["beta_tax"]
        result["fdi_tax_r2"] = fdi_reg["r_squared"]
    if rem_result:
        result["rem_tax_gap_pp"] = rem_result["tax_gap"]
    if to_reg:
        result["trade_tax_slope"] = to_reg["slope"]
        result["trade_tax_r2"] = to_reg["r_squared"]

    out_path = out / "bop_fiscal_analysis.xlsx"
    write_single_sheet_excel(result, out_path, sheet_name="BOP Fiscal Analysis")
    logger.info(f"[{MANIFEST['id']}] Saved {len(result)} rows to {out_path}")


if __name__ == "__main__":
    run()
