"""
A26: Resource Revenue and the Fiscal Curse
============================================
Tests whether resource dependence weakens non-resource tax effort.
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


def load_grd():
    fpath = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    return pd.read_parquet(fpath) if fpath.exists() else pd.DataFrame()


def test_resource_curse(grd: pd.DataFrame) -> pd.DataFrame:
    """Cross-section: higher resource revenue → lower non-resource tax effort?"""
    if grd.empty or 'resource_revenue' not in grd.columns:
        return pd.DataFrame()
    # Latest 3 years average
    latest = grd[grd['year'] >= grd['year'].max() - 2]
    avg = latest.groupby('iso').agg({
        'country': 'first', 'income_group': 'first',
        'resource_revenue': 'mean',
        'taxes_ex_sc': 'mean',
        'taxes_inc_sc': 'mean',
        'total_rev_inc_sc': 'mean',
    }).reset_index()
    avg = avg.dropna(subset=['resource_revenue', 'taxes_ex_sc'])
    avg['nonresource_tax'] = avg['taxes_ex_sc'] - avg.get('resource_taxes', 0)
    avg['resource_dependent'] = avg['resource_revenue'] > 5  # >5% GDP from resources
    return avg


def analyze_resource_volatility(grd: pd.DataFrame) -> pd.DataFrame:
    """Resource-dependent countries have more volatile revenue."""
    if grd.empty or 'resource_revenue' not in grd.columns:
        return pd.DataFrame()
    results = []
    for country, grp in grd.groupby('iso'):
        if len(grp) < 10:
            continue
        res = grp['resource_revenue'].dropna()
        tax = grp['taxes_inc_sc'].dropna()
        if len(res) < 5 or len(tax) < 5:
            continue
        results.append({
            'iso': country, 'country': grp['country'].iloc[0],
            'resource_mean': res.mean(),
            'resource_cv': res.std() / res.mean() if res.mean() > 0 else np.nan,
            'total_tax_cv': tax.std() / tax.mean() if tax.mean() > 0 else np.nan,
            'resource_dependent': res.mean() > 5,
        })
    df = pd.DataFrame(results)
    return df


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A26: RESOURCE FISCAL CURSE")
    logger.info("=" * 80)
    grd = load_grd()
    if grd.empty:
        return {}

    curse = test_resource_curse(grd)
    if not curse.empty:
        write_single_sheet_excel(curse, OUTPUT_DIR / "A26_resource_curse.xlsx", "Curse")
        dep = curse[curse['resource_dependent']]
        non_dep = curse[~curse['resource_dependent']]
        logger.info(f"Resource-dependent ({len(dep)}): avg non-res tax = {dep['taxes_ex_sc'].mean():.1f}% GDP")
        logger.info(f"Non-dependent ({len(non_dep)}): avg non-res tax = {non_dep['taxes_ex_sc'].mean():.1f}% GDP")
        # Regression test
        valid = curse[['resource_revenue', 'taxes_ex_sc']].dropna()
        if len(valid) > 10:
            slope, _, r, p, _ = stats.linregress(valid['resource_revenue'], valid['taxes_ex_sc'])
            logger.info(f"Regression: taxes = {slope:.2f}*resource_rev + const (R²={r**2:.3f}, p={p:.4f})")

    volatility = analyze_resource_volatility(grd)
    if not volatility.empty:
        write_single_sheet_excel(volatility, OUTPUT_DIR / "A26_resource_volatility.xlsx", "Volatility")
        dep_v = volatility[volatility['resource_dependent']]['total_tax_cv'].mean()
        non_v = volatility[~volatility['resource_dependent']]['total_tax_cv'].mean()
        logger.info(f"Revenue volatility (CV): resource-dep={dep_v:.2f}, non-dep={non_v:.2f}")

    logger.info("A26 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
