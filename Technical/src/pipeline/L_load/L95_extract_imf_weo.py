#!/usr/bin/env python3
"""
L95: Extract IMF WEO
Extract IMF World Economic Outlook fiscal data and projections.
Stage: L | ID: L95
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
    "id": "L95",
    "name": "Extract IMF WEO",
    "stage": "L",
    "description": "Extract IMF World Economic Outlook fiscal data and projections",
    "depends_on": [],
    "inputs": [],
    "outputs": [{"path": "Technical/data/processed/imf_weo_panel.xlsx"}],
    "timeout": 180,
    "parallel_safe": True,
}

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "data"))
IMF_DIR = DATA_ROOT / "IMF"

# WEO subject codes of interest
WEO_SUBJECTS = {
    "NGDP_RPCH": "gdp_growth_real",
    "NGDPD": "gdp_nominal_usd_bn",
    "PCPIPCH": "inflation_cpi",
    "LUR": "unemployment_rate",
    "GGR_NGDP": "govt_revenue_pct_gdp",
    "GGX_NGDP": "govt_expenditure_pct_gdp",
    "GGXWDG_NGDP": "govt_debt_pct_gdp",
    "GGXONLB_NGDP": "primary_balance_pct_gdp",
    "GGXCNL_NGDP": "overall_balance_pct_gdp",
    "BCA_NGDPD": "current_account_pct_gdp",
}

OUTPUT_FILENAME = "imf_weo_panel.xlsx"


def _find_weo_files() -> list:
    """Search for WEO data files in IMF directory."""
    candidates = []

    # Check WEO subdirectory
    weo_dir = IMF_DIR / "macroeconomic" / "weo"
    if weo_dir.exists():
        for f in weo_dir.rglob("*"):
            if f.suffix in (".csv", ".xlsx", ".xls", ".tsv"):
                candidates.append(f)

    # Also check top-level and other subdirectories
    for pattern in ["WEO*.csv", "WEO*.xlsx", "WEO*.tsv", "weo*.csv"]:
        candidates.extend(IMF_DIR.rglob(pattern))

    return list(set(candidates))


def _fetch_weo_from_api() -> pd.DataFrame:
    """Fetch WEO data via IMF JSON REST API (SDMX-based)."""
    import requests

    logger.info("Attempting IMF WEO API fetch...")

    # The IMF Dataflow for WEO
    base_url = "https://www.imf.org/external/datamapper/api/v1"
    all_records = []

    for subject_code, col_name in WEO_SUBJECTS.items():
        url = f"{base_url}/{subject_code}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"  {subject_code}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            values = data.get("values", {}).get(subject_code, {})

            for country_code, year_vals in values.items():
                for year_str, value in year_vals.items():
                    try:
                        all_records.append({
                            "country_code": country_code,
                            "year": int(year_str),
                            "variable": col_name,
                            "value": float(value),
                        })
                    except (ValueError, TypeError):
                        continue

            n_countries = len(values)
            logger.info(f"  {subject_code} ({col_name}): {n_countries} countries")

        except requests.exceptions.Timeout:
            logger.warning(f"  {subject_code}: timeout")
        except Exception as e:
            logger.warning(f"  {subject_code}: {e}")

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)

    # Pivot to wide format
    pivoted = df.pivot_table(
        index=["country_code", "year"],
        columns="variable",
        values="value",
    ).reset_index()
    pivoted.columns.name = None

    return pivoted


def _identify_projection_years(df: pd.DataFrame) -> pd.DataFrame:
    """Mark years beyond the current data year as projections."""
    import datetime
    # WEO typically has 2 years of projections beyond current year
    current_year = datetime.datetime.now().year
    # Data for current year and beyond is typically a projection
    df["is_projection"] = df["year"] >= current_year
    return df


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    # Explore IMF directory
    if IMF_DIR.exists():
        logger.info(f"IMF directory contents:")
        for item in sorted(IMF_DIR.iterdir()):
            if item.is_file():
                logger.info(f"  {item.name}: {item.stat().st_size / 1e6:.1f} MB")
            elif item.is_dir():
                logger.info(f"  {item.name}/")

    # Look for local WEO files
    weo_files = _find_weo_files()
    result = pd.DataFrame()

    if weo_files:
        logger.info(f"Found {len(weo_files)} WEO files: {[f.name for f in weo_files]}")
        # Try to read the first valid one
        for f in weo_files:
            try:
                if f.suffix == ".csv":
                    df = pd.read_csv(f, low_memory=False)
                elif f.suffix in (".xlsx", ".xls"):
                    df = pd.read_excel(f)
                elif f.suffix == ".tsv":
                    df = pd.read_csv(f, sep="\t", low_memory=False)
                else:
                    continue
                logger.info(f"Read {f.name}: {df.shape}, columns: {df.columns[:10].tolist()}")
                # TODO: parse WEO format if found
                break
            except Exception as e:
                logger.warning(f"Could not read {f.name}: {e}")
    else:
        logger.info("No local WEO files found in IMF directory")

    # Fall back to API
    if result.empty:
        result = _fetch_weo_from_api()

    if result.empty:
        logger.warning("WEO data unavailable from both local files and API")
        logger.info("Note: Many WEO variables overlap with WDI. WDI substitutes:")
        logger.info("  GDP growth: NY.GDP.MKTP.KD.ZG")
        logger.info("  Inflation: FP.CPI.TOTL.ZG")
        logger.info("  Unemployment: SL.UEM.TOTL.ZS")
        logger.info("  Current account: BN.CAB.XOKA.GD.ZS")
        logger.info("WEO integration requires manual download from imf.org/en/Publications/WEO")

        # Create minimal placeholder
        result = pd.DataFrame(columns=["country_code", "year", "is_projection"] +
                              list(WEO_SUBJECTS.values()))

    # Mark projections
    if len(result) > 0:
        result = _identify_projection_years(result)

    # Filter to 3-letter country codes
    if "country_code" in result.columns and len(result) > 0:
        result = result[result["country_code"].str.len() == 3].copy()

    result = result.sort_values(["country_code", "year"]).reset_index(drop=True) if len(result) > 0 else result

    # Summary
    if len(result) > 0:
        n_countries = result["country_code"].nunique()
        yr_range = f"{result['year'].min()}-{result['year'].max()}"
        n_proj = result["is_projection"].sum() if "is_projection" in result.columns else 0
        logger.info(f"WEO panel: {len(result)} rows, {n_countries} countries, {yr_range}")
        logger.info(f"  Projections: {n_proj} rows")
        for col in WEO_SUBJECTS.values():
            if col in result.columns:
                n = result[col].notna().sum()
                if n > 0:
                    logger.info(f"  {col}: {n} observations")
    else:
        logger.info("WEO panel: empty (placeholder created)")

    # Save
    output_dir = ensure_dir(project_root() / "Technical" / "data" / "processed")
    output_path = output_dir / OUTPUT_FILENAME
    write_single_sheet_excel(result, output_path)
    logger.info(f"Saved {output_path.name}")


if __name__ == "__main__":
    run()
