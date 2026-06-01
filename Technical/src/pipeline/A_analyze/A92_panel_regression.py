#!/usr/bin/env python3
"""
A92: Panel Regression
Panel fixed/random effects regression of tax determinants.
Stage: A | ID: A92
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
    "id": "A92",
    "name": "Panel Regression",
    "stage": "A",
    "description": "Panel fixed/random effects regression of tax determinants",
    "depends_on": ["P60"],
    "inputs": [{"path": "Output/Data/master_fiscal_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/panel_regression_results.xlsx"}],
    "timeout": 180,
    "parallel_safe": True,
}

DATA_DIR = output_data_dir()


def _ols_regression(y, X, labels, model_name, cluster_groups=None):
    """Run OLS and return coefficient rows.

    Parameters
    ----------
    y : array-like, shape (n,)
    X : array-like, shape (n, k) — should NOT include constant
    labels : list of str, variable names for X columns
    model_name : str
    cluster_groups : array-like or None — for clustered standard errors

    Returns list of dicts with coefficient info.
    """
    n = len(y)
    # Add constant
    X_c = np.column_stack([np.ones(n), X])
    all_labels = ["const"] + list(labels)

    try:
        beta = np.linalg.lstsq(X_c, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return []

    resid = y - X_c @ beta
    k = X_c.shape[1]
    ss_res = np.sum(resid ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    if cluster_groups is not None:
        # Clustered standard errors (White/sandwich estimator by group)
        try:
            XtX_inv = np.linalg.inv(X_c.T @ X_c)
            unique_groups = np.unique(cluster_groups)
            meat = np.zeros((k, k))
            for g in unique_groups:
                mask = cluster_groups == g
                Xg = X_c[mask]
                eg = resid[mask]
                score = Xg.T @ eg
                meat += np.outer(score, score)
            G = len(unique_groups)
            correction = G / (G - 1) * (n - 1) / (n - k)
            vcov = XtX_inv @ meat @ XtX_inv * correction
            se = np.sqrt(np.diag(vcov))
        except np.linalg.LinAlgError:
            se = np.full(k, np.nan)
    else:
        # Homoskedastic standard errors
        sigma2 = ss_res / (n - k) if n > k else np.nan
        try:
            vcov = sigma2 * np.linalg.inv(X_c.T @ X_c)
            se = np.sqrt(np.diag(vcov))
        except np.linalg.LinAlgError:
            se = np.full(k, np.nan)

    rows = []
    for i, label in enumerate(all_labels):
        t_stat = beta[i] / se[i] if se[i] > 0 else np.nan
        from scipy import stats as sp_stats
        p_val = 2 * (1 - sp_stats.t.cdf(abs(t_stat), n - k)) if not np.isnan(t_stat) else np.nan
        rows.append({
            "model": model_name,
            "variable": label,
            "coefficient": round(beta[i], 6),
            "std_error": round(se[i], 6),
            "t_stat": round(t_stat, 4) if not np.isnan(t_stat) else np.nan,
            "p_value": round(p_val, 6) if not np.isnan(p_val) else np.nan,
            "n_obs": n,
            "r_squared": round(r_squared, 4),
        })
    return rows


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    df = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
    if df.empty:
        logger.error("master_fiscal_panel.xlsx not found or empty")
        return

    logger.info(f"Loaded master_fiscal_panel: {len(df)} rows")

    # Prepare variables
    required = ["tax_revenue_pct_gdp", "gdp_per_capita_ppp", "trade_pct_gdp", "urban_pct", "country_code"]
    for col in required:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            return

    df = df.dropna(subset=["tax_revenue_pct_gdp", "gdp_per_capita_ppp", "trade_pct_gdp", "urban_pct"])
    df = df[df["gdp_per_capita_ppp"] > 0].copy()
    df["log_gdp_pc"] = np.log(df["gdp_per_capita_ppp"])

    logger.info(f"Rows with complete data: {len(df)}")

    y_col = "tax_revenue_pct_gdp"
    x_cols = ["log_gdp_pc", "trade_pct_gdp", "urban_pct"]

    all_results = []

    # ---- Model 1: Pooled OLS ----
    logger.info("Running Pooled OLS...")
    y = df[y_col].values
    X = df[x_cols].values
    rows = _ols_regression(y, X, x_cols, "Pooled OLS")
    all_results.extend(rows)
    logger.info(f"  Pooled OLS: {len(rows)} coefficients, n={len(y)}")

    # ---- Model 2: Fixed Effects (de-meaning) ----
    logger.info("Running Fixed Effects (within estimator)...")
    df_fe = df.copy()
    fe_cols = [y_col] + x_cols
    for col in fe_cols:
        df_fe[f"{col}_dm"] = df_fe.groupby("country_code")[col].transform(
            lambda x: x - x.mean()
        )

    dm_x_cols = [f"{c}_dm" for c in x_cols]
    valid_mask = df_fe[dm_x_cols + [f"{y_col}_dm"]].notna().all(axis=1)
    df_fe_valid = df_fe[valid_mask]

    y_fe = df_fe_valid[f"{y_col}_dm"].values
    X_fe = df_fe_valid[dm_x_cols].values
    groups_fe = df_fe_valid["country_code"].values

    rows_fe = _ols_regression(y_fe, X_fe, x_cols, "Fixed Effects", cluster_groups=groups_fe)
    # Remove const from FE (it's zero by construction)
    rows_fe = [r for r in rows_fe if r["variable"] != "const"]
    all_results.extend(rows_fe)
    logger.info(f"  Fixed Effects: {len(rows_fe)} coefficients, n={len(y_fe)}")

    # ---- Model 3: Between Effects (country means) ----
    logger.info("Running Between Effects (country means)...")
    df_be = df.groupby("country_code").agg(
        **{col: (col, "mean") for col in [y_col] + x_cols}
    ).reset_index()

    y_be = df_be[y_col].values
    X_be = df_be[x_cols].values
    rows_be = _ols_regression(y_be, X_be, x_cols, "Between Effects")
    all_results.extend(rows_be)
    logger.info(f"  Between Effects: {len(rows_be)} coefficients, n={len(y_be)}")

    # Build output
    results_df = pd.DataFrame(all_results)
    logger.info(f"\nTotal results: {len(results_df)} rows across 3 models")

    # Summary
    for model in ["Pooled OLS", "Fixed Effects", "Between Effects"]:
        subset = results_df[results_df["model"] == model]
        if not subset.empty:
            r2 = subset["r_squared"].iloc[0]
            n = subset["n_obs"].iloc[0]
            logger.info(f"  {model}: R²={r2:.4f}, n={n}")

    output_path = DATA_DIR / "panel_regression_results.xlsx"
    write_single_sheet_excel(results_df, output_path)
    logger.info(f"Output saved to {output_path}")


if __name__ == "__main__":
    run()
