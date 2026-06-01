"""
A12: Unified Master Fiscal Panel
==================================
Merges ALL available data into a single master panel — the core analytical
asset of Gerhard. Country × year × 30+ variables.

Sources merged:
- World Bank expenditure (200+ countries, 1960-2024)
- World Bank macro (GDP growth, debt, inflation, 258 countries)
- WDI fiscal detail (tax structure, 211 countries)
- JST Macrohistory (18 countries, 1870-2020)
- PWT profit rates (183 countries, 1950-2019)
- Eurostat COFOG (30 EU, 1995-2024)

Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir, processed_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

RAW_DIR = raw_data_dir()
PROCESSED_DIR = processed_data_dir()
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_wb_expenditure() -> pd.DataFrame:
    """Load WB expenditure indicators."""
    wb_dir = RAW_DIR / "worldbank" / "expenditure"
    files = {
        'gov_exp_gdp': 'wb_gov_expenditure_gdp.csv',
        'education_gdp': 'wb_education_expenditure.csv',
        'health_gdp': 'wb_health_expenditure.csv',
        'military_gdp': 'wb_military_expenditure.csv',
        'social_gdp': 'wb_social_expenditure.csv',
        'rd_gdp': 'wb_rd_expenditure.csv',
    }
    panels = []
    for key, fname in files.items():
        fpath = wb_dir / fname
        if fpath.exists():
            df = pd.read_csv(fpath)
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna(subset=['year', 'value'])
            df = df[df['country_code'].str.len() <= 3]
            panels.append(df[['country_code', 'year', 'value']].rename(columns={'value': key}))

    if not panels:
        return pd.DataFrame()
    result = panels[0]
    for p in panels[1:]:
        col = [c for c in p.columns if c not in ['country_code', 'year']][0]
        result = result.merge(p, on=['country_code', 'year'], how='outer')
    return result


def load_wb_macro() -> pd.DataFrame:
    """Load WB macro panel (GDP growth, debt, inflation, GDPPC)."""
    fpath = RAW_DIR / "worldbank" / "macro" / "wb_macro_combined.csv"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_csv(fpath)
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    return df


def load_wdi_fiscal() -> pd.DataFrame:
    """Load WDI fiscal detail (tax structure)."""
    fpath = PROCESSED_DIR / "wdi_fiscal_detail.xlsx"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_excel(fpath)
    # Keep key columns
    keep = ['country_code', 'year', 'tax_revenue_pct_gdp', 'income_tax_pct_revenue',
            'goods_services_tax_pct_revenue', 'trade_tax_pct_revenue',
            'revenue_excl_grants_pct_gdp', 'net_lending_borrowing_pct_gdp']
    available = [c for c in keep if c in df.columns]
    return df[available]


def load_jst() -> pd.DataFrame:
    """Load JST fiscal panel (18 countries, 1870-2020)."""
    fpath = RAW_DIR / "jst" / "jst_fiscal_panel.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_parquet(fpath)
    df = df.rename(columns={'country_code': 'iso3'})
    # Rename JST columns to avoid conflicts
    rename = {
        'revenue': 'jst_revenue',
        'expenditure': 'jst_expenditure',
        'debtgdp': 'jst_debt_gdp',
        'stir': 'jst_short_rate',
        'ltrate': 'jst_long_rate',
        'cpi': 'jst_cpi',
        'crisisJST': 'banking_crisis',
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    keep = ['iso3', 'year'] + [v for v in rename.values() if v in df.columns]
    return df[[c for c in keep if c in df.columns]].rename(columns={'iso3': 'country_code'})


def load_pwt() -> pd.DataFrame:
    """Load PWT profit rate panel."""
    fpath = RAW_DIR / "profit_rates" / "pwt_profit_rate_panel.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_parquet(fpath)
    df = df.rename(columns={'countrycode': 'country_code'})
    keep = ['country_code', 'year', 'labsh', 'capital_share', 'irr']
    available = [c for c in keep if c in df.columns]
    return df[available].rename(columns={
        'labsh': 'labor_share',
        'irr': 'profit_rate_irr',
    })


def build_master_panel() -> pd.DataFrame:
    """Merge all sources into unified panel."""
    logger.info("Loading data sources...")

    sources = {
        'WB expenditure': load_wb_expenditure(),
        'WB macro': load_wb_macro(),
        'WDI fiscal': load_wdi_fiscal(),
        'JST': load_jst(),
        'PWT': load_pwt(),
    }

    for name, df in sources.items():
        if not df.empty:
            logger.info(f"  {name}: {len(df):,} rows, {df['country_code'].nunique()} countries")
        else:
            logger.warning(f"  {name}: EMPTY")

    # Start with the largest panel (WB expenditure) as base
    non_empty = [(name, df) for name, df in sources.items() if not df.empty]
    if not non_empty:
        return pd.DataFrame()

    # Sort by size, start with largest
    non_empty.sort(key=lambda x: len(x[1]), reverse=True)
    base_name, base = non_empty[0]
    logger.info(f"Base panel: {base_name} ({len(base):,} rows)")

    master = base.copy()
    master['year'] = master['year'].astype(int)

    for name, df in non_empty[1:]:
        df = df.copy()
        df['year'] = df['year'].astype(int)
        # Only merge columns we don't already have
        new_cols = [c for c in df.columns if c not in master.columns or c in ['country_code', 'year']]
        if len(new_cols) <= 2:  # Only has keys
            continue
        master = master.merge(df[new_cols], on=['country_code', 'year'], how='outer')
        logger.info(f"  Merged {name}: now {len(master):,} rows, {len(master.columns)} cols")

    master = master.sort_values(['country_code', 'year']).reset_index(drop=True)
    master = master[master['country_code'].str.len() <= 3]

    logger.info(f"Master panel: {len(master):,} rows, {master['country_code'].nunique()} countries, "
               f"{len(master.columns)} variables")
    return master


def compute_coverage_matrix(master: pd.DataFrame) -> pd.DataFrame:
    """Compute data availability: which variables exist for which country-decades."""
    if master.empty:
        return pd.DataFrame()

    master = master.copy()
    master['decade'] = (master['year'] // 10) * 10

    data_cols = [c for c in master.columns if c not in ['country_code', 'year', 'decade']]
    coverage = master.groupby(['country_code', 'decade'])[data_cols].apply(
        lambda x: x.notna().sum() / len(x)).reset_index()

    # Summarize: average coverage by decade
    decade_summary = coverage.groupby('decade')[data_cols].mean()
    return decade_summary.reset_index()


def run() -> dict:
    """Build and analyze master panel."""
    logger.info("=" * 80)
    logger.info("A12: UNIFIED MASTER FISCAL PANEL")
    logger.info("=" * 80)

    master = build_master_panel()
    if master.empty:
        return {}

    # Save master panel
    master.to_parquet(OUTPUT_DIR / "A12_master_panel.parquet", index=False)
    logger.info(f"Saved master panel (parquet): {len(master):,} rows")

    # Save Excel subset (first 50k rows to keep file manageable)
    sample = master.head(50000)
    write_single_sheet_excel(sample, OUTPUT_DIR / "A12_master_panel_sample.xlsx", "MasterPanel")

    # Coverage matrix
    coverage = compute_coverage_matrix(master)
    if not coverage.empty:
        write_single_sheet_excel(coverage, OUTPUT_DIR / "A12_coverage_matrix.xlsx", "Coverage")
        logger.info(f"Coverage matrix: {len(coverage)} decades")

    # Summary statistics
    summary = {
        'total_rows': len(master),
        'countries': int(master['country_code'].nunique()),
        'year_min': int(master['year'].min()),
        'year_max': int(master['year'].max()),
        'variables': len(master.columns) - 2,
        'variable_list': [c for c in master.columns if c not in ['country_code', 'year']],
        'completeness': {col: f"{master[col].notna().sum() / len(master):.1%}"
                        for col in master.columns if col not in ['country_code', 'year']},
    }

    with open(OUTPUT_DIR / "A12_master_panel_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\nMASTER PANEL SUMMARY:")
    logger.info(f"  Rows: {summary['total_rows']:,}")
    logger.info(f"  Countries: {summary['countries']}")
    logger.info(f"  Years: {summary['year_min']}-{summary['year_max']}")
    logger.info(f"  Variables: {summary['variables']}")
    logger.info(f"  Top variables by completeness:")
    sorted_comp = sorted(summary['completeness'].items(), key=lambda x: x[1], reverse=True)
    for var, pct in sorted_comp[:10]:
        logger.info(f"    {var:30s} {pct}")

    logger.info("A12 COMPLETE")
    return summary


if __name__ == "__main__":
    run()
