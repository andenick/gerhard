"""
A04: Tax Structure Evolution Analysis
=======================================
Analyzes how tax systems evolve over time — the shift from trade taxes to
income taxes to VAT, and what drives these transitions.

Data: WDI fiscal + income panels (200 countries, 1972-2024)
Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir, processed_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

PROCESSED_DIR = processed_data_dir()
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_fiscal_panel() -> pd.DataFrame:
    """Load WDI fiscal detail panel."""
    fpath = PROCESSED_DIR / "wdi_fiscal_detail.xlsx"
    if not fpath.exists():
        logger.error(f"Missing: {fpath}")
        return pd.DataFrame()

    df = pd.read_excel(fpath)
    logger.info(f"Fiscal panel: {len(df):,} rows, {len(df.columns)} columns")
    logger.info(f"Columns: {df.columns.tolist()[:20]}")
    return df


def load_income_panel() -> pd.DataFrame:
    """Load WDI income detail panel."""
    fpath = PROCESSED_DIR / "wdi_income_detail.xlsx"
    if not fpath.exists():
        logger.warning(f"Missing: {fpath}")
        return pd.DataFrame()

    df = pd.read_excel(fpath)
    logger.info(f"Income panel: {len(df):,} rows")
    return df


def identify_tax_columns(df: pd.DataFrame) -> dict:
    """Identify which tax-related columns are available."""
    # Direct mapping for known WDI fiscal panel column names
    direct_map = {
        'tax_revenue_gdp': 'tax_revenue_pct_gdp',
        'taxes_income': 'income_tax_pct_revenue',
        'taxes_goods_services': 'goods_services_tax_pct_revenue',
        'taxes_trade': 'trade_tax_pct_revenue',
        'revenue_total': 'revenue_excl_grants_pct_gdp',
    }

    found = {}
    for key, col in direct_map.items():
        if col in df.columns:
            found[key] = col

    # If direct map didn't work, try pattern matching
    if not found:
        tax_patterns = {
            'tax_revenue_gdp': ['tax_revenue_pct_gdp', 'tax_revenue', 'GC.TAX.TOTL.GD.ZS'],
            'taxes_income': ['income_tax_pct_revenue', 'income_tax_pct_gdp', 'GC.TAX.YPKG'],
            'taxes_goods_services': ['goods_services_tax_pct_revenue', 'GC.TAX.GSRV'],
            'taxes_trade': ['trade_tax_pct_revenue', 'GC.TAX.INTT', 'export_tax'],
            'revenue_total': ['revenue_excl_grants_pct_gdp', 'GC.REV.XGRT', 'total_revenue'],
        }
        for key, patterns in tax_patterns.items():
            for pat in patterns:
                matches = [c for c in df.columns if pat.lower() in c.lower()]
                if matches:
                    found[key] = matches[0]
                    break

    logger.info(f"Tax columns identified: {found}")
    return found


def compute_tax_composition(panel: pd.DataFrame, tax_cols: dict) -> pd.DataFrame:
    """Compute tax composition shares (income, goods/services, trade as % of total)."""
    if 'tax_revenue_gdp' not in tax_cols:
        # Try to compute from components
        component_cols = {k: v for k, v in tax_cols.items() if k != 'tax_revenue_gdp'}
        if not component_cols:
            return pd.DataFrame()

    required = ['country_code', 'year']
    if not all(c in panel.columns for c in required):
        # Try common alternatives
        if 'country' in panel.columns:
            panel = panel.rename(columns={'country': 'country_code'})

    results = panel[['country_code', 'year']].copy()

    for key, col in tax_cols.items():
        if col in panel.columns:
            results[key] = pd.to_numeric(panel[col], errors='coerce')

    results = results.dropna(subset=['country_code', 'year'])
    results['year'] = results['year'].astype(int)

    # Compute shares where possible
    total_col = tax_cols.get('tax_revenue_gdp') or tax_cols.get('revenue_total')
    if total_col and total_col in results.columns:
        for key in ['taxes_income', 'taxes_goods_services', 'taxes_trade']:
            if key in results.columns and 'tax_revenue_gdp' in results.columns:
                results[f'{key}_share'] = results[key] / results['tax_revenue_gdp'] * 100

    return results


def analyze_tax_modernization(composition: pd.DataFrame) -> pd.DataFrame:
    """Track the "tax modernization" trajectory.

    Classical pattern: trade taxes → income taxes → VAT
    As countries develop, revenue shifts from easy-to-collect border taxes
    to harder-to-collect internal taxes (income, VAT).
    """
    if composition.empty:
        return pd.DataFrame()

    results = []
    share_cols = [c for c in composition.columns if c.endswith('_share')]

    for country, grp in composition.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 10:
            continue

        # Early period vs late period
        early = grp[grp['year'] <= grp['year'].median()]
        late = grp[grp['year'] > grp['year'].median()]

        row = {
            'country_code': country,
            'year_start': int(grp['year'].min()),
            'year_end': int(grp['year'].max()),
            'n_years': len(grp),
        }

        for col in share_cols:
            early_mean = early[col].mean()
            late_mean = late[col].mean()
            row[f'{col}_early'] = early_mean
            row[f'{col}_late'] = late_mean
            row[f'{col}_change'] = late_mean - early_mean

        # Tax effort (total tax/GDP)
        if 'tax_revenue_gdp' in composition.columns:
            row['tax_effort_early'] = early['tax_revenue_gdp'].mean()
            row['tax_effort_late'] = late['tax_revenue_gdp'].mean()
            row['tax_effort_change'] = row['tax_effort_late'] - row['tax_effort_early']

        results.append(row)

    return pd.DataFrame(results)


def compute_tax_buoyancy(panel: pd.DataFrame, tax_cols: dict) -> pd.DataFrame:
    """Compute tax buoyancy: elasticity of tax revenue to GDP.

    Buoyancy > 1 means tax system captures more than proportional share of growth.
    Indicates progressive structure or active policy changes.
    """
    results = []

    # Need tax/GDP and a GDP growth indicator
    tax_col = tax_cols.get('tax_revenue_gdp') or tax_cols.get('revenue_total')
    if not tax_col or tax_col not in panel.columns:
        return pd.DataFrame()

    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 15:
            continue

        grp = grp.copy()
        tax_values = pd.to_numeric(grp[tax_col], errors='coerce')
        if tax_values.isna().sum() > len(grp) * 0.5:
            continue

        # Compute growth rates
        tax_growth = tax_values.pct_change()
        # Use tax/GDP changes as proxy (if actual GDP not available)
        tax_level_change = tax_values.diff()

        # 10-year rolling buoyancy (trend growth)
        valid = tax_values.dropna()
        if len(valid) < 10:
            continue

        # Simple regression: log(tax_revenue) on time → trend growth rate
        log_tax = np.log(valid[valid > 0])
        if len(log_tax) < 10:
            continue

        # Piecewise: early vs late
        mid = len(log_tax) // 2
        early_trend = np.polyfit(range(mid), log_tax.iloc[:mid].values, 1)[0]
        late_trend = np.polyfit(range(len(log_tax) - mid), log_tax.iloc[mid:].values, 1)[0]

        results.append({
            'country_code': country,
            'n_years': len(valid),
            'tax_mean': tax_values.mean(),
            'tax_std': tax_values.std(),
            'tax_cv': tax_values.std() / tax_values.mean(),
            'early_trend_pct': early_trend * 100,
            'late_trend_pct': late_trend * 100,
            'trend_acceleration': (late_trend - early_trend) * 100,
        })

    return pd.DataFrame(results)


def analyze_tax_convergence(panel: pd.DataFrame, tax_cols: dict) -> pd.DataFrame:
    """Sigma-convergence in tax structures: are countries' tax systems converging?"""
    tax_col = tax_cols.get('tax_revenue_gdp') or tax_cols.get('revenue_total')
    if not tax_col or tax_col not in panel.columns:
        return pd.DataFrame()

    results = []
    for year, yr_data in panel.groupby('year'):
        values = pd.to_numeric(yr_data[tax_col], errors='coerce').dropna()
        if len(values) < 20:
            continue

        results.append({
            'year': int(year),
            'n_countries': len(values),
            'mean_tax_gdp': values.mean(),
            'std_tax_gdp': values.std(),
            'cv_tax_gdp': values.std() / values.mean(),
            'min': values.min(),
            'p25': values.quantile(0.25),
            'median': values.median(),
            'p75': values.quantile(0.75),
            'max': values.max(),
            'iqr': values.quantile(0.75) - values.quantile(0.25),
        })

    return pd.DataFrame(results)


