#!/usr/bin/env python3
"""
A84: Convergence Analysis
Sigma and beta convergence of global tax systems.
Stage: A | ID: A84
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
    "id": "A84",
    "name": "Convergence Analysis",
    "stage": "A",
    "description": "Sigma and beta convergence of global tax systems",
    "depends_on": ["P40"],
    "inputs": [{"path": "Output/Data/balanced_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/convergence_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def compute_sigma_convergence(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute cross-sectional dispersion measures for each year."""
    rows = []
    for year, grp in panel.groupby("year"):
        vals = grp["tax_revenue_pct_gdp"].dropna()
        if len(vals) < 3:
            continue
        q1, q3 = vals.quantile(0.25), vals.quantile(0.75)
        rows.append({
            "year": int(year),
            "sigma": round(vals.std(), 4),
            "cv": round(vals.std() / vals.mean(), 4) if vals.mean() != 0 else np.nan,
            "iqr": round(q3 - q1, 4),
            "mean": round(vals.mean(), 4),
            "median": round(vals.median(), 4),
            "n_countries": len(vals),
        })
    return pd.DataFrame(rows)


def compute_beta_convergence(panel: pd.DataFrame, group_label: str = "All"):
    """Compute beta convergence: regress growth rate on initial level.

    beta < 0 implies convergence (low-tax countries grow faster).
    """
    # For each country: initial level and annualized growth
    countries = []
    for cc, grp in panel.groupby("country_code"):
        grp = grp.sort_values("year")
        vals = grp["tax_revenue_pct_gdp"].dropna()
        if len(vals) < 5:
            continue
        initial = vals.iloc[0]
        final = vals.iloc[-1]
        n_years = grp["year"].iloc[-1] - grp["year"].iloc[0]
        if n_years == 0 or initial <= 0:
            continue
        # Annualized growth rate (percentage points per year)
        growth_rate = (final - initial) / n_years
        countries.append({
            "country_code": cc,
            "initial_level": initial,
            "growth_rate": growth_rate,
        })

    if len(countries) < 10:
        return None

    cdf = pd.DataFrame(countries)
    x = cdf["initial_level"].values
    y = cdf["growth_rate"].values

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    return {
        "group": group_label,
        "beta_estimate": round(slope, 6),
        "beta_se": round(std_err, 6),
        "beta_pvalue": p_value,
        "r_squared": round(r_value ** 2, 4),
        "n_countries": len(countries),
        "intercept": round(intercept, 6),
        "convergence": "Yes" if slope < 0 and p_value < 0.05 else "No" if slope >= 0 else "Weak (p>0.05)",
    }


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    panel = read_excel_safe(out / "balanced_panel.xlsx")
    if panel.empty:
        logger.error("Cannot load balanced_panel.xlsx; aborting.")
        return

    logger.info(f"Loaded balanced_panel: {len(panel)} rows, {panel['country_code'].nunique()} countries")

    # =========================================================================
    # 1. Sigma convergence
    # =========================================================================
    sigma_df = compute_sigma_convergence(panel)
    logger.info(f"Sigma convergence: {len(sigma_df)} years computed")

    # Test for declining sigma trend
    if len(sigma_df) >= 5:
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            sigma_df["year"].values, sigma_df["sigma"].values
        )
        sigma_trend = "Declining (convergence)" if slope < 0 and p_value < 0.05 else \
                       "Increasing (divergence)" if slope > 0 and p_value < 0.05 else \
                       "No significant trend"
        logger.info(f"Sigma trend: slope={slope:.4f}, p={p_value:.4f} -> {sigma_trend}")
    else:
        sigma_trend = "Insufficient data"

    # =========================================================================
    # 2. Beta convergence (all countries)
    # =========================================================================
    beta_all = compute_beta_convergence(panel, group_label="All")
    if beta_all:
        logger.info(
            f"Beta convergence (all): beta={beta_all['beta_estimate']:.4f}, "
            f"p={beta_all['beta_pvalue']:.4f}, R2={beta_all['r_squared']:.4f} -> {beta_all['convergence']}"
        )
    else:
        logger.warning("Insufficient data for beta convergence.")

    # =========================================================================
    # 3. Beta convergence by income group (if available)
    # =========================================================================
    beta_by_group = []
    enriched_path = out / "enriched_tax_panel.xlsx"
    if enriched_path.exists():
        enriched = read_excel_safe(enriched_path)
        if not enriched.empty and "income_group" in enriched.columns:
            # Merge income group into balanced panel
            ig_map = enriched[["country_code", "income_group"]].drop_duplicates("country_code")
            panel_ig = panel.merge(ig_map, on="country_code", how="left")
            panel_ig = panel_ig.dropna(subset=["income_group"])

            for ig, grp in panel_ig.groupby("income_group"):
                result = compute_beta_convergence(grp, group_label=str(ig))
                if result:
                    beta_by_group.append(result)
                    logger.info(
                        f"  {ig:30s}: beta={result['beta_estimate']:.4f}, "
                        f"p={result['beta_pvalue']:.4f} -> {result['convergence']}"
                    )
    else:
        logger.info("No enriched_tax_panel.xlsx found; skipping income-group analysis.")

    # =========================================================================
    # 4. Assemble output
    # =========================================================================
    # Add metadata columns to sigma_df
    sigma_df["measure"] = "sigma_convergence"

    # Build beta results dataframe
    beta_rows = []
    if beta_all:
        beta_rows.append(beta_all)
    beta_rows.extend(beta_by_group)

    if beta_rows:
        beta_df = pd.DataFrame(beta_rows)
        beta_df["measure"] = "beta_convergence"
    else:
        beta_df = pd.DataFrame()

    # Combine: sigma convergence yearly data + beta summary rows
    # Write sigma as main sheet, add summary info
    sigma_df["sigma_trend"] = sigma_trend

    # Create a combined summary
    summary_rows = []
    summary_rows.append({
        "analysis": "Sigma convergence",
        "result": sigma_trend,
        "detail": f"slope={slope:.4f}, p={p_value:.4f}" if len(sigma_df) >= 5 else "N/A",
        "n_years": len(sigma_df),
        "n_countries": sigma_df["n_countries"].median() if len(sigma_df) > 0 else 0,
    })
    if beta_all:
        summary_rows.append({
            "analysis": "Beta convergence (all)",
            "result": beta_all["convergence"],
            "detail": f"beta={beta_all['beta_estimate']:.4f}, p={beta_all['beta_pvalue']:.4f}, R2={beta_all['r_squared']:.4f}",
            "n_years": np.nan,
            "n_countries": beta_all["n_countries"],
        })
    for bg in beta_by_group:
        summary_rows.append({
            "analysis": f"Beta convergence ({bg['group']})",
            "result": bg["convergence"],
            "detail": f"beta={bg['beta_estimate']:.4f}, p={bg['beta_pvalue']:.4f}, R2={bg['r_squared']:.4f}",
            "n_years": np.nan,
            "n_countries": bg["n_countries"],
        })

    # Combine sigma yearly data with summary
    # Use multi-section output: sigma rows first, then blank row, then summary
    out_rows = []
    for _, row in sigma_df.iterrows():
        out_rows.append({
            "section": "sigma_yearly",
            "year": row["year"],
            "sigma": row["sigma"],
            "cv": row["cv"],
            "iqr": row["iqr"],
            "mean_tax": row["mean"],
            "median_tax": row["median"],
            "n_countries": row["n_countries"],
            "sigma_trend": row["sigma_trend"],
        })

    for s in summary_rows:
        out_rows.append({
            "section": "summary",
            "year": np.nan,
            "sigma": np.nan,
            "cv": np.nan,
            "iqr": np.nan,
            "mean_tax": np.nan,
            "median_tax": np.nan,
            "n_countries": s["n_countries"],
            "sigma_trend": np.nan,
            "analysis": s["analysis"],
            "result": s["result"],
            "detail": s["detail"],
        })

    out_df = pd.DataFrame(out_rows)
    out_path = out / "convergence_analysis.xlsx"
    write_single_sheet_excel(out_df, out_path)
    logger.info(f"Saved {len(out_df)} rows to {out_path}")


if __name__ == "__main__":
    run()
