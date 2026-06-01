#!/usr/bin/env python3
"""
L100: Extract WGI Governance
Extract World Governance Indicators from WDI or WB API.
Stage: L | ID: L100
Project: Gerhard
"""
import os
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
    "id": "L100",
    "name": "Extract WGI Governance",
    "stage": "L",
    "description": "Extract World Governance Indicators from WDI or WB API",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/processed/wgi_governance.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
WDI_CSV = DATA_ROOT / "WorldBank" / "WDI_CSV" / "[2025.10.10] WDICSV.csv"

# World Governance Indicators (6 dimensions, estimate values)
WGI_INDICATORS = {
    "GE.EST": "govt_effectiveness",
    "RQ.EST": "regulatory_quality",
    "RL.EST": "rule_of_law",
    "CC.EST": "control_of_corruption",
    "VA.EST": "voice_accountability",
    "PV.EST": "political_stability",
}

OUTPUT_FILENAME = "wgi_governance.xlsx"


def _extract_from_wdi() -> pd.DataFrame:
    """Extract WGI indicators from the WDI CSV."""
    if not WDI_CSV.exists():
        logger.warning(f"WDI CSV not found: {WDI_CSV}")
        return pd.DataFrame()

    logger.info(f"Reading WDI CSV ({WDI_CSV.stat().st_size / 1e6:.0f} MB)...")
    wdi = pd.read_csv(WDI_CSV, low_memory=False)

    filtered = wdi[wdi["Indicator Code"].isin(WGI_INDICATORS.keys())]
    n_indicators = filtered["Indicator Code"].nunique()
    logger.info(f"Found {len(filtered)} WGI rows ({n_indicators} of {len(WGI_INDICATORS)} indicators)")

    if filtered.empty:
        return pd.DataFrame()

    # Melt year columns to long format
    year_cols = [c for c in filtered.columns if c.isdigit()]
    melted = filtered.melt(
        id_vars=["Country Name", "Country Code", "Indicator Code"],
        value_vars=year_cols,
        var_name="year",
        value_name="value",
    )
    melted["year"] = melted["year"].astype(int)
    melted = melted.dropna(subset=["value"])

    # Pivot indicators to columns
    pivoted = melted.pivot_table(
        index=["Country Code", "Country Name", "year"],
        columns="Indicator Code",
        values="value",
    ).reset_index()
    pivoted.columns.name = None

    # Rename columns
    rename_map = {"Country Code": "country_code", "Country Name": "country_name"}
    rename_map.update(WGI_INDICATORS)
    pivoted = pivoted.rename(columns=rename_map)

    return pivoted


def _fetch_from_api() -> pd.DataFrame:
    """Fetch WGI indicators from World Bank API."""
    import requests

    logger.info("Fetching WGI from World Bank API...")
    all_dfs = {}

    for indicator_code, col_name in WGI_INDICATORS.items():
        url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator_code}"
        params = {"format": "json", "per_page": 10000, "date": "1996:2024"}

        try:
            resp = requests.get(url, params=params, timeout=45)
            if resp.status_code != 200:
                logger.warning(f"  {indicator_code}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            if len(data) < 2 or not data[1]:
                logger.warning(f"  {indicator_code}: no data")
                continue

            records = []
            for entry in data[1]:
                if entry.get("value") is not None:
                    iso3 = entry.get("countryiso3code", "") or entry["country"]["id"]
                    records.append({
                        "country_code": iso3,
                        "country_name": entry["country"]["value"],
                        "year": int(entry["date"]),
                        col_name: float(entry["value"]),
                    })

            df = pd.DataFrame(records)
            all_dfs[col_name] = df
            logger.info(f"  {indicator_code} ({col_name}): {len(df)} obs, {df['country_code'].nunique()} countries")

        except Exception as e:
            logger.warning(f"  {indicator_code}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    # Merge all indicators
    base_name = list(all_dfs.keys())[0]
    result = all_dfs[base_name]

    for col_name, df in all_dfs.items():
        if col_name == base_name:
            continue
        result = result.merge(
            df[["country_code", "year", col_name]],
            on=["country_code", "year"],
            how="outer",
        )

    return result


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    # Try WDI first (preferred: local, fast, no network)
    result = _extract_from_wdi()

    if result.empty:
        logger.info("WGI not found in WDI; trying World Bank API...")
        result = _fetch_from_api()

    if result.empty:
        logger.error("Could not extract WGI data from WDI or API")
        result = pd.DataFrame(columns=["country_code", "country_name", "year"] +
                              list(WGI_INDICATORS.values()))

    # Filter to real countries (3-letter codes)
    if len(result) > 0:
        result = result[result["country_code"].str.len() == 3].copy()

    result = result.sort_values(["country_code", "year"]).reset_index(drop=True) if len(result) > 0 else result

    # Summary
    if len(result) > 0:
        logger.info(f"WGI extraction: {len(result)} rows, {result['country_code'].nunique()} countries")
        logger.info(f"  Years: {result['year'].min()}-{result['year'].max()}")
        for code, col in WGI_INDICATORS.items():
            if col in result.columns:
                n = result[col].notna().sum()
                logger.info(f"  {col}: {n} observations")
    else:
        logger.info("WGI extraction: empty (placeholder created)")

    # Save
    output_dir = ensure_dir(project_root() / "Technical" / "data" / "processed")
    output_path = output_dir / OUTPUT_FILENAME
    write_single_sheet_excel(result, output_path)
    logger.info(f"Saved {output_path.name}")


if __name__ == "__main__":
    run()
