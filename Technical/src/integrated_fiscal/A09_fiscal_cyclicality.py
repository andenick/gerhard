"""
A09: Fiscal Cyclicality Analysis
=================================
Tests whether government spending is pro-cyclical or counter-cyclical,
and whether this behavior differs by income level, regime type, and era.

Pro-cyclical fiscal policy (spending more in booms, cutting in busts) is
a hallmark of developing countries and a core puzzle in public finance.

Data: WDI national accounts + fiscal panels (200 countries, 1970-2024)
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

PROCESSED_DIR = processed_data_dir()
WB_DIR = raw_data_dir() / "worldbank" / "expenditure"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_national_accounts() -> pd.DataFrame:
    """Load GDP growth data — try new macro download first, then WDI panel."""
    # Prefer the freshly-downloaded GDP growth CSV
    macro_path = raw_data_dir() / "worldbank" / "macro" / "wb_gdp_growth.csv"
    if macro_path.exists():
        df = pd.read_csv(macro_path)
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['year', 'value'])
        df = df[df['country_code'].str.len() <= 3]
        df = df.rename(columns={'value': 'gdp_growth'})
        logger.info(f"GDP growth (macro download): {len(df):,} rows, "
                   f"{df['country_code'].nunique()} countries")
        return df[['country_code', 'year', 'gdp_growth']]

    # Fallback to WDI national accounts
    fpath = PROCESSED_DIR / "wdi_national_accounts.xlsx"
    if not fpath.exists():
        logger.warning(f"No GDP growth data found")
        return pd.DataFrame()

    df = pd.read_excel(fpath)
    logger.info(f"National accounts: {len(df):,} rows, cols: {df.columns.tolist()[:10]}")
    return df


def load_expenditure_panel() -> pd.DataFrame:
    """Load WB government expenditure panel."""
    fpath = WB_DIR / "wb_gov_expenditure_gdp.csv"
    if not fpath.exists():
        return pd.DataFrame()

    df = pd.read_csv(fpath)
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['year', 'value'])
    df = df[df['country_code'].str.len() <= 3]
    df = df.rename(columns={'value': 'gov_exp_gdp'})
    return df[['country_code', 'year', 'gov_exp_gdp']]


def merge_panels(national: pd.DataFrame, expenditure: pd.DataFrame) -> pd.DataFrame:
    """Merge national accounts with expenditure data."""
    if national.empty:
        exp = expenditure.copy()
        exp['year'] = exp['year'].astype(int)
        exp = exp.sort_values(['country_code', 'year'])
        exp['exp_growth'] = exp.groupby('country_code')['gov_exp_gdp'].pct_change()
        return exp

    # If we loaded the macro CSV directly, gdp_growth is already the column name
    if 'gdp_growth' in national.columns:
        growth_panel = national[['country_code', 'year', 'gdp_growth']].copy()
    else:
        growth_cols = [c for c in national.columns
                      if any(kw in c.lower() for kw in ['gdp_growth', 'ny.gdp.mktp.kd.zg', 'growth_annual'])]
        if not growth_cols:
            logger.warning(f"No GDP growth column found. Cols: {national.columns.tolist()[:15]}")
            return expenditure
        growth_panel = national[['country_code', 'year', growth_cols[0]]].copy()
        growth_panel = growth_panel.rename(columns={growth_cols[0]: 'gdp_growth'})

    growth_panel['year'] = pd.to_numeric(growth_panel['year'], errors='coerce').astype(int)
    growth_panel['gdp_growth'] = pd.to_numeric(growth_panel['gdp_growth'], errors='coerce')

    expenditure['year'] = expenditure['year'].astype(int)
    merged = expenditure.merge(growth_panel, on=['country_code', 'year'], how='inner')
    merged = merged.sort_values(['country_code', 'year']).reset_index(drop=True)
    merged['exp_change'] = merged.groupby('country_code')['gov_exp_gdp'].diff()

    logger.info(f"Merged cyclicality panel: {len(merged):,} rows, "
               f"{merged['country_code'].nunique()} countries")
    return merged


def compute_cyclicality_by_country(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute fiscal cyclicality coefficient for each country.

    Cyclicality = correlation(Δexp/GDP, GDP_growth)
    Positive = pro-cyclical (spending rises in booms)
    Negative = counter-cyclical (spending rises in busts)
    """
    if 'gdp_growth' not in panel.columns and 'exp_change' not in panel.columns:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.dropna(subset=['gov_exp_gdp'])
        if len(grp) < 10:
            continue

        row = {
            'country_code': country,
            'n_years': len(grp),
            'year_start': int(grp['year'].min()),
            'year_end': int(grp['year'].max()),
            'exp_mean': grp['gov_exp_gdp'].mean(),
            'exp_std': grp['gov_exp_gdp'].std(),
        }

        if 'gdp_growth' in grp.columns and 'exp_change' in grp.columns:
            valid = grp[['gdp_growth', 'exp_change']].dropna()
            if len(valid) >= 8:
                corr = valid['gdp_growth'].corr(valid['exp_change'])
                slope, intercept, r, p, se = stats.linregress(
                    valid['gdp_growth'], valid['exp_change'])
                row['cyclicality_corr'] = corr
                row['cyclicality_beta'] = slope
                row['cyclicality_p_value'] = p
                row['cyclicality_r_squared'] = r ** 2
                row['is_procyclical'] = corr > 0
                row['significantly_procyclical'] = (corr > 0) and (p < 0.05)
                row['significantly_countercyclical'] = (corr < 0) and (p < 0.05)
        elif 'exp_change' in grp.columns:
            # Without GDP growth, use exp level trend as proxy
            exp_trend = np.polyfit(range(len(grp)), grp['gov_exp_gdp'].values, 1)[0]
            row['exp_trend'] = exp_trend

        results.append(row)

    return pd.DataFrame(results)


