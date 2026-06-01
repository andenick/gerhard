"""
A08: Cross-Country Fiscal Convergence Analysis
================================================
Tests whether fiscal structures are converging globally (sigma-convergence)
and whether poorer countries are catching up to rich-country fiscal capacity
(beta-convergence). Connects to Shaikh's equalization-of-profit-rates framework.

Data: All WB panels + WDI processed (200 countries, 1960-2024)
Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
from pathlib import Path
import sys
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir, processed_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

WB_DIR = raw_data_dir() / "worldbank" / "expenditure"
PROCESSED_DIR = processed_data_dir()
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OECD_COUNTRIES = ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN', 'AUS', 'ITA', 'ESP',
                  'NLD', 'SWE', 'NOR', 'DNK', 'FIN', 'BEL', 'AUT', 'CHE', 'IRL',
                  'NZL', 'KOR', 'ISR', 'MEX', 'TUR', 'POL', 'CZE', 'SVK', 'HUN',
                  'CHL', 'COL', 'CRI', 'LVA', 'LTU', 'EST', 'SVN', 'GRC', 'PRT',
                  'ISL', 'LUX']


def load_all_expenditure_indicators() -> pd.DataFrame:
    """Load and merge all WB expenditure indicators into unified panel."""
    files = {
        'gov_exp_gdp': 'wb_gov_expenditure_gdp.csv',
        'education_gdp': 'wb_education_expenditure.csv',
        'health_gdp': 'wb_health_expenditure.csv',
        'military_gdp': 'wb_military_expenditure.csv',
        'social_gdp': 'wb_social_expenditure.csv',
        'rd_gdp': 'wb_rd_expenditure.csv',
    }

    all_panels = []
    for key, fname in files.items():
        fpath = WB_DIR / fname
        if fpath.exists():
            df = pd.read_csv(fpath)
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna(subset=['year', 'value'])
            df = df[df['country_code'].str.len() <= 3]
            subset = df[['country_code', 'year', 'value']].copy()
            subset = subset.rename(columns={'value': key})
            all_panels.append(subset)

    if not all_panels:
        return pd.DataFrame()

    result = all_panels[0]
    for p in all_panels[1:]:
        col = [c for c in p.columns if c not in ['country_code', 'year']][0]
        result = result.merge(p, on=['country_code', 'year'], how='outer')

    result['year'] = result['year'].astype(int)
    result = result.sort_values(['country_code', 'year']).reset_index(drop=True)
    logger.info(f"Unified panel: {len(result):,} rows, {result['country_code'].nunique()} countries")
    return result


def compute_sigma_convergence(panel: pd.DataFrame) -> pd.DataFrame:
    """Sigma-convergence: is the cross-country dispersion of fiscal indicators declining?

    If CV (coefficient of variation) falls over time → convergence.
    """
    exp_cols = [c for c in panel.columns if c.endswith('_gdp')]
    results = []

    for year in sorted(panel['year'].unique()):
        yr = panel[panel['year'] == year]
        row = {'year': year, 'n_countries': yr['country_code'].nunique()}

        for col in exp_cols:
            valid = yr[col].dropna()
            if len(valid) >= 20:
                row[f'{col}_mean'] = valid.mean()
                row[f'{col}_std'] = valid.std()
                row[f'{col}_cv'] = valid.std() / valid.mean()
                row[f'{col}_gini'] = _gini(valid.values)
                row[f'{col}_p90p10'] = valid.quantile(0.9) / valid.quantile(0.1) \
                    if valid.quantile(0.1) > 0 else np.nan

        results.append(row)

    return pd.DataFrame(results)


def _gini(values: np.ndarray) -> float:
    """Compute Gini coefficient for an array of values."""
    values = values[~np.isnan(values)]
    if len(values) < 2 or values.sum() == 0:
        return np.nan
    sorted_vals = np.sort(values)
    n = len(sorted_vals)
    index = np.arange(1, n + 1)
    return (2 * np.sum(index * sorted_vals) - (n + 1) * np.sum(sorted_vals)) / (n * np.sum(sorted_vals))


def compute_beta_convergence(panel: pd.DataFrame, indicator: str,
                             start_year: int = 1990, end_year: int = 2020) -> pd.DataFrame:
    """Beta-convergence: do countries with low initial values grow faster?

    Regression: growth_rate = α + β * initial_level + ε
    If β < 0 → convergence (countries catching up).
    """
    if indicator not in panel.columns:
        return pd.DataFrame()

    # Get initial and final values
    start_data = panel[panel['year'] == start_year][['country_code', indicator]].rename(
        columns={indicator: 'initial_value'})
    end_data = panel[panel['year'] == end_year][['country_code', indicator]].rename(
        columns={indicator: 'final_value'})

    if start_data.empty or end_data.empty:
        # Try nearest available years
        start_range = panel[(panel['year'] >= start_year - 2) & (panel['year'] <= start_year + 2)]
        end_range = panel[(panel['year'] >= end_year - 2) & (panel['year'] <= end_year + 2)]
        start_data = start_range.groupby('country_code')[indicator].first().reset_index().rename(
            columns={indicator: 'initial_value'})
        end_data = end_range.groupby('country_code')[indicator].last().reset_index().rename(
            columns={indicator: 'final_value'})

    merged = start_data.merge(end_data, on='country_code')
    merged = merged.dropna()
    merged = merged[merged['initial_value'] > 0]

    if len(merged) < 10:
        return pd.DataFrame()

    # Compute annualized growth rate
    years = end_year - start_year
    merged['growth_rate'] = (merged['final_value'] / merged['initial_value']) ** (1 / years) - 1
    merged['log_initial'] = np.log(merged['initial_value'])

    # Run regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        merged['log_initial'], merged['growth_rate'])

    merged['indicator'] = indicator
    merged['beta'] = slope
    merged['r_squared'] = r_value ** 2
    merged['p_value'] = p_value
    merged['convergence'] = 'YES' if slope < 0 and p_value < 0.05 else 'NO'

    logger.info(f"Beta-convergence ({indicator}, {start_year}-{end_year}): "
               f"β={slope:.4f}, R²={r_value**2:.3f}, p={p_value:.4f} → "
               f"{'CONVERGENCE' if slope < 0 and p_value < 0.05 else 'NO CONVERGENCE'}")

    return merged


def analyze_club_convergence(panel: pd.DataFrame) -> pd.DataFrame:
    """Test for convergence clubs: do OECD converge among themselves?
    Do non-OECD converge? Or is convergence only within clubs?
    """
    results = []
    exp_cols = [c for c in panel.columns if c.endswith('_gdp')]

    panel = panel.copy()
    panel['is_oecd'] = panel['country_code'].isin(OECD_COUNTRIES)

    for col in exp_cols:
        for year in sorted(panel['year'].unique()):
            yr = panel[panel['year'] == year]
            for club, mask in [('OECD', yr['is_oecd']), ('non-OECD', ~yr['is_oecd'])]:
                club_data = yr[mask][col].dropna()
                if len(club_data) >= 10:
                    results.append({
                        'year': year,
                        'indicator': col,
                        'club': club,
                        'n': len(club_data),
                        'mean': club_data.mean(),
                        'std': club_data.std(),
                        'cv': club_data.std() / club_data.mean() if club_data.mean() > 0 else np.nan,
                    })

    return pd.DataFrame(results)


def analyze_fiscal_state_capacity(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute composite fiscal state capacity index.

    State capacity proxied by: tax effort (gov_exp_gdp), human capital spending
    (education), public goods (health), and R&D investment.
    """
    if panel.empty:
        return pd.DataFrame()

    # Latest available year per country
    latest = panel.groupby('country_code').last().reset_index()

    capacity_cols = ['gov_exp_gdp', 'education_gdp', 'health_gdp', 'rd_gdp']
    available = [c for c in capacity_cols if c in latest.columns]

    if not available:
        return pd.DataFrame()

    # Normalize each indicator to 0-1 range (relative to global max)
    for col in available:
        col_max = latest[col].quantile(0.95)  # Use 95th percentile to avoid outlier distortion
        if col_max > 0:
            latest[f'{col}_norm'] = latest[col].clip(upper=col_max) / col_max

    norm_cols = [f'{c}_norm' for c in available if f'{c}_norm' in latest.columns]
    if norm_cols:
        latest['fiscal_capacity_index'] = latest[norm_cols].mean(axis=1)
        latest['fiscal_capacity_rank'] = latest['fiscal_capacity_index'].rank(
            ascending=False, method='min')

    result = latest[['country_code'] + available +
                   [c for c in latest.columns if 'norm' in c or 'capacity' in c or 'rank' in c]]
    result = result.dropna(subset=available, how='all')
    result = result.sort_values('fiscal_capacity_index', ascending=False).reset_index(drop=True)

    return result


