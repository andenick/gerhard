#!/usr/bin/env python3
"""
P100: Integrate WID Inequality
Build comprehensive inequality panel from WID + World Bank.
Stage: P | ID: P100
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
    "id": "P100",
    "name": "Integrate WID Inequality",
    "stage": "P",
    "description": "Build comprehensive inequality panel from WID + World Bank",
    "depends_on": ["L90"],
    "inputs": [
        {"path": "Technical/data/processed/wid_inequality_extracted.xlsx", "required": False},
        {"path": "Output/Data/social_outcomes_panel.xlsx", "required": True},
    ],
    "outputs": [{"path": "Output/Data/inequality_panel.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}

# ISO 2-letter to 3-letter mapping for WID -> WB merge
# We build this from pycountry if available, otherwise a common subset
def _build_iso2_to_iso3() -> dict:
    """Build ISO alpha-2 to alpha-3 mapping."""
    try:
        import pycountry
        return {c.alpha_2: c.alpha_3 for c in pycountry.countries}
    except ImportError:
        pass

    # Fallback: load from WID countries + WB social panel intersection
    # Common mappings for major countries
    return {
        "US": "USA", "GB": "GBR", "FR": "FRA", "DE": "DEU", "JP": "JPN",
        "CN": "CHN", "IN": "IND", "BR": "BRA", "RU": "RUS", "CA": "CAN",
        "AU": "AUS", "IT": "ITA", "ES": "ESP", "MX": "MEX", "KR": "KOR",
        "AR": "ARG", "ZA": "ZAF", "SE": "SWE", "NO": "NOR", "DK": "DNK",
        "FI": "FIN", "NL": "NLD", "BE": "BEL", "AT": "AUT", "CH": "CHE",
        "PT": "PRT", "IE": "IRL", "NZ": "NZL", "CL": "CHL", "CO": "COL",
        "PE": "PER", "EG": "EGY", "NG": "NGA", "KE": "KEN", "GH": "GHA",
        "TZ": "TZA", "ET": "ETH", "PK": "PAK", "BD": "BGD", "ID": "IDN",
        "TH": "THA", "VN": "VNM", "MY": "MYS", "PH": "PHL", "TR": "TUR",
        "PL": "POL", "CZ": "CZE", "HU": "HUN", "RO": "ROU", "GR": "GRC",
        "IL": "ISR", "SA": "SAU", "AE": "ARE", "QA": "QAT", "KW": "KWT",
        "SG": "SGP", "HK": "HKG", "TW": "TWN", "UY": "URY", "EC": "ECU",
        "VE": "VEN", "BO": "BOL", "PY": "PRY", "CR": "CRI", "PA": "PAN",
        "GT": "GTM", "HN": "HND", "SV": "SLV", "NI": "NIC", "DO": "DOM",
        "JM": "JAM", "TT": "TTO", "CU": "CUB", "MA": "MAR", "TN": "TUN",
        "DZ": "DZA", "LY": "LBY", "CI": "CIV", "SN": "SEN", "CM": "CMR",
        "UG": "UGA", "MZ": "MOZ", "ZM": "ZMB", "ZW": "ZWE", "BW": "BWA",
        "NA": "NAM", "MU": "MUS", "MG": "MDG", "LK": "LKA", "NP": "NPL",
        "MM": "MMR", "KH": "KHM", "LA": "LAO", "MN": "MNG", "KZ": "KAZ",
        "UZ": "UZB", "GE": "GEO", "AM": "ARM", "AZ": "AZE", "UA": "UKR",
        "BY": "BLR", "LT": "LTU", "LV": "LVA", "EE": "EST", "SK": "SVK",
        "SI": "SVN", "HR": "HRV", "RS": "SRB", "BA": "BIH", "MK": "MKD",
        "AL": "ALB", "ME": "MNE", "BG": "BGR", "CY": "CYP", "MT": "MLT",
        "LU": "LUX", "IS": "ISL",
    }


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    root = project_root()

    # Load WID data (optional)
    wid_path = root / "Technical" / "data" / "processed" / "wid_inequality_extracted.xlsx"
    wid_df = None
    if wid_path.exists():
        wid_df = pd.read_excel(wid_path)
        logger.info(f"WID data: {len(wid_df)} rows, {wid_df['country_code_2'].nunique()} countries")
    else:
        logger.warning("WID extraction not found; building inequality panel from WB Gini only")

    # Load social outcomes panel (has WB Gini)
    social_path = out / "social_outcomes_panel.xlsx"
    social = pd.read_excel(social_path)
    logger.info(f"Social outcomes: {len(social)} rows")

    # Extract WB Gini
    gini_col = None
    for candidate in ["gini_coefficient", "gini_index", "gini_wb"]:
        if candidate in social.columns:
            gini_col = candidate
            break

    wb_gini = pd.DataFrame()
    if gini_col:
        wb_gini = social[["country_code", "year", gini_col]].dropna(subset=[gini_col]).copy()
        wb_gini = wb_gini.rename(columns={gini_col: "gini_wb"})
        logger.info(f"WB Gini: {len(wb_gini)} observations from column '{gini_col}'")
    else:
        logger.warning(f"No Gini column found in social_outcomes_panel. Columns: {social.columns.tolist()}")

    # Add country names from social panel
    name_map = social.dropna(subset=["country_name"]).drop_duplicates("country_code").set_index("country_code")["country_name"]

    # Build base from WB Gini
    if not wb_gini.empty:
        result = wb_gini.copy()
    else:
        result = pd.DataFrame(columns=["country_code", "year", "gini_wb"])

    # Merge WID data if available
    wid_cols = ["top1_income_share", "top10_income_share", "bottom50_income_share",
                "top1_wealth_share", "top10_wealth_share"]

    if wid_df is not None and len(wid_df) > 0:
        # Convert WID 2-letter codes to 3-letter
        iso_map = _build_iso2_to_iso3()
        wid_df["country_code"] = wid_df["country_code_2"].map(iso_map)
        wid_mapped = wid_df.dropna(subset=["country_code"]).copy()
        unmapped = wid_df["country_code"].isna().sum()
        if unmapped > 0:
            logger.info(f"  {unmapped} WID rows with unmapped 2-letter codes dropped")

        # Select WID columns for merge
        wid_merge_cols = ["country_code", "year"] + [c for c in wid_cols if c in wid_mapped.columns]
        wid_for_merge = wid_mapped[wid_merge_cols].copy()

        # Outer merge with WB Gini
        result = result.merge(wid_for_merge, on=["country_code", "year"], how="outer")
        logger.info(f"After WID merge: {len(result)} rows, {result['country_code'].nunique()} countries")
    else:
        # Add empty WID columns
        for col in wid_cols:
            result[col] = np.nan

    # Add gini_wid placeholder (WID doesn't have standard Gini in our extraction)
    result["gini_wid"] = np.nan

    # Add country names
    result["country_name"] = result["country_code"].map(name_map)

    # Order columns
    ordered_cols = [
        "country_code", "country_name", "year", "gini_wb", "gini_wid",
        "top1_income_share", "top10_income_share", "bottom50_income_share",
        "top1_wealth_share", "top10_wealth_share",
    ]
    for col in ordered_cols:
        if col not in result.columns:
            result[col] = np.nan
    result = result[ordered_cols]

    # Filter to real countries (3-letter codes only)
    result = result[result["country_code"].str.len() == 3].copy()

    result = result.sort_values(["country_code", "year"]).reset_index(drop=True)

    # Summary statistics
    logger.info(f"Inequality panel: {len(result)} rows, {result['country_code'].nunique()} countries")
    for col in ordered_cols[3:]:
        n = result[col].notna().sum()
        if n > 0:
            logger.info(f"  {col}: {n} observations")

    write_single_sheet_excel(result, out / "inequality_panel.xlsx")
    logger.info("Saved inequality_panel.xlsx")


if __name__ == "__main__":
    run()
