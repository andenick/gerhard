#!/usr/bin/env python3
"""
A96: Fiscal Projections
5-year forward projections of tax-to-GDP using ARIMA or linear trend.
Stage: A | ID: A96
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
    "id": "A96",
    "name": "Fiscal Projections",
    "stage": "A",
    "description": "5-year forward projections of tax-to-GDP using ARIMA",
    "depends_on": ["P60", "A82"],
    "inputs": [
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/trend_decomposition.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/fiscal_projections_2025_2030.xlsx"}],
    "timeout": 300,
    "parallel_safe": True,
}

DATA_DIR = output_data_dir()

PROJECTION_YEARS = list(range(2025, 2031))  # 2025-2030


def _try_arima(series: np.ndarray):
    """Try ARIMA(1,1,1) projection using statsmodels. Returns projections or None."""
    try:
        from statsmodels.tsa.arima.model import ARIMA
        model = ARIMA(series, order=(1, 1, 1))
        fit = model.fit()
        forecast = fit.get_forecast(steps=len(PROJECTION_YEARS))
        pred = forecast.predicted_mean
        ci = forecast.conf_int(alpha=0.10)  # 90% CI
        return pred, ci[:, 0], ci[:, 1], "ARIMA(1,1,1)"
    except Exception:
        return None


def _linear_trend_projection(series: np.ndarray):
    """Linear trend on last 10 years, projected forward."""
    recent = series[-10:] if len(series) >= 10 else series
    t = np.arange(len(recent))
    slope, intercept = np.polyfit(t, recent, 1)

    # Residual standard error for CI
    predicted_in = intercept + slope * t
    residuals = recent - predicted_in
    rse = np.std(residuals, ddof=2) if len(residuals) > 2 else np.std(residuals)

    n_proj = len(PROJECTION_YEARS)
    base_t = len(recent)
    projections = np.array([intercept + slope * (base_t + i) for i in range(n_proj)])

    # 90% CI: ±1.645 * rse * sqrt(1 + 1/n + (t-tbar)^2/sum(t-tbar)^2)
    from scipy import stats
    t_bar = np.mean(t)
    ss_t = np.sum((t - t_bar) ** 2)
    ci_lower = np.zeros(n_proj)
    ci_upper = np.zeros(n_proj)
    for i in range(n_proj):
        t_new = base_t + i
        leverage = 1 + 1 / len(recent) + (t_new - t_bar) ** 2 / ss_t if ss_t > 0 else 2
        margin = 1.645 * rse * np.sqrt(leverage)
        ci_lower[i] = projections[i] - margin
        ci_upper[i] = projections[i] + margin

    return projections, ci_lower, ci_upper, "Linear trend"


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    df = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
    if df.empty:
        logger.error("master_fiscal_panel.xlsx not found or empty")
        return

    logger.info(f"Loaded master_fiscal_panel: {len(df)} rows")

    # Optionally load trend decomposition for context
    trends = read_excel_safe(DATA_DIR / "trend_decomposition.xlsx")
    if not trends.empty:
        logger.info(f"Loaded trend_decomposition: {len(trends)} rows")

    df = df.sort_values(["country_code", "year"])

    # Filter to countries with >= 10 years of tax data
    country_years = df.dropna(subset=["tax_revenue_pct_gdp"]).groupby("country_code").size()
    valid_countries = country_years[country_years >= 10].index
    logger.info(f"Countries with >= 10 years tax data: {len(valid_countries)}")

    results = []
    arima_count = 0
    linear_count = 0

    for code in valid_countries:
        grp = df[df["country_code"] == code].dropna(subset=["tax_revenue_pct_gdp"]).sort_values("year")
        tax_series = grp["tax_revenue_pct_gdp"].values

        # Try ARIMA first, fall back to linear trend
        arima_result = _try_arima(tax_series)
        if arima_result is not None:
            proj, ci_lo, ci_hi, method = arima_result
            arima_count += 1
        else:
            proj, ci_lo, ci_hi, method = _linear_trend_projection(tax_series)
            linear_count += 1

        # Get latest expenditure and debt for sustainability flags
        latest = grp.iloc[-1]
        last_exp = latest.get("expenditure_pct_gdp", np.nan)
        last_debt = latest.get("debt_pct_gdp", np.nan)

        # Simple expenditure projection: assume constant ratio
        # Simple debt projection: if fiscal_balance available, accumulate
        last_fiscal_bal = latest.get("fiscal_balance_pct_gdp", np.nan)

        for i, year in enumerate(PROJECTION_YEARS):
            proj_tax = proj[i] if i < len(proj) else np.nan
            ci_l = ci_lo[i] if i < len(ci_lo) else np.nan
            ci_u = ci_hi[i] if i < len(ci_hi) else np.nan

            # Project expenditure: constant
            proj_exp = last_exp if not np.isnan(last_exp) else np.nan

            # Project debt: simple accumulation
            if not np.isnan(last_debt) and not np.isnan(last_fiscal_bal):
                proj_debt = last_debt - last_fiscal_bal * (i + 1)
            elif not np.isnan(last_debt):
                proj_debt = last_debt
            else:
                proj_debt = np.nan

            # Sustainability flags
            flags = []
            if not np.isnan(proj_debt) and proj_debt > 100:
                flags.append("high_debt")
            if not np.isnan(last_fiscal_bal) and last_fiscal_bal < -5:
                flags.append("large_deficit")
            if not np.isnan(proj_tax) and proj_tax < 10:
                flags.append("low_tax_capacity")

            sustainability_flag = "; ".join(flags) if flags else "stable"

            results.append({
                "country_code": code,
                "year": year,
                "projected_tax_pct": round(proj_tax, 2) if not np.isnan(proj_tax) else np.nan,
                "ci_lower": round(ci_l, 2) if not np.isnan(ci_l) else np.nan,
                "ci_upper": round(ci_u, 2) if not np.isnan(ci_u) else np.nan,
                "projected_exp_pct": round(proj_exp, 2) if not np.isnan(proj_exp) else np.nan,
                "projected_debt_pct": round(proj_debt, 2) if not np.isnan(proj_debt) else np.nan,
                "sustainability_flag": sustainability_flag,
                "method": method,
            })

    results_df = pd.DataFrame(results)
    logger.info(f"Projections generated: {len(results_df)} rows")
    logger.info(f"  ARIMA: {arima_count} countries, Linear: {linear_count} countries")

    if not results_df.empty:
        # Summary of sustainability flags
        flag_counts = results_df["sustainability_flag"].value_counts()
        logger.info("\nSustainability flags:")
        for flag, count in flag_counts.head(10).items():
            logger.info(f"  {flag}: {count}")

    output_path = DATA_DIR / "fiscal_projections_2025_2030.xlsx"
    write_single_sheet_excel(results_df, output_path)
    logger.info(f"Output saved to {output_path}")


if __name__ == "__main__":
    run()
