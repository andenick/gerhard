"""
A01: Government Expenditure Composition Analysis
=================================================
Analyzes how governments allocate spending across functions (education, health,
military, social protection) and how these allocations evolve over time.

Data: World Bank expenditure indicators (200+ countries, 1960-2024)
Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.config import project_root
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

WB_DIR = raw_data_dir() / "worldbank" / "expenditure"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_wb_expenditure() -> dict[str, pd.DataFrame]:
    """Load all World Bank expenditure CSV files into a dict."""
    files = {
        'total_gdp': 'wb_gov_expenditure_gdp.csv',
        'total_usd': 'wb_gov_expenditure_usd.csv',
        'education_gdp': 'wb_education_expenditure.csv',
        'education_govt': 'wb_education_expenditure_govt.csv',
        'health_gdp': 'wb_health_expenditure.csv',
        'health_govt': 'wb_health_expenditure_govt.csv',
        'military_gdp': 'wb_military_expenditure.csv',
        'rd_gdp': 'wb_rd_expenditure.csv',
        'social_gdp': 'wb_social_expenditure.csv',
    }
    data = {}
    for key, fname in files.items():
        fpath = WB_DIR / fname
        if fpath.exists():
            df = pd.read_csv(fpath)
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            data[key] = df
            logger.info(f"Loaded {key}: {len(df):,} rows")
        else:
            logger.warning(f"Missing: {fpath}")
    return data


def build_composition_panel(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build unified panel: country × year × expenditure components."""
    panels = []

    indicator_map = {
        'total_gdp': 'exp_total_pct_gdp',
        'education_gdp': 'exp_education_pct_gdp',
        'health_gdp': 'exp_health_pct_gdp',
        'military_gdp': 'exp_military_pct_gdp',
        'rd_gdp': 'exp_rd_pct_gdp',
        'social_gdp': 'exp_social_pct_gdp',
    }

    for key, col_name in indicator_map.items():
        if key in data:
            df = data[key][['country_code', 'country_name', 'year', 'value']].copy()
            df = df.rename(columns={'value': col_name})
            panels.append(df)

    if not panels:
        logger.error("No expenditure data loaded")
        return pd.DataFrame()

    panel = panels[0]
    for p in panels[1:]:
        col = [c for c in p.columns if c.startswith('exp_')][0]
        panel = panel.merge(
            p[['country_code', 'year', col]],
            on=['country_code', 'year'],
            how='outer'
        )

    panel = panel.dropna(subset=['country_code', 'year'])
    panel = panel[~panel['country_code'].str.len().gt(3)]
    panel['year'] = panel['year'].astype(int)
    panel = panel.sort_values(['country_code', 'year']).reset_index(drop=True)

    # Derived: residual = total - (education + health + military)
    known_components = ['exp_education_pct_gdp', 'exp_health_pct_gdp', 'exp_military_pct_gdp']
    existing_cols = [c for c in known_components if c in panel.columns]
    if existing_cols and 'exp_total_pct_gdp' in panel.columns:
        panel['exp_other_pct_gdp'] = panel['exp_total_pct_gdp'] - panel[existing_cols].sum(axis=1)

    logger.info(f"Composition panel: {len(panel):,} rows, {panel['country_code'].nunique()} countries")
    return panel


