#!/usr/bin/env python3
"""
A155: Inequality Deep Analysis
Cross-domain analysis linking inequality panels with fiscal regime, revenue
composition, and tax data.  Examines tax progressivity vs inequality, wealth
concentration by regime, pre/post-tax Gini gaps, and trend dynamics.
Stage: A | ID: A155
Project: Gerhard

MANIFEST depends_on: ["P100"]
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
    "id": "A155",
    "name": "Inequality Deep Analysis",
    "stage": "A",
    "description": (
        "Cross-domain inequality analysis: tax progressivity, wealth concentration, "
        "pre/post-tax Gini, inequality trends by fiscal regime"
    ),
    "depends_on": ["P100"],
    "inputs": [
        {"path": "Output/Data/inequality_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": False},
        {"path": "Output/Data/fiscal_regime_taxonomy.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/inequality_deep_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    ineq = read_excel_safe(out / "inequality_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    rev_comp = read_excel_safe(out / "revenue_composition_panel.xlsx")
    regimes = read_excel_safe(out / "fiscal_regime_taxonomy.xlsx")

    if ineq.empty or master.empty:
        logger.error("Cannot load inequality_panel or master_fiscal_panel; aborting.")
        return

    logger.info(
        f"Inequality panel: {len(ineq)} rows, {ineq['country_code'].nunique()} countries"
    )

    # ── Merge inequality with master fiscal ──
    master_cols = [
        "country_code", "year", "tax_revenue_pct_gdp", "income_group",
        "expenditure_pct_gdp", "country_name", "region",
    ]
    master_sub = master[[c for c in master_cols if c in master.columns]].drop_duplicates(
        subset=["country_code", "year"]
    )
    merged = ineq.merge(master_sub, on=["country_code", "year"], how="inner",
                        suffixes=("", "_master"))
    # Resolve duplicate country_name
    if "country_name_master" in merged.columns:
        merged["country_name"] = merged["country_name"].fillna(merged["country_name_master"])
        merged.drop(columns=["country_name_master"], inplace=True)

    # Merge revenue composition
    if not rev_comp.empty:
        rc_cols = ["country_code", "year", "income_tax_pct_revenue",
                   "goods_services_tax_pct_revenue", "trade_tax_pct_revenue",
                   "tax_diversification_index"]
        rc_sub = rev_comp[[c for c in rc_cols if c in rev_comp.columns]].drop_duplicates(
            subset=["country_code", "year"]
        )
        merged = merged.merge(rc_sub, on=["country_code", "year"], how="left")

    # Merge regime classification (cross-section)
    if not regimes.empty:
        regime_cols = ["country_code", "fiscal_regime", "cluster_name"]
        regime_sub = regimes[[c for c in regime_cols if c in regimes.columns]]
        merged = merged.merge(regime_sub, on="country_code", how="left")

    logger.info(
        f"Merged dataset: {len(merged)} rows, {merged['country_code'].nunique()} countries"
    )

    results_rows = []

    # ════════════════════════════════════════════════════════════════
    # (a) Tax progressivity vs inequality
    # ════════════════════════════════════════════════════════════════
    if "income_tax_pct_revenue" in merged.columns and "top10_income_share" in merged.columns:
        prog_df = merged.dropna(subset=["income_tax_pct_revenue", "top10_income_share"])
        prog_latest = prog_df.sort_values("year").groupby("country_code").last().reset_index()

        if len(prog_latest) >= 15:
            slope, intercept, r_val, p_val, se = stats.linregress(
                prog_latest["income_tax_pct_revenue"], prog_latest["top10_income_share"]
            )
            corr_val = prog_latest["income_tax_pct_revenue"].corr(
                prog_latest["top10_income_share"]
            )
            interpretation = (
                "Higher income-tax reliance associated with LOWER top-10 share"
                if slope < 0
                else "No clear negative relationship; higher income-tax reliance "
                     "does NOT reduce top-10 share"
            )
            logger.info(
                f"(a) Tax progressivity vs top10: r={corr_val:.3f}, slope={slope:.4f}, "
                f"p={p_val:.4f}, n={len(prog_latest)} -> {interpretation}"
            )
            for _, row in prog_latest.iterrows():
                results_rows.append({
                    "analysis": "a_tax_progressivity",
                    "country_code": row["country_code"],
                    "country_name": row.get("country_name", ""),
                    "year": row["year"],
                    "income_tax_pct_revenue": round(row["income_tax_pct_revenue"], 2),
                    "top10_income_share": round(row["top10_income_share"], 2),
                    "regression_slope": round(slope, 4),
                    "regression_r2": round(r_val ** 2, 4),
                    "regression_p": round(p_val, 6),
                    "correlation": round(corr_val, 4),
                    "interpretation": interpretation,
                })
        else:
            logger.warning(f"(a) Insufficient overlap for tax progressivity: {len(prog_latest)}")

    # ════════════════════════════════════════════════════════════════
    # (b) Wealth concentration vs fiscal regime
    # ════════════════════════════════════════════════════════════════
    if "fiscal_regime" in merged.columns and "top1_wealth_share" in merged.columns:
        wealth_df = merged.dropna(subset=["fiscal_regime", "top1_wealth_share"])
        wealth_latest = wealth_df.sort_values("year").groupby("country_code").last().reset_index()

        if len(wealth_latest) >= 5:
            regime_wealth = (
                wealth_latest.groupby("fiscal_regime")
                .agg(
                    mean_top1_wealth=("top1_wealth_share", "mean"),
                    median_top1_wealth=("top1_wealth_share", "median"),
                    mean_top10_wealth=("top10_wealth_share", lambda x: x.mean()
                                       if "top10_wealth_share" in wealth_latest.columns
                                       else np.nan),
                    n_countries=("country_code", "nunique"),
                )
                .round(3)
                .reset_index()
            )
            logger.info(f"(b) Wealth concentration by regime:\n{regime_wealth.to_string(index=False)}")
            for _, row in regime_wealth.iterrows():
                results_rows.append({
                    "analysis": "b_wealth_by_regime",
                    "country_code": "",
                    "country_name": row["fiscal_regime"],
                    "year": np.nan,
                    "mean_top1_wealth": row["mean_top1_wealth"],
                    "median_top1_wealth": row["median_top1_wealth"],
                    "n_countries_regime": row["n_countries"],
                    "interpretation": "",
                })
        else:
            logger.warning(f"(b) Insufficient wealth-regime overlap: {len(wealth_latest)}")

    # ════════════════════════════════════════════════════════════════
    # (c) Pre-tax vs post-tax inequality (Gini WB vs Gini WID)
    # ════════════════════════════════════════════════════════════════
    gini_both = merged.dropna(subset=["gini_wb", "gini_wid"])
    if len(gini_both) >= 10:
        gini_both = gini_both.copy()
        gini_both["gini_gap"] = gini_both["gini_wid"] - gini_both["gini_wb"]
        gini_both["redistribution_pct"] = (
            100 * gini_both["gini_gap"] / gini_both["gini_wid"]
        ).round(1)

        gini_latest = gini_both.sort_values("year").groupby("country_code").last().reset_index()
        mean_gap = gini_latest["gini_gap"].mean()
        median_gap = gini_latest["gini_gap"].median()
        logger.info(
            f"(c) Pre-vs-post-tax Gini: n={len(gini_latest)}, "
            f"mean_gap(WID-WB)={mean_gap:.3f}, median_gap={median_gap:.3f}"
        )

        # By income group
        if "income_group" in gini_latest.columns:
            ig_gaps = (
                gini_latest.groupby("income_group")
                .agg(
                    mean_gini_wb=("gini_wb", "mean"),
                    mean_gini_wid=("gini_wid", "mean"),
                    mean_gini_gap=("gini_gap", "mean"),
                    mean_redistribution_pct=("redistribution_pct", "mean"),
                    n=("country_code", "nunique"),
                )
                .round(3)
                .reset_index()
            )
            logger.info(f"(c) Gini gap by income group:\n{ig_gaps.to_string(index=False)}")

        for _, row in gini_latest.iterrows():
            results_rows.append({
                "analysis": "c_pretax_posttax",
                "country_code": row["country_code"],
                "country_name": row.get("country_name", ""),
                "year": row["year"],
                "gini_wb": round(row["gini_wb"], 3),
                "gini_wid": round(row["gini_wid"], 3),
                "gini_gap": round(row["gini_gap"], 3),
                "redistribution_pct": row["redistribution_pct"],
                "interpretation": (
                    "Positive gap = fiscal redistribution narrows inequality"
                    if row["gini_gap"] > 0
                    else "Negative/zero gap = minimal fiscal redistribution"
                ),
            })
    else:
        logger.warning(f"(c) Insufficient dual-Gini data: {len(gini_both)} rows")

    # ════════════════════════════════════════════════════════════════
    # (d) Inequality trends by regime (1990-2024)
    # ════════════════════════════════════════════════════════════════
    if "fiscal_regime" in merged.columns:
        trend_df = merged[
            (merged["year"] >= 1990) & (merged["year"] <= 2024)
        ].dropna(subset=["fiscal_regime", "gini_wb"])

        if len(trend_df) >= 20:
            # Compute 5-year bins
            trend_df = trend_df.copy()
            trend_df["period"] = pd.cut(
                trend_df["year"],
                bins=[1989, 1994, 1999, 2004, 2009, 2014, 2019, 2025],
                labels=["1990-94", "1995-99", "2000-04", "2005-09",
                        "2010-14", "2015-19", "2020-24"],
            )
            regime_trends = (
                trend_df.groupby(["fiscal_regime", "period"], observed=True)
                .agg(mean_gini=("gini_wb", "mean"), n_obs=("country_code", "count"))
                .round(3)
                .reset_index()
            )
            logger.info(f"(d) Inequality trends by regime: {len(regime_trends)} period-regime cells")

            # Per-regime linear trend (year coefficient)
            for regime, grp in trend_df.groupby("fiscal_regime"):
                if len(grp) >= 10:
                    slope, _, r_val, p_val, _ = stats.linregress(grp["year"], grp["gini_wb"])
                    direction = "rising" if slope > 0.001 else ("falling" if slope < -0.001 else "stable")
                    results_rows.append({
                        "analysis": "d_trend_by_regime",
                        "country_code": "",
                        "country_name": str(regime),
                        "year": np.nan,
                        "gini_trend_slope": round(slope, 5),
                        "gini_trend_r2": round(r_val ** 2, 4),
                        "gini_trend_p": round(p_val, 4),
                        "trend_direction": direction,
                        "n_obs": len(grp),
                        "interpretation": f"{regime}: Gini is {direction} "
                                          f"(slope={slope:.5f}/yr, p={p_val:.4f})",
                    })
        else:
            logger.warning(f"(d) Insufficient trend data: {len(trend_df)}")

    # ════════════════════════════════════════════════════════════════
    # (e) Summary table by income group
    # ════════════════════════════════════════════════════════════════
    latest = merged.sort_values("year").groupby("country_code").last().reset_index()
    if "income_group" in latest.columns:
        ig_groups = latest.dropna(subset=["income_group"]).groupby("income_group")

        for ig, grp in ig_groups:
            row_dict = {
                "analysis": "e_income_group_summary",
                "country_code": "",
                "country_name": str(ig),
                "year": np.nan,
                "n_countries": grp["country_code"].nunique(),
            }
            for col, label in [
                ("gini_wb", "mean_gini"),
                ("top1_income_share", "mean_top1_share"),
                ("bottom50_income_share", "mean_bottom50_share"),
                ("tax_revenue_pct_gdp", "mean_tax_pct_gdp"),
            ]:
                if col in grp.columns:
                    row_dict[label] = round(grp[col].mean(), 3) if grp[col].notna().any() else np.nan

            # Correlation tax vs gini within income group
            tax_gini = grp.dropna(subset=["gini_wb", "tax_revenue_pct_gdp"])
            if len(tax_gini) >= 5:
                row_dict["corr_tax_gini"] = round(
                    tax_gini["tax_revenue_pct_gdp"].corr(tax_gini["gini_wb"]), 3
                )
            else:
                row_dict["corr_tax_gini"] = np.nan

            results_rows.append(row_dict)

    # ── Build output ──
    if not results_rows:
        logger.error("No analysis produced results; aborting output.")
        return

    result_df = pd.DataFrame(results_rows)

    # Sort: summary first, then per-country analyses
    sort_order = {
        "e_income_group_summary": 0,
        "d_trend_by_regime": 1,
        "b_wealth_by_regime": 2,
        "a_tax_progressivity": 3,
        "c_pretax_posttax": 4,
    }
    result_df["_sort"] = result_df["analysis"].map(sort_order).fillna(99)
    result_df = result_df.sort_values(["_sort", "analysis", "country_code"]).drop(
        columns=["_sort"]
    )

    out_path = out / "inequality_deep_analysis.xlsx"
    write_single_sheet_excel(result_df, out_path, sheet_name="Inequality Deep Analysis")

    logger.info(
        f"[{MANIFEST['id']}] Complete: {len(result_df)} rows, "
        f"{result_df['analysis'].nunique()} analysis sections saved to {out_path.name}"
    )


if __name__ == "__main__":
    run()
