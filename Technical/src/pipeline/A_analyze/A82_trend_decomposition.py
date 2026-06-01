#!/usr/bin/env python3
"""
A82: Trend Decomposition
HP filter decomposition of tax-to-GDP into trend + cycle.
Stage: A | ID: A82
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
    "id": "A82",
    "name": "Trend Decomposition",
    "stage": "A",
    "description": "HP filter decomposition of tax-to-GDP into trend + cycle",
    "depends_on": ["P40"],
    "inputs": [{"path": "Output/Data/clean_tax_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/trend_decomposition.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def hp_filter(y: np.ndarray, lamb: float = 6.25):
    """Hodrick-Prescott filter.

    Args:
        y: Time series values.
        lamb: Smoothing parameter. 6.25 for annual data (Ravn-Uhlig).

    Returns:
        (trend, cycle) arrays.
    """
    T = len(y)
    if T < 3:
        return y.copy(), np.zeros(T)

    # Try statsmodels first
    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter
        cycle, trend = hpfilter(y, lamb=lamb)
        return trend, cycle
    except ImportError:
        pass

    # Manual implementation: minimize sum((y-t)^2) + lamb * sum((t_{i+2}-2*t_{i+1}+t_i)^2)
    I = np.eye(T)
    D = np.zeros((T - 2, T))
    for i in range(T - 2):
        D[i, i] = 1
        D[i, i + 1] = -2
        D[i, i + 2] = 1
    trend = np.linalg.solve(I + lamb * D.T @ D, y)
    cycle = y - trend
    return trend, cycle


def classify_trend(years: np.ndarray, values: np.ndarray, slope: float) -> str:
    """Classify the trend shape of a time series."""
    n = len(years)
    if n < 5:
        return "Insufficient data"

    # Check for U-shape / inverted-U by fitting quadratic
    t = years - years.mean()
    # Fit: y = a + b*t + c*t^2
    A = np.column_stack([np.ones(n), t, t ** 2])
    try:
        coeffs, _, _, _ = np.linalg.lstsq(A, values, rcond=None)
        quad_coeff = coeffs[2]

        # If quadratic term is significant relative to linear
        if abs(quad_coeff) > 0.001:
            if quad_coeff > 0:
                return "U-shaped"
            else:
                return "Inverted-U"
    except np.linalg.LinAlgError:
        pass

    # Otherwise classify by linear slope (pp per year)
    if slope > 0.1:
        return "Increasing"
    elif slope < -0.1:
        return "Decreasing"
    else:
        return "Stable"


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    df = read_excel_safe(out / "clean_tax_panel.xlsx")
    if df.empty:
        logger.error("Cannot load clean_tax_panel.xlsx; aborting.")
        return

    logger.info(f"Loaded clean_tax_panel: {len(df)} rows, {df['country_code'].nunique()} countries")

    # Filter to countries with series_length >= 10
    eligible = df[df["series_length"] >= 10]["country_code"].unique()
    logger.info(f"Countries with series_length >= 10: {len(eligible)}")

    all_rows = []
    trend_summary = []

    for cc in eligible:
        cdf = df[df["country_code"] == cc].sort_values("year")
        years = cdf["year"].values
        vals = cdf["tax_revenue_pct_gdp"].values
        cname = cdf["country_name"].iloc[0]

        # Drop NaN
        mask = ~np.isnan(vals)
        if mask.sum() < 10:
            continue
        years_clean = years[mask]
        vals_clean = vals[mask]

        # HP filter
        trend, cycle = hp_filter(vals_clean, lamb=6.25)

        # Linear trend via OLS: y = alpha + beta * year
        n = len(years_clean)
        X = np.column_stack([np.ones(n), years_clean.astype(float)])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(X, vals_clean, rcond=None)
            alpha, beta = coeffs
        except np.linalg.LinAlgError:
            alpha, beta = vals_clean.mean(), 0.0

        linear_trend_vals = alpha + beta * years_clean.astype(float)
        classification = classify_trend(years_clean, vals_clean, beta)

        for j in range(n):
            all_rows.append({
                "country_code": cc,
                "country_name": cname,
                "year": int(years_clean[j]),
                "tax_pct_gdp": round(vals_clean[j], 4),
                "hp_trend": round(trend[j], 4),
                "hp_cycle": round(cycle[j], 4),
                "linear_trend": round(linear_trend_vals[j], 4),
                "linear_slope": round(beta, 6),
                "trend_classification": classification,
            })

        trend_summary.append({
            "country_code": cc,
            "country_name": cname,
            "linear_slope": round(beta, 6),
            "trend_classification": classification,
            "n_obs": n,
            "mean_tax": round(vals_clean.mean(), 2),
            "cycle_volatility": round(np.std(cycle), 4),
        })

    results_df = pd.DataFrame(all_rows)
    out_path = out / "trend_decomposition.xlsx"
    write_single_sheet_excel(results_df, out_path)
    logger.info(f"Saved {len(results_df)} rows to {out_path}")

    # Log summary
    summary_df = pd.DataFrame(trend_summary)
    if len(summary_df) > 0:
        counts = summary_df["trend_classification"].value_counts()
        logger.info("Trend classification summary:")
        for cls, cnt in counts.items():
            logger.info(f"  {cls:15s}: {cnt} countries")

        logger.info("\nTop 5 fastest-increasing countries:")
        top_inc = summary_df.nlargest(5, "linear_slope")
        for _, row in top_inc.iterrows():
            logger.info(f"  {row['country_name']:30s} | slope={row['linear_slope']:+.4f} pp/yr")

        logger.info("\nTop 5 fastest-decreasing countries:")
        top_dec = summary_df.nsmallest(5, "linear_slope")
        for _, row in top_dec.iterrows():
            logger.info(f"  {row['country_name']:30s} | slope={row['linear_slope']:+.4f} pp/yr")


if __name__ == "__main__":
    run()
