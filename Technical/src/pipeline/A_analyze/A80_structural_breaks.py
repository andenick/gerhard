#!/usr/bin/env python3
"""
A80: Structural Breaks
Detect structural breaks in tax-to-GDP time series using Chow-type tests.
Stage: A | ID: A80
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
    "id": "A80",
    "name": "Structural Breaks",
    "stage": "A",
    "description": "Detect structural breaks in tax-to-GDP time series",
    "depends_on": ["P40"],
    "inputs": [{"path": "Output/Data/clean_tax_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/structural_breaks.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def find_structural_break(years: np.ndarray, values: np.ndarray):
    """Find the most significant structural break point using Chow-type F-test.

    Tests each candidate break year (with at least 5 observations on each side)
    by comparing a restricted model (single mean) vs unrestricted (two separate means).

    Returns dict with break details or None if no significant break found.
    """
    n = len(values)
    if n < 11:
        return None

    best_f = 0.0
    best_idx = None

    # RSS restricted: single mean for the whole series
    rss_r = np.sum((values - values.mean()) ** 2)

    for i in range(5, n - 5):
        y1, y2 = values[:i], values[i:]
        # RSS unrestricted: two separate means
        rss_u = np.sum((y1 - y1.mean()) ** 2) + np.sum((y2 - y2.mean()) ** 2)

        # F-statistic: k=1 restriction (same mean)
        if rss_u == 0:
            continue
        f_stat = ((rss_r - rss_u) / 1) / (rss_u / (n - 2))

        if f_stat > best_f:
            best_f = f_stat
            best_idx = i

    if best_idx is None:
        return None

    p_value = 1.0 - stats.f.cdf(best_f, 1, n - 2)
    pre_mean = values[:best_idx].mean()
    post_mean = values[best_idx:].mean()
    change = post_mean - pre_mean

    return {
        "break_year": int(years[best_idx]),
        "f_statistic": round(best_f, 4),
        "p_value": p_value,
        "pre_break_mean": round(pre_mean, 4),
        "post_break_mean": round(post_mean, 4),
        "change_magnitude": round(change, 4),
        "n_obs": n,
    }


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    df = read_excel_safe(out / "clean_tax_panel.xlsx")
    if df.empty:
        logger.error("Cannot load clean_tax_panel.xlsx; aborting.")
        return

    logger.info(f"Loaded clean_tax_panel: {len(df)} rows, {df['country_code'].nunique()} countries")

    # Filter to countries with series_length >= 15
    eligible = df[df["series_length"] >= 15]["country_code"].unique()
    logger.info(f"Countries with series_length >= 15: {len(eligible)}")

    results = []
    for cc in eligible:
        cdf = df[df["country_code"] == cc].sort_values("year")
        years = cdf["year"].values
        vals = cdf["tax_revenue_pct_gdp"].values

        # Drop NaN
        mask = ~np.isnan(vals)
        if mask.sum() < 11:
            continue
        years_clean = years[mask]
        vals_clean = vals[mask]

        brk = find_structural_break(years_clean, vals_clean)
        if brk is not None and brk["p_value"] < 0.05:
            cname = cdf["country_name"].iloc[0]
            brk["country_code"] = cc
            brk["country_name"] = cname
            results.append(brk)

    if not results:
        logger.warning("No significant structural breaks found.")
        results_df = pd.DataFrame(columns=[
            "country_code", "country_name", "break_year", "f_statistic",
            "p_value", "pre_break_mean", "post_break_mean", "change_magnitude", "n_obs"
        ])
    else:
        results_df = pd.DataFrame(results)
        # Sort by absolute change magnitude descending
        results_df["abs_change"] = results_df["change_magnitude"].abs()
        results_df = results_df.sort_values("abs_change", ascending=False).drop(columns=["abs_change"])
        # Reorder columns
        results_df = results_df[
            ["country_code", "country_name", "break_year", "f_statistic",
             "p_value", "pre_break_mean", "post_break_mean", "change_magnitude", "n_obs"]
        ]

    out_path = out / "structural_breaks.xlsx"
    write_single_sheet_excel(results_df, out_path)
    logger.info(f"Saved {len(results_df)} structural breaks to {out_path}")

    # Log top findings
    if len(results_df) > 0:
        logger.info("Top 10 structural breaks by magnitude:")
        for _, row in results_df.head(10).iterrows():
            logger.info(
                f"  {row['country_name']:30s} | year={row['break_year']} | "
                f"change={row['change_magnitude']:+.2f}pp | "
                f"F={row['f_statistic']:.1f} (p={row['p_value']:.4f})"
            )


if __name__ == "__main__":
    run()
