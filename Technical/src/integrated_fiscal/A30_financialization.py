"""
A30: Financialization as Profit Extraction
============================================
Tracks 150-year credit/GDP trajectory (JST) and correlates with profit rate decline.
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
    sources = {}
    jst_path = raw_data_dir() / "jst" / "JSTdatasetR6.parquet"
    if jst_path.exists():
        sources['jst'] = pd.read_parquet(jst_path)
    pwt_path = raw_data_dir() / "profit_rates" / "pwt_profit_rate_panel.parquet"
    if pwt_path.exists():
        sources['pwt'] = pd.read_parquet(pwt_path).rename(columns={'countrycode': 'iso'})
    return sources


def track_financialization_150yr(jst: pd.DataFrame) -> pd.DataFrame:
    """Credit/GDP from 1870 to 2020 — the financialization trajectory."""
    if jst.empty or 'tloans' not in jst.columns:
        return pd.DataFrame()

    results = []
    for year in sorted(jst['year'].unique()):
        yr = jst[jst['year'] == year]
        row = {'year': year, 'n_countries': yr['iso'].nunique() if 'iso' in yr.columns else len(yr)}
        for col in ['tloans', 'tmort', 'thh', 'tbus']:
            if col in yr.columns and 'gdp' in yr.columns:
                # Normalize to GDP ratio
                ratio = (yr[col] / yr['gdp']).replace([np.inf, -np.inf], np.nan).dropna()
                if len(ratio) >= 5:
                    row[f'{col}_mean'] = ratio.mean()
                    row[f'{col}_median'] = ratio.median()
        for col in ['money', 'narrowm']:
            if col in yr.columns and 'gdp' in yr.columns:
                ratio = (yr[col] / yr['gdp']).replace([np.inf, -np.inf], np.nan).dropna()
                if len(ratio) >= 5:
                    row[f'{col}_mean'] = ratio.mean()
        results.append(row)

    return pd.DataFrame(results)


def credit_vs_profit_rate(jst: pd.DataFrame, pwt: pd.DataFrame) -> pd.DataFrame:
    """Test: did credit grow as profit rates fell?"""
    if jst.empty or pwt.empty:
        return pd.DataFrame()

    # Merge on iso + year
    iso_col = 'iso' if 'iso' in jst.columns else 'country_code'
    jst_sub = jst[[iso_col, 'year', 'tloans', 'gdp']].copy()
    jst_sub['credit_gdp'] = jst_sub['tloans'] / jst_sub['gdp']
    jst_sub = jst_sub.replace([np.inf, -np.inf], np.nan)
    merged = jst_sub[[iso_col, 'year', 'credit_gdp']].merge(
        pwt[['iso', 'year', 'irr']], left_on=[iso_col, 'year'], right_on=['iso', 'year'], how='inner')

    if len(merged) < 50:
        return pd.DataFrame()

    results = []
    for country, grp in merged.groupby(iso_col):
        grp = grp.sort_values('year').dropna(subset=['credit_gdp', 'irr'])
        if len(grp) < 15:
            continue
        corr = grp['credit_gdp'].corr(grp['irr'])
        credit_trend = np.polyfit(range(len(grp)), grp['credit_gdp'].values, 1)[0]
        irr_trend = np.polyfit(range(len(grp)), grp['irr'].values, 1)[0]
        results.append({
            'iso': country, 'n_years': len(grp),
            'corr_credit_irr': corr,
            'credit_trend': credit_trend,
            'irr_trend': irr_trend,
            'financialization_while_profit_decline': credit_trend > 0 and irr_trend < 0,
        })

    return pd.DataFrame(results)


def decompose_credit_growth(jst: pd.DataFrame) -> pd.DataFrame:
    """Decompose: household vs business credit growth."""
    if jst.empty:
        return pd.DataFrame()

    jst = jst.copy()
    jst['decade'] = (jst['year'] // 10) * 10
    # Normalize all credit to GDP ratio
    for col in ['tloans', 'tmort', 'thh', 'tbus']:
        if col in jst.columns and 'gdp' in jst.columns:
            jst[f'{col}_gdp'] = jst[col] / jst['gdp']

    gdp_cols = [c for c in jst.columns if c.endswith('_gdp') and c != 'debtgdp']
    if not gdp_cols:
        return pd.DataFrame()

    results = jst.groupby('decade')[gdp_cols].mean().reset_index()
    results = results.replace([np.inf, -np.inf], np.nan)
    # Compute household share
    if 'thh_gdp' in results.columns and 'tloans_gdp' in results.columns:
        results['hh_share_pct'] = results['thh_gdp'] / results['tloans_gdp'] * 100
    if 'tbus_gdp' in results.columns and 'tloans_gdp' in results.columns:
        results['bus_share_pct'] = results['tbus_gdp'] / results['tloans_gdp'] * 100

    return results


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A30: FINANCIALIZATION AS PROFIT EXTRACTION")
    logger.info("=" * 80)

    sources = load_data()
    if 'jst' not in sources:
        logger.error("No JST data")
        return {}

    jst = sources['jst']

    # 150-year trajectory
    trajectory = track_financialization_150yr(jst)
    if not trajectory.empty:
        write_single_sheet_excel(trajectory, OUTPUT_DIR / "A30_financialization_150yr.xlsx", "Trajectory")
        early = trajectory[trajectory['year'] <= 1913]['tloans_mean'].mean()
        mid = trajectory[(trajectory['year'] >= 1950) & (trajectory['year'] <= 1979)]['tloans_mean'].mean()
        late = trajectory[trajectory['year'] >= 2000]['tloans_mean'].mean()
        logger.info(f"Credit/GDP: pre-WWI={early:.0%}, 1950-79={mid:.0%}, post-2000={late:.0%}")

    # Credit vs profit rate
    if 'pwt' in sources:
        cross = credit_vs_profit_rate(jst, sources['pwt'])
        if not cross.empty:
            write_single_sheet_excel(cross, OUTPUT_DIR / "A30_credit_vs_profit.xlsx", "CreditProfit")
            n_fin = cross['financialization_while_profit_decline'].sum()
            logger.info(f"Financialization while profit declining: {n_fin}/{len(cross)} countries")

    # Credit decomposition
    decomp = decompose_credit_growth(jst)
    if not decomp.empty:
        write_single_sheet_excel(decomp, OUTPUT_DIR / "A30_credit_decomposition.xlsx", "Decomposition")
        logger.info("Credit decomposition by decade:")
        for _, row in decomp.iterrows():
            hh = row.get('hh_share', np.nan)
            logger.info(f"  {int(row['decade'])}s: total={row.get('tloans',0):.0%} GDP, "
                       f"HH share={hh:.0f}%" if pd.notna(hh) else f"  {int(row['decade'])}s: total={row.get('tloans',0):.0%} GDP")

    logger.info("A30 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
