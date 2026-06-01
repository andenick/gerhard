#!/usr/bin/env python3
"""
L90: Extract WID Inequality
Extract income/wealth distribution from WID.world bulk data.
Stage: L | ID: L90
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import ensure_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "L90",
    "name": "Extract WID Inequality",
    "stage": "L",
    "description": "Extract income/wealth distribution from WID.world data",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/processed/wid_inequality_extracted.xlsx"}],
    "timeout": 300,
    "parallel_safe": True,
}

WID_DIR = Path(__file__).resolve().parents[3] / "Technical" / "data" / "raw" / "wid"

# Target variables: j suffix = equal-split adults, 992 = adults 20+
# sptincj992 = pre-tax national income share
# shwealj992 = net personal wealth share
TARGET_VARIABLES = {
    "sptincj992": {
        "p99p100": "top1_income_share",
        "p90p100": "top10_income_share",
        "p0p50": "bottom50_income_share",
    },
    "shwealj992": {
        "p99p100": "top1_wealth_share",
        "p90p100": "top10_wealth_share",
    },
}

# WID uses 2-letter ISO codes; map to ISO3 via countries file
OUTPUT_FILENAME = "wid_inequality_extracted.xlsx"


def _load_country_map() -> dict:
    """Load WID alpha2 -> country name mapping."""
    countries_file = WID_DIR / "WID_countries.csv"
    if not countries_file.exists():
        return {}
    df = pd.read_csv(countries_file, sep=";")
    return dict(zip(df["alpha2"], df["shortname"]))


def _extract_from_csvs() -> pd.DataFrame:
    """Extract target variables from per-country WID CSVs."""
    csv_files = sorted(WID_DIR.glob("WID_data_*.csv"))
    if not csv_files:
        logger.warning("No WID_data_*.csv files found")
        return pd.DataFrame()

    logger.info(f"Found {len(csv_files)} WID country CSV files")

    all_records = []
    processed = 0
    errors = 0

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, sep=";", low_memory=False)
            country_code = csv_file.stem.replace("WID_data_", "")

            for variable, percentile_map in TARGET_VARIABLES.items():
                var_data = df[df["variable"] == variable]
                if var_data.empty:
                    continue

                for percentile, col_name in percentile_map.items():
                    subset = var_data[var_data["percentile"] == percentile]
                    for _, row in subset.iterrows():
                        all_records.append({
                            "country_code_2": country_code,
                            "year": int(row["year"]),
                            col_name: float(row["value"]),
                        })
            processed += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning(f"Error reading {csv_file.name}: {e}")

    if errors > 5:
        logger.warning(f"... and {errors - 5} more read errors")

    logger.info(f"Processed {processed} country files, {len(all_records)} records extracted")

    if not all_records:
        return pd.DataFrame()

    result = pd.DataFrame(all_records)

    # Pivot: group by country + year, take first non-null for each column
    value_cols = [c for c in result.columns if c not in ("country_code_2", "year")]
    grouped = result.groupby(["country_code_2", "year"])[value_cols].first().reset_index()

    return grouped


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    if not WID_DIR.exists():
        logger.error(f"WID directory not found: {WID_DIR}")
        return

    # Explore what's available
    all_files = list(WID_DIR.iterdir())
    csv_files = [f for f in all_files if f.suffix == ".csv" and f.name.startswith("WID_data_")]
    logger.info(f"WID directory: {len(all_files)} items, {len(csv_files)} country CSVs")

    for f in sorted(all_files)[:10]:
        if f.is_file():
            logger.info(f"  {f.name}: {f.stat().st_size / 1e6:.1f} MB")
        elif f.is_dir():
            n = sum(1 for _ in f.iterdir())
            logger.info(f"  {f.name}/: {n} files")

    # Extract from per-country CSVs
    result = _extract_from_csvs()

    if result.empty:
        logger.warning("WID extraction produced no data")
        # Create minimal placeholder
        result = pd.DataFrame(columns=[
            "country_code_2", "year", "top1_income_share", "top10_income_share",
            "bottom50_income_share", "top1_wealth_share", "top10_wealth_share",
        ])

    # Add country names from WID countries file
    country_map = _load_country_map()
    if country_map:
        result["country_name"] = result["country_code_2"].map(country_map)

    # Sort
    result = result.sort_values(["country_code_2", "year"]).reset_index(drop=True)

    # Log summary
    value_cols = ["top1_income_share", "top10_income_share", "bottom50_income_share",
                  "top1_wealth_share", "top10_wealth_share"]
    for col in value_cols:
        if col in result.columns:
            n = result[col].notna().sum()
            logger.info(f"  {col}: {n} observations")

    countries = result["country_code_2"].nunique()
    years_range = f"{result['year'].min()}-{result['year'].max()}" if len(result) > 0 else "none"
    logger.info(f"WID extraction: {len(result)} rows, {countries} countries, years {years_range}")

    # Save
    output_dir = ensure_dir(project_root() / "Technical" / "data" / "processed")
    output_path = output_dir / OUTPUT_FILENAME
    write_single_sheet_excel(result, output_path)
    logger.info(f"Saved {output_path.name}")


if __name__ == "__main__":
    run()
