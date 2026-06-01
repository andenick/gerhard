"""
A24: Corporate Tax Race to the Bottom (Extended)
=================================================
Full analysis of statutory + effective corporate rate convergence and revenue consequences.
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
    tf_path = raw_data_dir() / "tax_foundation" / "final_index_data_2025.csv"
    if tf_path.exists():
        sources['tf'] = pd.read_csv(tf_path)
    oecd_path = raw_data_dir() / "oecd" / "revenue_stats" / "oecd_revenue_wide.parquet"
    if oecd_path.exists():
        sources['oecd'] = pd.read_parquet(oecd_path)
    bachas_path = raw_data_dir() / "bachas_etr" / "globalETR_bfjz.csv"
    if bachas_path.exists():
        sources['bachas'] = pd.read_csv(bachas_path)
    return sources


def analyze_cit_revenue_trajectory(grd: pd.DataFrame) -> pd.DataFrame:
    """Track CIT revenue/GDP over time by income group."""
    if grd.empty or 'cit' not in grd.columns:
        return pd.DataFrame()
    grd = grd.copy()
    grd['decade'] = (grd['year'] // 10) * 10
    results = grd.groupby(['income_group', 'decade']).agg(
        cit_mean=('cit', 'mean'), cit_median=('cit', 'median'),
        taxes_mean=('taxes_inc_sc', 'mean'), n=('iso', 'count')
    ).reset_index()
    results['cit_share'] = results['cit_mean'] / results['taxes_mean'] * 100
    return results


def analyze_cit_convergence(grd: pd.DataFrame) -> pd.DataFrame:
    """Sigma-convergence of CIT revenue across countries."""
    if grd.empty or 'cit' not in grd.columns:
        return pd.DataFrame()
    results = []
    for year in sorted(grd['year'].unique()):
        vals = grd[grd['year'] == year]['cit'].dropna()
        if len(vals) >= 20:
            results.append({
                'year': year, 'n': len(vals),
                'mean': vals.mean(), 'std': vals.std(),
                'cv': vals.std() / vals.mean() if vals.mean() > 0 else np.nan,
                'min': vals.min(), 'max': vals.max(),
            })
    return pd.DataFrame(results)


def test_laffer_with_grd(grd: pd.DataFrame) -> pd.DataFrame:
    """Country-level: did CIT revenue rise or fall over time?"""
    if grd.empty or 'cit' not in grd.columns:
        return pd.DataFrame()
    results = []
    for country, grp in grd.groupby('iso'):
        grp = grp.sort_values('year')
        cit = grp['cit'].dropna()
        if len(cit) < 10:
            continue
        trend = np.polyfit(range(len(cit)), cit.values, 1)[0]
        peak = cit.max()
        peak_year = grp.loc[cit.idxmax(), 'year']
        results.append({
            'iso': country, 'country': grp['country'].iloc[0],
            'income_group': grp['income_group'].iloc[0],
            'cit_trend_pp_per_year': trend,
            'cit_peak': peak, 'cit_peak_year': int(peak_year),
            'cit_latest': cit.iloc[-1],
            'cit_decline_from_peak': peak - cit.iloc[-1],
            'revenue_rising': trend > 0,
        })
    return pd.DataFrame(results)


def compare_developed_developing(bachas: pd.DataFrame) -> pd.DataFrame:
    """Bachas et al key finding: developed cut CIT, developing raised it."""
    if bachas.empty or 'ETR_K' not in bachas.columns:
        return pd.DataFrame()
    bachas = bachas.copy()
    bachas['decade'] = (bachas['year'] // 10) * 10
    # Use Tau_K (corporate tax rate component) if available
    k_col = 'Tau_K' if 'Tau_K' in bachas.columns else 'ETR_K'
    results = bachas.groupby(['wb_inc', 'decade']).agg(
        etr_k_mean=(k_col, 'mean'), n=('country', 'count')
    ).reset_index()
    return results


def statutory_rates_snapshot(tf: pd.DataFrame) -> pd.DataFrame:
    """Tax Foundation statutory rates for OECD."""
    if tf.empty or 'corporate_rate' not in tf.columns:
        return pd.DataFrame()
    return tf[['ISO_3', 'country', 'corporate_rate']].rename(
        columns={'ISO_3': 'iso'}).sort_values('corporate_rate', ascending=False)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A24: CORPORATE TAX RACE TO THE BOTTOM")
    logger.info("=" * 80)

    sources = load_data()

    # CIT trajectory
    if 'grd' in sources:
        traj = analyze_cit_revenue_trajectory(sources['grd'])
        if not traj.empty:
            write_single_sheet_excel(traj, OUTPUT_DIR / "A24_cit_trajectory.xlsx", "Trajectory")
            logger.info("CIT/GDP by income group and decade:")
            hi = traj[traj['income_group'] == 'High income']
            for _, r in hi.iterrows():
                logger.info(f"  {int(r['decade'])}s: CIT={r['cit_mean']:.2f}% GDP (share={r['cit_share']:.1f}%)")

        # Convergence
        conv = analyze_cit_convergence(sources['grd'])
        if not conv.empty:
            write_single_sheet_excel(conv, OUTPUT_DIR / "A24_cit_convergence.xlsx", "Convergence")
            early_cv = conv[conv['year'] <= 1995]['cv'].mean()
            late_cv = conv[conv['year'] >= 2015]['cv'].mean()
            logger.info(f"CIT CV: {early_cv:.3f} (pre-1995) → {late_cv:.3f} (post-2015)")

        # Laffer test
        laffer = test_laffer_with_grd(sources['grd'])
        if not laffer.empty:
            write_single_sheet_excel(laffer, OUTPUT_DIR / "A24_cit_laffer.xlsx", "Laffer")
            n_rising = laffer['revenue_rising'].sum()
            logger.info(f"CIT revenue trend: rising in {n_rising}/{len(laffer)} countries")
            avg_decline = laffer['cit_decline_from_peak'].mean()
            logger.info(f"Avg CIT decline from peak: {avg_decline:.2f} pp GDP")

    # Developed vs developing (Bachas)
    if 'bachas' in sources:
        dev_comp = compare_developed_developing(sources['bachas'])
        if not dev_comp.empty:
            write_single_sheet_excel(dev_comp, OUTPUT_DIR / "A24_developed_vs_developing.xlsx", "DevComp")
            logger.info("ETR_K by income group and decade (Bachas):")
            for _, r in dev_comp.iterrows():
                logger.info(f"  {r['wb_inc']} {int(r['decade'])}s: ETR_K={r['etr_k_mean']:.1%}")

    # Statutory rates
    if 'tf' in sources:
        rates = statutory_rates_snapshot(sources['tf'])
        if not rates.empty:
            write_single_sheet_excel(rates, OUTPUT_DIR / "A24_statutory_rates_2025.xlsx", "Statutory")
            logger.info(f"OECD statutory rates 2025: mean={rates['corporate_rate'].mean():.1f}%, "
                       f"min={rates['corporate_rate'].min():.1f}%, max={rates['corporate_rate'].max():.1f}%")

    logger.info("A24 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