def analyze_cyclicality_by_income(cyclicality: pd.DataFrame) -> pd.DataFrame:
    """Group cyclicality results by country income level."""
    if cyclicality.empty or 'cyclicality_corr' not in cyclicality.columns:
        return pd.DataFrame()

    income_map = {
        'High': ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN', 'AUS', 'ITA', 'ESP',
                'NLD', 'SWE', 'NOR', 'DNK', 'FIN', 'BEL', 'AUT', 'CHE', 'IRL',
                'NZL', 'KOR', 'SGP', 'ISR'],
        'Upper-Middle': ['BRA', 'MEX', 'TUR', 'RUS', 'CHN', 'ZAF', 'ARG', 'COL',
                        'THA', 'MYS', 'PER', 'CHL'],
        'Lower-Middle': ['IND', 'IDN', 'PHL', 'VNM', 'EGY', 'NGA', 'PAK', 'BGD',
                        'UKR', 'KEN', 'GHA', 'MAR'],
        'Low': ['ETH', 'TZA', 'MOZ', 'UGA', 'MWI', 'MLI', 'BFA', 'NER'],
    }

    country_to_income = {}
    for group, codes in income_map.items():
        for c in codes:
            country_to_income[c] = group

    cyclicality = cyclicality.copy()
    cyclicality['income_group'] = cyclicality['country_code'].map(country_to_income)

    results = []
    for group, grp in cyclicality.groupby('income_group'):
        valid = grp.dropna(subset=['cyclicality_corr'])
        if valid.empty:
            continue
        results.append({
            'income_group': group,
            'n_countries': len(valid),
            'avg_cyclicality': valid['cyclicality_corr'].mean(),
            'median_cyclicality': valid['cyclicality_corr'].median(),
            'pct_procyclical': valid['is_procyclical'].mean() * 100,
            'pct_significant_pro': valid['significantly_procyclical'].mean() * 100,
            'pct_significant_counter': valid['significantly_countercyclical'].mean() * 100,
        })

    return pd.DataFrame(results)


def analyze_asymmetric_cyclicality(panel: pd.DataFrame) -> pd.DataFrame:
    """Test whether fiscal policy is asymmetrically cyclical.

    Key question: Do governments spend more in booms AND cut in busts (pro-cyclical)?
    Or spend more in booms but NOT cut in busts (ratchet effect)?
    """
    if 'gdp_growth' not in panel.columns:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.dropna(subset=['gdp_growth', 'exp_change'])
        if len(grp) < 15:
            continue

        booms = grp[grp['gdp_growth'] > grp['gdp_growth'].median()]
        busts = grp[grp['gdp_growth'] <= grp['gdp_growth'].median()]

        if len(booms) < 5 or len(busts) < 5:
            continue

        results.append({
            'country_code': country,
            'n_booms': len(booms),
            'n_busts': len(busts),
            'avg_exp_change_boom': booms['exp_change'].mean(),
            'avg_exp_change_bust': busts['exp_change'].mean(),
            'exp_rises_in_boom': booms['exp_change'].mean() > 0,
            'exp_falls_in_bust': busts['exp_change'].mean() < 0,
            'symmetric': (booms['exp_change'].mean() > 0) and (busts['exp_change'].mean() < 0),
            'ratchet': (booms['exp_change'].mean() > 0) and (busts['exp_change'].mean() >= 0),
        })

    return pd.DataFrame(results)


