#!/usr/bin/env python3
"""
A198: Monetary-Fiscal Coordination
US-focused analysis of Fed balance sheet, M2 growth, Treasury holdings,
seigniorage, and QE-deficit linkages.
Stage: A | ID: A198
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
    "id": "A198",
    "name": "Monetary-Fiscal Coordination",
    "stage": "A",
    "description": "Fed balance sheet, M2, Treasury holdings, seigniorage, QE-deficit analysis",
    "depends_on": ["P111", "P106"],
    "inputs": [
        {"path": "Output/Data/us_monetary_panel.xlsx", "required": True},
        {"path": "Output/Data/us_mts_panel.xlsx", "required": False},
        {"path": "Output/Data/treasury_security_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/monetary_fiscal_coordination.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    monetary = read_excel_safe(out / "us_monetary_panel.xlsx")
    mts = read_excel_safe(out / "us_mts_panel.xlsx")
    treasury = read_excel_safe(out / "treasury_security_panel.xlsx")

    if monetary.empty:
        logger.error("Cannot load us_monetary_panel.xlsx; aborting.")
        return

    sheets = {}

    # ── 1. Fed balance sheet / GDP trend ──
    logger.info("1. Fed balance sheet / GDP trend...")
    mon = monetary.copy()
    if "date" in mon.columns:
        mon["date"] = pd.to_datetime(mon["date"])
    elif "month_end" in mon.columns:
        mon["date"] = pd.to_datetime(mon["month_end"])

    # WALCL = Fed total assets (millions)
    if "WALCL" in mon.columns:
        # Use GDP from master fiscal panel for USA
        master = read_excel_safe(out / "master_fiscal_panel.xlsx")
        if not master.empty and "gdp_current_usd" in master.columns:
            us_gdp = master[master["country_code"] == "USA"][["year", "gdp_current_usd"]].dropna()
            mon["year"] = mon["date"].dt.year if "date" in mon.columns else mon.get("year")
            mon = mon.merge(us_gdp, on="year", how="left")
            # WALCL is in millions, GDP is in current USD
            mask = mon["WALCL"].notna() & mon["gdp_current_usd"].notna() & (mon["gdp_current_usd"] > 0)
            mon.loc[mask, "fed_assets_pct_gdp"] = (
                mon.loc[mask, "WALCL"] * 1e6 / mon.loc[mask, "gdp_current_usd"] * 100
            )
            fed_trend = mon.dropna(subset=["fed_assets_pct_gdp"])[
                ["date", "year", "WALCL", "gdp_current_usd", "fed_assets_pct_gdp"]
            ].copy()
            sheets["fed_balance_sheet"] = fed_trend
            logger.info(f"  Fed/GDP: {len(fed_trend)} months, "
                        f"range {fed_trend['fed_assets_pct_gdp'].min():.1f}% to "
                        f"{fed_trend['fed_assets_pct_gdp'].max():.1f}%")

    # ── 2. M2 growth vs inflation correlation ──
    logger.info("2. M2 growth vs inflation...")
    m2_growth_col = None
    for c in ["M2SL_yoy", "M2_yoy", "M2SL_growth_yoy"]:
        if c in mon.columns:
            m2_growth_col = c
            break

    cpi_col = None
    for c in ["CPIAUCSL_yoy", "CPI_yoy", "CPIAUCSL_growth_yoy"]:
        if c in mon.columns:
            cpi_col = c
            break

    if m2_growth_col and cpi_col:
        valid = mon.dropna(subset=[m2_growth_col, cpi_col])
        if len(valid) > 12:
            corr = valid[m2_growth_col].corr(valid[cpi_col])
            # Lagged correlation (M2 leads CPI by 12-18 months)
            m2_lag12 = valid[m2_growth_col].shift(12)
            lag_corr = m2_lag12.corr(valid[cpi_col])
            logger.info(f"  M2-CPI correlation: contemporaneous={corr:.3f}, 12m lag={lag_corr:.3f}")

            m2_cpi = valid[["date", m2_growth_col, cpi_col]].copy()
            m2_cpi["m2_lag12"] = m2_lag12
            sheets["m2_inflation"] = m2_cpi

    # ── 3. Fed Treasury holdings as % of outstanding (from MSPD) ──
    logger.info("3. Fed Treasury holdings % outstanding...")
    if not treasury.empty and "WTREGEN" in mon.columns:
        # Treasury security panel has total_outstanding_bil by type
        total_by_date = (
            treasury.groupby("record_date")["total_outstanding_bil"]
            .sum()
            .reset_index()
            .rename(columns={"record_date": "date", "total_outstanding_bil": "total_mspd_bil"})
        )
        total_by_date["date"] = pd.to_datetime(total_by_date["date"])
        total_by_date["year_month"] = total_by_date["date"].dt.to_period("M")

        mon_copy = mon.copy()
        mon_copy["year_month"] = mon_copy["date"].dt.to_period("M")
        merged = mon_copy.merge(total_by_date[["year_month", "total_mspd_bil"]], on="year_month", how="inner")

        if not merged.empty and "WTREGEN" in merged.columns:
            # WTREGEN is in millions
            mask = merged["WTREGEN"].notna() & merged["total_mspd_bil"].notna() & (merged["total_mspd_bil"] > 0)
            merged.loc[mask, "fed_pct_outstanding"] = (
                merged.loc[mask, "WTREGEN"] / 1e3 / merged.loc[mask, "total_mspd_bil"] * 100
            )
            fed_holdings = merged.dropna(subset=["fed_pct_outstanding"])[
                ["date", "WTREGEN", "total_mspd_bil", "fed_pct_outstanding"]
            ].copy()
            sheets["fed_treasury_holdings"] = fed_holdings
            logger.info(f"  Fed holdings: {len(fed_holdings)} months, "
                        f"latest {fed_holdings.iloc[-1]['fed_pct_outstanding']:.1f}%")

    # ── 4. Seigniorage proxy: M0 growth * (M0/GDP) ──
    logger.info("4. Seigniorage proxy...")
    m0_col = None
    for c in ["BOGMBASE", "MBCURRCIR"]:
        if c in mon.columns:
            m0_col = c
            break

    if m0_col and "gdp_current_usd" in mon.columns:
        mask = mon[m0_col].notna() & mon["gdp_current_usd"].notna() & (mon["gdp_current_usd"] > 0)
        mon_s = mon.loc[mask].copy()
        mon_s["m0_pct_gdp"] = mon_s[m0_col] * 1e6 / mon_s["gdp_current_usd"] * 100
        mon_s["m0_growth"] = mon_s[m0_col].pct_change(periods=12)
        mon_s["seigniorage_proxy"] = mon_s["m0_growth"] * mon_s["m0_pct_gdp"]

        seign = mon_s.dropna(subset=["seigniorage_proxy"])[
            ["date", "year", m0_col, "m0_pct_gdp", "m0_growth", "seigniorage_proxy"]
        ].copy()
        if not seign.empty:
            sheets["seigniorage"] = seign
            logger.info(f"  Seigniorage: {len(seign)} months")

    # ── 5. QE periods vs fiscal deficit ──
    logger.info("5. QE periods vs fiscal deficit...")
    if not mts.empty and "WALCL" in mon.columns:
        # Aggregate MTS to annual
        mts_copy = mts.copy()
        mts_copy["record_date"] = pd.to_datetime(mts_copy["record_date"])

        # Get annual deficit from master
        master2 = read_excel_safe(out / "master_fiscal_panel.xlsx")
        if not master2.empty:
            us_fiscal = master2[master2["country_code"] == "USA"][
                ["year", "fiscal_balance_pct_gdp", "debt_pct_gdp"]
            ].dropna(subset=["fiscal_balance_pct_gdp"])

            # Annual Fed assets
            annual_fed = (
                mon.dropna(subset=["WALCL"])
                .groupby("year")["WALCL"]
                .last()
                .reset_index()
            )

            qe = us_fiscal.merge(annual_fed, on="year", how="inner")
            if "gdp_current_usd" in mon.columns:
                annual_gdp = mon.dropna(subset=["gdp_current_usd"]).groupby("year")["gdp_current_usd"].first().reset_index()
                qe = qe.merge(annual_gdp, on="year", how="left")
                mask = qe["WALCL"].notna() & qe["gdp_current_usd"].notna() & (qe["gdp_current_usd"] > 0)
                qe.loc[mask, "fed_assets_pct_gdp"] = (
                    qe.loc[mask, "WALCL"] * 1e6 / qe.loc[mask, "gdp_current_usd"] * 100
                )

            if not qe.empty:
                sheets["qe_vs_deficit"] = qe
                logger.info(f"  QE vs deficit: {len(qe)} years")

    # --- Write output ---
    if not sheets:
        logger.error("No analysis sheets produced; aborting.")
        return

    filepath = out / "monetary_fiscal_coordination.xlsx"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets.items():
            for col in sheet_df.select_dtypes(include=[np.number]).columns:
                sheet_df[col] = sheet_df[col].round(4)
            sheet_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    total_rows = sum(len(s) for s in sheets.values())
    logger.info(f"[{MANIFEST['id']}] Done. {len(sheets)} sheets, {total_rows} total rows")


if __name__ == "__main__":
    run()
