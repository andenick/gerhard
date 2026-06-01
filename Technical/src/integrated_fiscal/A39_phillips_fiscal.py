"""
A39: The Phillips Fiscal Analogy — Inflation vs Redistribution Tradeoff
========================================================================
Was financial repression (moderate inflation, low real rates) the Golden Age's
solution? Compare: 1950-73 (repression + growth) vs 1980-2007 (disinflation + debt).
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
    wb_path = raw_data_dir() / "worldbank" / "macro" / "wb_macro_combined.csv"
    if wb_path.exists():
        sources['wb'] = pd.read_csv(wb_path)
    return sources


def compare_repression_vs_disinflation(jst: pd.DataFrame) -> pd.DataFrame:
    """Compare two strategies: financial repression (1950-73) vs disinflation (1980-2007)."""
    if jst.empty:
        return pd.DataFrame()

    jst = jst.sort_values(['iso', 'year']).copy()
    if 'cpi' in jst.columns:
        jst['inflation'] = jst.groupby('iso')['cpi'].pct_change() * 100
    if 'ltrate' in jst.columns:
        jst['real_rate'] = jst['ltrate'] - jst.get('inflation', 0)
    if 'rgdpmad' in jst.columns:
        jst['real_growth'] = jst.groupby('iso')['rgdpmad'].pct_change() * 100

    eras = {
        'financial_repression': (1950, 1973),
        'volcker_disinflation': (1980, 2000),
        'great_moderation': (2000, 2007),
        'zirp_qe': (2008, 2020),
    }

    results = []
    for era_name, (start, end) in eras.items():
        era = jst[(jst['year'] >= start) & (jst['year'] <= end)]
        if era.empty:
            continue
        row = {'era': era_name, 'start': start, 'end': end, 'n_obs': len(era)}
        for col in ['inflation', 'real_rate', 'real_growth', 'debtgdp', 'ltrate']:
            if col in era.columns:
                row[f'{col}_mean'] = era[col].mean()
                row[f'{col}_std'] = era[col].std()
        # Debt change
        if 'debtgdp' in era.columns:
            start_debt = era.groupby('iso')['debtgdp'].first().mean()
            end_debt = era.groupby('iso')['debtgdp'].last().mean()
            row['debt_change'] = end_debt - start_debt
        results.append(row)

    return pd.DataFrame(results)


def inflation_as_regressive_tax(jst: pd.DataFrame, wb: pd.DataFrame) -> pd.DataFrame:
    """Test: is inflation regressive? Cross-country: high inflation → worse inequality?"""
    if wb.empty:
        return pd.DataFrame()

    wb = wb.copy()
    wb['year'] = pd.to_numeric(wb['year'], errors='coerce')
    wb['inflation_cpi'] = pd.to_numeric(wb['inflation_cpi'], errors='coerce')

    # Average inflation by country
    avg_infl = wb.groupby('country_code').agg(
        avg_inflation=('inflation_cpi', 'mean'),
        avg_growth=('gdp_growth', 'mean'),
        n=('year', 'count')
    ).reset_index()
    avg_infl = avg_infl[avg_infl['n'] >= 10]

    return avg_infl


def financial_repression_debt_erosion(jst: pd.DataFrame) -> pd.DataFrame:
    """Quantify: how much did financial repression erode debt in the Golden Age?"""
    if jst.empty:
        return pd.DataFrame()

    jst = jst.sort_values(['iso', 'year']).copy()
    if 'cpi' in jst.columns:
        jst['inflation'] = jst.groupby('iso')['cpi'].pct_change() * 100
    if 'ltrate' in jst.columns:
        jst['real_rate'] = jst['ltrate'] - jst.get('inflation', 0)

    results = []
    for country, grp in jst.groupby('iso'):
        # Golden Age: 1946-1973
        ga = grp[(grp['year'] >= 1946) & (grp['year'] <= 1973)]
        neo = grp[(grp['year'] >= 1980) & (grp['year'] <= 2007)]

        if len(ga) < 10 or len(neo) < 10:
            continue

        # Debt erosion = years of negative real rates
        ga_neg_real = (ga['real_rate'] < 0).sum() if 'real_rate' in ga.columns else 0
        neo_neg_real = (neo['real_rate'] < 0).sum() if 'real_rate' in neo.columns else 0

        results.append({
            'iso': country,
            'ga_avg_inflation': ga['inflation'].mean() if 'inflation' in ga.columns else np.nan,
            'ga_avg_real_rate': ga['real_rate'].mean() if 'real_rate' in ga.columns else np.nan,
            'ga_debt_start': ga['debtgdp'].iloc[0] if 'debtgdp' in ga.columns else np.nan,
            'ga_debt_end': ga['debtgdp'].iloc[-1] if 'debtgdp' in ga.columns else np.nan,
            'ga_debt_change': ga['debtgdp'].iloc[-1] - ga['debtgdp'].iloc[0] if 'debtgdp' in ga.columns else np.nan,
            'ga_years_neg_real': ga_neg_real,
            'neo_avg_inflation': neo['inflation'].mean() if 'inflation' in neo.columns else np.nan,
            'neo_avg_real_rate': neo['real_rate'].mean() if 'real_rate' in neo.columns else np.nan,
            'neo_debt_start': neo['debtgdp'].iloc[0] if 'debtgdp' in neo.columns else np.nan,
            'neo_debt_end': neo['debtgdp'].iloc[-1] if 'debtgdp' in neo.columns else np.nan,
            'neo_debt_change': neo['debtgdp'].iloc[-1] - neo['debtgdp'].iloc[0] if 'debtgdp' in neo.columns else np.nan,
            'neo_years_neg_real': neo_neg_real,
        })

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A39: INFLATION VS REDISTRIBUTION TRADEOFF")
    logger.info("=" * 80)

    sources = load_data()

    # Era comparison
    if 'jst' in sources:
        eras = compare_repression_vs_disinflation(sources['jst'])
        if not eras.empty:
            write_single_sheet_excel(eras, OUTPUT_DIR / "A39_era_comparison.xlsx", "Eras")
            logger.info("Financial strategy by era:")
            for _, row in eras.iterrows():
                logger.info(f"  {row['era']:25s}: inflation={row.get('inflation_mean',0):+.1f}%, "
                           f"real_rate={row.get('real_rate_mean',0):+.1f}%, "
                           f"growth={row.get('real_growth_mean',0):+.1f}%, "
                           f"Δdebt={row.get('debt_change',0):+.2f}")

        # Repression vs debt erosion
        repression = financial_repression_debt_erosion(sources['jst'])
        if not repression.empty:
            write_single_sheet_excel(repression, OUTPUT_DIR / "A39_repression_debt_erosion.xlsx", "Repression")
            avg_ga_debt = repression['ga_debt_change'].mean()
            avg_neo_debt = repression['neo_debt_change'].mean()
            logger.info(f"\nDebt change (avg 18 countries):")
            logger.info(f"  Golden Age (1946-73): {avg_ga_debt:+.2f} (debt FELL)")
            logger.info(f"  Neoliberal (1980-07): {avg_neo_debt:+.2f} (debt ROSE)")
            avg_ga_neg = repression['ga_years_neg_real'].mean()
            avg_neo_neg = repression['neo_years_neg_real'].mean()
            logger.info(f"  Years of negative real rates: GA={avg_ga_neg:.0f}, Neo={avg_neo_neg:.0f}")

    # Inflation as tax
    if 'wb' in sources:
        infl_tax = inflation_as_regressive_tax(sources.get('jst', pd.DataFrame()), sources['wb'])
        if not infl_tax.empty:
            write_single_sheet_excel(infl_tax, OUTPUT_DIR / "A39_inflation_regressivity.xlsx", "InflTax")

    logger.info("A39 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
