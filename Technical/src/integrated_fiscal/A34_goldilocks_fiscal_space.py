"""
A34: The Goldilocks Constraint — Fiscal Space and Profit Rates
===============================================================
Tests Mian-Straub-Sufi: free lunch exists only when R < G - φ.
Our extension: φ depends on profit rate regime.
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
    jst_path = raw_data_dir() / "jst" / "JSTdatasetR6.parquet"
    if jst_path.exists():
        sources['jst'] = pd.read_parquet(jst_path)
    pwt_path = raw_data_dir() / "profit_rates" / "pwt_profit_rate_panel.parquet"
    if pwt_path.exists():
        sources['pwt'] = pd.read_parquet(pwt_path).rename(columns={'countrycode': 'iso'})
    return sources


def compute_r_g_phi(jst: pd.DataFrame) -> pd.DataFrame:
    """Compute r, g, and estimate φ (interest rate sensitivity to debt)."""
    if jst.empty:
        return pd.DataFrame()

    jst = jst.sort_values(['iso', 'year']).copy()

    # Real interest rate
    if 'cpi' in jst.columns:
        jst['inflation'] = jst.groupby('iso')['cpi'].pct_change() * 100
    if 'ltrate' in jst.columns:
        jst['real_rate'] = jst['ltrate'] - jst.get('inflation', 0)
    # Real growth
    if 'rgdpmad' in jst.columns:
        jst['real_growth'] = jst.groupby('iso')['rgdpmad'].pct_change() * 100

    jst['r_minus_g'] = jst.get('real_rate', 0) - jst.get('real_growth', 0)

    # Estimate φ: regression of Δr on debt level (by country, rolling)
    results = []
    for country, grp in jst.groupby('iso'):
        grp = grp.sort_values('year').dropna(subset=['debtgdp'])
        if 'real_rate' not in grp.columns or len(grp) < 20:
            continue

        grp = grp.copy()
        grp['d_rate'] = grp['real_rate'].diff()

        # Full-sample φ
        valid = grp[['d_rate', 'debtgdp']].dropna()
        if len(valid) < 15:
            continue

        try:
            slope, _, r, p, _ = stats.linregress(valid['debtgdp'], valid['d_rate'])
        except Exception:
            continue

        # φ by era
        for era_name, (start, end) in [('golden_age', (1950, 1973)), ('neoliberal', (1980, 2007)),
                                        ('post_gfc', (2008, 2020))]:
            era = grp[(grp['year'] >= start) & (grp['year'] <= end)]
            era_valid = era[['d_rate', 'debtgdp']].dropna()
            if len(era_valid) < 8:
                continue
            try:
                era_slope, _, era_r, era_p, _ = stats.linregress(era_valid['debtgdp'], era_valid['d_rate'])
            except Exception:
                era_slope, era_r, era_p = np.nan, np.nan, np.nan

            # Free lunch condition: R < G - φ
            era_r_mean = era.get('real_rate', pd.Series()).mean()
            era_g_mean = era.get('real_growth', pd.Series()).mean()
            free_lunch_threshold = era_g_mean - era_slope if pd.notna(era_slope) else np.nan

            results.append({
                'iso': country, 'era': era_name,
                'phi': era_slope, 'phi_p': era_p,
                'avg_real_rate': era_r_mean,
                'avg_real_growth': era_g_mean,
                'avg_r_minus_g': era_r_mean - era_g_mean if pd.notna(era_r_mean) else np.nan,
                'avg_debt_gdp': era['debtgdp'].mean(),
                'free_lunch_threshold': free_lunch_threshold,
                'free_lunch_exists': era_r_mean < free_lunch_threshold if pd.notna(free_lunch_threshold) else False,
            })

    return pd.DataFrame(results)


def phi_vs_profit_rate(phi_panel: pd.DataFrame, jst: pd.DataFrame, pwt: pd.DataFrame) -> pd.DataFrame:
    """H3: Is φ higher when profit rates are low?"""
    if phi_panel.empty or pwt.empty:
        return pd.DataFrame()

    # Get average profit rate by country-era
    pwt_era = pwt.copy()
    pwt_era['era'] = 'other'
    for era_name, (start, end) in [('golden_age', (1950, 1973)), ('neoliberal', (1980, 2007)),
                                    ('post_gfc', (2008, 2019))]:
        mask = (pwt_era['year'] >= start) & (pwt_era['year'] <= end)
        pwt_era.loc[mask, 'era'] = era_name

    irr_by_era = pwt_era[pwt_era['era'] != 'other'].groupby(['iso', 'era'])['irr'].mean().reset_index()

    merged = phi_panel.merge(irr_by_era, on=['iso', 'era'], how='inner')
    if merged.empty:
        return pd.DataFrame()

    # Test: does higher profit rate predict lower φ?
    valid = merged[['phi', 'irr']].dropna()
    if len(valid) > 10:
        slope, _, r, p, _ = stats.linregress(valid['irr'], valid['phi'])
        logger.info(f"φ vs profit rate: β={slope:.4f}, R²={r**2:.3f}, p={p:.4f}")
        logger.info(f"  {'Higher profits → LOWER φ (more fiscal space)' if slope < 0 else 'Higher profits → HIGHER φ (less space)'}")

    return merged


def summarize_fiscal_space_by_era(phi_panel: pd.DataFrame) -> pd.DataFrame:
    """How much fiscal space existed in each era?"""
    if phi_panel.empty:
        return pd.DataFrame()

    results = phi_panel.groupby('era').agg({
        'phi': 'mean', 'avg_real_rate': 'mean', 'avg_real_growth': 'mean',
        'avg_r_minus_g': 'mean', 'avg_debt_gdp': 'mean',
        'free_lunch_exists': 'mean', 'iso': 'count',
    }).reset_index().rename(columns={'iso': 'n_countries', 'free_lunch_exists': 'pct_free_lunch'})
    results['pct_free_lunch'] *= 100
    return results


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A34: GOLDILOCKS FISCAL SPACE")
    logger.info("=" * 80)

    sources = load_data()
    if 'jst' not in sources:
        return {}

    # Compute r, g, φ
    phi_panel = compute_r_g_phi(sources['jst'])
    if phi_panel.empty:
        logger.error("Could not compute φ")
        return {}

    write_single_sheet_excel(phi_panel, OUTPUT_DIR / "A34_phi_estimates.xlsx", "Phi")
    logger.info(f"φ estimates: {len(phi_panel)} country-eras")

    # Summarize by era
    era_summary = summarize_fiscal_space_by_era(phi_panel)
    if not era_summary.empty:
        write_single_sheet_excel(era_summary, OUTPUT_DIR / "A34_fiscal_space_by_era.xlsx", "FiscalSpace")
        logger.info("Fiscal space by era:")
        for _, row in era_summary.iterrows():
            logger.info(f"  {row['era']:15s}: φ={row['phi']:+.3f}, r-g={row['avg_r_minus_g']:+.1f}pp, "
                       f"debt={row['avg_debt_gdp']:.0%}, free_lunch={row['pct_free_lunch']:.0f}% of countries")

    # φ vs profit rate
    if 'pwt' in sources:
        cross = phi_vs_profit_rate(phi_panel, sources['jst'], sources['pwt'])
        if not cross.empty:
            write_single_sheet_excel(cross, OUTPUT_DIR / "A34_phi_vs_profit.xlsx", "PhiProfit")

    logger.info("A34 COMPLETE")
    return {'country_eras': len(phi_panel)}


if __name__ == "__main__":
    run()
