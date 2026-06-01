"""
A28: Government Debt Interest as Upward Transfer
==================================================
Quantifies how interest payments on public debt flow to wealthy bondholders.
Tests: did debt REPLACE lost corporate tax revenue?
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
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
JST_DIR = raw_data_dir() / "jst"
OECD_DIR = raw_data_dir() / "oecd" / "revenue_stats"


def load_jst():
    fpath = JST_DIR / "JSTdatasetR6.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_parquet(fpath)
    if 'iso' in df.columns:
        df = df.rename(columns={'iso': 'country_code'})
    return df


def analyze_interest_payments(jst: pd.DataFrame) -> pd.DataFrame:
    """Track government interest payments as transfer channel."""
    # JST doesn't have explicit interest payments, but we can use:
    # expenditure - (expenditure proxy without interest)
    # OR use the debt × interest rate as proxy
    if jst.empty:
        return pd.DataFrame()

    jst = jst.copy()
    # Interest payment proxy = debt_ratio × long-term rate
    if 'debtgdp' in jst.columns and 'ltrate' in jst.columns:
        jst['interest_payments_proxy'] = jst['debtgdp'] * jst['ltrate'] / 100
        # As % of GDP
        jst['interest_gdp_proxy'] = jst['interest_payments_proxy']

    results = []
    for year in sorted(jst['year'].unique()):
        yr = jst[jst['year'] == year]
        row = {'year': year, 'n_countries': len(yr)}
        for col in ['debtgdp', 'ltrate', 'interest_gdp_proxy', 'revenue', 'expenditure']:
            if col in yr.columns:
                valid = yr[col].dropna()
                if len(valid) >= 5:
                    row[f'{col}_mean'] = valid.mean()
        results.append(row)

    return pd.DataFrame(results)


def test_debt_replaced_tax_cuts(jst: pd.DataFrame) -> pd.DataFrame:
    """Test H1: debt accumulation = cumulative corporate tax revenue lost."""
    if jst.empty:
        return pd.DataFrame()

    # For JST countries, compare debt accumulation post-1980 with revenue trajectory
    results = []
    for country, grp in jst.groupby('country_code'):
        grp = grp.sort_values('year')
        pre = grp[(grp['year'] >= 1960) & (grp['year'] <= 1979)]
        post = grp[(grp['year'] >= 1980) & (grp['year'] <= 2019)]

        if len(pre) < 10 or len(post) < 10:
            continue

        # Revenue decline from pre-1980 trend
        pre_rev_mean = pre['revenue'].mean() if 'revenue' in pre.columns else np.nan
        post_rev_mean = post['revenue'].mean() if 'revenue' in post.columns else np.nan

        # Debt accumulation
        debt_1980 = grp[grp['year'] == 1980]['debtgdp'].values
        debt_2019 = grp[grp['year'] == 2019]['debtgdp'].values

        if len(debt_1980) > 0 and len(debt_2019) > 0:
            debt_change = debt_2019[0] - debt_1980[0]
        else:
            debt_change = np.nan

        results.append({
            'country_code': country,
            'revenue_pre1980': pre_rev_mean,
            'revenue_post1980': post_rev_mean,
            'revenue_decline': post_rev_mean - pre_rev_mean if pd.notna(pre_rev_mean) else np.nan,
            'debt_1980': debt_1980[0] if len(debt_1980) > 0 else np.nan,
            'debt_2019': debt_2019[0] if len(debt_2019) > 0 else np.nan,
            'debt_accumulation': debt_change,
        })

    df = pd.DataFrame(results)
    if not df.empty and 'revenue_decline' in df.columns and 'debt_accumulation' in df.columns:
        valid = df[['revenue_decline', 'debt_accumulation']].dropna()
        if len(valid) > 5:
            corr = valid['revenue_decline'].corr(valid['debt_accumulation'])
            logger.info(f"Correlation (revenue decline vs debt accumulation): {corr:.3f}")

    return df


def compute_interest_transfer_estimate(jst: pd.DataFrame) -> pd.DataFrame:
    """Estimate annual interest transfer to wealthy bondholders."""
    if jst.empty or 'debtgdp' not in jst.columns:
        return pd.DataFrame()

    jst = jst.copy()
    jst['decade'] = (jst['year'] // 10) * 10

    # Interest = debt/GDP × interest rate
    if 'ltrate' in jst.columns:
        jst['interest_gdp'] = jst['debtgdp'] * jst['ltrate'] / 100
        # Assume top 10% hold ~50-70% of government bonds (conservative)
        # This varies by country and era
        jst['transfer_to_top10'] = jst['interest_gdp'] * 0.6  # 60% to top decile
    else:
        return pd.DataFrame()

    results = jst.groupby('decade').agg({
        'debtgdp': 'mean',
        'ltrate': 'mean',
        'interest_gdp': 'mean',
        'transfer_to_top10': 'mean',
        'country_code': 'count',
    }).reset_index().rename(columns={'country_code': 'n_obs'})

    return results


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A28: PUBLIC DEBT INTEREST AS UPWARD TRANSFER")
    logger.info("=" * 80)

    jst = load_jst()
    if jst.empty:
        logger.error("No JST data")
        return {}

    # Interest payments over time
    interest_ts = analyze_interest_payments(jst)
    if not interest_ts.empty:
        write_single_sheet_excel(interest_ts, OUTPUT_DIR / "A28_interest_payments.xlsx", "Interest")
        logger.info(f"Interest payments: {len(interest_ts)} years")

    # Debt replaced tax cuts?
    replacement = test_debt_replaced_tax_cuts(jst)
    if not replacement.empty:
        write_single_sheet_excel(replacement, OUTPUT_DIR / "A28_debt_replaced_tax.xlsx", "Replacement")
        avg_debt_acc = replacement['debt_accumulation'].dropna().mean()
        logger.info(f"Avg debt accumulation 1980-2019: {avg_debt_acc:.1%} of GDP")

    # Transfer estimate
    transfer = compute_interest_transfer_estimate(jst)
    if not transfer.empty:
        write_single_sheet_excel(transfer, OUTPUT_DIR / "A28_transfer_estimate.xlsx", "Transfer")
        logger.info("Interest transfer by decade:")
        for _, row in transfer.iterrows():
            logger.info(f"  {int(row['decade'])}s: debt={row['debtgdp']:.0%} GDP, "
                       f"rate={row['ltrate']:.1f}%, interest={row['interest_gdp']:.1%} GDP, "
                       f"transfer to top 10%={row['transfer_to_top10']:.1%} GDP")

    logger.info("A28 COMPLETE")
    return {'years': len(interest_ts)}


if __name__ == "__main__":
    run()
