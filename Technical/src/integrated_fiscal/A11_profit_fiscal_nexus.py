"""
A11: Profit Rate ↔ Fiscal Dynamics Nexus
==========================================
THE dissertation connection. Tests whether declining profit rates drive
fiscal deterioration across 18 advanced economies, 1870-2020.

Uses JST Macrohistory (fiscal) + PWT (profit rates) to test:
- Do profit rate declines precede fiscal deficits?
- Does revenue composition shift when profits fall?
- Are these relationships regime-dependent?

Data: JST (18 countries, 1870-2020) + PWT (183 countries, 1950-2019)
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
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

JST_DIR = raw_data_dir() / "jst"
PWT_DIR = raw_data_dir() / "profit_rates"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ISO2→ISO3 mapping for PWT→JST merge
ISO2_TO_ISO3 = {
    'AU': 'AUS', 'BE': 'BEL', 'CA': 'CAN', 'CH': 'CHE', 'DE': 'DEU',
    'DK': 'DNK', 'ES': 'ESP', 'FI': 'FIN', 'FR': 'FRA', 'GB': 'GBR',
    'IE': 'IRL', 'IT': 'ITA', 'JP': 'JPN', 'NL': 'NLD', 'NO': 'NOR',
    'PT': 'PRT', 'SE': 'SWE', 'US': 'USA',
}
ISO3_TO_ISO2 = {v: k for k, v in ISO2_TO_ISO3.items()}


def load_jst_fiscal() -> pd.DataFrame:
    """Load JST fiscal panel."""
    fpath = JST_DIR / "jst_fiscal_panel.parquet"
    if not fpath.exists():
        logger.error(f"JST fiscal panel not found: {fpath}")
        return pd.DataFrame()

    df = pd.read_parquet(fpath)
    df = df.rename(columns={'country_code': 'iso3'})
    logger.info(f"JST fiscal: {len(df)} rows, {df['iso3'].nunique()} countries, "
               f"{df['year'].min()}-{df['year'].max()}")
    return df


def load_pwt_profit() -> pd.DataFrame:
    """Load PWT profit rate panel."""
    fpath = PWT_DIR / "pwt_profit_rate_panel.parquet"
    if not fpath.exists():
        logger.error(f"PWT profit panel not found: {fpath}")
        return pd.DataFrame()

    df = pd.read_parquet(fpath)
    # Filter to JST countries only
    jst_codes = list(ISO2_TO_ISO3.values())
    df = df[df['countrycode'].isin(jst_codes)].copy()
    df = df.rename(columns={'countrycode': 'iso3'})
    logger.info(f"PWT profit (JST countries): {len(df)} rows, {df['iso3'].nunique()} countries, "
               f"{df['year'].min()}-{df['year'].max()}")
    return df


def merge_profit_fiscal() -> pd.DataFrame:
    """Merge JST fiscal with PWT profit rates."""
    jst = load_jst_fiscal()
    pwt = load_pwt_profit()

    if jst.empty or pwt.empty:
        return pd.DataFrame()

    # Merge on iso3 + year (overlap: 1950-2019)
    pwt_subset = pwt[['iso3', 'year', 'labsh', 'capital_share', 'irr']].copy()
    merged = jst.merge(pwt_subset, on=['iso3', 'year'], how='inner')

    logger.info(f"Merged profit-fiscal panel: {len(merged)} rows, "
               f"{merged['iso3'].nunique()} countries, "
               f"{merged['year'].min()}-{merged['year'].max()}")
    return merged


def compute_profit_fiscal_correlations(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute country-level correlations between profit rates and fiscal variables."""
    if panel.empty:
        return pd.DataFrame()

    results = []
    fiscal_vars = ['revenue', 'expenditure', 'debtgdp']
    available_fiscal = [v for v in fiscal_vars if v in panel.columns]

    for country, grp in panel.groupby('iso3'):
        grp = grp.sort_values('year').dropna(subset=['irr'])
        if len(grp) < 15:
            continue

        row = {
            'iso3': country,
            'n_years': len(grp),
            'irr_mean': grp['irr'].mean(),
            'irr_trend': np.polyfit(grp['year'] - grp['year'].min(), grp['irr'], 1)[0],
            'labsh_mean': grp['labsh'].mean(),
        }

        # Level correlations
        for fvar in available_fiscal:
            valid = grp[['irr', fvar]].dropna()
            if len(valid) > 10:
                row[f'corr_irr_{fvar}'] = valid['irr'].corr(valid[fvar])

        # Change correlations (first differences)
        grp_diff = grp[['irr'] + available_fiscal].diff()
        grp_diff = grp_diff.dropna()
        if len(grp_diff) > 10:
            for fvar in available_fiscal:
                valid = grp_diff[['irr', fvar]].dropna()
                if len(valid) > 8:
                    row[f'corr_dirr_d{fvar}'] = valid['irr'].corr(valid[fvar])

        # Granger-style test: does lagged profit rate predict fiscal balance?
        if 'revenue' in grp.columns and 'expenditure' in grp.columns:
            grp = grp.copy()
            grp['fiscal_balance'] = grp['revenue'] - grp['expenditure']
            grp['irr_lag1'] = grp['irr'].shift(1)
            grp['irr_lag2'] = grp['irr'].shift(2)
            valid = grp[['fiscal_balance', 'irr_lag1', 'irr_lag2']].dropna()
            if len(valid) > 15:
                slope, _, r, p, _ = stats.linregress(valid['irr_lag1'], valid['fiscal_balance'])
                row['granger_slope_lag1'] = slope
                row['granger_r2_lag1'] = r ** 2
                row['granger_p_lag1'] = p
                row['profit_predicts_fiscal'] = p < 0.05

        results.append(row)

    return pd.DataFrame(results)


