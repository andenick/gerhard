"""
Pipeline: Efficiency Frontier
Government spending efficiency analysis using frontier approach.
Project: Gerhard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe

logger = setup_logging(__name__)


def _clean_country_name(val):
    """Parse dict-like country name strings from WB API."""
    if pd.isna(val):
        return val
    s = str(val)
    if s.startswith("{") and "'value'" in s:
        import ast
        try:
            d = ast.literal_eval(s)
            return d.get("value", s)
        except (ValueError, SyntaxError):
            return s
    return val


MANIFEST = {
    "id": "A90",
    "name": "Efficiency Frontier",
    "stage": "A",
    "description": "Government spending efficiency analysis",
    "depends_on": ["P60"],
    "inputs": [{"path": "Output/Data/master_fiscal_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/fiscal_efficiency.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}

DATA_DIR = output_data_dir()


def _fetch_iso2_to_iso3_map() -> dict:
    """Fetch ISO2 -> ISO3 country code mapping from World Bank API."""
    import requests
    try:
        url = "https://api.worldbank.org/v2/country"
        params = {"format": "json", "per_page": 500}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return {}
        data = r.json()
        if len(data) < 2 or data[1] is None:
            return {}
        return {item["iso2Code"]: item["id"] for item in data[1] if item.get("iso2Code") and item.get("id")}
    except Exception:
        return {}


def fetch_hci_data() -> pd.DataFrame:
    """Try to fetch Human Capital Index from World Bank API."""
    import requests

    logger.info("Attempting to fetch Human Capital Index from World Bank API...")
    try:
        url = "https://api.worldbank.org/v2/country/all/indicator/HD.HCI.OVRL"
        params = {"format": "json", "per_page": 500, "date": "2018:2023"}
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            logger.warning(f"World Bank API returned status {response.status_code}")
            return pd.DataFrame()

        data = response.json()
        if len(data) < 2 or data[1] is None:
            logger.warning("No HCI data returned from API")
            return pd.DataFrame()

        # Build ISO2->ISO3 mapping
        iso_map = _fetch_iso2_to_iso3_map()

        records = []
        for item in data[1]:
            if item["value"] is not None:
                iso2 = item["country"]["id"]
                iso3 = iso_map.get(iso2, iso2)  # Use ISO3 if mapping exists
                records.append({
                    "country_code": iso3,
                    "hci": item["value"],
                    "hci_year": int(item["date"]),
                })

        if not records:
            return pd.DataFrame()

        hci_df = pd.DataFrame(records)
        # Keep most recent per country
        hci_df = hci_df.sort_values("hci_year", ascending=False).groupby("country_code").first().reset_index()
        logger.info(f"Fetched HCI for {len(hci_df)} countries (ISO3 codes)")
        return hci_df

    except Exception as e:
        logger.warning(f"Could not fetch HCI data: {e}")
        return pd.DataFrame()


def compute_frontier(expenditure: np.ndarray, outcome: np.ndarray, n_bins: int = 20):
    """Compute efficiency frontier as upper envelope.

    Bins expenditure levels and takes the max outcome in each bin,
    then interpolates to get the frontier value for any expenditure level.
    """
    # Remove invalid
    mask = (expenditure > 0) & (outcome > 0) & np.isfinite(expenditure) & np.isfinite(outcome)
    exp_valid = expenditure[mask]
    out_valid = outcome[mask]

    if len(exp_valid) < 10:
        return np.full(len(expenditure), np.nan)

    # Use log expenditure for binning
    ln_exp = np.log(exp_valid)
    bins = np.linspace(ln_exp.min(), ln_exp.max(), n_bins + 1)
    bin_centers = []
    bin_maxes = []

    for i in range(len(bins) - 1):
        in_bin = (ln_exp >= bins[i]) & (ln_exp < bins[i + 1])
        if in_bin.sum() > 0:
            bin_centers.append((bins[i] + bins[i + 1]) / 2)
            bin_maxes.append(out_valid[in_bin].max())

    if len(bin_centers) < 3:
        return np.full(len(expenditure), np.nan)

    bin_centers = np.array(bin_centers)
    bin_maxes = np.array(bin_maxes)

    # Interpolate frontier for all points
    frontier_values = np.full(len(expenditure), np.nan)
    valid_idx = np.where(mask)[0]
    ln_exp_all = np.log(expenditure[mask])
    frontier_valid = np.interp(ln_exp_all, bin_centers, bin_maxes)
    frontier_values[valid_idx] = frontier_valid

    return frontier_values


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    # Load data
    df = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
    if df.empty:
        logger.error("master_fiscal_panel.xlsx not found or empty")
        return

    logger.info(f"Loaded master_fiscal_panel: {len(df)} rows")

    # Clean dict-like country names
    df["country_name"] = df["country_name"].apply(_clean_country_name)

    # Get latest values per country
    records = []
    for code, grp in df.groupby("country_code"):
        grp_sorted = grp.sort_values("year", ascending=False)
        row = {"country_code": code}
        row["country_name"] = grp_sorted["country_name"].iloc[0]
        row["region"] = grp_sorted["region"].iloc[0] if "region" in grp_sorted.columns else ""
        row["income_group"] = grp_sorted["income_group"].iloc[0] if "income_group" in grp_sorted.columns else ""

        for col in ["expenditure_pct_gdp", "gdp_per_capita_usd", "gdp_per_capita_ppp"]:
            if col in grp_sorted.columns:
                valid = grp_sorted[grp_sorted[col].notna()]
                row[col] = valid[col].iloc[0] if len(valid) > 0 else np.nan
            else:
                row[col] = np.nan
        records.append(row)

    latest = pd.DataFrame(records)

    # Use gdp_per_capita_ppp if available, else gdp_per_capita_usd
    latest["gdp_per_capita"] = latest.get("gdp_per_capita_ppp", pd.Series(dtype=float))
    if "gdp_per_capita_usd" in latest.columns:
        latest["gdp_per_capita"] = latest["gdp_per_capita"].fillna(latest["gdp_per_capita_usd"])

    # Filter to countries with both expenditure and GDP per capita
    valid_mask = latest["expenditure_pct_gdp"].notna() & latest["gdp_per_capita"].notna()
    filtered = latest[valid_mask].copy()
    logger.info(f"Countries with expenditure + GDP per capita: {len(filtered)}")

    if len(filtered) < 10:
        logger.error("Too few countries for efficiency analysis")
        return

    # Try to get HCI data
    hci_df = fetch_hci_data()
    has_hci = not hci_df.empty

    if has_hci:
        filtered = filtered.merge(hci_df[["country_code", "hci"]], on="country_code", how="left")
        hci_count = filtered["hci"].notna().sum()
        logger.info(f"Merged HCI data: {hci_count} countries with HCI")
    else:
        filtered["hci"] = np.nan

    # Compute efficiency using GDP per capita as outcome
    exp_arr = filtered["expenditure_pct_gdp"].values
    gdp_arr = filtered["gdp_per_capita"].values

    frontier_gdp = compute_frontier(exp_arr, gdp_arr)
    filtered["frontier_gdp_pc"] = frontier_gdp
    filtered["efficiency_score"] = np.where(
        frontier_gdp > 0,
        gdp_arr / frontier_gdp,
        np.nan
    )

    # Cap efficiency score at 1.0 (frontier countries)
    filtered["efficiency_score"] = filtered["efficiency_score"].clip(upper=1.0)

    # If HCI available, also compute HCI-based efficiency
    if has_hci and filtered["hci"].notna().sum() >= 10:
        hci_mask = filtered["hci"].notna()
        hci_sub = filtered[hci_mask].copy()
        frontier_hci = compute_frontier(
            hci_sub["expenditure_pct_gdp"].values,
            hci_sub["hci"].values,
        )
        filtered.loc[hci_mask, "hci_efficiency"] = np.where(
            frontier_hci > 0,
            hci_sub["hci"].values / frontier_hci,
            np.nan
        )
        filtered.loc[hci_mask, "hci_efficiency"] = filtered.loc[hci_mask, "hci_efficiency"].clip(upper=1.0)
    else:
        filtered["hci_efficiency"] = np.nan

    # Rank by efficiency score
    filtered["efficiency_rank"] = filtered["efficiency_score"].rank(ascending=False, method="min").astype("Int64")

    # Assign peer groups by expenditure quintile
    filtered["peer_group"] = pd.qcut(
        filtered["expenditure_pct_gdp"],
        q=5,
        labels=["Q1 (Lowest Spending)", "Q2", "Q3", "Q4", "Q5 (Highest Spending)"],
        duplicates="drop",
    )

    # Distance to frontier
    filtered["distance_to_frontier"] = 1.0 - filtered["efficiency_score"]

    # Prepare output
    output_cols = [
        "country_code", "country_name", "expenditure_pct_gdp", "gdp_per_capita",
        "efficiency_score", "efficiency_rank", "peer_group", "distance_to_frontier",
        "region", "income_group",
    ]
    if has_hci:
        output_cols.insert(5, "hci")
        output_cols.insert(6, "hci_efficiency")

    existing = [c for c in output_cols if c in filtered.columns]
    results_df = filtered[existing].sort_values("efficiency_rank")

    # Round numeric columns
    for col in ["efficiency_score", "distance_to_frontier", "hci_efficiency", "hci"]:
        if col in results_df.columns:
            results_df[col] = results_df[col].round(4)
    for col in ["expenditure_pct_gdp", "gdp_per_capita"]:
        if col in results_df.columns:
            results_df[col] = results_df[col].round(2)

    # Log summary
    logger.info(f"\nEfficiency summary:")
    logger.info(f"  Mean efficiency score: {results_df['efficiency_score'].mean():.3f}")
    logger.info(f"  Median efficiency score: {results_df['efficiency_score'].median():.3f}")
    logger.info(f"  Top 5 most efficient:")
    for _, row in results_df.head(5).iterrows():
        logger.info(f"    {row['country_name']}: {row['efficiency_score']:.3f} "
                     f"(exp={row['expenditure_pct_gdp']:.1f}%, gdp_pc={row['gdp_per_capita']:,.0f})")

    logger.info(f"\nBy peer group:")
    for pg, pg_data in results_df.groupby("peer_group", observed=True):
        logger.info(f"  {pg}: mean_eff={pg_data['efficiency_score'].mean():.3f}, n={len(pg_data)}")

    # Save
    output_path = DATA_DIR / "fiscal_efficiency.xlsx"
    write_single_sheet_excel(results_df, output_path)
    logger.info(f"Output saved to {output_path}: {len(results_df)} countries")


if __name__ == "__main__":
    run()
