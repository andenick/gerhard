#!/usr/bin/env python3
"""
P98: Build Aggregates Panel
Compute group-level summary statistics (region, income_group, global)
across all companion panels, weighted by GDP.
Stage: P | ID: P98
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
    "id": "P98",
    "name": "Build Aggregates Panel",
    "stage": "P",
    "description": "Group-level statistics across all companion panels",
    "depends_on": ["P65", "P70", "P75", "P80", "P85", "P90", "P95", "P97"],
    "inputs": [
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/expenditure_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/bop_panel.xlsx", "required": True},
        {"path": "Output/Data/exchange_rate_panel.xlsx", "required": True},
        {"path": "Output/Data/trade_panel.xlsx", "required": True},
        {"path": "Output/Data/debt_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/social_outcomes_panel.xlsx", "required": True},
        {"path": "Output/Data/national_accounts_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/aggregates_panel.xlsx"}],
    "timeout": 300,
    "parallel_safe": True,
}

PANEL_FILES = {
    "revenue_composition": "revenue_composition_panel.xlsx",
    "expenditure_composition": "expenditure_composition_panel.xlsx",
    "bop": "bop_panel.xlsx",
    "exchange_rate": "exchange_rate_panel.xlsx",
    "trade": "trade_panel.xlsx",
    "debt_composition": "debt_composition_panel.xlsx",
    "social_outcomes": "social_outcomes_panel.xlsx",
    "national_accounts": "national_accounts_panel.xlsx",
}

# Non-numeric columns to exclude from aggregation
SKIP_COLS = {
    "country_code", "country_name", "year", "region", "income_group",
    "trade_structure_type", "is_outlier", "quality_tier", "data_completeness",
    "debt_source", "interpolated",
}


def weighted_mean(values, weights):
    """Compute weighted mean, ignoring NaN in either."""
    mask = values.notna() & weights.notna() & (weights > 0)
    if mask.sum() == 0:
        return np.nan
    return np.average(values[mask], weights=weights[mask])


def compute_group_stats(df, group_col, group_name, year, var, gdp_series):
    """Compute stats for one group-variable-year combination."""
    vals = df[var].dropna()
    if len(vals) == 0:
        return None

    row = {
        "aggregate_type": group_col if group_col != "global" else "global",
        "aggregate_name": group_name,
        "year": year,
        "variable": var,
        "mean": vals.mean(),
        "median": vals.median(),
        "n_countries": len(vals),
        "min": vals.min(),
        "max": vals.max(),
    }

    # Weighted mean by GDP
    if gdp_series is not None:
        row["weighted_mean"] = weighted_mean(df[var], gdp_series)
    else:
        row["weighted_mean"] = np.nan

    return row


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    # --- Load master panel for country metadata (region, income_group, GDP) ---
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    if master.empty:
        logger.error("Cannot load master_fiscal_panel.xlsx; aborting.")
        return

    # Build country metadata lookup from master panel
    # Use latest available region/income_group per country
    meta_cols = ["country_code", "region", "income_group"]
    meta = master[meta_cols].dropna(subset=["region"]).drop_duplicates(subset=["country_code"], keep="last")
    logger.info(f"Country metadata: {len(meta)} countries with region/income_group")

    # GDP lookup: country_code + year -> gdp_current_usd
    gdp_lookup = master[["country_code", "year", "gdp_current_usd"]].dropna(subset=["gdp_current_usd"])
    gdp_lookup = gdp_lookup.set_index(["country_code", "year"])["gdp_current_usd"]

    # --- Process each panel ---
    all_rows = []

    for panel_name, filename in PANEL_FILES.items():
        df = read_excel_safe(out / filename)
        if df.empty:
            logger.warning(f"  {filename} not found or empty; skipping.")
            continue

        # Merge country metadata
        if "region" not in df.columns:
            df = df.merge(meta, on="country_code", how="left")

        # Identify numeric columns to aggregate
        numeric_cols = [
            c for c in df.columns
            if c not in SKIP_COLS and pd.api.types.is_numeric_dtype(df[c]) and c != "year"
        ]

        if not numeric_cols:
            logger.info(f"  {panel_name}: no numeric columns to aggregate")
            continue

        logger.info(f"  {panel_name}: {len(numeric_cols)} numeric variables, {len(df)} rows")

        # Process by year
        for year, ydf in df.groupby("year"):
            # Attach GDP weights
            gdp_vals = ydf["country_code"].map(
                lambda cc: gdp_lookup.get((cc, year), np.nan)
            )

            for var in numeric_cols:
                # Global aggregates
                row = compute_group_stats(ydf, "global", "Global", year, var, gdp_vals)
                if row:
                    row["source_panel"] = panel_name
                    all_rows.append(row)

                # By region
                if "region" in ydf.columns:
                    for region, rdf in ydf.groupby("region"):
                        if pd.isna(region):
                            continue
                        rgdp = gdp_vals.loc[rdf.index]
                        row = compute_group_stats(rdf, "region", region, year, var, rgdp)
                        if row:
                            row["source_panel"] = panel_name
                            all_rows.append(row)

                # By income group
                if "income_group" in ydf.columns:
                    for ig, igdf in ydf.groupby("income_group"):
                        if pd.isna(ig):
                            continue
                        iggdp = gdp_vals.loc[igdf.index]
                        row = compute_group_stats(igdf, "income_group", ig, year, var, iggdp)
                        if row:
                            row["source_panel"] = panel_name
                            all_rows.append(row)

    if not all_rows:
        logger.error("No aggregate rows produced; aborting.")
        return

    # --- Build output ---
    agg = pd.DataFrame(all_rows)

    # Reorder columns
    col_order = [
        "aggregate_type", "aggregate_name", "year", "source_panel", "variable",
        "mean", "median", "weighted_mean", "n_countries", "min", "max",
    ]
    agg = agg[[c for c in col_order if c in agg.columns]]
    agg = agg.sort_values(["source_panel", "aggregate_type", "aggregate_name", "year", "variable"])
    agg = agg.reset_index(drop=True)

    write_single_sheet_excel(agg, out / "aggregates_panel.xlsx")
    logger.info(f"Saved aggregates_panel.xlsx: {len(agg)} rows, "
                f"{agg['aggregate_type'].nunique()} aggregate types, "
                f"{agg['source_panel'].nunique()} source panels")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
