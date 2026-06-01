"""
A33: Redistribution Effectiveness — Taxes vs Transfers
========================================================
Tests Fisher-Gethin finding: 90% of redistribution from transfers, 10% from taxes.
Implications: if austerity cuts transfers, redistribution collapses.
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
    wb_path = raw_data_dir() / "worldbank" / "expenditure" / "wb_social_expenditure.csv"
    if wb_path.exists():
        df = pd.read_csv(wb_path)
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        sources['wb_social'] = df
    return sources


def analyze_tax_vs_transfer_by_income(grd: pd.DataFrame) -> pd.DataFrame:
    """Compare tax effort vs social spending across income groups."""
    if grd.empty:
        return pd.DataFrame()

    grd = grd.copy()
    grd['decade'] = (grd['year'] // 10) * 10

    # Tax progressivity proxy: PIT/total (higher = more progressive tax)
    if 'pit' in grd.columns and 'taxes_inc_sc' in grd.columns:
        grd['pit_share'] = grd['pit'] / grd['taxes_inc_sc'] * 100

    # Transfer proxy: social contributions (limited but available)
    cols = ['taxes_inc_sc', 'pit', 'cit', 'social_contributions', 'goods_services']
    available = [c for c in cols + ['pit_share'] if c in grd.columns]

    results = grd.groupby(['income_group', 'decade'])[available].mean().reset_index()
    return results


def test_austerity_redistribution_link(grd: pd.DataFrame) -> pd.DataFrame:
    """H2: Countries that cut spending saw inequality rise more."""
    if grd.empty:
        return pd.DataFrame()

    results = []
    for country, grp in grd.groupby('iso'):
        grp = grp.sort_values('year')
        if len(grp) < 15:
            continue

        # Revenue trajectory
        mid = grp['year'].median()
        early = grp[grp['year'] <= mid]
        late = grp[grp['year'] > mid]

        row = {
            'iso': country, 'country': grp['country'].iloc[0],
            'income_group': grp['income_group'].iloc[0],
        }

        for col in ['taxes_inc_sc', 'social_contributions', 'pit', 'goods_services']:
            if col in grp.columns:
                row[f'{col}_early'] = early[col].mean()
                row[f'{col}_late'] = late[col].mean()
                row[f'{col}_change'] = late[col].mean() - early[col].mean()

        # Did the system become more regressive?
        if 'pit_change' in row and 'goods_services_change' in row:
            pit_c = row.get('pit_change', 0)
            gs_c = row.get('goods_services_change', 0)
            row['became_more_regressive'] = (pit_c or 0) < 0 and (gs_c or 0) > 0

        results.append(row)

    return pd.DataFrame(results)


def cross_tax_progressivity_with_social_spending(grd: pd.DataFrame, wb_social: pd.DataFrame) -> pd.DataFrame:
    """Cross: progressive taxes + generous transfers = most redistribution."""
    if grd.empty or wb_social.empty:
        return pd.DataFrame()

    # Get latest social spending
    social = wb_social[wb_social['country_code'].str.len() <= 3]
    social_latest = social.groupby('country_code')['value'].mean().reset_index()
    social_latest = social_latest.rename(columns={'country_code': 'iso', 'value': 'social_spending_gdp'})

    # Get latest tax progressivity proxy from GRD
    grd_latest = grd[grd['year'] >= grd['year'].max() - 3]
    tax_avg = grd_latest.groupby('iso').agg({
        'taxes_inc_sc': 'mean', 'pit': 'mean', 'goods_services': 'mean'
    }).reset_index()

    if 'pit' in tax_avg.columns and 'taxes_inc_sc' in tax_avg.columns:
        tax_avg['progressivity_proxy'] = tax_avg['pit'] / tax_avg['taxes_inc_sc'] * 100

    merged = tax_avg.merge(social_latest, on='iso', how='inner')
    if merged.empty:
        return pd.DataFrame()

    # Correlation: progressive taxes AND generous spending
    if 'progressivity_proxy' in merged.columns and 'social_spending_gdp' in merged.columns:
        valid = merged[['progressivity_proxy', 'social_spending_gdp']].dropna()
        if len(valid) > 10:
            corr = valid['progressivity_proxy'].corr(valid['social_spending_gdp'])
            logger.info(f"Correlation (tax progressivity vs social spending): {corr:.3f}")

    return merged


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A33: REDISTRIBUTION EFFECTIVENESS")
    logger.info("=" * 80)

    sources = load_data()
    if 'grd' not in sources:
        return {}

    # Tax vs transfer by income
    by_income = analyze_tax_vs_transfer_by_income(sources['grd'])
    if not by_income.empty:
        write_single_sheet_excel(by_income, OUTPUT_DIR / "A33_tax_vs_transfer.xlsx", "TaxTransfer")
        logger.info(f"Tax vs transfer: {len(by_income)} rows")

    # Austerity-redistribution link
    austerity = test_austerity_redistribution_link(sources['grd'])
    if not austerity.empty:
        write_single_sheet_excel(austerity, OUTPUT_DIR / "A33_austerity_redistribution.xlsx", "Austerity")
        if 'became_more_regressive' in austerity.columns:
            n_regressive = austerity['became_more_regressive'].sum()
            logger.info(f"Became more regressive: {n_regressive}/{len(austerity)} countries")

    # Cross progressivity × social spending
    if 'wb_social' in sources:
        cross = cross_tax_progressivity_with_social_spending(sources['grd'], sources['wb_social'])
        if not cross.empty:
            write_single_sheet_excel(cross, OUTPUT_DIR / "A33_progressivity_spending.xlsx", "Cross")

    logger.info("A33 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