def analyze_regime_differences(panel: pd.DataFrame) -> pd.DataFrame:
    """Test if profit-fiscal relationship differs across accumulation regimes."""
    if panel.empty:
        return pd.DataFrame()

    regimes = {
        'golden_age': (1950, 1973),
        'crisis_transition': (1974, 1982),
        'neoliberal': (1983, 2007),
        'post_gfc': (2008, 2019),
    }

    panel = panel.copy()
    panel['regime'] = 'other'
    for name, (start, end) in regimes.items():
        mask = (panel['year'] >= start) & (panel['year'] <= end)
        panel.loc[mask, 'regime'] = name

    results = []
    for regime in regimes.keys():
        regime_data = panel[panel['regime'] == regime]
        if len(regime_data) < 50:
            continue

        row = {'regime': regime, 'n_obs': len(regime_data)}

        # Average profit rate and fiscal indicators
        row['avg_irr'] = regime_data['irr'].mean()
        row['avg_labsh'] = regime_data['labsh'].mean()
        if 'debtgdp' in regime_data.columns:
            row['avg_debtgdp'] = regime_data['debtgdp'].mean()
        if 'revenue' in regime_data.columns:
            row['avg_revenue'] = regime_data['revenue'].mean()
        if 'expenditure' in regime_data.columns:
            row['avg_expenditure'] = regime_data['expenditure'].mean()

        # Correlation within regime
        if 'revenue' in regime_data.columns:
            valid = regime_data[['irr', 'revenue']].dropna()
            if len(valid) > 20:
                row['corr_irr_revenue'] = valid['irr'].corr(valid['revenue'])

        if 'debtgdp' in regime_data.columns:
            valid = regime_data[['irr', 'debtgdp']].dropna()
            if len(valid) > 20:
                row['corr_irr_debt'] = valid['irr'].corr(valid['debtgdp'])

        results.append(row)

    return pd.DataFrame(results)


