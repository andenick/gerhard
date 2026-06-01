"""
A20: Effective Tax Rates on Labor vs Capital (Global, 1965-2018)
================================================================
Uses Bachas et al dataset (150 countries) + EU ITR (31 countries) to test
whether capital ETR fell while labor ETR rose.
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


def load_bachas() -> pd.DataFrame:
    fpath = raw_data_dir() / "bachas_etr" / "globalETR_bfjz.csv"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_csv(fpath)
    logger.info(f"Bachas ETR: {len(df)} rows, {df.columns.tolist()[:10]}")
    return df


def load_eu_itr() -> pd.DataFrame:
    fpath = raw_data_dir() / "eurostat" / "itr" / "eu_itr.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_parquet(fpath)
    return df


def analyze_global_etr_trends(bachas: pd.DataFrame) -> pd.DataFrame:
    """Track ETR_L and ETR_K over time globally."""
    if bachas.empty or 'ETR_L' not in bachas.columns:
        return pd.DataFrame()

    results = []
    for year in sorted(bachas['year'].unique()):
        yr = bachas[bachas['year'] == year]
        row = {'year': year, 'n_countries': len(yr)}

        for col in ['ETR_L', 'ETR_K', 'Lsh_ndp']:
            valid = yr[col].dropna()
            if len(valid) > 10:
                row[f'{col}_mean'] = valid.mean()
                row[f'{col}_median'] = valid.median()
                row[f'{col}_std'] = valid.std()

        # ETR ratio (capital/labor)
        both = yr[['ETR_L', 'ETR_K']].dropna()
        if len(both) > 10:
            row['etr_ratio_K_L'] = (both['ETR_K'] / both['ETR_L']).median()

        results.append(row)

    return pd.DataFrame(results)


def analyze_etr_by_income(bachas: pd.DataFrame) -> pd.DataFrame:
    """ETR patterns by World Bank income group."""
    if bachas.empty or 'wb_inc' not in bachas.columns:
        return pd.DataFrame()

    bachas = bachas.copy()
    bachas['decade'] = (bachas['year'] // 10) * 10

    results = bachas.groupby(['wb_inc', 'decade']).agg({
        'ETR_L': 'mean', 'ETR_K': 'mean', 'Lsh_ndp': 'mean',
        'country': 'count'
    }).reset_index().rename(columns={'country': 'n_obs'})

    return results


def analyze_etr_country_trends(bachas: pd.DataFrame) -> pd.DataFrame:
    """For each country: did ETR_K fall and ETR_L rise?"""
    if bachas.empty:
        return pd.DataFrame()

    results = []
    country_col = 'country' if 'country' in bachas.columns else 'country_name'

    for country, grp in bachas.groupby(country_col):
        grp = grp.sort_values('year')
        if len(grp) < 15:
            continue

        row = {'country': country, 'n_years': len(grp)}

        for col in ['ETR_L', 'ETR_K', 'Lsh_ndp']:
            if col not in grp.columns:
                continue
            valid = grp[['year', col]].dropna()
            if len(valid) < 10:
                continue
            slope = np.polyfit(valid['year'], valid[col], 1)[0]
            row[f'{col}_trend'] = slope
            row[f'{col}_mean'] = valid[col].mean()
            row[f'{col}_early'] = valid[valid['year'] <= valid['year'].median()][col].mean()
            row[f'{col}_late'] = valid[valid['year'] > valid['year'].median()][col].mean()

        # Key test: ETR_K falling while ETR_L rising?
        if 'ETR_K_trend' in row and 'ETR_L_trend' in row:
            row['burden_shift'] = row['ETR_K_trend'] < 0 and row['ETR_L_trend'] > 0
            row['both_falling'] = row['ETR_K_trend'] < 0 and row['ETR_L_trend'] < 0

        results.append(row)

    return pd.DataFrame(results)


def cross_with_labor_share(bachas: pd.DataFrame) -> pd.DataFrame:
    """Test: does falling labor share correlate with ETR changes?"""
    if bachas.empty:
        return pd.DataFrame()

    results = []
    country_col = 'country' if 'country' in bachas.columns else 'country_name'

    for country, grp in bachas.groupby(country_col):
        grp = grp.sort_values('year')
        valid = grp[['ETR_L', 'ETR_K', 'Lsh_ndp']].dropna()
        if len(valid) < 15:
            continue

        row = {'country': country, 'n_years': len(valid)}
        row['corr_labsh_etr_l'] = valid['Lsh_ndp'].corr(valid['ETR_L'])
        row['corr_labsh_etr_k'] = valid['Lsh_ndp'].corr(valid['ETR_K'])

        # Changes correlation
        changes = valid.diff().dropna()
        if len(changes) > 10:
            row['corr_d_labsh_d_etr_l'] = changes['Lsh_ndp'].corr(changes['ETR_L'])
            row['corr_d_labsh_d_etr_k'] = changes['Lsh_ndp'].corr(changes['ETR_K'])

        results.append(row)

    return pd.DataFrame(results)


def validate_against_eu_itr(bachas: pd.DataFrame, eu_itr: pd.DataFrame) -> pd.DataFrame:
    """Cross-validate Bachas ETR against EU ITR for European countries."""
    if bachas.empty or eu_itr.empty:
        return pd.DataFrame()

    # EU ITR has ITR column with labels like "Implicit Tax rate on Labour"
    # Need to identify the ITR type column
    itr_col = None
    for col in eu_itr.columns:
        if 'ITR' in col or 'itr' in col.lower():
            if eu_itr[col].dtype == object:
                itr_col = col
                break

    if itr_col:
        # Filter to labor and capital
        labor_itr = eu_itr[eu_itr[itr_col].str.contains('L|Labour|Labor', case=False, na=False)]
        capital_itr = eu_itr[eu_itr[itr_col].str.contains('K|Capital', case=False, na=False)]
        logger.info(f"EU ITR: {len(labor_itr)} labor obs, {len(capital_itr)} capital obs")

    return pd.DataFrame()  # Placeholder for cross-validation


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A20: EFFECTIVE TAX RATES — LABOR VS CAPITAL (GLOBAL)")
    logger.info("=" * 80)

    bachas = load_bachas()
    eu_itr = load_eu_itr()

    if bachas.empty:
        logger.error("No Bachas ETR data")
        return {}

    # Global trends
    trends = analyze_global_etr_trends(bachas)
    if not trends.empty:
        write_single_sheet_excel(trends, OUTPUT_DIR / "A20_global_etr_trends.xlsx", "Trends")
        if 'ETR_K_mean' in trends.columns:
            early = trends[trends['year'] <= 1985]['ETR_K_mean'].mean()
            late = trends[trends['year'] >= 2005]['ETR_K_mean'].mean()
            logger.info(f"Global ETR_K: {early:.1%} (pre-1985) → {late:.1%} (post-2005)")
        if 'ETR_L_mean' in trends.columns:
            early = trends[trends['year'] <= 1985]['ETR_L_mean'].mean()
            late = trends[trends['year'] >= 2005]['ETR_L_mean'].mean()
            logger.info(f"Global ETR_L: {early:.1%} (pre-1985) → {late:.1%} (post-2005)")

    # By income group
    by_income = analyze_etr_by_income(bachas)
    if not by_income.empty:
        write_single_sheet_excel(by_income, OUTPUT_DIR / "A20_etr_by_income.xlsx", "ByIncome")
        logger.info(f"ETR by income group: {len(by_income)} rows")

    # Country trends
    country_trends = analyze_etr_country_trends(bachas)
    if not country_trends.empty:
        write_single_sheet_excel(country_trends, OUTPUT_DIR / "A20_etr_country_trends.xlsx", "Countries")
        if 'burden_shift' in country_trends.columns:
            n_shift = country_trends['burden_shift'].sum()
            logger.info(f"Burden shift (ETR_K↓ + ETR_L↑): {n_shift}/{len(country_trends)} countries")

    # Cross with labor share
    labor_cross = cross_with_labor_share(bachas)
    if not labor_cross.empty:
        write_single_sheet_excel(labor_cross, OUTPUT_DIR / "A20_etr_vs_labor_share.xlsx", "LaborCross")
        if 'corr_labsh_etr_k' in labor_cross.columns:
            avg_corr = labor_cross['corr_labsh_etr_k'].mean()
            logger.info(f"Avg correlation (labor share vs ETR_K): {avg_corr:.3f}")

    logger.info("A20 COMPLETE")
    return {'countries': len(country_trends) if not country_trends.empty else 0}


if __name__ == "__main__":
    run()