def analyze_composition_trends(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute decade-average composition shares by income group."""
    if panel.empty:
        return pd.DataFrame()

    income_groups = {
        'High income': ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN', 'AUS', 'ITA', 'ESP',
                       'NLD', 'SWE', 'NOR', 'DNK', 'FIN', 'BEL', 'AUT', 'CHE', 'IRL',
                       'NZL', 'KOR', 'SGP', 'ISR'],
        'Upper middle': ['BRA', 'MEX', 'TUR', 'RUS', 'CHN', 'ZAF', 'ARG', 'COL',
                        'THA', 'MYS', 'PER', 'CHL'],
        'Lower middle': ['IND', 'IDN', 'PHL', 'VNM', 'EGY', 'NGA', 'PAK', 'BGD',
                        'UKR', 'KEN', 'GHA', 'MAR'],
        'Low income': ['ETH', 'TZA', 'MOZ', 'UGA', 'MWI', 'MLI', 'BFA', 'NER',
                      'TCD', 'SLE', 'LBR', 'BDI']
    }

    panel = panel.copy()
    panel['decade'] = (panel['year'] // 10) * 10

    country_to_group = {}
    for group, codes in income_groups.items():
        for code in codes:
            country_to_group[code] = group
    panel['income_group'] = panel['country_code'].map(country_to_group)

    exp_cols = [c for c in panel.columns if c.startswith('exp_') and c.endswith('_pct_gdp')]
    trends = panel.dropna(subset=['income_group']).groupby(
        ['income_group', 'decade']
    )[exp_cols].mean().reset_index()

    return trends


def analyze_guns_vs_butter(panel: pd.DataFrame) -> pd.DataFrame:
    """Test the guns-vs-butter tradeoff: military vs social spending correlation."""
    if panel.empty:
        return pd.DataFrame()

    cols_needed = ['exp_military_pct_gdp', 'exp_education_pct_gdp', 'exp_health_pct_gdp']
    available = [c for c in cols_needed if c in panel.columns]
    if len(available) < 2:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        if len(grp) < 10:
            continue
        row = {'country_code': country, 'n_years': len(grp)}
        for col in available:
            row[f'{col}_mean'] = grp[col].mean()
            row[f'{col}_std'] = grp[col].std()

        if 'exp_military_pct_gdp' in available and 'exp_education_pct_gdp' in available:
            valid = grp[['exp_military_pct_gdp', 'exp_education_pct_gdp']].dropna()
            if len(valid) > 5:
                row['corr_military_education'] = valid['exp_military_pct_gdp'].corr(
                    valid['exp_education_pct_gdp'])

        if 'exp_military_pct_gdp' in available and 'exp_health_pct_gdp' in available:
            valid = grp[['exp_military_pct_gdp', 'exp_health_pct_gdp']].dropna()
            if len(valid) > 5:
                row['corr_military_health'] = valid['exp_military_pct_gdp'].corr(
                    valid['exp_health_pct_gdp'])

        results.append(row)

    return pd.DataFrame(results)


def analyze_expenditure_convergence(panel: pd.DataFrame) -> pd.DataFrame:
    """Test sigma-convergence: are expenditure patterns converging across countries?"""
    if panel.empty:
        return pd.DataFrame()

    exp_cols = [c for c in panel.columns if c.startswith('exp_') and c.endswith('_pct_gdp')]
    results = []

    for year in sorted(panel['year'].unique()):
        yr_data = panel[panel['year'] == year]
        row = {'year': year, 'n_countries': yr_data['country_code'].nunique()}
        for col in exp_cols:
            valid = yr_data[col].dropna()
            if len(valid) >= 10:
                row[f'{col}_mean'] = valid.mean()
                row[f'{col}_std'] = valid.std()
                row[f'{col}_cv'] = valid.std() / valid.mean() if valid.mean() > 0 else np.nan
        results.append(row)

    return pd.DataFrame(results)


def run() -> dict:
    """Execute full expenditure composition analysis."""
    logger.info("=" * 80)
    logger.info("A01: EXPENDITURE COMPOSITION ANALYSIS")
    logger.info("=" * 80)

    data = load_wb_expenditure()
    if not data:
        logger.error("No data loaded. Aborting.")
        return {}

    panel = build_composition_panel(data)
    if panel.empty:
        return {}

    write_single_sheet_excel(panel, OUTPUT_DIR / "A01_expenditure_panel.xlsx", "Panel")
    logger.info(f"Wrote expenditure panel: {len(panel):,} rows")

    trends = analyze_composition_trends(panel)
    if not trends.empty:
        write_single_sheet_excel(trends, OUTPUT_DIR / "A01_composition_trends.xlsx", "Trends")
        logger.info(f"Wrote composition trends: {len(trends)} rows")

    guns_butter = analyze_guns_vs_butter(panel)
    if not guns_butter.empty:
        write_single_sheet_excel(guns_butter, OUTPUT_DIR / "A01_guns_vs_butter.xlsx", "Correlations")
        logger.info(f"Wrote guns-vs-butter: {len(guns_butter)} countries")

    convergence = analyze_expenditure_convergence(panel)
    if not convergence.empty:
        write_single_sheet_excel(convergence, OUTPUT_DIR / "A01_expenditure_convergence.xlsx", "Convergence")
        logger.info(f"Wrote convergence: {len(convergence)} years")

    results = {
        'panel_rows': len(panel),
        'countries': panel['country_code'].nunique(),
        'year_range': f"{panel['year'].min()}-{panel['year'].max()}",
        'guns_butter_countries': len(guns_butter),
        'convergence_years': len(convergence),
    }

    logger.info("A01 COMPLETE")
    return results


if __name__ == "__main__":
    run()