def run() -> dict:
    """Execute full tax structure analysis."""
    logger.info("=" * 80)
    logger.info("A04: TAX STRUCTURE EVOLUTION")
    logger.info("=" * 80)

    fiscal = load_fiscal_panel()
    if fiscal.empty:
        logger.error("No fiscal data. Aborting.")
        return {}

    tax_cols = identify_tax_columns(fiscal)
    if not tax_cols:
        logger.error("No tax columns identified. Check panel structure.")
        logger.info(f"Available columns: {fiscal.columns.tolist()}")
        return {}

    composition = compute_tax_composition(fiscal, tax_cols)
    if not composition.empty:
        write_single_sheet_excel(composition, OUTPUT_DIR / "A04_tax_composition.xlsx", "Composition")
        logger.info(f"Tax composition: {len(composition):,} rows, "
                   f"{composition['country_code'].nunique()} countries")

    modernization = analyze_tax_modernization(composition)
    if not modernization.empty:
        write_single_sheet_excel(modernization, OUTPUT_DIR / "A04_tax_modernization.xlsx", "Modernization")
        logger.info(f"Tax modernization: {len(modernization)} countries")

    buoyancy = compute_tax_buoyancy(fiscal, tax_cols)
    if not buoyancy.empty:
        write_single_sheet_excel(buoyancy, OUTPUT_DIR / "A04_tax_buoyancy.xlsx", "Buoyancy")
        logger.info(f"Tax buoyancy: {len(buoyancy)} countries")

    convergence = analyze_tax_convergence(fiscal, tax_cols)
    if not convergence.empty:
        write_single_sheet_excel(convergence, OUTPUT_DIR / "A04_tax_convergence.xlsx", "Convergence")
        logger.info(f"Tax convergence: {len(convergence)} years")

    logger.info("A04 COMPLETE")
    return {
        'composition_rows': len(composition),
        'modernization_countries': len(modernization),
        'buoyancy_countries': len(buoyancy),
    }


if __name__ == "__main__":
    run()
