#!/usr/bin/env python3
"""
A175: Yield Curve Analysis
Regime analysis, inversion episodes, cross-maturity correlations, and fiscal linkages.
Stage: A | ID: A175
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
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A175",
    "name": "Yield Curve Analysis",
    "stage": "A",
    "description": "Yield curve regime analysis, inversions, correlations, and fiscal linkages",
    "depends_on": ["P120"],
    "inputs": [
        {"path": "Output/Data/yield_curve_monthly.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/yield_curve_analysis.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}

KEY_MATURITIES = ["DGS1MO", "DGS3MO", "DGS1", "DGS2", "DGS3", "DGS5", "DGS7", "DGS10", "DGS20", "DGS30"]


def find_inversion_episodes(df):
    """Identify yield curve inversion episodes (10Y < 2Y)."""
    df = df.sort_values("month_end").copy()
    df["inverted"] = df["inversion_flag"] == 1

    episodes = []
    in_episode = False
    start = None
    max_depth = 0

    for _, row in df.iterrows():
        if row["inverted"] and not in_episode:
            in_episode = True
            start = row["month_end"]
            max_depth = row["term_spread_10y2y"]
        elif row["inverted"] and in_episode:
            if pd.notna(row["term_spread_10y2y"]):
                max_depth = min(max_depth, row["term_spread_10y2y"])
        elif not row["inverted"] and in_episode:
            in_episode = False
            end = row["month_end"]
            duration = (pd.Timestamp(end) - pd.Timestamp(start)).days / 30.44
            episodes.append({
                "start_date": start,
                "end_date": end,
                "duration_months": round(duration, 1),
                "max_inversion_depth_pct": round(max_depth, 3),
            })

    # Handle ongoing inversion
    if in_episode:
        end = df["month_end"].max()
        duration = (pd.Timestamp(end) - pd.Timestamp(start)).days / 30.44
        episodes.append({
            "start_date": start,
            "end_date": end,
            "duration_months": round(duration, 1),
            "max_inversion_depth_pct": round(max_depth, 3),
        })

    return pd.DataFrame(episodes)


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    # --- Load yield curve monthly ---
    yc = read_excel_safe(out / "yield_curve_monthly.xlsx")
    if yc.empty:
        logger.error("Yield curve monthly panel is empty")
        return

    yc["month_end"] = pd.to_datetime(yc["month_end"])
    yc["year"] = yc["month_end"].dt.year
    yc["decade"] = (yc["year"] // 10) * 10
    logger.info(f"Yield curve monthly: {len(yc)} rows")

    # --- 1. Regime frequency by decade ---
    logger.info("Computing regime frequencies by decade...")
    regime_by_decade = yc.groupby(["decade", "curve_regime"]).size().unstack(fill_value=0)
    regime_pct = regime_by_decade.div(regime_by_decade.sum(axis=1), axis=0) * 100
    regime_pct = regime_pct.round(1).reset_index()
    logger.info(f"Regime summary: {len(regime_pct)} decades")

    # --- 2. Inversion episodes ---
    logger.info("Finding inversion episodes...")
    episodes = find_inversion_episodes(yc)
    logger.info(f"Found {len(episodes)} inversion episodes")
    for _, ep in episodes.iterrows():
        logger.info(f"  {ep['start_date']} to {ep['end_date']}: "
                     f"{ep['duration_months']} months, depth={ep['max_inversion_depth_pct']}%")

    # --- 3. Cross-maturity correlation matrix ---
    logger.info("Computing cross-maturity correlation matrix...")
    available_mats = [c for c in KEY_MATURITIES if c in yc.columns]
    corr_matrix = yc[available_mats].corr().round(3)
    corr_df = corr_matrix.reset_index().rename(columns={"index": "maturity"})

    # --- 4. Volatility by maturity (rolling 12-month std dev) ---
    logger.info("Computing rolling volatility by maturity...")
    yc_sorted = yc.sort_values("month_end")
    vol_records = []
    for mat in available_mats:
        rolling_vol = yc_sorted[mat].rolling(12, min_periods=6).std()
        vol_records.append({
            "maturity": mat,
            "avg_vol_12m": rolling_vol.mean(),
            "max_vol_12m": rolling_vol.max(),
            "current_vol_12m": rolling_vol.iloc[-1] if len(rolling_vol) > 0 else np.nan,
        })
    vol_df = pd.DataFrame(vol_records).round(4)
    logger.info(f"Volatility computed for {len(vol_df)} maturities")

    # --- 5. Term premium proxy ---
    logger.info("Computing term premium proxy...")
    if "DGS10" in yc.columns and "DGS1" in yc.columns:
        yc_sorted["dgs1_rolling_10y"] = yc_sorted["DGS1"].rolling(120, min_periods=60).mean()
        yc_sorted["term_premium_proxy"] = yc_sorted["DGS10"] - yc_sorted["dgs1_rolling_10y"]

    # --- 6. Fiscal correlation ---
    logger.info("Loading fiscal data for deficit-yield correlation...")
    fiscal = read_excel_safe(out / "master_fiscal_panel.xlsx")
    fiscal_corr_df = pd.DataFrame()

    if not fiscal.empty and "fiscal_balance_pct_gdp" in fiscal.columns:
        us_fiscal = fiscal[fiscal["country_code"] == "USA"].copy()
        if not us_fiscal.empty:
            us_fiscal["year"] = pd.to_numeric(us_fiscal["year"], errors="coerce")
            yc_annual = yc.groupby("year").agg({
                "DGS10": "mean",
                "term_spread_10y2y": "mean",
                "DFF": "mean",
            }).reset_index()

            merged = pd.merge(us_fiscal[["year", "fiscal_balance_pct_gdp", "debt_pct_gdp"]],
                              yc_annual, on="year", how="inner")

            if len(merged) > 5:
                corrs = {
                    "deficit_vs_10y_yield": merged["fiscal_balance_pct_gdp"].corr(merged["DGS10"]),
                    "deficit_vs_term_spread": merged["fiscal_balance_pct_gdp"].corr(merged["term_spread_10y2y"]),
                    "deficit_vs_fed_funds": merged["fiscal_balance_pct_gdp"].corr(merged["DFF"]),
                    "debt_vs_10y_yield": merged["debt_pct_gdp"].corr(merged["DGS10"]) if "debt_pct_gdp" in merged.columns else np.nan,
                    "n_years": len(merged),
                }
                fiscal_corr_df = pd.DataFrame([corrs])
                logger.info(f"Fiscal correlations (n={len(merged)} years):")
                for k, v in corrs.items():
                    if k != "n_years":
                        logger.info(f"  {k}: {v:.3f}")
    else:
        logger.warning("No fiscal data available for correlation analysis")

    # --- Write output (multiple sheets via separate files, or combine into one) ---
    # Combine key results into a single summary DataFrame
    summary_rows = []

    # Add regime summary
    for _, row in regime_pct.iterrows():
        summary_rows.append({
            "section": "regime_by_decade",
            "key": f"decade_{int(row['decade'])}",
            **{col: row[col] for col in regime_pct.columns if col != "decade"},
        })

    # Add inversion episodes
    for _, row in episodes.iterrows():
        summary_rows.append({
            "section": "inversion_episode",
            "key": str(row["start_date"]),
            **row.to_dict(),
        })

    # Add volatility
    for _, row in vol_df.iterrows():
        summary_rows.append({
            "section": "volatility",
            "key": row["maturity"],
            **row.to_dict(),
        })

    # Add fiscal correlations
    if not fiscal_corr_df.empty:
        for _, row in fiscal_corr_df.iterrows():
            summary_rows.append({
                "section": "fiscal_correlation",
                "key": "us_annual",
                **row.to_dict(),
            })

    summary = pd.DataFrame(summary_rows)

    # Also write the correlation matrix as the primary output (most useful)
    # Combine: correlation matrix + episodes + regime + volatility
    write_single_sheet_excel(corr_df, out / "yield_curve_analysis.xlsx", sheet_name="Analysis")

    # Write the full analysis summary separately for completeness
    write_single_sheet_excel(summary, out / "yield_curve_analysis_detail.xlsx", sheet_name="Detail")

    logger.info(f"[{MANIFEST['id']}] Done. {len(episodes)} inversion episodes, "
                f"{len(corr_df)} maturity correlations")


if __name__ == "__main__":
    run()