def analyze_era_shifts(panel: pd.DataFrame) -> pd.DataFrame:
    """Has cyclicality changed over time? Compare pre-2000 vs post-2000."""
    if 'gdp_growth' not in panel.columns:
        return pd.DataFrame()

    eras = {'pre_2000': (1970, 1999), 'post_2000': (2000, 2024)}
    results = []

    for country, grp in panel.groupby('country_code'):
        for era_name, (start, end) in eras.items():
            era_data = grp[(grp['year'] >= start) & (grp['year'] <= end)]
            valid = era_data[['gdp_growth', 'exp_change']].dropna()
            if len(valid) < 8:
                continue

            corr = valid['gdp_growth'].corr(valid['exp_change'])
            results.append({
                'country_code': country,
                'era': era_name,
                'n_years': len(valid),
                'cyclicality': corr,
            })

    df = pd.DataFrame(results)
    if df.empty:
        return df

    # Pivot to compare eras
    pivot = df.pivot_table(index='country_code', columns='era',
                          values='cyclicality', aggfunc='first').reset_index()
    pivot.columns.name = None
    if 'pre_2000' in pivot.columns and 'post_2000' in pivot.columns:
        pivot['cyclicality_change'] = pivot['post_2000'] - pivot['pre_2000']
        pivot['became_more_countercyclical'] = pivot['cyclicality_change'] < 0

    return pivot


def run() -> dict:
    """Execute full fiscal cyclicality analysis."""
    logger.info("=" * 80)
    logger.info("A09: FISCAL CYCLICALITY ANALYSIS")
    logger.info("=" * 80)

    national = load_national_accounts()
    expenditure = load_expenditure_panel()

    if expenditure.empty:
        logger.error("No expenditure data. Aborting.")
        return {}

    panel = merge_panels(national, expenditure)
    if panel.empty:
        return {}

    # Country-level cyclicality
    cyclicality = compute_cyclicality_by_country(panel)
    if not cyclicality.empty:
        write_single_sheet_excel(cyclicality, OUTPUT_DIR / "A09_cyclicality_by_country.xlsx", "Cyclicality")
        if 'is_procyclical' in cyclicality.columns:
            pro = cyclicality['is_procyclical'].mean() * 100
            logger.info(f"Cyclicality: {len(cyclicality)} countries, {pro:.1f}% pro-cyclical")

    # By income group
    by_income = analyze_cyclicality_by_income(cyclicality)
    if not by_income.empty:
        write_single_sheet_excel(by_income, OUTPUT_DIR / "A09_cyclicality_by_income.xlsx", "ByIncome")
        logger.info(f"By income group:\n{by_income.to_string(index=False)}")

    # Asymmetric cyclicality
    asymmetric = analyze_asymmetric_cyclicality(panel)
    if not asymmetric.empty:
        write_single_sheet_excel(asymmetric, OUTPUT_DIR / "A09_asymmetric_cyclicality.xlsx", "Asymmetric")
        if 'ratchet' in asymmetric.columns:
            ratchet_pct = asymmetric['ratchet'].mean() * 100
            logger.info(f"Ratchet effect: {ratchet_pct:.1f}% of countries")

    # Era shifts
    era_shifts = analyze_era_shifts(panel)
    if not era_shifts.empty:
        write_single_sheet_excel(era_shifts, OUTPUT_DIR / "A09_era_shifts.xlsx", "EraShifts")
        if 'became_more_countercyclical' in era_shifts.columns:
            improved = era_shifts['became_more_countercyclical'].mean() * 100
            logger.info(f"Became more counter-cyclical post-2000: {improved:.1f}% of countries")

    logger.info("A09 COMPLETE")
    return {
        'countries_analyzed': len(cyclicality),
        'pct_procyclical': cyclicality['is_procyclical'].mean() * 100 if 'is_procyclical' in cyclicality.columns else None,
    }


if __name__ == "__main__":
    run()
