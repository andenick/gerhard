#!/usr/bin/env python3
"""
A94: Granger Causality
Granger causality tests between tax ratios and GDP growth.
Stage: A | ID: A94
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
    "id": "A94",
    "name": "Granger Causality",
    "stage": "A",
    "description": "Granger causality tests between tax ratios and GDP growth",
    "depends_on": ["P40"],
    "inputs": [{"path": "Output/Data/balanced_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/granger_causality.xlsx"}],
    "timeout": 180,
    "parallel_safe": True,
}

DATA_DIR = output_data_dir()


def granger_test(y: np.ndarray, x: np.ndarray, max_lag: int = 2):
    """Manual Granger causality test: does adding lagged X improve prediction of Y?

    Parameters
    ----------
    y : array of shape (T,) — dependent variable
    x : array of shape (T,) — potential cause
    max_lag : number of lags to include

    Returns
    -------
    f_stat, p_value : float
    """
    T = len(y)
    n = T - max_lag
    if n < max_lag * 2 + 5:
        return np.nan, np.nan

    Y = y[max_lag:]

    # Restricted model: Y_t = a + b1*Y_{t-1} + ... + bk*Y_{t-k}
    X_r_cols = [np.ones(n)]
    for i in range(max_lag):
        X_r_cols.append(y[max_lag - i - 1: T - i - 1])
    X_r = np.column_stack(X_r_cols)

    try:
        beta_r = np.linalg.lstsq(X_r, Y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    rss_r = np.sum((Y - X_r @ beta_r) ** 2)

    # Unrestricted model: add lagged X
    X_u_cols = list(X_r_cols)
    for i in range(max_lag):
        X_u_cols.append(x[max_lag - i - 1: T - i - 1])
    X_u = np.column_stack(X_u_cols)

    try:
        beta_u = np.linalg.lstsq(X_u, Y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    rss_u = np.sum((Y - X_u @ beta_u) ** 2)

    # F-test
    df_num = max_lag
    df_den = n - 2 * max_lag - 1
    if df_den <= 0 or rss_u <= 0:
        return np.nan, np.nan

    f_stat = ((rss_r - rss_u) / df_num) / (rss_u / df_den)
    if f_stat < 0:
        return np.nan, np.nan
    p_value = 1 - stats.f.cdf(f_stat, df_num, df_den)
    return f_stat, p_value


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    # Load balanced panel
    bp = read_excel_safe(DATA_DIR / "balanced_panel.xlsx")
    if bp.empty:
        logger.error("balanced_panel.xlsx not found or empty")
        return

    logger.info(f"Loaded balanced_panel: {len(bp)} rows")

    # Load enriched panel for GDP data
    ep = read_excel_safe(DATA_DIR / "enriched_tax_panel.xlsx")
    if ep.empty:
        # Try master panel as fallback
        ep = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")

    if ep.empty:
        logger.error("No GDP data source found")
        return

    # Merge GDP into balanced panel
    gdp_cols = ["country_code", "year"]
    if "gdp_current_usd" in ep.columns:
        gdp_cols.append("gdp_current_usd")
    if "gdp_constant_2015_usd" in ep.columns:
        gdp_cols.append("gdp_constant_2015_usd")

    gdp_src = ep[gdp_cols].drop_duplicates(subset=["country_code", "year"])
    df = bp.merge(gdp_src, on=["country_code", "year"], how="left")

    # Use constant USD for growth computation (real GDP growth)
    gdp_col = "gdp_constant_2015_usd" if "gdp_constant_2015_usd" in df.columns else "gdp_current_usd"
    if gdp_col not in df.columns:
        logger.error("No GDP column available after merge")
        return

    df = df.sort_values(["country_code", "year"])

    # Compute GDP growth as delta-log
    df["ln_gdp"] = np.log(df[gdp_col].clip(lower=1))
    df["gdp_growth"] = df.groupby("country_code")["ln_gdp"].diff()

    logger.info(f"Rows with GDP growth: {df['gdp_growth'].notna().sum()}")

    results = []
    countries = df.groupby("country_code")
    min_years = 15
    tested = 0
    significant_count = 0

    for code, grp in countries:
        grp = grp.dropna(subset=["tax_revenue_pct_gdp", "gdp_growth"]).sort_values("year")
        if len(grp) < min_years:
            continue

        tax = grp["tax_revenue_pct_gdp"].values
        gdp_g = grp["gdp_growth"].values
        tested += 1

        for max_lag in [1, 2, 3]:
            # Direction 1: Tax -> GDP growth
            f1, p1 = granger_test(gdp_g, tax, max_lag)
            sig1 = p1 < 0.05 if not np.isnan(p1) else False
            if sig1:
                conclusion1 = "Tax Granger-causes GDP growth"
            else:
                conclusion1 = "No Granger causality"
            results.append({
                "country_code": code,
                "direction": "Tax -> GDP_growth",
                "lags": max_lag,
                "f_statistic": round(f1, 4) if not np.isnan(f1) else np.nan,
                "p_value": round(p1, 6) if not np.isnan(p1) else np.nan,
                "significant": sig1,
                "conclusion": conclusion1,
            })

            # Direction 2: GDP growth -> Tax
            f2, p2 = granger_test(tax, gdp_g, max_lag)
            sig2 = p2 < 0.05 if not np.isnan(p2) else False
            if sig2:
                conclusion2 = "GDP growth Granger-causes Tax"
            else:
                conclusion2 = "No Granger causality"
            results.append({
                "country_code": code,
                "direction": "GDP_growth -> Tax",
                "lags": max_lag,
                "f_statistic": round(f2, 4) if not np.isnan(f2) else np.nan,
                "p_value": round(p2, 6) if not np.isnan(p2) else np.nan,
                "significant": sig2,
                "conclusion": conclusion2,
            })

            if sig1 or sig2:
                significant_count += 1

    results_df = pd.DataFrame(results)
    logger.info(f"Countries tested: {tested}")
    logger.info(f"Total test rows: {len(results_df)}")
    logger.info(f"Significant results (p<0.05): {results_df['significant'].sum()}")

    if not results_df.empty:
        # Summary by direction and lag
        summary = results_df.groupby(["direction", "lags"]).agg(
            n_tests=("significant", "count"),
            n_significant=("significant", "sum"),
        ).reset_index()
        summary["pct_significant"] = (summary["n_significant"] / summary["n_tests"] * 100).round(1)
        logger.info("\nSummary:")
        for _, row in summary.iterrows():
            logger.info(f"  {row['direction']} (lag={row['lags']}): "
                        f"{row['n_significant']}/{row['n_tests']} significant "
                        f"({row['pct_significant']}%)")

    output_path = DATA_DIR / "granger_causality.xlsx"
    write_single_sheet_excel(results_df, output_path)
    logger.info(f"Output saved to {output_path}")


if __name__ == "__main__":
    run()
