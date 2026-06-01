"""
Pipeline: Tax Elasticity Analysis
Estimate tax buoyancy (long-run) and elasticity (short-run) relative to GDP.
Project: Gerhard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe

logger = setup_logging(__name__)


def _clean_country_name(val):
    """Parse dict-like country name strings from WB API."""
    if pd.isna(val):
        return val
    s = str(val)
    if s.startswith("{") and "'value'" in s:
        import ast
        try:
            d = ast.literal_eval(s)
            return d.get("value", s)
        except (ValueError, SyntaxError):
            return s
    return val


MANIFEST = {
    "id": "A86",
    "name": "Tax Elasticity",
    "stage": "A",
    "description": "Tax buoyancy and elasticity estimation relative to GDP",
    "depends_on": ["P60"],
    "inputs": [{"path": "Output/Data/master_fiscal_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/tax_elasticity.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}

DATA_DIR = output_data_dir()


def estimate_buoyancy(years: np.ndarray, tax: np.ndarray, gdp: np.ndarray):
    """Long-run buoyancy via log-log OLS: ln(tax_rev) = a + beta*ln(GDP)."""
    mask = (tax > 0) & (gdp > 0)
    if mask.sum() < 10:
        return np.nan, np.nan, 0
    ln_tax = np.log(tax[mask])
    ln_gdp = np.log(gdp[mask])
    beta, alpha = np.polyfit(ln_gdp, ln_tax, 1)
    # R-squared
    predicted = alpha + beta * ln_gdp
    ss_res = np.sum((ln_tax - predicted) ** 2)
    ss_tot = np.sum((ln_tax - np.mean(ln_tax)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return beta, r2, int(mask.sum())


def estimate_elasticity(tax: np.ndarray, gdp: np.ndarray):
    """Short-run elasticity via first differences of logs."""
    mask = (tax > 0) & (gdp > 0)
    if mask.sum() < 10:
        return np.nan, np.nan
    ln_tax = np.log(tax[mask])
    ln_gdp = np.log(gdp[mask])
    d_ln_tax = np.diff(ln_tax)
    d_ln_gdp = np.diff(ln_gdp)
    if len(d_ln_tax) < 5:
        return np.nan, np.nan
    beta, alpha = np.polyfit(d_ln_gdp, d_ln_tax, 1)
    predicted = alpha + beta * d_ln_gdp
    ss_res = np.sum((d_ln_tax - predicted) ** 2)
    ss_tot = np.sum((d_ln_tax - np.mean(d_ln_tax)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return beta, r2


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    # Load data
    df = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
    if df.empty:
        logger.error("master_fiscal_panel.xlsx not found or empty")
        return

    logger.info(f"Loaded master_fiscal_panel: {len(df)} rows")

    # Clean dict-like country names
    df["country_name"] = df["country_name"].apply(_clean_country_name)

    # Filter to rows with both tax and GDP
    mask = df["tax_revenue_pct_gdp"].notna() & df["gdp_current_usd"].notna()
    df_valid = df[mask].copy()
    logger.info(f"Rows with tax + GDP data: {len(df_valid)}")

    # Compute actual tax revenue in USD
    df_valid["tax_revenue_usd"] = (df_valid["tax_revenue_pct_gdp"] / 100) * df_valid["gdp_current_usd"]

    # Sort by country and year
    df_valid = df_valid.sort_values(["country_code", "year"])

    # Country-level estimates
    results = []
    countries = df_valid.groupby("country_code")

    for code, grp in countries:
        years = grp["year"].values
        tax = grp["tax_revenue_usd"].values
        gdp = grp["gdp_current_usd"].values

        buoyancy, buoy_r2, n_years = estimate_buoyancy(years, tax, gdp)
        if n_years < 10:
            continue

        elast, elast_r2 = estimate_elasticity(tax, gdp)

        country_name = grp["country_name"].iloc[0]
        income_group = grp["income_group"].iloc[-1] if "income_group" in grp.columns else ""
        region = grp["region"].iloc[-1] if "region" in grp.columns else ""

        results.append({
            "country_code": code,
            "country_name": country_name,
            "n_years": n_years,
            "buoyancy_estimate": round(buoyancy, 4) if not np.isnan(buoyancy) else np.nan,
            "buoyancy_r_squared": round(buoy_r2, 4) if not np.isnan(buoy_r2) else np.nan,
            "elasticity_estimate": round(elast, 4) if not np.isnan(elast) else np.nan,
            "elasticity_r_squared": round(elast_r2, 4) if not np.isnan(elast_r2) else np.nan,
            "income_group": income_group,
            "region": region,
        })

    results_df = pd.DataFrame(results)
    logger.info(f"Countries with >=10 years: {len(results_df)}")

    if results_df.empty:
        logger.warning("No countries met the minimum data threshold")
        return

    # Summary statistics
    avg_buoyancy = results_df["buoyancy_estimate"].mean()
    median_buoyancy = results_df["buoyancy_estimate"].median()
    elastic_count = (results_df["buoyancy_estimate"] > 1).sum()
    inelastic_count = (results_df["buoyancy_estimate"] <= 1).sum()

    logger.info(f"Average buoyancy: {avg_buoyancy:.3f}")
    logger.info(f"Median buoyancy: {median_buoyancy:.3f}")
    logger.info(f"Elastic (beta>1): {elastic_count}, Inelastic (beta<=1): {inelastic_count}")

    # By income group
    if "income_group" in results_df.columns:
        ig_stats = results_df.groupby("income_group").agg(
            mean_buoyancy=("buoyancy_estimate", "mean"),
            mean_elasticity=("elasticity_estimate", "mean"),
            count=("country_code", "count"),
        ).reset_index()
        logger.info("\nBuoyancy by income group:")
        for _, row in ig_stats.iterrows():
            logger.info(f"  {row['income_group']}: buoyancy={row['mean_buoyancy']:.3f}, "
                        f"elasticity={row['mean_elasticity']:.3f}, n={row['count']}")

    # Sort by buoyancy
    results_df = results_df.sort_values("buoyancy_estimate", ascending=False)

    # Save
    output_path = DATA_DIR / "tax_elasticity.xlsx"
    write_single_sheet_excel(results_df, output_path)
    logger.info(f"Output saved to {output_path}")


if __name__ == "__main__":
    run()
