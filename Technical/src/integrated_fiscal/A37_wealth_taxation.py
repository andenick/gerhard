"""
A37: Wealth Taxation — The Missing Instrument
===============================================
Tracks the decline of wealth taxes and tests whether countries that
abolished them saw faster wealth concentration.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"

# Countries known to have had/abolished wealth taxes
WEALTH_TAX_HISTORY = {
    'SWE': {'had': True, 'abolished': 2007}, 'FRA': {'had': True, 'abolished': 2018},
    'ESP': {'had': True, 'abolished': None}, 'NOR': {'had': True, 'abolished': None},
    'CHE': {'had': True, 'abolished': None}, 'NLD': {'had': True, 'abolished': 2001},
    'FIN': {'had': True, 'abolished': 2006}, 'ISL': {'had': True, 'abolished': 2006},
    'DEU': {'had': True, 'abolished': 1997}, 'AUT': {'had': True, 'abolished': 1994},
    'DNK': {'had': True, 'abolished': 1997}, 'LUX': {'had': True, 'abolished': 2006},
    'ITA': {'had': True, 'abolished': 1992}, 'IRL': {'had': True, 'abolished': 1978},
    'USA': {'had': False, 'abolished': None}, 'GBR': {'had': False, 'abolished': None},
    'CAN': {'had': False, 'abolished': None}, 'AUS': {'had': False, 'abolished': None},
    'JPN': {'had': False, 'abolished': None}, 'KOR': {'had': False, 'abolished': None},
    'COL': {'had': True, 'abolished': None},
}


def load_data():
    sources = {}
    grd_path = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    if grd_path.exists():
        sources['grd'] = pd.read_parquet(grd_path)
    # WID wealth shares
    wid_dir = raw_data_dir() / "wid"
    sources['wid_dir'] = wid_dir
    return sources


def track_property_tax_trends(grd: pd.DataFrame) -> pd.DataFrame:
    """Track property tax revenue (proxy for wealth-adjacent taxation)."""
    if grd.empty or 'property_taxes' not in grd.columns:
        return pd.DataFrame()

    results = []
    for country, grp in grd.groupby('iso'):
        grp = grp.sort_values('year')
        prop = grp['property_taxes'].dropna()
        if len(prop) < 5:
            continue
        results.append({
            'iso': country, 'country': grp['country'].iloc[0],
            'income_group': grp['income_group'].iloc[0],
            'property_tax_mean': prop.mean(),
            'property_tax_latest': prop.iloc[-1],
            'property_tax_trend': np.polyfit(range(len(prop)), prop.values, 1)[0] if len(prop) >= 5 else np.nan,
            'had_wealth_tax': WEALTH_TAX_HISTORY.get(country, {}).get('had', False),
            'abolished_year': WEALTH_TAX_HISTORY.get(country, {}).get('abolished'),
        })

    return pd.DataFrame(results)


def compute_wealth_tax_gap(grd: pd.DataFrame) -> pd.DataFrame:
    """Estimate: if a 1% wealth tax existed, how much revenue?
    Proxy: total wealth ≈ 5× GDP (typical for advanced economies).
    """
    if grd.empty:
        return pd.DataFrame()

    latest = grd[grd['year'] >= grd['year'].max() - 2]
    avg = latest.groupby('iso').agg({
        'country': 'first', 'income_group': 'first',
        'taxes_inc_sc': 'mean', 'property_taxes': 'mean',
    }).reset_index()

    # Hypothetical 1% annual wealth tax on net wealth ≈ 5× GDP
    avg['hypothetical_wealth_tax_1pct'] = 5.0  # 1% of 500% GDP = 5% GDP
    avg['actual_property_tax'] = avg['property_taxes']
    avg['wealth_tax_gap'] = avg['hypothetical_wealth_tax_1pct'] - avg['actual_property_tax'].fillna(0)
    avg['gap_as_pct_current_tax'] = avg['wealth_tax_gap'] / avg['taxes_inc_sc'] * 100

    return avg.sort_values('wealth_tax_gap', ascending=False)


def extract_wid_wealth_shares(wid_dir: Path) -> pd.DataFrame:
    """Extract top 1% wealth share from WID for key countries."""
    results = []
    for country_code in ['US', 'GB', 'FR', 'DE', 'SE', 'NO', 'DK', 'AU', 'CA', 'JP']:
        fpath = wid_dir / f"WID_data_{country_code}.csv"
        if not fpath.exists():
            continue
        try:
            df = pd.read_csv(fpath, sep=';', low_memory=False)
            # Top 1% wealth share: variable starts with 'shweal', percentile 'p99p100'
            wealth = df[(df['variable'].str.startswith('shweal')) & (df['percentile'] == 'p99p100')]
            if wealth.empty:
                continue
            wealth = wealth[['year', 'value']].copy()
            wealth['year'] = pd.to_numeric(wealth['year'], errors='coerce')
            wealth['value'] = pd.to_numeric(wealth['value'], errors='coerce')
            wealth = wealth.dropna()
            wealth['country_code'] = country_code
            results.append(wealth)
        except Exception:
            continue

    if results:
        return pd.concat(results, ignore_index=True)
    return pd.DataFrame()


def test_abolition_wealth_concentration(wealth_shares: pd.DataFrame) -> pd.DataFrame:
    """H10: Did countries that abolished wealth taxes see faster wealth concentration?"""
    if wealth_shares.empty:
        return pd.DataFrame()

    # Map 2-letter to abolition status
    iso2_to_status = {
        'SE': ('abolished', 2007), 'FR': ('abolished', 2018),
        'DE': ('abolished', 1997), 'DK': ('abolished', 1997),
        'NO': ('kept', None), 'US': ('never_had', None),
        'GB': ('never_had', None), 'AU': ('never_had', None),
        'CA': ('never_had', None), 'JP': ('never_had', None),
    }

    results = []
    for country, grp in wealth_shares.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 10:
            continue

        status, year = iso2_to_status.get(country, ('unknown', None))
        row = {'country_code': country, 'status': status, 'abolition_year': year}

        if year and status == 'abolished':
            pre = grp[grp['year'] < year]['value']
            post = grp[grp['year'] >= year]['value']
            if len(pre) >= 3 and len(post) >= 3:
                row['top1_share_pre'] = pre.mean()
                row['top1_share_post'] = post.mean()
                row['top1_change'] = post.mean() - pre.mean()
                row['wealth_concentrated_after'] = post.mean() > pre.mean()
        else:
            row['top1_share_latest'] = grp['value'].iloc[-1]

        # Overall trend
        if len(grp) >= 10:
            row['top1_trend'] = np.polyfit(grp['year'].values, grp['value'].values, 1)[0]

        results.append(row)

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A37: WEALTH TAXATION — THE MISSING INSTRUMENT")
    logger.info("=" * 80)

    sources = load_data()

    # Property tax trends
    if 'grd' in sources:
        prop_trends = track_property_tax_trends(sources['grd'])
        if not prop_trends.empty:
            write_single_sheet_excel(prop_trends, OUTPUT_DIR / "A37_property_tax_trends.xlsx", "PropTax")
            avg_by_group = prop_trends.groupby('income_group')['property_tax_mean'].mean()
            logger.info(f"Avg property tax by income group:\n{avg_by_group.to_string()}")

        # Wealth tax gap
        gap = compute_wealth_tax_gap(sources['grd'])
        if not gap.empty:
            write_single_sheet_excel(gap, OUTPUT_DIR / "A37_wealth_tax_gap.xlsx", "Gap")
            avg_gap = gap['wealth_tax_gap'].mean()
            logger.info(f"Avg wealth tax gap: {avg_gap:.1f}% GDP "
                       f"(= {gap['gap_as_pct_current_tax'].mean():.0f}% of current tax revenue)")

    # WID wealth shares
    if 'wid_dir' in sources:
        wealth_shares = extract_wid_wealth_shares(sources['wid_dir'])
        if not wealth_shares.empty:
            logger.info(f"WID wealth shares: {len(wealth_shares)} obs, "
                       f"{wealth_shares['country_code'].nunique()} countries")

            abolition_test = test_abolition_wealth_concentration(wealth_shares)
            if not abolition_test.empty:
                write_single_sheet_excel(abolition_test, OUTPUT_DIR / "A37_abolition_test.xlsx", "Abolition")
                abolished = abolition_test[abolition_test['status'] == 'abolished']
                if not abolished.empty and 'wealth_concentrated_after' in abolished.columns:
                    n_concentrated = abolished['wealth_concentrated_after'].sum()
                    logger.info(f"Wealth concentrated after tax abolition: "
                               f"{n_concentrated}/{len(abolished)} countries")
                logger.info("Wealth tax abolition results:")
                for _, row in abolition_test.iterrows():
                    trend = row.get('top1_trend', np.nan)
                    trend_str = f"trend={trend*100:.2f}pp/yr" if pd.notna(trend) else ""
                    logger.info(f"  {row['country_code']}: {row['status']} {trend_str}")

    logger.info("A37 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
