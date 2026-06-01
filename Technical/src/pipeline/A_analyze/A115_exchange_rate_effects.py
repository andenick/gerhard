#!/usr/bin/env python3
"""
A115: Exchange Rate Effects on Fiscal Variables
Analyze REER-tax correlation, Olivera-Tanzi effect, currency crisis episodes, and PPP notes.
Stage: A | ID: A115
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
    "id": "A115",
    "name": "Exchange Rate Effects",
    "stage": "A",
    "description": "Analyze REER-tax correlation, Olivera-Tanzi effect, currency crises, and PPP considerations",
    "depends_on": ["P80"],
    "inputs": [
        {"path": "Output/Data/exchange_rate_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/exchange_rate_fiscal_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    exr = read_excel_safe(out / "exchange_rate_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if exr.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    logger.info(f"Exchange rate panel: {len(exr)} rows, {exr['country_code'].nunique()} countries")

    # Merge fiscal data
    fiscal_cols = ["country_code", "year", "tax_revenue_pct_gdp", "income_group",
                   "gdp_current_usd", "country_name"]
    master_sub = master[[c for c in fiscal_cols if c in master.columns]].drop_duplicates(
        subset=["country_code", "year"])
    merged = exr.merge(master_sub, on=["country_code", "year"], how="inner",
                       suffixes=("", "_master"))
    if "country_name_master" in merged.columns:
        merged["country_name"] = merged["country_name"].fillna(merged["country_name_master"])
        merged.drop(columns=["country_name_master"], inplace=True)

    logger.info(f"Merged EXR-fiscal: {len(merged)} rows")

    # Compute YoY tax change
    merged = merged.sort_values(["country_code", "year"])
    merged["tax_change_yoy"] = merged.groupby("country_code")["tax_revenue_pct_gdp"].diff()

    # ── 1. REER-Tax Correlation ──
    reer_tax = merged.dropna(subset=["reer_change_pct", "tax_change_yoy"])
    if len(reer_tax) > 20:
        corr, p_val = stats.pearsonr(reer_tax["reer_change_pct"], reer_tax["tax_change_yoy"])
        logger.info(f"REER-tax change correlation: r={corr:.4f}, p={p_val:.4f}, n={len(reer_tax)}")
    else:
        corr, p_val = np.nan, np.nan
        logger.warning("Insufficient data for REER-tax correlation")

    # ── 2. Olivera-Tanzi Effect ──
    # For countries with inflation > 10%, does higher inflation reduce next-year real tax?
    high_infl = merged[merged["inflation_pct"] > 10].copy()
    high_infl["tax_next_year"] = high_infl.groupby("country_code")["tax_revenue_pct_gdp"].shift(-1)
    ot_data = high_infl.dropna(subset=["inflation_pct", "tax_next_year"])
    ot_result = {}
    if len(ot_data) > 20:
        slope, intercept, r_val, p_val_ot, se = stats.linregress(
            ot_data["inflation_pct"].values, ot_data["tax_next_year"].values
        )
        ot_result = {
            "slope": round(slope, 5),
            "r_squared": round(r_val ** 2, 4),
            "p_value": round(p_val_ot, 6),
            "n_obs": len(ot_data),
            "interpretation": "negative slope supports Olivera-Tanzi" if slope < 0 else "no Olivera-Tanzi evidence",
        }
        logger.info(f"Olivera-Tanzi: slope={ot_result['slope']}, R2={ot_result['r_squared']}, "
                     f"p={ot_result['p_value']} -> {ot_result['interpretation']}")
    else:
        logger.warning(f"Insufficient high-inflation observations for Olivera-Tanzi: {len(ot_data)}")

    # ── 3. Currency Crisis Episodes ──
    crises = merged[merged["reer_change_pct"] < -15].copy()
    crises["decade"] = (crises["year"] // 10 * 10).astype(int)
    crisis_by_decade = crises.groupby("decade").agg(
        n_episodes=("country_code", "count"),
        n_countries=("country_code", "nunique"),
    ).reset_index()
    logger.info(f"Currency crisis episodes (REER drop > 15%):\n{crisis_by_decade.to_string(index=False)}")

    # Top crisis countries
    crisis_countries = crises.groupby(["country_code", "country_name"]).size().reset_index(name="n_crises")
    crisis_countries = crisis_countries.sort_values("n_crises", ascending=False).head(20)

    # ── 4. PPP Comparison Note ──
    ppp_note = ("WDI tax data expressed as % of GDP is scale-free and requires no exchange rate "
                "conversion for cross-country comparison. Exchange rate effects matter only for "
                "absolute USD comparisons (e.g., total tax revenue in USD). REER movements may "
                "indirectly affect tax-to-GDP ratios through trade channel effects on the tax base.")

    # ── Build output ──
    country_latest = merged.sort_values("year").groupby("country_code").last().reset_index()
    result = country_latest[["country_code", "country_name", "year", "income_group"]].copy()

    for col in ["inflation_pct", "reer_change_pct", "tax_revenue_pct_gdp",
                "exchange_rate_lcu_per_usd", "reer_index"]:
        if col in country_latest.columns:
            result[col] = country_latest[col]

    # Add analysis results
    result["reer_tax_corr"] = round(corr, 4) if not np.isnan(corr) else np.nan
    result["reer_tax_corr_p"] = round(p_val, 4) if not np.isnan(p_val) else np.nan

    if ot_result:
        result["olivera_tanzi_slope"] = ot_result["slope"]
        result["olivera_tanzi_r2"] = ot_result["r_squared"]

    # Count crises per country
    crisis_count = crises.groupby("country_code").size().reset_index(name="n_currency_crises")
    result = result.merge(crisis_count, on="country_code", how="left")
    result["n_currency_crises"] = result["n_currency_crises"].fillna(0).astype(int)

    result["ppp_note"] = ppp_note

    out_path = out / "exchange_rate_fiscal_analysis.xlsx"
    write_single_sheet_excel(result, out_path, sheet_name="Exchange Rate Effects")
    logger.info(f"[{MANIFEST['id']}] Saved {len(result)} rows to {out_path}")


if __name__ == "__main__":
    run()
