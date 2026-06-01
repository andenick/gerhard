"""
A23: VAT Transition and Regressivity
======================================
Documents the worldwide shift from trade taxes and income taxes to VAT.
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


def load_grd():
    fpath = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    return pd.read_parquet(fpath) if fpath.exists() else pd.DataFrame()


def track_vat_adoption(grd: pd.DataFrame) -> pd.DataFrame:
    """Identify when each country first reports significant VAT revenue."""
    if grd.empty or 'vat' not in grd.columns:
        return pd.DataFrame()
    results = []
    for country, grp in grd.groupby('iso'):
        grp = grp.sort_values('year')
        vat_data = grp[grp['vat'] > 0.5]  # > 0.5% GDP = meaningful VAT
        if not vat_data.empty:
            first_year = int(vat_data['year'].min())
            latest = grp['vat'].iloc[-1] if pd.notna(grp['vat'].iloc[-1]) else 0
            results.append({'iso': country, 'country': grp['country'].iloc[0],
                          'vat_intro_year': first_year, 'vat_latest_gdp': latest,
                          'region': grp['region'].iloc[0], 'income_group': grp['income_group'].iloc[0]})
    df = pd.DataFrame(results)
    if not df.empty:
        df['decade_adopted'] = (df['vat_intro_year'] // 10) * 10
    return df


def analyze_vat_replaced_what(grd: pd.DataFrame) -> pd.DataFrame:
    """Test: did VAT revenue rise as trade taxes or PIT fell?"""
    if grd.empty:
        return pd.DataFrame()
    results = []
    for country, grp in grd.groupby('iso'):
        grp = grp.sort_values('year')
        cols = ['vat', 'trade_taxes', 'pit', 'goods_services', 'taxes_inc_sc']
        valid = grp[['year'] + [c for c in cols if c in grp.columns]].dropna(subset=[c for c in ['vat', 'trade_taxes'] if c in grp.columns], how='all')
        if len(valid) < 10:
            continue
        mid = valid['year'].median()
        early = valid[valid['year'] <= mid]
        late = valid[valid['year'] > mid]
        row = {'iso': country, 'n_years': len(valid)}
        for col in cols:
            if col in valid.columns:
                row[f'{col}_early'] = early[col].mean()
                row[f'{col}_late'] = late[col].mean()
                row[f'{col}_change'] = late[col].mean() - early[col].mean()
        # Did VAT replace trade taxes?
        if 'vat_change' in row and 'trade_taxes_change' in row:
            row['vat_replaced_trade'] = row.get('vat_change', 0) > 0 and row.get('trade_taxes_change', 0) < 0
        results.append(row)
    return pd.DataFrame(results)


def analyze_vat_revenue_productivity(grd: pd.DataFrame) -> pd.DataFrame:
    """VAT Revenue Ratio = actual VAT revenue / (standard_rate × consumption/GDP).
    Without rate data, use VAT/goods_services as efficiency proxy."""
    if grd.empty or 'vat' not in grd.columns or 'goods_services' not in grd.columns:
        return pd.DataFrame()
    latest = grd[grd['year'] >= grd['year'].max() - 2]
    avg = latest.groupby('iso').agg({
        'country': 'first', 'income_group': 'first',
        'vat': 'mean', 'goods_services': 'mean', 'taxes_inc_sc': 'mean'
    }).reset_index()
    avg['vat_share_of_gs'] = avg['vat'] / avg['goods_services'] * 100
    avg['vat_share_of_total'] = avg['vat'] / avg['taxes_inc_sc'] * 100
    return avg.dropna(subset=['vat']).sort_values('vat', ascending=False)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A23: VAT TRANSITION AND REGRESSIVITY")
    logger.info("=" * 80)
    grd = load_grd()
    if grd.empty:
        return {}

    adoption = track_vat_adoption(grd)
    if not adoption.empty:
        write_single_sheet_excel(adoption, OUTPUT_DIR / "A23_vat_adoption.xlsx", "Adoption")
        by_decade = adoption['decade_adopted'].value_counts().sort_index()
        logger.info(f"VAT adoption waves:\n{by_decade.to_string()}")

    substitution = analyze_vat_replaced_what(grd)
    if not substitution.empty:
        write_single_sheet_excel(substitution, OUTPUT_DIR / "A23_vat_substitution.xlsx", "Substitution")
        n_replaced = substitution.get('vat_replaced_trade', pd.Series()).sum()
        logger.info(f"VAT replaced trade taxes: {n_replaced}/{len(substitution)} countries")

    productivity = analyze_vat_revenue_productivity(grd)
    if not productivity.empty:
        write_single_sheet_excel(productivity, OUTPUT_DIR / "A23_vat_productivity.xlsx", "Productivity")
        logger.info(f"VAT productivity: {len(productivity)} countries ranked")

    logger.info("A23 COMPLETE")
    return {'countries': len(adoption)}


if __name__ == "__main__":
    run()
