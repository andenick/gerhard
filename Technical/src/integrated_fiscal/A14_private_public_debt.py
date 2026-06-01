"""
A14: Private vs Public Debt Dynamics
======================================
Tests Minsky hypothesis: private debt buildup → financial crisis → fiscal crisis.
Uses IMF private debt + JST banking crises + PWT profit rates.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

IMF_DIR = raw_data_dir() / "imf" / "gfs"
JST_DIR = raw_data_dir() / "jst"
PWT_DIR = raw_data_dir() / "profit_rates"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"


def load_data():
    """Load all required panels."""
    panels = {}

    # IMF private debt
    fpath = IMF_DIR / "imf_private_debt_wide.parquet"
    if fpath.exists():
        panels['imf_private'] = pd.read_parquet(fpath)
        logger.info(f"IMF private debt: {len(panels['imf_private']):,} rows")

    # IMF public debt (from combined)
    fpath2 = IMF_DIR / "imf_fiscal_wide_v2.parquet"
    if fpath2.exists():
        panels['imf_fiscal'] = pd.read_parquet(fpath2)
        logger.info(f"IMF fiscal: {len(panels['imf_fiscal']):,} rows")

    # JST
    fpath3 = JST_DIR / "jst_fiscal_panel.parquet"
    if fpath3.exists():
        df = pd.read_parquet(fpath3)
        df = df.rename(columns={'country_code': 'country_code'})
        panels['jst'] = df
        logger.info(f"JST: {len(df):,} rows")

    # PWT
    fpath4 = PWT_DIR / "pwt_profit_rate_panel.parquet"
    if fpath4.exists():
        df = pd.read_parquet(fpath4).rename(columns={'countrycode': 'country_code'})
        panels['pwt'] = df[['country_code', 'year', 'irr', 'labsh']].dropna(subset=['irr'])
        logger.info(f"PWT: {len(panels['pwt']):,} rows")

    return panels


def build_leverage_panel(panels: dict) -> pd.DataFrame:
    """Build combined public + private debt panel."""
    dfs = []

    # IMF private debt
    if 'imf_private' in panels:
        priv = panels['imf_private'].copy()
        priv_cols = [c for c in priv.columns if c not in ['country_code', 'year']]
        # Sum household + corporate = private total (or use Privatedebt_all)
        if 'Privatedebt_all' in priv.columns:
            priv['private_debt_gdp'] = priv['Privatedebt_all']
        elif 'HH_ALL' in priv.columns and 'NFC_ALL' in priv.columns:
            priv['private_debt_gdp'] = priv['HH_ALL'].fillna(0) + priv['NFC_ALL'].fillna(0)
        keep = ['country_code', 'year', 'private_debt_gdp']
        if 'HH_ALL' in priv.columns:
            keep.append('HH_ALL')
            priv = priv.rename(columns={'HH_ALL': 'hh_debt_gdp'})
            keep[-1] = 'hh_debt_gdp'
        if 'NFC_ALL' in priv.columns:
            keep.append('NFC_ALL')
            priv = priv.rename(columns={'NFC_ALL': 'nfc_debt_gdp'})
            keep[-1] = 'nfc_debt_gdp'
        available = [c for c in keep if c in priv.columns]
        dfs.append(priv[available])

    # IMF public debt
    if 'imf_fiscal' in panels:
        pub = panels['imf_fiscal'].copy()
        debt_col = next((c for c in pub.columns if 'XWDG' in c or 'DEBT' in c.upper()), None)
        if debt_col:
            pub = pub.rename(columns={debt_col: 'public_debt_gdp'})
            dfs.append(pub[['country_code', 'year', 'public_debt_gdp']])

    if not dfs:
        # Fallback to JST
        if 'jst' in panels:
            jst = panels['jst'].copy()
            result = pd.DataFrame()
            if 'debtgdp' in jst.columns:
                result['public_debt_gdp'] = jst['debtgdp'] * 100  # JST is ratio, convert to %
            if 'tloans' in jst.columns:
                result['private_debt_gdp'] = jst['tloans'] * 100
            if 'thh' in jst.columns:
                result['hh_debt_gdp'] = jst['thh'] * 100
            if 'tbus' in jst.columns:
                result['nfc_debt_gdp'] = jst['tbus'] * 100
            result['country_code'] = jst['country_code']
            result['year'] = jst['year']
            return result.dropna(subset=['country_code', 'year'])

        return pd.DataFrame()

    # Merge all
    result = dfs[0]
    for df in dfs[1:]:
        result = result.merge(df, on=['country_code', 'year'], how='outer')

    # Compute total leverage
    if 'private_debt_gdp' in result.columns and 'public_debt_gdp' in result.columns:
        result['total_leverage'] = result['private_debt_gdp'].fillna(0) + result['public_debt_gdp'].fillna(0)
        result['private_share'] = result['private_debt_gdp'] / result['total_leverage']
        result['public_share'] = result['public_debt_gdp'] / result['total_leverage']

    return result.dropna(subset=['country_code', 'year'])


def test_granger_private_to_public(panel: pd.DataFrame) -> pd.DataFrame:
    """Test: does private debt buildup predict public debt increase?"""
    if 'private_debt_gdp' not in panel.columns or 'public_debt_gdp' not in panel.columns:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year').dropna(subset=['private_debt_gdp', 'public_debt_gdp'])
        if len(grp) < 15:
            continue

        grp = grp.copy()
        grp['d_private'] = grp['private_debt_gdp'].diff()
        grp['d_public'] = grp['public_debt_gdp'].diff()
        grp['d_private_lag1'] = grp['d_private'].shift(1)
        grp['d_private_lag2'] = grp['d_private'].shift(2)

        valid = grp[['d_public', 'd_private_lag1', 'd_private_lag2']].dropna()
        if len(valid) < 10:
            continue

        # Simple Granger-style: does lagged private debt change predict public debt change?
        slope, intercept, r, p, se = stats.linregress(valid['d_private_lag1'], valid['d_public'])
        results.append({
            'country_code': country,
            'n_years': len(valid),
            'granger_slope': slope,
            'granger_r2': r ** 2,
            'granger_p': p,
            'private_predicts_public': slope > 0 and p < 0.10,
            'avg_private_debt': grp['private_debt_gdp'].mean(),
            'avg_public_debt': grp['public_debt_gdp'].mean(),
        })

    return pd.DataFrame(results)


def test_leverage_stability(panel: pd.DataFrame) -> pd.DataFrame:
    """H5: Is total leverage more stable than its components?"""
    if 'total_leverage' not in panel.columns:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year').dropna(subset=['total_leverage', 'private_debt_gdp', 'public_debt_gdp'])
        if len(grp) < 10:
            continue

        cv_total = grp['total_leverage'].std() / grp['total_leverage'].mean()
        cv_private = grp['private_debt_gdp'].std() / grp['private_debt_gdp'].mean()
        cv_public = grp['public_debt_gdp'].std() / grp['public_debt_gdp'].mean()

        # Correlation between changes
        changes = grp[['private_debt_gdp', 'public_debt_gdp']].diff().dropna()
        corr_changes = changes['private_debt_gdp'].corr(changes['public_debt_gdp'])

        results.append({
            'country_code': country,
            'cv_total': cv_total,
            'cv_private': cv_private,
            'cv_public': cv_public,
            'total_more_stable': cv_total < min(cv_private, cv_public),
            'corr_d_private_d_public': corr_changes,
            'substitution': corr_changes < 0,
        })

    return pd.DataFrame(results)


def crisis_event_study(panels: dict) -> pd.DataFrame:
    """Event study: what happens to debt around banking crises?"""
    if 'jst' not in panels:
        return pd.DataFrame()

    jst = panels['jst'].copy()
    if 'crisisJST' not in jst.columns or 'debtgdp' not in jst.columns:
        return pd.DataFrame()

    # Find crisis starts (transition from 0 to 1)
    jst = jst.sort_values(['country_code', 'year'])
    jst['crisis_start'] = (jst['crisisJST'] == 1) & (jst['crisisJST'].shift(1) == 0)

    crisis_events = jst[jst['crisis_start']].copy()
    logger.info(f"Banking crisis events: {len(crisis_events)}")

    results = []
    for _, event in crisis_events.iterrows():
        country = event['country_code']
        crisis_year = event['year']

        # Get window t-5 to t+5
        window = jst[(jst['country_code'] == country) &
                     (jst['year'] >= crisis_year - 5) &
                     (jst['year'] <= crisis_year + 5)].copy()
        if len(window) < 8:
            continue

        window['t'] = window['year'] - crisis_year

        row = {'country_code': country, 'crisis_year': crisis_year}

        # Debt at crisis vs 5 years later
        debt_at_crisis = window[window['t'] == 0]['debtgdp'].values
        debt_after = window[window['t'] == 5]['debtgdp'].values
        debt_before = window[window['t'] == -3]['debtgdp'].values

        if len(debt_at_crisis) > 0:
            row['debt_at_crisis'] = debt_at_crisis[0]
        if len(debt_after) > 0 and len(debt_at_crisis) > 0:
            row['debt_5yr_after'] = debt_after[0]
            row['fiscal_cost'] = (debt_after[0] - debt_at_crisis[0]) * 100  # pp of GDP

        # Private credit before crisis
        if 'tloans' in window.columns:
            pre_credit = window[window['t'] <= 0]['tloans'].mean()
            row['pre_crisis_credit_gdp'] = pre_credit

        results.append(row)

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A14: PRIVATE VS PUBLIC DEBT DYNAMICS")
    logger.info("=" * 80)

    panels = load_data()
    if not panels:
        logger.error("No data loaded")
        return {}

    leverage = build_leverage_panel(panels)
    if leverage.empty:
        logger.error("Could not build leverage panel")
        return {}

    write_single_sheet_excel(leverage.head(50000), OUTPUT_DIR / "A14_leverage_panel.xlsx", "Leverage")
    logger.info(f"Leverage panel: {len(leverage):,} rows, {leverage['country_code'].nunique()} countries")

    # Granger test
    granger = test_granger_private_to_public(leverage)
    if not granger.empty:
        write_single_sheet_excel(granger, OUTPUT_DIR / "A14_granger_causality.xlsx", "Granger")
        n_predicts = granger['private_predicts_public'].sum()
        logger.info(f"Private predicts public: {n_predicts}/{len(granger)} countries")

    # Stability test
    stability = test_leverage_stability(leverage)
    if not stability.empty:
        write_single_sheet_excel(stability, OUTPUT_DIR / "A14_leverage_stability.xlsx", "Stability")
        n_stable = stability['total_more_stable'].sum()
        n_substitution = stability['substitution'].sum()
        logger.info(f"Total more stable than components: {n_stable}/{len(stability)}")
        logger.info(f"Substitution (negative corr): {n_substitution}/{len(stability)}")

    # Crisis event study (JST)
    crisis = crisis_event_study(panels)
    if not crisis.empty:
        write_single_sheet_excel(crisis, OUTPUT_DIR / "A14_crisis_event_study.xlsx", "CrisisEvents")
        avg_cost = crisis['fiscal_cost'].dropna().mean()
        logger.info(f"Banking crises: {len(crisis)} events, avg fiscal cost: {avg_cost:.1f} pp GDP")

    logger.info("A14 COMPLETE")
    return {'leverage_rows': len(leverage)}


if __name__ == "__main__":
    run()
