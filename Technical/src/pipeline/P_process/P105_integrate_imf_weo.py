#!/usr/bin/env python3
"""
P105: Integrate IMF WEO
Merge IMF WEO forecasts with master panel, flag projection years.
Stage: P | ID: P105
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "P105",
    "name": "Integrate IMF WEO",
    "stage": "P",
    "description": "Merge IMF WEO with master panel and flag projections",
    "depends_on": ["L95"],
    "inputs": [
        {"path": "Technical/data/processed/imf_weo_panel.xlsx", "required": True},
        {"path": "Output/Data/master_panel.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/imf_weo_enriched.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}

# WDI equivalents for cross-validation
WDI_EQUIVALENTS = {
    "gdp_growth_real": "NY.GDP.MKTP.KD.ZG",
    "inflation_cpi": "FP.CPI.TOTL.ZG",
    "unemployment_rate": "SL.UEM.TOTL.ZS",
    "current_account_pct_gdp": "BN.CAB.XOKA.GD.ZS",
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    root = project_root()

    # Load WEO extraction
    weo_path = root / "Technical" / "data" / "processed" / "imf_weo_panel.xlsx"
    weo = pd.read_excel(weo_path)
    logger.info(f"WEO data: {len(weo)} rows")

    if len(weo) == 0:
        logger.warning("WEO panel is empty; creating placeholder output")
        write_single_sheet_excel(weo, out / "imf_weo_enriched.xlsx")
        logger.info("Saved imf_weo_enriched.xlsx (empty)")
        return

    # Try to load master panel for cross-validation
    master_path = out / "master_panel.xlsx"
    master = None
    if master_path.exists():
        try:
            master = pd.read_excel(master_path)
            logger.info(f"Master panel: {len(master)} rows for cross-validation")
        except Exception as e:
            logger.warning(f"Could not load master panel: {e}")

    # Cross-validate WEO with master panel where both have data
    if master is not None and len(weo) > 0:
        # Check GDP growth correlation
        for weo_col, wdi_desc in WDI_EQUIVALENTS.items():
            if weo_col not in weo.columns:
                continue
            # Look for matching column in master
            for m_col in master.columns:
                if "gdp" in m_col.lower() and "growth" in m_col.lower() and weo_col == "gdp_growth_real":
                    merged = weo[["country_code", "year", weo_col]].merge(
                        master[["country_code", "year", m_col]],
                        on=["country_code", "year"],
                        how="inner",
                    )
                    both_valid = merged.dropna(subset=[weo_col, m_col])
                    if len(both_valid) > 10:
                        corr = both_valid[weo_col].corr(both_valid[m_col])
                        logger.info(f"Cross-validation {weo_col} vs {m_col}: r={corr:.3f} (n={len(both_valid)})")
                    break

    # Enrich: add data quality flags
    value_cols = [c for c in weo.columns if c not in ("country_code", "year", "is_projection")]
    weo["n_variables"] = weo[value_cols].notna().sum(axis=1)

    # Separate historical and projection data
    if "is_projection" in weo.columns:
        n_hist = (~weo["is_projection"]).sum()
        n_proj = weo["is_projection"].sum()
        logger.info(f"Historical: {n_hist} rows, Projections: {n_proj} rows")

    # Summary by variable
    for col in value_cols:
        if col in weo.columns:
            n = weo[col].notna().sum()
            if n > 0:
                logger.info(f"  {col}: {n} obs, mean={weo[col].mean():.2f}")

    # Sort and save
    weo = weo.sort_values(["country_code", "year"]).reset_index(drop=True)

    n_countries = weo["country_code"].nunique()
    logger.info(f"IMF WEO enriched: {len(weo)} rows, {n_countries} countries")

    write_single_sheet_excel(weo, out / "imf_weo_enriched.xlsx")
    logger.info("Saved imf_weo_enriched.xlsx")


if __name__ == "__main__":
    run()
