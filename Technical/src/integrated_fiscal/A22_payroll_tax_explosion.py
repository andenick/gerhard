"""
A22: Payroll Tax Explosion — The Stealth Regressive Shift
==========================================================
Documents how social security contributions (flat payroll taxes) doubled
across the OECD since 1965, replacing progressive income taxes.
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


def load_data():
    grd_path = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    oecd_path = raw_data_dir() / "oecd" / "revenue_stats" / "oecd_revenue_wide.parquet"
    grd = pd.read_parquet(grd_path) if grd_path.exists() else pd.DataFrame()
    oecd = pd.read_parquet(oecd_path) if oecd_path.exists() else pd.DataFrame()
    return grd, oecd


def analyze_ssc_trajectory(grd: pd.DataFrame) -> pd.DataFrame:
    if grd.empty or 'social_contributions' not in grd.columns:
        return pd.DataFrame()
    grd = grd.copy()
    grd['decade'] = (grd['year'] // 10) * 10
    results = grd.groupby(['income_group', 'decade']).agg(
        ssc_mean=('social_contributions', 'mean'),
        ssc_median=('social_contributions', 'median'),
        taxes_mean=('taxes_inc_sc', 'mean'),
        n=('iso', 'count')
    ).reset_index()
    results['ssc_share_of_total'] = results['ssc_mean'] / results['taxes_mean'] * 100
    return results


def analyze_ssc_vs_pit(grd: pd.DataFrame) -> pd.DataFrame:
    """Track the SSC/PIT ratio over time — rising = more regressive."""
    if grd.empty:
        return pd.DataFrame()
    results = []
    for country, grp in grd.groupby('iso'):
        grp = grp.sort_values('year')
        valid = grp[['year', 'pit', 'social_contributions', 'taxes_inc_sc']].dropna(subset=['pit', 'social_contributions'])
        if len(valid) < 10:
            continue
        mid = valid['year'].median()
        early = valid[valid['year'] <= mid]
        late = valid[valid['year'] > mid]
        results.append({
            'iso': country, 'country': grp['country'].iloc[0],
            'income_group': grp['income_group'].iloc[0],
            'ssc_early': early['social_contributions'].mean(),
            'ssc_late': late['social_contributions'].mean(),
            'ssc_change': late['social_contributions'].mean() - early['social_contributions'].mean(),
            'pit_early': early['pit'].mean(),
            'pit_late': late['pit'].mean(),
            'pit_change': late['pit'].mean() - early['pit'].mean(),
            'ssc_pit_ratio_early': early['social_contributions'].mean() / early['pit'].mean() if early['pit'].mean() > 0 else np.nan,
            'ssc_pit_ratio_late': late['social_contributions'].mean() / late['pit'].mean() if late['pit'].mean() > 0 else np.nan,
        })
    return pd.DataFrame(results)


def analyze_bismarck_vs_beveridge(grd: pd.DataFrame) -> pd.DataFrame:
    """Compare Bismarckian (high SSC) vs Beveridge (general revenue) systems."""
    bismarck = ['DEU', 'FRA', 'AUT', 'BEL', 'NLD', 'LUX', 'ITA', 'ESP', 'PRT', 'GRC', 'JPN']
    beveridge = ['GBR', 'IRL', 'DNK', 'SWE', 'NOR', 'FIN', 'ISL', 'AUS', 'NZL', 'CAN']
    hybrid = ['USA', 'CHE']

    if grd.empty:
        return pd.DataFrame()
    grd = grd.copy()
    grd['welfare_model'] = grd['iso'].map(
        {**{c: 'Bismarck' for c in bismarck},
         **{c: 'Beveridge' for c in beveridge},
         **{c: 'Hybrid' for c in hybrid}})
    classified = grd.dropna(subset=['welfare_model'])
    if classified.empty:
        return pd.DataFrame()

    classified['decade'] = (classified['year'] // 10) * 10
    cols = ['social_contributions', 'pit', 'taxes_inc_sc', 'goods_services']
    available = [c for c in cols if c in classified.columns]
    results = classified.groupby(['welfare_model', 'decade'])[available].mean().reset_index()
    return results


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A22: PAYROLL TAX EXPLOSION")
    logger.info("=" * 80)

    grd, oecd = load_data()
    if grd.empty:
        return {}

    trajectory = analyze_ssc_trajectory(grd)
    if not trajectory.empty:
        write_single_sheet_excel(trajectory, OUTPUT_DIR / "A22_ssc_trajectory.xlsx", "Trajectory")
        logger.info(f"SSC trajectory: {len(trajectory)} rows")
        hi = trajectory[trajectory['income_group'] == 'High income']
        if not hi.empty:
            logger.info(f"High income SSC/GDP by decade:\n{hi[['decade','ssc_mean','ssc_share_of_total']].to_string(index=False)}")

    ssc_pit = analyze_ssc_vs_pit(grd)
    if not ssc_pit.empty:
        write_single_sheet_excel(ssc_pit, OUTPUT_DIR / "A22_ssc_vs_pit.xlsx", "SSC_PIT")
        n_ssc_rose = (ssc_pit['ssc_change'] > 0).sum()
        n_pit_fell = (ssc_pit['pit_change'] < 0).sum()
        logger.info(f"SSC rose in {n_ssc_rose}/{len(ssc_pit)} countries")
        logger.info(f"PIT fell in {n_pit_fell}/{len(ssc_pit)} countries")

    welfare = analyze_bismarck_vs_beveridge(grd)
    if not welfare.empty:
        write_single_sheet_excel(welfare, OUTPUT_DIR / "A22_bismarck_beveridge.xlsx", "WelfareModel")
        logger.info(f"Welfare model comparison: {len(welfare)} rows")

    logger.info("A22 COMPLETE")
    return {'countries': len(ssc_pit) if not ssc_pit.empty else 0}


if __name__ == "__main__":
    run()
