"""
A36: The Nordic Exception — Why Some Countries Resisted the Regressive Turn
============================================================================
Denmark, Sweden, Norway, Finland maintained high taxes + high growth.
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

NORDICS = ['DNK', 'SWE', 'NOR', 'FIN', 'ISL']
ANGLOS = ['USA', 'GBR', 'CAN', 'AUS', 'NZL', 'IRL']
CONTINENTAL = ['DEU', 'FRA', 'AUT', 'BEL', 'NLD']


def load_data():
    sources = {}
    grd_path = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    if grd_path.exists():
        sources['grd'] = pd.read_parquet(grd_path)
    pwt_path = raw_data_dir() / "profit_rates" / "pwt_profit_rate_panel.parquet"
    if pwt_path.exists():
        sources['pwt'] = pd.read_parquet(pwt_path).rename(columns={'countrycode': 'iso'})
    bachas_path = raw_data_dir() / "bachas_etr" / "globalETR_bfjz.csv"
    if bachas_path.exists():
        sources['bachas'] = pd.read_csv(bachas_path)
    return sources


def compare_models(grd: pd.DataFrame) -> pd.DataFrame:
    """Compare Nordic vs Anglo vs Continental tax structures over time."""
    if grd.empty:
        return pd.DataFrame()
    grd = grd.copy()
    grd['model'] = grd['iso'].map({
        **{c: 'Nordic' for c in NORDICS},
        **{c: 'Anglo' for c in ANGLOS},
        **{c: 'Continental' for c in CONTINENTAL}})
    classified = grd.dropna(subset=['model'])
    classified['decade'] = (classified['year'] // 10) * 10

    rev_cols = [c for c in grd.columns if any(kw in c for kw in
               ['pit', 'cit', 'social', 'goods_services', 'vat', 'taxes_inc', 'total_rev', 'property'])]
    available = [c for c in rev_cols if c in classified.columns]

    results = classified.groupby(['model', 'decade'])[available].mean().reset_index()
    return results


def compare_profit_rates(pwt: pd.DataFrame) -> pd.DataFrame:
    """H8: Are Nordic profit rates lower despite higher taxes?"""
    if pwt.empty:
        return pd.DataFrame()
    pwt = pwt.copy()
    pwt['model'] = pwt['iso'].map({
        **{c: 'Nordic' for c in NORDICS},
        **{c: 'Anglo' for c in ANGLOS},
        **{c: 'Continental' for c in CONTINENTAL}})
    classified = pwt.dropna(subset=['model'])
    classified['decade'] = (classified['year'] // 10) * 10

    results = classified.groupby(['model', 'decade']).agg(
        irr_mean=('irr', 'mean'), labsh_mean=('labsh', 'mean'), n=('iso', 'count')
    ).reset_index()
    return results


def compare_etr(bachas: pd.DataFrame) -> pd.DataFrame:
    """Nordic vs others on effective tax rates."""
    if bachas.empty:
        return pd.DataFrame()
    bachas = bachas.copy()
    bachas['model'] = bachas['country'].map({
        **{c: 'Nordic' for c in NORDICS},
        **{c: 'Anglo' for c in ANGLOS},
        **{c: 'Continental' for c in CONTINENTAL}})
    classified = bachas.dropna(subset=['model'])
    classified['decade'] = (classified['year'] // 10) * 10

    results = classified.groupby(['model', 'decade']).agg(
        ETR_L=('ETR_L', 'mean'), ETR_K=('ETR_K', 'mean'), n=('country', 'count')
    ).reset_index()
    results['etr_ratio_K_L'] = results['ETR_K'] / results['ETR_L']
    return results


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A36: THE NORDIC EXCEPTION")
    logger.info("=" * 80)

    sources = load_data()

    # Tax structure comparison
    if 'grd' in sources:
        models = compare_models(sources['grd'])
        if not models.empty:
            write_single_sheet_excel(models, OUTPUT_DIR / "A36_model_comparison.xlsx", "Models")
            logger.info("Tax structure by model (latest decade):")
            latest = models[models['decade'] == models['decade'].max()]
            for _, row in latest.iterrows():
                logger.info(f"  {row['model']:12s}: tax={row.get('taxes_inc_sc',0):.1f}% "
                           f"PIT={row.get('pit',0):.1f}% CIT={row.get('cit',0):.1f}% "
                           f"SSC={row.get('social_contributions',0):.1f}% "
                           f"G&S={row.get('goods_services',0):.1f}%")

    # Profit rate comparison
    if 'pwt' in sources:
        profits = compare_profit_rates(sources['pwt'])
        if not profits.empty:
            write_single_sheet_excel(profits, OUTPUT_DIR / "A36_profit_comparison.xlsx", "Profits")
            latest = profits[profits['decade'] == profits['decade'].max()]
            logger.info("\nProfit rates by model (latest decade):")
            for _, row in latest.iterrows():
                logger.info(f"  {row['model']:12s}: IRR={row['irr_mean']:.1%} "
                           f"labor_share={row['labsh_mean']:.1%}")

    # ETR comparison
    if 'bachas' in sources:
        etr = compare_etr(sources['bachas'])
        if not etr.empty:
            write_single_sheet_excel(etr, OUTPUT_DIR / "A36_etr_comparison.xlsx", "ETR")
            latest = etr[etr['decade'] == etr['decade'].max()]
            logger.info("\nEffective tax rates by model (latest decade):")
            for _, row in latest.iterrows():
                logger.info(f"  {row['model']:12s}: ETR_L={row['ETR_L']:.1%} "
                           f"ETR_K={row['ETR_K']:.1%} ratio K/L={row['etr_ratio_K_L']:.2f}")

    logger.info("A36 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
