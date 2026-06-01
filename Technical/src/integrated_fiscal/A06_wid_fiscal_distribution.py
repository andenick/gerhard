"""
A06: WID-Based Fiscal Distribution Analysis
=============================================
Uses World Inequality Database (4.1 GB, 422 countries) to analyze the
relationship between income distribution, factor shares, and fiscal outcomes.

Tests: Does higher inequality correlate with lower tax effort?
       Does labor share predict social spending?
       Do top income shares drive tax structure choices?

Data: WID country files (422 CSVs, semicolon-separated)
Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
from pathlib import Path
import sys
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

WID_DIR = raw_data_dir() / "wid"
WB_DIR = raw_data_dir() / "worldbank" / "expenditure"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# WID variable codes for fiscal-relevant series
WID_VARIABLES = {
    # Factor shares (national income decomposition)
    'wlabsh': 'labor_share',          # Labor share of national income (compensation/NI)
    'wcapsh': 'capital_share',         # Capital share
    # Top income shares (pre-tax)
    'sptinc': 'pretax_income_share',   # Pre-tax national income share
    'sdiinc': 'disposable_income_share',  # Post-tax income share
    # Government revenue/spending
    'mgdpro': 'gdp',                   # GDP
    'mnninc': 'national_income',       # National income
    'mhweal': 'wealth',               # Net household wealth
    # Tax revenue variables
    'tgover': 'govt_revenue',          # Government revenue
    'tgoexp': 'govt_expenditure',      # Government expenditure
}

# Key percentile groups
PERCENTILES_OF_INTEREST = ['p0p50', 'p50p90', 'p90p100', 'p99p100', 'p0p100']

# Priority countries (those with rich WID data)
PRIORITY_COUNTRIES = ['US', 'FR', 'GB', 'DE', 'SE', 'NO', 'DK', 'FI',
                     'AU', 'CA', 'NZ', 'JP', 'KR', 'IN', 'CN', 'ZA',
                     'BR', 'MX', 'AR', 'CL', 'IT', 'ES', 'NL']


def load_wid_country(country_code: str) -> Optional[pd.DataFrame]:
    """Load WID data for a single country."""
    fpath = WID_DIR / f"WID_data_{country_code}.csv"
    if not fpath.exists():
        return None

    try:
        df = pd.read_csv(fpath, sep=';', low_memory=False)
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        return df
    except Exception as e:
        logger.warning(f"Error loading {country_code}: {e}")
        return None


def extract_factor_shares(wid_df: pd.DataFrame, country: str) -> pd.DataFrame:
    """Extract labor/capital share time series from WID data."""
    # Labor share variable patterns in WID
    labor_patterns = ['wlabsh', 'xlabsh']
    capital_patterns = ['wcapsh', 'xcapsh']

    results = []
    for var_pattern in labor_patterns:
        matches = wid_df[wid_df['variable'].str.contains(var_pattern, na=False)]
        if not matches.empty:
            # Get total economy (p0p100)
            total = matches[matches['percentile'] == 'p0p100']
            if total.empty:
                total = matches
            for _, row in total.iterrows():
                results.append({
                    'country_code': country,
                    'year': row['year'],
                    'labor_share': row['value'],
                    'variable': row['variable'],
                })
            break

    return pd.DataFrame(results)


def extract_top_income_shares(wid_df: pd.DataFrame, country: str) -> pd.DataFrame:
    """Extract top 1%, top 10%, bottom 50% pre-tax income shares."""
    results = []

    # Pre-tax national income share
    pretax = wid_df[wid_df['variable'].str.startswith('sptinc')]

    target_percentiles = {
        'p99p100': 'top1_share',
        'p90p100': 'top10_share',
        'p0p50': 'bottom50_share',
    }

    for pct, name in target_percentiles.items():
        pct_data = pretax[pretax['percentile'] == pct]
        for _, row in pct_data.iterrows():
            if pd.notna(row['value']) and pd.notna(row['year']):
                results.append({
                    'country_code': country,
                    'year': int(row['year']),
                    'measure': name,
                    'value': row['value'],
                })

    return pd.DataFrame(results)


def build_wid_fiscal_panel() -> pd.DataFrame:
    """Build panel of factor shares + inequality for priority countries."""
    all_shares = []
    all_inequality = []

    for country in PRIORITY_COUNTRIES:
        wid = load_wid_country(country)
        if wid is None:
            continue

        logger.info(f"Processing WID {country}: {len(wid):,} rows")

        # Factor shares
        shares = extract_factor_shares(wid, country)
        if not shares.empty:
            all_shares.append(shares)

        # Income inequality
        ineq = extract_top_income_shares(wid, country)
        if not ineq.empty:
            all_inequality.append(ineq)

    factor_panel = pd.concat(all_shares, ignore_index=True) if all_shares else pd.DataFrame()
    ineq_panel = pd.concat(all_inequality, ignore_index=True) if all_inequality else pd.DataFrame()

    logger.info(f"Factor shares: {len(factor_panel):,} obs from "
               f"{factor_panel['country_code'].nunique() if not factor_panel.empty else 0} countries")
    logger.info(f"Inequality: {len(ineq_panel):,} obs from "
               f"{ineq_panel['country_code'].nunique() if not ineq_panel.empty else 0} countries")

    return factor_panel, ineq_panel


def load_fiscal_for_merge() -> pd.DataFrame:
    """Load World Bank expenditure data for merging with WID."""
    files = {
        'gov_exp_gdp': WB_DIR / 'wb_gov_expenditure_gdp.csv',
        'education': WB_DIR / 'wb_education_expenditure.csv',
        'health': WB_DIR / 'wb_health_expenditure.csv',
        'military': WB_DIR / 'wb_military_expenditure.csv',
        'social': WB_DIR / 'wb_social_expenditure.csv',
    }

    panels = []
    for key, fpath in files.items():
        if fpath.exists():
            df = pd.read_csv(fpath)
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df[df['country_code'].str.len() <= 3].dropna(subset=['year', 'value'])
            # WID uses 2-letter codes, WB uses 3-letter
            subset = df[['country_code', 'year', 'value']].rename(columns={'value': key})
            panels.append(subset)

    if not panels:
        return pd.DataFrame()

    result = panels[0]
    for p in panels[1:]:
        col = [c for c in p.columns if c not in ['country_code', 'year']][0]
        result = result.merge(p, on=['country_code', 'year'], how='outer')

    return result


def analyze_inequality_fiscal_nexus(
    ineq_panel: pd.DataFrame,
    fiscal_panel: pd.DataFrame
) -> pd.DataFrame:
    """Test: does higher inequality correlate with different fiscal patterns?"""
    if ineq_panel.empty or fiscal_panel.empty:
        return pd.DataFrame()

    # Pivot inequality to wide (country × year × top1, top10, bottom50)
    ineq_wide = ineq_panel.pivot_table(
        index=['country_code', 'year'],
        columns='measure',
        values='value',
        aggfunc='first'
    ).reset_index()
    ineq_wide.columns.name = None

    # WID uses 2-letter, WB uses 3-letter — need a crosswalk
    iso2_to_iso3 = {
        'US': 'USA', 'FR': 'FRA', 'GB': 'GBR', 'DE': 'DEU', 'SE': 'SWE',
        'NO': 'NOR', 'DK': 'DNK', 'FI': 'FIN', 'AU': 'AUS', 'CA': 'CAN',
        'NZ': 'NZL', 'JP': 'JPN', 'KR': 'KOR', 'IN': 'IND', 'CN': 'CHN',
        'ZA': 'ZAF', 'BR': 'BRA', 'MX': 'MEX', 'AR': 'ARG', 'CL': 'CHL',
        'IT': 'ITA', 'ES': 'ESP', 'NL': 'NLD',
    }

    ineq_wide['country_code_3'] = ineq_wide['country_code'].map(iso2_to_iso3)
    ineq_wide = ineq_wide.dropna(subset=['country_code_3'])

    merged = ineq_wide.merge(
        fiscal_panel,
        left_on=['country_code_3', 'year'],
        right_on=['country_code', 'year'],
        how='inner',
        suffixes=('_wid', '_wb')
    )

    if merged.empty:
        logger.warning("No overlap between WID inequality and WB fiscal data")
        return pd.DataFrame()

    logger.info(f"Merged inequality-fiscal panel: {len(merged):,} rows")
    return merged


def compute_redistribution_effort(merged: pd.DataFrame) -> pd.DataFrame:
    """Compute redistribution metrics: how much does the fiscal system reduce inequality?"""
    if merged.empty:
        return pd.DataFrame()

    results = []
    for country, grp in merged.groupby('country_code_wid'):
        if len(grp) < 5:
            continue

        row = {'country_code': country, 'n_years': len(grp)}

        # Average inequality measures
        for col in ['top1_share', 'top10_share', 'bottom50_share']:
            if col in grp.columns:
                row[f'avg_{col}'] = grp[col].mean()

        # Average fiscal effort
        for col in ['gov_exp_gdp', 'education', 'health', 'social']:
            if col in grp.columns:
                row[f'avg_{col}'] = grp[col].mean()

        # Correlation: top1 share vs government spending
        if 'top1_share' in grp.columns and 'gov_exp_gdp' in grp.columns:
            valid = grp[['top1_share', 'gov_exp_gdp']].dropna()
            if len(valid) > 5:
                row['corr_top1_govexp'] = valid['top1_share'].corr(valid['gov_exp_gdp'])

        # Correlation: top1 share vs social spending
        if 'top1_share' in grp.columns and 'social' in grp.columns:
            valid = grp[['top1_share', 'social']].dropna()
            if len(valid) > 5:
                row['corr_top1_social'] = valid['top1_share'].corr(valid['social'])

        results.append(row)

    return pd.DataFrame(results)


def analyze_labor_share_fiscal(factor_panel: pd.DataFrame) -> pd.DataFrame:
    """Test: does declining labor share correlate with fiscal changes?

    Hypothesis (Shaikh framework): falling labor share → lower wage-tax base
    → governments shift to consumption taxes or deficit spending.
    """
    if factor_panel.empty:
        return pd.DataFrame()

    results = []
    for country, grp in factor_panel.groupby('country_code'):
        grp = grp.sort_values('year').dropna(subset=['labor_share'])
        if len(grp) < 10:
            continue

        # Trend analysis
        years = grp['year'].values
        values = grp['labor_share'].values

        if len(years) >= 10:
            slope = np.polyfit(years - years[0], values, 1)[0]
            mid = len(years) // 2
            early_mean = values[:mid].mean()
            late_mean = values[mid:].mean()

            results.append({
                'country_code': country,
                'year_start': int(years[0]),
                'year_end': int(years[-1]),
                'n_years': len(years),
                'labor_share_mean': values.mean(),
                'labor_share_early': early_mean,
                'labor_share_late': late_mean,
                'labor_share_change': late_mean - early_mean,
                'labor_share_trend': slope,
                'declining': slope < -0.001,
            })

    return pd.DataFrame(results)


def run() -> dict:
    """Execute full WID fiscal distribution analysis."""
    logger.info("=" * 80)
    logger.info("A06: WID-BASED FISCAL DISTRIBUTION ANALYSIS")
    logger.info("=" * 80)

    factor_panel, ineq_panel = build_wid_fiscal_panel()

    if not factor_panel.empty:
        write_single_sheet_excel(factor_panel, OUTPUT_DIR / "A06_factor_shares.xlsx", "FactorShares")
        logger.info(f"Wrote factor shares: {len(factor_panel)} rows")

    if not ineq_panel.empty:
        write_single_sheet_excel(ineq_panel, OUTPUT_DIR / "A06_inequality_panel.xlsx", "Inequality")
        logger.info(f"Wrote inequality panel: {len(ineq_panel)} rows")

    # Labor share analysis
    labor_analysis = analyze_labor_share_fiscal(factor_panel)
    if not labor_analysis.empty:
        write_single_sheet_excel(labor_analysis, OUTPUT_DIR / "A06_labor_share_trends.xlsx", "LaborShare")
        declining = labor_analysis['declining'].sum()
        logger.info(f"Labor share trends: {len(labor_analysis)} countries, "
                   f"{declining} with declining labor share")

    # Merge WID with fiscal data
    fiscal = load_fiscal_for_merge()
    merged = analyze_inequality_fiscal_nexus(ineq_panel, fiscal)
    if not merged.empty:
        write_single_sheet_excel(merged, OUTPUT_DIR / "A06_inequality_fiscal_merged.xlsx", "Merged")
        logger.info(f"Inequality-fiscal merge: {len(merged)} rows")

        # Redistribution analysis
        redistribution = compute_redistribution_effort(merged)
        if not redistribution.empty:
            write_single_sheet_excel(
                redistribution, OUTPUT_DIR / "A06_redistribution_effort.xlsx", "Redistribution")
            logger.info(f"Redistribution effort: {len(redistribution)} countries")

    logger.info("A06 COMPLETE")
    return {
        'factor_share_obs': len(factor_panel),
        'inequality_obs': len(ineq_panel),
        'countries_with_labor_share': len(labor_analysis) if not labor_analysis.empty else 0,
    }


if __name__ == "__main__":
    run()
