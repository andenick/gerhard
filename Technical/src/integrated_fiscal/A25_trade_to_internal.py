"""
A25: Trade Tax to Internal Tax Transition
==========================================
Documents how developing countries shifted from customs duties to internal taxes.
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


def load_grd():
    fpath = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    return pd.read_parquet(fpath) if fpath.exists() else pd.DataFrame()


def analyze_trade_tax_decline(grd: pd.DataFrame) -> pd.DataFrame:
    if grd.empty or 'trade_taxes' not in grd.columns:
        return pd.DataFrame()
    grd = grd.copy()
    grd['decade'] = (grd['year'] // 10) * 10
    # Focus on developing countries
    dev = grd[grd['income_group'].isin(['Low income', 'Lower middle income', 'Upper middle income'])]
    results = dev.groupby(['income_group', 'decade']).agg(
        trade_mean=('trade_taxes', 'mean'),
        goods_services_mean=('goods_services', 'mean'),
        vat_mean=('vat', 'mean'),
        taxes_mean=('taxes_inc_sc', 'mean'),
        n=('iso', 'count')
    ).reset_index()
    results['trade_share'] = results['trade_mean'] / results['taxes_mean'] * 100
    results['gs_share'] = results['goods_services_mean'] / results['taxes_mean'] * 100
    return results


def identify_transition_episodes(grd: pd.DataFrame) -> pd.DataFrame:
    """Find countries where trade taxes fell significantly and identify replacement."""
    if grd.empty:
        return pd.DataFrame()
    results = []
    for country, grp in grd.groupby('iso'):
        grp = grp.sort_values('year')
        if len(grp) < 10 or 'trade_taxes' not in grp.columns:
            continue
        trade = grp['trade_taxes'].dropna()
        if len(trade) < 5:
            continue
        peak = trade.max()
        latest = trade.iloc[-1]
        if peak > 3 and (peak - latest) > 2:  # Significant decline
            peak_year = grp.loc[trade.idxmax(), 'year']
            row = {'iso': country, 'country': grp['country'].iloc[0],
                  'income_group': grp['income_group'].iloc[0],
                  'trade_peak': peak, 'trade_peak_year': int(peak_year),
                  'trade_latest': latest, 'trade_decline': peak - latest}
            # What replaced it?
            pre = grp[grp['year'] <= peak_year]
            post = grp[grp['year'] > peak_year]
            if len(post) >= 3:
                for col in ['vat', 'goods_services', 'pit', 'cit']:
                    if col in grp.columns:
                        row[f'{col}_pre'] = pre[col].mean()
                        row[f'{col}_post'] = post[col].mean()
                        row[f'{col}_change'] = post[col].mean() - pre[col].mean()
                # Revenue recovery?
                row['total_tax_pre'] = pre['taxes_inc_sc'].mean() if 'taxes_inc_sc' in pre else np.nan
                row['total_tax_post'] = post['taxes_inc_sc'].mean() if 'taxes_inc_sc' in post else np.nan
                row['revenue_recovered'] = row.get('total_tax_post', 0) >= row.get('total_tax_pre', 0)
            results.append(row)
    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A25: TRADE TAX TO INTERNAL TAX TRANSITION")
    logger.info("=" * 80)
    grd = load_grd()
    if grd.empty:
        return {}

    decline = analyze_trade_tax_decline(grd)
    if not decline.empty:
        write_single_sheet_excel(decline, OUTPUT_DIR / "A25_trade_tax_decline.xlsx", "Decline")
        logger.info(f"Trade tax decline by income group:\n{decline[['income_group','decade','trade_mean','trade_share']].to_string(index=False)}")

    episodes = identify_transition_episodes(grd)
    if not episodes.empty:
        write_single_sheet_excel(episodes, OUTPUT_DIR / "A25_transition_episodes.xlsx", "Episodes")
        n_recovered = episodes.get('revenue_recovered', pd.Series()).sum()
        logger.info(f"Transition episodes: {len(episodes)} countries, {n_recovered} recovered revenue")

    logger.info("A25 COMPLETE")
    return {'episodes': len(episodes)}


if __name__ == "__main__":
    run()
