"""
A02: Military Spending and Fiscal Tradeoffs
============================================
Tests military Keynesianism hypothesis and the guns-vs-butter tradeoff
across accumulation regimes (Cold War, post-Cold War, post-9/11, post-2020).

Data: World Bank military expenditure + education + health (170 countries, 1960-2024)
Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

WB_DIR = raw_data_dir() / "worldbank" / "expenditure"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REGIMES = {
    'cold_war': (1960, 1991),
    'peace_dividend': (1992, 2000),
    'gwot': (2001, 2008),
    'austerity': (2009, 2019),
    'pandemic_rearm': (2020, 2024),
}

NATO_COUNTRIES = ['USA', 'GBR', 'FRA', 'DEU', 'ITA', 'CAN', 'TUR', 'NLD', 'BEL',
                  'NOR', 'DNK', 'PRT', 'ESP', 'GRC', 'POL', 'CZE', 'HUN']
BRICS = ['BRA', 'RUS', 'IND', 'CHN', 'ZAF']


def load_military_data() -> pd.DataFrame:
    """Load military, education, health expenditure and build joint panel."""
    files = {
        'military': 'wb_military_expenditure.csv',
        'education': 'wb_education_expenditure.csv',
        'health': 'wb_health_expenditure.csv',
        'total': 'wb_gov_expenditure_gdp.csv',
    }

    panels = {}
    for key, fname in files.items():
        fpath = WB_DIR / fname
        if fpath.exists():
            df = pd.read_csv(fpath)
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna(subset=['year', 'value'])
            df = df[df['country_code'].str.len() <= 3]
            panels[key] = df[['country_code', 'year', 'value']].rename(
                columns={'value': f'{key}_pct_gdp'})

    if 'military' not in panels:
        logger.error("Military expenditure data not found")
        return pd.DataFrame()

    result = panels['military']
    for key in ['education', 'health', 'total']:
        if key in panels:
            result = result.merge(panels[key], on=['country_code', 'year'], how='outer')

    result['year'] = result['year'].astype(int)
    result = result.sort_values(['country_code', 'year']).reset_index(drop=True)
    logger.info(f"Military panel: {len(result):,} rows, {result['country_code'].nunique()} countries")
    return result


def classify_regime(year: int) -> str:
    for name, (start, end) in REGIMES.items():
        if start <= year <= end:
            return name
    return 'other'


def analyze_regime_shifts(panel: pd.DataFrame) -> pd.DataFrame:
    """Compare military spending across geopolitical regimes."""
    panel = panel.copy()
    panel['regime'] = panel['year'].apply(classify_regime)
    panel = panel[panel['regime'] != 'other']

    # Classify country blocs
    def classify_bloc(code):
        if code in NATO_COUNTRIES:
            return 'NATO'
        elif code in BRICS:
            return 'BRICS'
        else:
            return 'Other'

    panel['bloc'] = panel['country_code'].apply(classify_bloc)

    cols = [c for c in panel.columns if c.endswith('_pct_gdp')]
    results = panel.groupby(['bloc', 'regime'])[cols].agg(['mean', 'std', 'count']).reset_index()
    results.columns = ['_'.join(c).strip('_') for c in results.columns]

    return results


def compute_peace_dividend(panel: pd.DataFrame) -> pd.DataFrame:
    """Quantify the peace dividend: decline in military spending post-1991."""
    results = []

    for country, grp in panel.groupby('country_code'):
        cold_war = grp[(grp['year'] >= 1985) & (grp['year'] <= 1991)]['military_pct_gdp']
        post_cw = grp[(grp['year'] >= 1995) & (grp['year'] <= 2000)]['military_pct_gdp']

        if len(cold_war) >= 3 and len(post_cw) >= 3:
            cw_mean = cold_war.mean()
            pcw_mean = post_cw.mean()
            dividend = cw_mean - pcw_mean

            # Where did savings go?
            edu_cw = grp[(grp['year'] >= 1985) & (grp['year'] <= 1991)]['education_pct_gdp'].mean()
            edu_pcw = grp[(grp['year'] >= 1995) & (grp['year'] <= 2000)]['education_pct_gdp'].mean()
            health_cw = grp[(grp['year'] >= 1985) & (grp['year'] <= 1991)]['health_pct_gdp'].mean()
            health_pcw = grp[(grp['year'] >= 1995) & (grp['year'] <= 2000)]['health_pct_gdp'].mean()

            results.append({
                'country_code': country,
                'military_cold_war': cw_mean,
                'military_post_cw': pcw_mean,
                'peace_dividend_pct_gdp': dividend,
                'education_change': edu_pcw - edu_cw if not np.isnan(edu_cw) else np.nan,
                'health_change': health_pcw - health_cw if not np.isnan(health_cw) else np.nan,
            })

    df = pd.DataFrame(results)
    if not df.empty:
        df['dividend_to_social'] = df['education_change'].fillna(0) + df['health_change'].fillna(0)
        df['dividend_captured_pct'] = np.where(
            df['peace_dividend_pct_gdp'] > 0,
            df['dividend_to_social'] / df['peace_dividend_pct_gdp'] * 100,
            np.nan
        )
    return df


def analyze_military_crowding(panel: pd.DataFrame) -> pd.DataFrame:
    """Panel-level test: do military spending increases crowd out social spending?"""
    results = []

    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 15:
            continue

        grp = grp.set_index('year')
        cols = ['military_pct_gdp', 'education_pct_gdp', 'health_pct_gdp', 'total_pct_gdp']
        available = [c for c in cols if c in grp.columns]
        grp_clean = grp[available].dropna()
        if len(grp_clean) < 10:
            continue

        # Changes (first differences)
        changes = grp_clean.diff().dropna()
        if len(changes) < 5:
            continue

        row = {'country_code': country, 'n_years': len(changes)}

        if 'military_pct_gdp' in changes and 'education_pct_gdp' in changes:
            row['corr_dmil_dedu'] = changes['military_pct_gdp'].corr(changes['education_pct_gdp'])

        if 'military_pct_gdp' in changes and 'health_pct_gdp' in changes:
            row['corr_dmil_dhealth'] = changes['military_pct_gdp'].corr(changes['health_pct_gdp'])

        if 'military_pct_gdp' in changes and 'total_pct_gdp' in changes:
            row['corr_dmil_dtotal'] = changes['military_pct_gdp'].corr(changes['total_pct_gdp'])
            # Does military go UP when total goes UP? (expansion) or substitute?
            row['mil_share_of_expansion'] = np.nan
            both_up = changes[(changes['military_pct_gdp'] > 0) & (changes['total_pct_gdp'] > 0)]
            if len(both_up) > 3:
                row['mil_share_of_expansion'] = (
                    both_up['military_pct_gdp'].sum() / both_up['total_pct_gdp'].sum()
                )

        results.append(row)

    return pd.DataFrame(results)


def analyze_rearmament_2020s(panel: pd.DataFrame) -> pd.DataFrame:
    """Track the 2020s rearmament trend (post-Ukraine, NATO 2% target)."""
    recent = panel[panel['year'] >= 2014].copy()
    if recent.empty:
        return pd.DataFrame()

    results = []
    for country, grp in recent.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 5:
            continue

        mil = grp['military_pct_gdp'].dropna()
        if len(mil) < 3:
            continue

        results.append({
            'country_code': country,
            'mil_2014': grp[grp['year'] == 2014]['military_pct_gdp'].values[0]
                if 2014 in grp['year'].values else np.nan,
            'mil_latest': mil.iloc[-1],
            'mil_latest_year': grp[grp['military_pct_gdp'].notna()]['year'].iloc[-1],
            'mil_change_since_2014': mil.iloc[-1] - mil.iloc[0],
            'above_nato_2pct': mil.iloc[-1] >= 2.0,
            'trend_slope': np.polyfit(range(len(mil)), mil.values, 1)[0]
                if len(mil) >= 3 else np.nan,
        })

    return pd.DataFrame(results)


def run() -> dict:
    """Execute full military-fiscal tradeoff analysis."""
    logger.info("=" * 80)
    logger.info("A02: MILITARY SPENDING AND FISCAL TRADEOFFS")
    logger.info("=" * 80)

    panel = load_military_data()
    if panel.empty:
        return {}

    write_single_sheet_excel(panel, OUTPUT_DIR / "A02_military_panel.xlsx", "Panel")

    regime_shifts = analyze_regime_shifts(panel)
    if not regime_shifts.empty:
        write_single_sheet_excel(regime_shifts, OUTPUT_DIR / "A02_regime_shifts.xlsx", "Regimes")
        logger.info(f"Regime shift analysis: {len(regime_shifts)} rows")

    peace_div = compute_peace_dividend(panel)
    if not peace_div.empty:
        write_single_sheet_excel(peace_div, OUTPUT_DIR / "A02_peace_dividend.xlsx", "PeaceDividend")
        logger.info(f"Peace dividend: {len(peace_div)} countries, "
                   f"avg dividend = {peace_div['peace_dividend_pct_gdp'].mean():.2f}% GDP")

    crowding = analyze_military_crowding(panel)
    if not crowding.empty:
        write_single_sheet_excel(crowding, OUTPUT_DIR / "A02_crowding_out.xlsx", "Crowding")
        logger.info(f"Crowding analysis: {len(crowding)} countries")

    rearm = analyze_rearmament_2020s(panel)
    if not rearm.empty:
        write_single_sheet_excel(rearm, OUTPUT_DIR / "A02_rearmament_2020s.xlsx", "Rearmament")
        above_2pct = rearm['above_nato_2pct'].sum()
        logger.info(f"2020s rearmament: {len(rearm)} countries tracked, "
                   f"{above_2pct} above NATO 2% target")

    results = {
        'panel_rows': len(panel),
        'countries': panel['country_code'].nunique(),
        'peace_dividend_countries': len(peace_div),
        'avg_peace_dividend': peace_div['peace_dividend_pct_gdp'].mean() if not peace_div.empty else 0,
    }
    logger.info("A02 COMPLETE")
    return results


if __name__ == "__main__":
    run()
