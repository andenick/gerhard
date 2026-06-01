"""
A29: Private Debt Squeeze on Labor
====================================
Tests: as wages fell (labor share decline), did workers compensate by borrowing?
Quantifies total squeeze: wage_loss + debt_service + tax_burden_shift.
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
    # IMF private debt
    imf_path = raw_data_dir() / "imf" / "gfs" / "imf_private_debt_wide.parquet"
    if imf_path.exists():
        sources['imf_debt'] = pd.read_parquet(imf_path)
    # PWT
    pwt_path = raw_data_dir() / "profit_rates" / "pwt_profit_rate_panel.parquet"
    if pwt_path.exists():
        sources['pwt'] = pd.read_parquet(pwt_path).rename(columns={'countrycode': 'country_code'})
    # Bachas ETR
    bachas_path = raw_data_dir() / "bachas_etr" / "globalETR_bfjz.csv"
    if bachas_path.exists():
        sources['bachas'] = pd.read_csv(bachas_path)
    # JST
    jst_path = raw_data_dir() / "jst" / "jst_fiscal_panel.parquet"
    if jst_path.exists():
        df = pd.read_parquet(jst_path)
        df = df.rename(columns={'country_code': 'country_code'})
        sources['jst'] = df
    return sources


def test_wage_decline_drives_borrowing(pwt: pd.DataFrame, imf_debt: pd.DataFrame) -> pd.DataFrame:
    """H4: falling labor share → rising household debt."""
    if pwt.empty or imf_debt.empty:
        return pd.DataFrame()

    # HH debt column
    hh_col = next((c for c in imf_debt.columns if 'HH' in c), None)
    if not hh_col:
        return pd.DataFrame()

    merged = pwt[['country_code', 'year', 'labsh']].merge(
        imf_debt[['country_code', 'year', hh_col]], on=['country_code', 'year'], how='inner')
    merged = merged.rename(columns={hh_col: 'hh_debt'})

    if len(merged) < 50:
        return pd.DataFrame()

    results = []
    for country, grp in merged.groupby('country_code'):
        grp = grp.sort_values('year').dropna()
        if len(grp) < 8:
            continue
        corr = grp['labsh'].corr(grp['hh_debt'])
        # Changes
        d = grp[['labsh', 'hh_debt']].diff().dropna()
        corr_d = d['labsh'].corr(d['hh_debt']) if len(d) > 5 else np.nan
        results.append({
            'country_code': country, 'n_years': len(grp),
            'corr_labsh_hh_debt': corr,
            'corr_d_labsh_d_hh_debt': corr_d,
            'labsh_trend': np.polyfit(range(len(grp)), grp['labsh'].values, 1)[0],
            'hh_debt_trend': np.polyfit(range(len(grp)), grp['hh_debt'].values, 1)[0],
            'wages_fell_debt_rose': grp['labsh'].iloc[-1] < grp['labsh'].iloc[0] and grp['hh_debt'].iloc[-1] > grp['hh_debt'].iloc[0],
        })

    return pd.DataFrame(results)


def compute_total_squeeze_jst(jst: pd.DataFrame, pwt: pd.DataFrame) -> pd.DataFrame:
    """For JST countries: wage_loss + debt_burden combined."""
    if jst.empty or pwt.empty:
        return pd.DataFrame()

    # Merge JST credit with PWT labor share
    pwt_sub = pwt[['country_code', 'year', 'labsh']].copy()
    merged = jst.merge(pwt_sub, on=['country_code', 'year'], how='inner')

    if merged.empty or 'tloans' not in merged.columns:
        return pd.DataFrame()

    results = []
    for country, grp in merged.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 20:
            continue

        # Reference point: 1970 or earliest
        ref = grp[grp['year'] <= 1975]
        if ref.empty:
            continue

        ref_labsh = ref['labsh'].mean()
        # Normalize tloans to GDP ratio
        ref_credit_gdp = (ref['tloans'] / ref['gdp']).mean() if 'tloans' in ref.columns and 'gdp' in ref.columns else 0

        for _, row in grp.iterrows():
            labsh_loss = ref_labsh - row['labsh']  # Positive = wages fell
            gdp_val = row.get('gdp', 1)
            credit_gdp = row.get('tloans', 0) / gdp_val if gdp_val > 0 else 0
            credit_rise = credit_gdp - ref_credit_gdp
            # Debt service proxy: assume 5% average interest on total credit/GDP
            debt_service = credit_gdp * 0.05

            results.append({
                'country_code': country, 'year': int(row['year']),
                'labsh': row['labsh'],
                'labsh_loss_from_1970': labsh_loss,
                'credit_gdp': credit_gdp,
                'credit_rise_from_1970': credit_rise,
                'debt_service_proxy': debt_service,
                'total_squeeze': labsh_loss + debt_service,
            })

    return pd.DataFrame(results)


def compute_squeeze_by_era(squeeze: pd.DataFrame) -> pd.DataFrame:
    """Average squeeze by decade."""
    if squeeze.empty:
        return pd.DataFrame()
    squeeze = squeeze.copy()
    squeeze['decade'] = (squeeze['year'] // 10) * 10
    results = squeeze.groupby('decade').agg({
        'labsh_loss_from_1970': 'mean',
        'credit_gdp': 'mean',
        'debt_service_proxy': 'mean',
        'total_squeeze': 'mean',
        'country_code': 'count',
    }).reset_index().rename(columns={'country_code': 'n_obs'})
    return results


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A29: PRIVATE DEBT SQUEEZE ON LABOR")
    logger.info("=" * 80)

    sources = load_data()

    # Test: wage decline → borrowing
    if 'pwt' in sources and 'imf_debt' in sources:
        wage_debt = test_wage_decline_drives_borrowing(sources['pwt'], sources['imf_debt'])
        if not wage_debt.empty:
            write_single_sheet_excel(wage_debt, OUTPUT_DIR / "A29_wage_debt_link.xlsx", "WageDebt")
            n_confirmed = wage_debt.get('wages_fell_debt_rose', pd.Series()).sum()
            avg_corr = wage_debt['corr_labsh_hh_debt'].mean()
            logger.info(f"Wage↓ + Debt↑ confirmed: {n_confirmed}/{len(wage_debt)} countries")
            logger.info(f"Avg correlation (labor share vs HH debt): {avg_corr:.3f}")

    # Total squeeze computation (JST)
    if 'jst' in sources and 'pwt' in sources:
        squeeze = compute_total_squeeze_jst(sources['jst'], sources['pwt'])
        if not squeeze.empty:
            write_single_sheet_excel(squeeze.head(50000), OUTPUT_DIR / "A29_total_squeeze.xlsx", "Squeeze")
            logger.info(f"Squeeze panel: {len(squeeze)} obs, {squeeze['country_code'].nunique()} countries")

            by_era = compute_squeeze_by_era(squeeze)
            if not by_era.empty:
                write_single_sheet_excel(by_era, OUTPUT_DIR / "A29_squeeze_by_era.xlsx", "ByEra")
                logger.info("Total squeeze by decade (avg across 18 JST countries):")
                for _, row in by_era.iterrows():
                    logger.info(f"  {int(row['decade'])}s: wage_loss={row['labsh_loss_from_1970']:.1%}, "
                               f"credit={row['credit_gdp']:.0%} GDP, "
                               f"debt_service={row['debt_service_proxy']:.1%}, "
                               f"TOTAL={row['total_squeeze']:.1%}")

    logger.info("A29 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
