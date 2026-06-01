#!/usr/bin/env python3
"""
P90: Build Debt Composition Panel
Compute PPG share and composite debt risk score from WDI debt detail.
Stage: P | ID: P90
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
    "id": "P90",
    "name": "Build Debt Composition Panel",
    "stage": "P",
    "description": "Debt composition with PPG share and risk score",
    "depends_on": ["L75"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_debt_detail.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/debt_composition_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_debt_detail.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_debt_detail.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_debt_detail: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- PPG as % of total external debt ---
    if "ppg_debt_usd" in panel.columns and "external_debt_total_usd" in panel.columns:
        mask = panel["ppg_debt_usd"].notna() & panel["external_debt_total_usd"].notna() & (panel["external_debt_total_usd"] != 0)
        panel["ppg_pct_total"] = np.where(
            mask,
            panel["ppg_debt_usd"] / panel["external_debt_total_usd"] * 100,
            np.nan,
        )
        logger.info(f"  ppg_pct_total computed for {mask.sum()} rows")

    # --- Composite debt risk score ---
    # Normalized: (short_term_pct_reserves/100 + debt_service_pct_gni/20 + external_debt_pct_gni/200) / 3
    # Clipped to [0, 1]
    comp1 = panel.get("short_term_pct_reserves", pd.Series(np.nan, index=panel.index)) / 100
    comp2 = panel.get("debt_service_pct_gni", pd.Series(np.nan, index=panel.index)) / 20
    comp3 = panel.get("external_debt_pct_gni", pd.Series(np.nan, index=panel.index)) / 200

    # Average of available components
    components = pd.DataFrame({"c1": comp1, "c2": comp2, "c3": comp3})
    panel["debt_risk_score"] = components.mean(axis=1, skipna=True)
    panel["debt_risk_score"] = panel["debt_risk_score"].clip(0, 1)

    n_risk = panel["debt_risk_score"].notna().sum()
    logger.info(f"  debt_risk_score computed for {n_risk} rows")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "debt_composition_panel.xlsx")
    logger.info(f"Saved debt_composition_panel.xlsx: {len(panel)} rows, "
                f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
