#!/usr/bin/env python3
"""
P85: Build Trade Panel
Classify trade structure type from WDI trade detail.
Stage: P | ID: P85
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
    "id": "P85",
    "name": "Build Trade Panel",
    "stage": "P",
    "description": "Trade panel with structure classification",
    "depends_on": ["L65"],
    "inputs": [
        {"path": "Technical/data/processed/wdi_trade_detail.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/trade_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def classify_trade_structure(row):
    """Classify trade structure based on export composition."""
    fuel = row.get("fuel_exports_pct", np.nan)
    ores = row.get("ores_metals_exports_pct", np.nan)
    manuf = row.get("manufactures_exports_pct", np.nan)

    # Need at least some data to classify
    if pd.isna(fuel) and pd.isna(ores) and pd.isna(manuf):
        return np.nan

    fuel = fuel if pd.notna(fuel) else 0
    ores = ores if pd.notna(ores) else 0
    manuf = manuf if pd.notna(manuf) else 0

    if fuel + ores > 50:
        return "commodity_exporter"
    elif manuf > 50:
        return "manufacturer"
    else:
        return "mixed"


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    processed = project_root() / "Technical" / "data" / "processed"
    out = output_data_dir()

    # --- Load ---
    df = read_excel_safe(processed / "wdi_trade_detail.xlsx")
    if df.empty:
        logger.error("Cannot load wdi_trade_detail.xlsx; aborting.")
        return
    logger.info(f"Loaded wdi_trade_detail: {len(df)} rows, {df['country_code'].nunique()} countries")

    panel = df.copy()

    # --- Classify trade structure ---
    panel["trade_structure_type"] = panel.apply(classify_trade_structure, axis=1)

    n_classified = panel["trade_structure_type"].notna().sum()
    logger.info(f"  trade_structure_type classified for {n_classified} rows")
    if n_classified > 0:
        for val, cnt in panel["trade_structure_type"].value_counts().items():
            logger.info(f"    {val}: {cnt}")

    # --- Sort and save ---
    panel = panel.sort_values(["country_code", "year"]).reset_index(drop=True)
    write_single_sheet_excel(panel, out / "trade_panel.xlsx")
    logger.info(f"Saved trade_panel.xlsx: {len(panel)} rows, "
                f"{panel['country_code'].nunique()} countries, {len(panel.columns)} cols")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
