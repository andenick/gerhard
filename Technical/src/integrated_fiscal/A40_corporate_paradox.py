"""
A40: The Corporate Paradox — Rate Cuts, Base Broadening, Revenue
=================================================================
Resolves why CIT revenue ROSE in 120/164 countries despite rate cuts.
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


def load_data():
    sources = {}
    grd_path = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    if grd_path.exists():
        sources['grd'] = pd.read_parquet(grd_path)
    bachas_path = raw_data_dir() / "bachas_etr" / "globalETR_bfjz.csv"
    if bachas_path.exists():
        sources['bachas'] = pd.read_csv(bachas_path)
    return sources


def decompose_revenue_change(grd: pd.DataFrame) -> pd.DataFrame:
    """Revenue = Rate × Base. Decompose what drove changes."""
    if grd.empty or 'cit' not in grd.columns:
        return pd.DataFrame()

    results = []
    for country, grp in grd.groupby('iso'):
        grp = grp.sort_values('year')
        cit = grp['cit'].dropna()
        if len(cit) < 10:
            continue

        # Split into pre-2000 and post-2000
        pre = grp[grp['year'] <= 2000]['cit'].dropna()
        post = grp[grp['year'] > 2000]['cit'].dropna()
        full_trend = np.polyfit(range(len(cit)), cit.values, 1)[0] if len(cit) >= 5 else np.nan

        row = {
            'iso': country, 'country': grp['country'].iloc[0],
            'income_group': grp['income_group'].iloc[0],
            'cit_1990s': pre.mean() if len(pre) > 0 else np.nan,
            'cit_2010s': post[post.index.isin(grp[grp['year'] >= 2010].index)].mean() if len(post) > 0 else np.nan,
            'cit_full_trend': full_trend,
            'revenue_rose': full_trend > 0 if pd.notna(full_trend) else False,
        }
        results.append(row)

    df = pd.DataFrame(results)
    if not df.empty:
        df['cit_change'] = df['cit_2010s'] - df['cit_1990s']
    return df


def developed_vs_developing_paradox(bachas: pd.DataFrame) -> pd.DataFrame:
    """Bachas key finding: developed cut ETR_K, developing raised it."""
    if bachas.empty:
        return pd.DataFrame()

    # Split by income
    bachas = bachas.copy()
    bachas['period'] = np.where(bachas['year'] <= 1990, 'early', 'late')

    results = []
    for (inc, period), grp in bachas.groupby(['wb_inc', 'period']):
        results.append({
            'income_group': inc, 'period': period,
            'ETR_K_mean': grp['ETR_K'].mean(),
            'ETR_L_mean': grp['ETR_L'].mean(),
            'n': len(grp),
        })

    df = pd.DataFrame(results)
    # Pivot
    if not df.empty:
        pivot = df.pivot_table(index='income_group', columns='period',
                              values=['ETR_K_mean', 'ETR_L_mean'], aggfunc='first')
        pivot.columns = ['_'.join(c) for c in pivot.columns]
        pivot = pivot.reset_index()
        if 'ETR_K_mean_early' in pivot.columns and 'ETR_K_mean_late' in pivot.columns:
            pivot['ETR_K_change'] = pivot['ETR_K_mean_late'] - pivot['ETR_K_mean_early']
        if 'ETR_L_mean_early' in pivot.columns and 'ETR_L_mean_late' in pivot.columns:
            pivot['ETR_L_change'] = pivot['ETR_L_mean_late'] - pivot['ETR_L_mean_early']
        return pivot

    return df


def formalization_effect(grd: pd.DataFrame) -> pd.DataFrame:
    """Test: in developing countries, did CIT rise because more firms became formal?"""
    if grd.empty:
        return pd.DataFrame()

    developing = grd[grd['income_group'].isin(['Low income', 'Lower middle income', 'Upper middle income'])]
    if developing.empty:
        return pd.DataFrame()

    results = []
    for country, grp in developing.groupby('iso'):
        grp = grp.sort_values('year')
        cit = grp['cit'].dropna()
        total = grp['taxes_inc_sc'].dropna()
        if len(cit) < 10 or len(total) < 10:
            continue

        cit_trend = np.polyfit(range(len(cit)), cit.values, 1)[0]
        total_trend = np.polyfit(range(len(total)), total.values, 1)[0]

        results.append({
            'iso': country, 'country': grp['country'].iloc[0],
            'income_group': grp['income_group'].iloc[0],
            'cit_trend': cit_trend, 'total_tax_trend': total_trend,
            'cit_rose': cit_trend > 0, 'total_rose': total_trend > 0,
            'cit_grew_faster': cit_trend > total_trend,
        })

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A40: THE CORPORATE PARADOX")
    logger.info("=" * 80)

    sources = load_data()

    # Revenue decomposition
    if 'grd' in sources:
        decomp = decompose_revenue_change(sources['grd'])
        if not decomp.empty:
            write_single_sheet_excel(decomp, OUTPUT_DIR / "A40_revenue_decomposition.xlsx", "Decomp")
            n_rose = decomp['revenue_rose'].sum()
            logger.info(f"CIT revenue rising: {n_rose}/{len(decomp)} countries")
            by_inc = decomp.groupby('income_group')['revenue_rose'].mean() * 100
            logger.info(f"% with rising CIT by income group:\n{by_inc.to_string()}")

        # Formalization effect
        formal = formalization_effect(sources['grd'])
        if not formal.empty:
            write_single_sheet_excel(formal, OUTPUT_DIR / "A40_formalization.xlsx", "Formalization")
            n_cit_faster = formal['cit_grew_faster'].sum()
            logger.info(f"CIT growing faster than total tax: {n_cit_faster}/{len(formal)} developing countries")

    # Developed vs developing
    if 'bachas' in sources:
        paradox = developed_vs_developing_paradox(sources['bachas'])
        if not paradox.empty:
            write_single_sheet_excel(paradox, OUTPUT_DIR / "A40_dev_vs_developing.xlsx", "Paradox")
            logger.info(f"ETR_K change by income group:")
            for _, row in paradox.iterrows():
                logger.info(f"  {row['income_group']}: ETR_K {row.get('ETR_K_change',0):+.3f}, "
                           f"ETR_L {row.get('ETR_L_change',0):+.3f}")

    logger.info("A40 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