def analyze_crisis_fiscal_interaction(panel: pd.DataFrame) -> pd.DataFrame:
    """Do banking crises amplify the profit→fiscal channel?"""
    if panel.empty or 'crisisJST' not in panel.columns:
        return pd.DataFrame()

    panel = panel.copy()
    panel['fiscal_balance'] = panel.get('revenue', 0) - panel.get('expenditure', 0)

    # Compare fiscal deterioration in crisis vs non-crisis years
    crisis = panel[panel['crisisJST'] == 1]
    normal = panel[panel['crisisJST'] == 0]

    results = [{
        'period': 'crisis_years',
        'n_obs': len(crisis),
        'avg_irr': crisis['irr'].mean(),
        'avg_fiscal_balance': crisis['fiscal_balance'].mean() if 'fiscal_balance' in crisis else np.nan,
        'avg_debt_change': crisis['debtgdp'].diff().mean() if 'debtgdp' in crisis else np.nan,
    }, {
        'period': 'normal_years',
        'n_obs': len(normal),
        'avg_irr': normal['irr'].mean(),
        'avg_fiscal_balance': normal['fiscal_balance'].mean() if 'fiscal_balance' in normal else np.nan,
        'avg_debt_change': normal['debtgdp'].diff().mean() if 'debtgdp' in normal else np.nan,
    }]

    # Does low profit rate predict crises?
    if len(panel) > 100:
        panel['irr_lag3'] = panel.groupby('iso3')['irr'].shift(3)
        valid = panel[['crisisJST', 'irr_lag3']].dropna()
        if len(valid) > 50:
            crisis_irr = valid[valid['crisisJST'] == 1]['irr_lag3'].mean()
            normal_irr = valid[valid['crisisJST'] == 0]['irr_lag3'].mean()
            results.append({
                'period': 'irr_3yr_before_crisis',
                'n_obs': len(valid[valid['crisisJST'] == 1]),
                'avg_irr': crisis_irr,
                'avg_fiscal_balance': np.nan,
                'avg_debt_change': np.nan,
            })
            results.append({
                'period': 'irr_3yr_before_normal',
                'n_obs': len(valid[valid['crisisJST'] == 0]),
                'avg_irr': normal_irr,
                'avg_fiscal_balance': np.nan,
                'avg_debt_change': np.nan,
            })

    return pd.DataFrame(results)


def compute_long_run_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Create decade-average panel for long-run structural analysis."""
    if panel.empty:
        return pd.DataFrame()

    panel = panel.copy()
    panel['decade'] = (panel['year'] // 10) * 10

    numeric_cols = panel.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ['year', 'decade']]

    decade_panel = panel.groupby(['iso3', 'decade'])[numeric_cols].mean().reset_index()
    return decade_panel


def run() -> dict:
    """Execute profit-fiscal nexus analysis."""
    logger.info("=" * 80)
    logger.info("A11: PROFIT RATE ↔ FISCAL DYNAMICS NEXUS")
    logger.info("=" * 80)

    panel = merge_profit_fiscal()
    if panel.empty:
        logger.error("Cannot merge profit and fiscal data. Aborting.")
        return {}

    write_single_sheet_excel(panel, OUTPUT_DIR / "A11_profit_fiscal_panel.xlsx", "Panel")
    logger.info(f"Wrote merged panel: {len(panel)} rows")

    # Country-level correlations
    correlations = compute_profit_fiscal_correlations(panel)
    if not correlations.empty:
        write_single_sheet_excel(correlations, OUTPUT_DIR / "A11_profit_fiscal_correlations.xlsx", "Correlations")
        logger.info(f"Correlations: {len(correlations)} countries")

        if 'profit_predicts_fiscal' in correlations.columns:
            n_sig = correlations['profit_predicts_fiscal'].sum()
            logger.info(f"Profit rate predicts fiscal balance: {n_sig}/{len(correlations)} countries (p<0.05)")

        if 'corr_irr_debtgdp' in correlations.columns:
            avg_corr = correlations['corr_irr_debtgdp'].mean()
            logger.info(f"Avg correlation (profit rate vs debt/GDP): {avg_corr:.3f}")

    # Regime analysis
    regimes = analyze_regime_differences(panel)
    if not regimes.empty:
        write_single_sheet_excel(regimes, OUTPUT_DIR / "A11_regime_analysis.xlsx", "Regimes")
        logger.info(f"Regime analysis:")
        for _, row in regimes.iterrows():
            logger.info(f"  {row['regime']:20s}  IRR={row['avg_irr']:.1%}  "
                       f"debt={row.get('avg_debtgdp', 0):.1f}%")

    # Crisis interaction
    crisis = analyze_crisis_fiscal_interaction(panel)
    if not crisis.empty:
        write_single_sheet_excel(crisis, OUTPUT_DIR / "A11_crisis_interaction.xlsx", "Crisis")
        logger.info(f"Crisis-fiscal interaction: {len(crisis)} comparisons")

    # Decade panel for structural analysis
    decade_panel = compute_long_run_panel(panel)
    if not decade_panel.empty:
        write_single_sheet_excel(decade_panel, OUTPUT_DIR / "A11_decade_panel.xlsx", "Decades")
        logger.info(f"Decade panel: {len(decade_panel)} obs")

    logger.info("A11 COMPLETE")
    return {
        'panel_rows': len(panel),
        'countries': panel['iso3'].nunique(),
        'year_range': f"{panel['year'].min()}-{panel['year'].max()}",
    }


if __name__ == "__main__":
    run()
