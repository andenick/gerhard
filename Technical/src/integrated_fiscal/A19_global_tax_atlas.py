"""
A19: Global Tax Composition Atlas
===================================
Maps every country's tax DNA using GRD 2025 (196 countries).
Tracks structural transitions: trade→VAT→income.
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


def load_grd() -> pd.DataFrame:
    fpath = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    if not fpath.exists():
        fpath = raw_data_dir() / "grd" / "grd_2025_merged.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_parquet(fpath)
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    return df


def compute_composition_shares(grd: pd.DataFrame) -> pd.DataFrame:
    """Compute tax type shares of total for each country-year."""
    components = ['pit', 'cit', 'social_contributions', 'goods_services',
                  'trade_taxes', 'property_taxes', 'other_taxes']
    available = [c for c in components if c in grd.columns]

    grd = grd.copy()
    total_col = 'taxes_inc_sc' if 'taxes_inc_sc' in grd.columns else 'taxes_ex_sc'
    if total_col not in grd.columns:
        return pd.DataFrame()

    for col in available:
        grd[f'{col}_share'] = np.where(
            grd[total_col] > 0,
            grd[col] / grd[total_col] * 100,
            np.nan
        )

    keep = ['iso', 'country', 'year', 'region', 'income_group', total_col] + \
           available + [f'{c}_share' for c in available]
    return grd[[c for c in keep if c in grd.columns]]


def analyze_by_income_group(grd: pd.DataFrame) -> pd.DataFrame:
    """Average tax composition by World Bank income group."""
    rev_cols = [c for c in grd.columns if any(kw in c for kw in
               ['pit', 'cit', 'social', 'goods_services', 'trade', 'property', 'vat', 'excise',
                'resource', 'taxes_inc', 'total_rev'])]

    results = grd.groupby('income_group')[rev_cols].mean().reset_index()
    return results


def analyze_by_region(grd: pd.DataFrame) -> pd.DataFrame:
    """Average tax composition by world region."""
    rev_cols = [c for c in grd.columns if any(kw in c for kw in
               ['pit', 'cit', 'social', 'goods_services', 'trade', 'property', 'vat',
                'resource', 'taxes_inc', 'total_rev'])]

    results = grd.groupby('region')[rev_cols].mean().reset_index()
    return results


def track_structural_transition(grd: pd.DataFrame) -> pd.DataFrame:
    """Track the trade→internal tax transition over time."""
    grd = grd.copy()
    grd['decade'] = (grd['year'] // 10) * 10

    rev_cols = ['taxes_inc_sc', 'pit', 'cit', 'goods_services', 'vat',
                'trade_taxes', 'social_contributions', 'resource_revenue']
    available = [c for c in rev_cols if c in grd.columns]

    results = grd.groupby(['income_group', 'decade'])[available].mean().reset_index()
    return results


def identify_tax_system_types(grd: pd.DataFrame) -> pd.DataFrame:
    """Classify each country's latest tax system into structural types."""
    # Use latest 3 years average
    latest = grd[grd['year'] >= grd['year'].max() - 2]
    avg = latest.groupby('iso').agg({
        'country': 'first', 'region': 'first', 'income_group': 'first',
        **{c: 'mean' for c in ['taxes_inc_sc', 'pit', 'cit', 'goods_services',
           'vat', 'trade_taxes', 'social_contributions', 'resource_revenue']
           if c in latest.columns}
    }).reset_index()

    # Classification rules
    def classify(row):
        total = row.get('taxes_inc_sc', 0)
        if total == 0 or pd.isna(total):
            return 'insufficient_data'
        pit_share = row.get('pit', 0) / total * 100 if total > 0 else 0
        ssc_share = row.get('social_contributions', 0) / total * 100 if total > 0 else 0
        trade_share = row.get('trade_taxes', 0) / total * 100 if total > 0 else 0
        resource = row.get('resource_revenue', 0)
        vat_share = row.get('vat', 0) / total * 100 if total > 0 else 0

        if resource and resource > 10:
            return 'resource_dependent'
        if trade_share > 30:
            return 'trade_tax_dependent'
        if ssc_share > 35:
            return 'social_insurance_dominant'
        if pit_share > 30:
            return 'progressive_income_dominant'
        if vat_share > 30:
            return 'consumption_dominant'
        if total < 15:
            return 'low_tax'
        return 'mixed'

    avg['tax_system_type'] = avg.apply(classify, axis=1)
    return avg


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A19: GLOBAL TAX COMPOSITION ATLAS")
    logger.info("=" * 80)

    grd = load_grd()
    if grd.empty:
        logger.error("No GRD data")
        return {}

    logger.info(f"GRD: {len(grd)} rows, {grd['iso'].nunique()} countries")

    # Composition shares
    shares = compute_composition_shares(grd)
    if not shares.empty:
        write_single_sheet_excel(shares.head(50000), OUTPUT_DIR / "A19_composition_shares.xlsx", "Shares")
        logger.info(f"Composition shares: {len(shares)} rows")

    # By income group
    by_income = analyze_by_income_group(grd)
    if not by_income.empty:
        write_single_sheet_excel(by_income, OUTPUT_DIR / "A19_by_income_group.xlsx", "ByIncome")
        logger.info(f"By income group:\n{by_income.to_string(index=False)}")

    # By region
    by_region = analyze_by_region(grd)
    if not by_region.empty:
        write_single_sheet_excel(by_region, OUTPUT_DIR / "A19_by_region.xlsx", "ByRegion")

    # Structural transition
    transition = track_structural_transition(grd)
    if not transition.empty:
        write_single_sheet_excel(transition, OUTPUT_DIR / "A19_structural_transition.xlsx", "Transition")
        logger.info(f"Structural transition: {len(transition)} rows")

    # Tax system types
    types = identify_tax_system_types(grd)
    if not types.empty:
        write_single_sheet_excel(types, OUTPUT_DIR / "A19_tax_system_types.xlsx", "Types")
        type_counts = types['tax_system_type'].value_counts()
        logger.info(f"Tax system types:\n{type_counts.to_string()}")

    logger.info("A19 COMPLETE")
    return {'countries': grd['iso'].nunique()}


if __name__ == "__main__":
    run()