def run() -> dict:
    """Execute full cross-country convergence analysis."""
    logger.info("=" * 80)
    logger.info("A08: CROSS-COUNTRY FISCAL CONVERGENCE")
    logger.info("=" * 80)

    panel = load_all_expenditure_indicators()
    if panel.empty:
        return {}

    # Sigma convergence
    sigma = compute_sigma_convergence(panel)
    if not sigma.empty:
        write_single_sheet_excel(sigma, OUTPUT_DIR / "A08_sigma_convergence.xlsx", "Sigma")
        logger.info(f"Sigma convergence: {len(sigma)} years")

    # Beta convergence for each indicator
    beta_results = []
    for col in [c for c in panel.columns if c.endswith('_gdp')]:
        for period in [(1990, 2020), (2000, 2020), (1980, 2010)]:
            beta = compute_beta_convergence(panel, col, *period)
            if not beta.empty:
                beta_results.append(beta)

    if beta_results:
        all_beta = pd.concat(beta_results, ignore_index=True)
        write_single_sheet_excel(all_beta, OUTPUT_DIR / "A08_beta_convergence.xlsx", "Beta")
        logger.info(f"Beta convergence: {len(all_beta)} country-indicator pairs")

    # Club convergence
    clubs = analyze_club_convergence(panel)
    if not clubs.empty:
        write_single_sheet_excel(clubs, OUTPUT_DIR / "A08_club_convergence.xlsx", "Clubs")
        logger.info(f"Club convergence: {len(clubs)} observations")

    # State capacity index
    capacity = analyze_fiscal_state_capacity(panel)
    if not capacity.empty:
        write_single_sheet_excel(capacity, OUTPUT_DIR / "A08_fiscal_capacity.xlsx", "Capacity")
        logger.info(f"Fiscal capacity index: {len(capacity)} countries")
        top10 = capacity.head(10)['country_code'].tolist()
        logger.info(f"Top 10 fiscal capacity: {top10}")

    logger.info("A08 COMPLETE")
    return {
        'sigma_years': len(sigma),
        'beta_tests': len(beta_results),
        'capacity_countries': len(capacity),
    }


if __name__ == "__main__":
    run()
