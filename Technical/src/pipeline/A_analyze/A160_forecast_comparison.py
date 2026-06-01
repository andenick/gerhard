#!/usr/bin/env python3
"""
A160: Forecast Comparison
Compare our ARIMA fiscal projections (A96) with IMF WEO projections (P105).
Evaluate side-by-side differences, historical accuracy, systematic bias,
and coverage gaps.
Stage: A | ID: A160
Project: Gerhard

MANIFEST depends_on: ["A96", "P105"]
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
    "id": "A160",
    "name": "Forecast Comparison",
    "stage": "A",
    "description": (
        "Compare ARIMA fiscal projections with IMF WEO projections: "
        "side-by-side, historical accuracy, systematic bias, coverage"
    ),
    "depends_on": ["A96", "P105"],
    "inputs": [
        {"path": "Output/Data/fiscal_projections_2025_2030.xlsx", "required": True},
        {"path": "Output/Data/imf_weo_enriched.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/forecast_comparison.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    arima = read_excel_safe(out / "fiscal_projections_2025_2030.xlsx")
    imf = read_excel_safe(out / "imf_weo_enriched.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if arima.empty or imf.empty:
        logger.error("Cannot load projections or IMF data; aborting.")
        return

    logger.info(
        f"ARIMA projections: {len(arima)} rows, {arima['country_code'].nunique()} countries"
    )
    logger.info(
        f"IMF WEO: {len(imf)} rows, {imf['country_code'].nunique()} countries"
    )

    results_rows = []

    # ════════════════════════════════════════════════════════════════
    # (a) Side-by-side comparison of projected years
    # ════════════════════════════════════════════════════════════════
    # ARIMA: projected_tax_pct for 2025-2030
    # IMF projections: is_projection == True (typically 2026-2030)
    imf_proj = imf[imf["is_projection"] == True].copy()
    logger.info(
        f"IMF projection years: {sorted(imf_proj['year'].unique())}, "
        f"{imf_proj['country_code'].nunique()} countries"
    )

    # ARIMA has projected_tax_pct; IMF has overall_balance_pct_gdp, gdp_growth_real, etc.
    # Compare on overlapping years
    overlap_years = set(arima["year"].unique()) & set(imf_proj["year"].unique())
    logger.info(f"Overlapping projection years: {sorted(overlap_years)}")

    if overlap_years:
        arima_ov = arima[arima["year"].isin(overlap_years)][
            ["country_code", "year", "projected_tax_pct", "ci_lower", "ci_upper", "method"]
        ].copy()

        # IMF has fiscal balance, not tax/GDP directly; compare what we can
        imf_ov = imf_proj[imf_proj["year"].isin(overlap_years)].copy()

        comparison = arima_ov.merge(
            imf_ov[["country_code", "year", "overall_balance_pct_gdp",
                     "gdp_growth_real", "govt_debt_pct_gdp", "inflation_cpi"]],
            on=["country_code", "year"],
            how="inner",
        )
        logger.info(f"(a) Side-by-side overlap: {len(comparison)} country-year pairs")

        for _, row in comparison.iterrows():
            results_rows.append({
                "analysis": "a_sidebyside",
                "country_code": row["country_code"],
                "year": row["year"],
                "arima_tax_pct": round(row["projected_tax_pct"], 2),
                "arima_ci_lower": round(row["ci_lower"], 2) if pd.notna(row["ci_lower"]) else np.nan,
                "arima_ci_upper": round(row["ci_upper"], 2) if pd.notna(row["ci_upper"]) else np.nan,
                "arima_method": row["method"],
                "imf_fiscal_balance": (round(row["overall_balance_pct_gdp"], 2)
                                       if pd.notna(row["overall_balance_pct_gdp"]) else np.nan),
                "imf_gdp_growth": (round(row["gdp_growth_real"], 2)
                                   if pd.notna(row["gdp_growth_real"]) else np.nan),
                "imf_debt_pct_gdp": (round(row["govt_debt_pct_gdp"], 2)
                                     if pd.notna(row["govt_debt_pct_gdp"]) else np.nan),
                "imf_inflation": (round(row["inflation_cpi"], 2)
                                  if pd.notna(row["inflation_cpi"]) else np.nan),
            })

    # ════════════════════════════════════════════════════════════════
    # (b) Historical accuracy: compare fitted ARIMA vs actual for 2020-2024
    # ════════════════════════════════════════════════════════════════
    if not master.empty:
        # Get actual tax/GDP from master for recent years
        recent_actual = master[
            master["year"].between(2015, 2024)
        ][["country_code", "year", "tax_revenue_pct_gdp"]].dropna().copy()

        # IMF historical data
        imf_hist = imf[imf["is_projection"] == False].copy()

        # Compare IMF historical GDP growth with master fiscal data
        hist_compare = recent_actual.merge(
            imf_hist[["country_code", "year", "gdp_growth_real",
                      "overall_balance_pct_gdp", "govt_debt_pct_gdp"]],
            on=["country_code", "year"],
            how="inner",
        )

        if len(hist_compare) >= 20:
            # For countries with ARIMA projections, assess if simple trend
            # would have predicted recent changes well
            # Compute country-level tax/GDP change 2015-2019 vs 2020-2024
            pre_covid = recent_actual[recent_actual["year"].between(2015, 2019)]
            post_covid = recent_actual[recent_actual["year"].between(2020, 2024)]

            pre_mean = pre_covid.groupby("country_code")["tax_revenue_pct_gdp"].mean()
            post_mean = post_covid.groupby("country_code")["tax_revenue_pct_gdp"].mean()

            accuracy_df = pd.DataFrame({
                "pre_covid_mean_tax": pre_mean,
                "post_covid_mean_tax": post_mean,
            }).dropna()
            accuracy_df["actual_change"] = accuracy_df["post_covid_mean_tax"] - accuracy_df["pre_covid_mean_tax"]
            mae = accuracy_df["actual_change"].abs().mean()
            logger.info(
                f"(b) Historical volatility (pre- vs post-COVID tax/GDP): "
                f"MAE={mae:.3f} pp, n={len(accuracy_df)} countries"
            )

            for cc, row in accuracy_df.iterrows():
                results_rows.append({
                    "analysis": "b_historical_accuracy",
                    "country_code": cc,
                    "year": np.nan,
                    "pre_covid_mean_tax": round(row["pre_covid_mean_tax"], 2),
                    "post_covid_mean_tax": round(row["post_covid_mean_tax"], 2),
                    "actual_change_pp": round(row["actual_change"], 2),
                })

            # Summary row
            results_rows.append({
                "analysis": "b_historical_accuracy_summary",
                "country_code": "ALL",
                "year": np.nan,
                "n_countries": len(accuracy_df),
                "mae_change_pp": round(mae, 3),
                "mean_change_pp": round(accuracy_df["actual_change"].mean(), 3),
                "median_change_pp": round(accuracy_df["actual_change"].median(), 3),
                "pct_declined": round(
                    100 * (accuracy_df["actual_change"] < 0).mean(), 1
                ),
            })
        else:
            logger.warning(f"(b) Insufficient historical overlap: {len(hist_compare)}")

    # ════════════════════════════════════════════════════════════════
    # (c) Systematic bias: IMF vs trend-based projections
    # ════════════════════════════════════════════════════════════════
    # Compare IMF projected fiscal balance with ARIMA projected tax level
    # The comparison is imperfect (different variables) but informative
    if overlap_years and len(comparison) >= 10:
        # Where both ARIMA tax projection and IMF fiscal balance exist,
        # examine systematic patterns
        bias_df = comparison.dropna(subset=["projected_tax_pct", "overall_balance_pct_gdp"])

        if len(bias_df) >= 10:
            # Country-level: average projection values
            country_avg = bias_df.groupby("country_code").agg(
                mean_arima_tax=("projected_tax_pct", "mean"),
                mean_imf_balance=("overall_balance_pct_gdp", "mean"),
                mean_imf_growth=("gdp_growth_real", "mean"),
            ).reset_index()

            # Test: does IMF project positive growth for countries where
            # ARIMA projects declining tax/GDP?
            # Use master to get last actual tax/GDP
            if not master.empty:
                last_actual = (
                    master.sort_values("year")
                    .groupby("country_code")["tax_revenue_pct_gdp"]
                    .last()
                    .reset_index()
                    .rename(columns={"tax_revenue_pct_gdp": "last_actual_tax"})
                )
                country_avg = country_avg.merge(last_actual, on="country_code", how="left")
                country_avg["arima_direction"] = np.where(
                    country_avg["mean_arima_tax"] > country_avg["last_actual_tax"],
                    "increasing", "decreasing"
                )

                # IMF optimism check: positive growth projection
                country_avg["imf_growth_positive"] = country_avg["mean_imf_growth"] > 0

                n_arima_dec = (country_avg["arima_direction"] == "decreasing").sum()
                n_imf_opt = country_avg["imf_growth_positive"].sum()

                logger.info(
                    f"(c) Systematic bias: {n_arima_dec}/{len(country_avg)} countries "
                    f"have declining ARIMA tax trend; {n_imf_opt}/{len(country_avg)} "
                    f"have positive IMF growth projection"
                )

                # Mean IMF balance
                mean_bal = country_avg["mean_imf_balance"].mean()
                t_stat, p_val = stats.ttest_1samp(
                    country_avg["mean_imf_balance"].dropna(), 0
                )
                logger.info(
                    f"(c) IMF mean fiscal balance: {mean_bal:.2f}% GDP, "
                    f"t={t_stat:.2f}, p={p_val:.4f} (test vs zero)"
                )

                results_rows.append({
                    "analysis": "c_systematic_bias",
                    "country_code": "ALL",
                    "year": np.nan,
                    "n_countries": len(country_avg),
                    "mean_imf_fiscal_balance": round(mean_bal, 3),
                    "t_stat_vs_zero": round(t_stat, 3),
                    "p_value": round(p_val, 4),
                    "pct_arima_declining": round(
                        100 * n_arima_dec / len(country_avg), 1
                    ) if len(country_avg) > 0 else np.nan,
                    "pct_imf_positive_growth": round(
                        100 * n_imf_opt / len(country_avg), 1
                    ) if len(country_avg) > 0 else np.nan,
                    "interpretation": (
                        "IMF projects systematically positive fiscal balance"
                        if mean_bal > 0
                        else "IMF projects deficits on average"
                    ),
                })

    # ════════════════════════════════════════════════════════════════
    # (d) Coverage comparison
    # ════════════════════════════════════════════════════════════════
    arima_countries = set(arima["country_code"].unique())
    imf_proj_countries = set(imf_proj["country_code"].unique()) if not imf_proj.empty else set()
    imf_all_countries = set(imf["country_code"].unique())

    both = arima_countries & imf_proj_countries
    arima_only = arima_countries - imf_proj_countries
    imf_only = imf_proj_countries - arima_countries

    logger.info(
        f"(d) Coverage: ARIMA={len(arima_countries)}, IMF projections={len(imf_proj_countries)}, "
        f"both={len(both)}, ARIMA-only={len(arima_only)}, IMF-only={len(imf_only)}"
    )

    results_rows.append({
        "analysis": "d_coverage_summary",
        "country_code": "ALL",
        "year": np.nan,
        "n_arima": len(arima_countries),
        "n_imf_projections": len(imf_proj_countries),
        "n_imf_all": len(imf_all_countries),
        "n_both": len(both),
        "n_arima_only": len(arima_only),
        "n_imf_only": len(imf_only),
    })

    # List countries unique to each source
    for cc in sorted(arima_only):
        results_rows.append({
            "analysis": "d_arima_only",
            "country_code": cc,
            "year": np.nan,
        })
    for cc in sorted(imf_only):
        results_rows.append({
            "analysis": "d_imf_only",
            "country_code": cc,
            "year": np.nan,
        })

    # ── Build output ──
    if not results_rows:
        logger.error("No analysis produced results; aborting output.")
        return

    result_df = pd.DataFrame(results_rows)

    # Sort: summary/bias first, then side-by-side, then coverage details
    sort_order = {
        "c_systematic_bias": 0,
        "d_coverage_summary": 1,
        "b_historical_accuracy_summary": 2,
        "a_sidebyside": 3,
        "b_historical_accuracy": 4,
        "d_arima_only": 5,
        "d_imf_only": 6,
    }
    result_df["_sort"] = result_df["analysis"].map(sort_order).fillna(99)
    result_df = result_df.sort_values(["_sort", "country_code", "year"]).drop(columns=["_sort"])

    out_path = out / "forecast_comparison.xlsx"
    write_single_sheet_excel(result_df, out_path, sheet_name="Forecast Comparison")

    logger.info(
        f"[{MANIFEST['id']}] Complete: {len(result_df)} rows, "
        f"{result_df['analysis'].nunique()} analysis sections saved to {out_path.name}"
    )


if __name__ == "__main__":
    run()
