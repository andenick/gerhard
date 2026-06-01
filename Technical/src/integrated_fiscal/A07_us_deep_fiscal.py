"""
A07: US Deep Fiscal Analysis (PSZ/DINA)
========================================
Uses Piketty-Saez-Zucman Distributional National Accounts (20 MB) to analyze
US fiscal incidence across the income distribution, 1913-2022.

Tests: Who actually pays? How has the effective rate structure changed?
       What is the true progressivity of the US fiscal system?

Data: PSZ2022_MacroSeries.xlsx (13 MB), PSZ2022_DistributionalSeries.xlsx (5 MB)
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
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

DINA_DIR = raw_data_dir() / "us_dina"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_psz_macro() -> pd.DataFrame:
    """Load PSZ2022 Macro Series (aggregate US national accounts + taxes)."""
    fpath = DINA_DIR / "PSZ2022_MacroSeries.xlsx"
    if not fpath.exists():
        logger.error(f"PSZ Macro file not found: {fpath}")
        return pd.DataFrame()

    try:
        # PSZ files have multiple sheets — try to find the main data
        xl = pd.ExcelFile(fpath)
        logger.info(f"PSZ Macro sheets: {xl.sheet_names}")

        # Try common sheet names
        for sheet in xl.sheet_names:
            df = pd.read_excel(fpath, sheet_name=sheet, header=None, nrows=5)
            # Look for year column
            if df.shape[1] > 5:
                logger.info(f"Sheet '{sheet}': {df.shape}, first row: {df.iloc[0].tolist()[:5]}")

        # Load first substantive sheet
        main_sheet = xl.sheet_names[0]
        df = pd.read_excel(fpath, sheet_name=main_sheet)
        logger.info(f"PSZ Macro loaded from '{main_sheet}': {df.shape}")
        logger.info(f"Columns: {df.columns.tolist()[:15]}")
        return df

    except Exception as e:
        logger.error(f"Error loading PSZ Macro: {e}")
        return pd.DataFrame()


def load_psz_distributional() -> pd.DataFrame:
    """Load PSZ2022 Distributional Series — taxrates sheet (1913-2019)."""
    fpath = DINA_DIR / "PSZ2022_DistributionalSeries.xlsx"
    if not fpath.exists():
        logger.error(f"PSZ Distributional file not found: {fpath}")
        return pd.DataFrame()

    try:
        df = pd.read_excel(fpath, sheet_name="taxrates")
        logger.info(f"PSZ taxrates: {len(df)} years ({df['year'].min()}-{df['year'].max()}), "
                   f"{len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"Error loading PSZ taxrates: {e}")
        return pd.DataFrame()


def analyze_macro_tax_trends(macro: pd.DataFrame) -> pd.DataFrame:
    """Extract aggregate tax/GDP trends from PSZ macro series."""
    if macro.empty:
        return pd.DataFrame()

    # PSZ macro typically has year as first column or index
    # Look for year-like column
    year_col = None
    for col in macro.columns:
        if 'year' in str(col).lower():
            year_col = col
            break
        # Check if column contains years
        try:
            vals = pd.to_numeric(macro[col], errors='coerce')
            if vals.between(1900, 2030).sum() > 50:
                year_col = col
                break
        except:
            pass

    if year_col is None:
        # Try first column
        year_col = macro.columns[0]

    macro = macro.copy()
    macro['year'] = pd.to_numeric(macro[year_col], errors='coerce')
    macro = macro.dropna(subset=['year'])
    macro['year'] = macro['year'].astype(int)
    macro = macro[(macro['year'] >= 1900) & (macro['year'] <= 2025)]

    # Identify tax-related columns
    tax_cols = [c for c in macro.columns
                if any(kw in str(c).lower() for kw in
                       ['tax', 'revenue', 'income tax', 'corporate', 'estate',
                        'payroll', 'sales', 'excise', 'property'])]

    if not tax_cols:
        logger.warning(f"No tax columns found. Available: {macro.columns.tolist()}")
        # Return whatever numeric data we can find
        numeric_cols = macro.select_dtypes(include=[np.number]).columns.tolist()
        if 'year' in numeric_cols:
            numeric_cols.remove('year')
        result = macro[['year'] + numeric_cols[:20]].copy()
        return result

    logger.info(f"Tax columns found: {tax_cols[:10]}")
    result = macro[['year'] + tax_cols].copy()
    return result


def analyze_distributional_incidence(dist: pd.DataFrame) -> pd.DataFrame:
    """Analyze effective tax rates across the income distribution (PSZ taxrates).

    Columns follow pattern: {tax_type}{income_group}
    Types: tax (total), salestax, proprestax, paytax, ditax (income), corptax, estatetax
    Groups: all, bot50, bot90, top10, top1, top01, top001, mid40, next9, next4
    """
    if dist.empty or 'year' not in dist.columns:
        return pd.DataFrame()

    # Extract key progressivity metrics
    results = []
    for _, row in dist.iterrows():
        year = int(row['year'])
        entry = {'year': year}

        # Total effective rate by group
        for group in ['all', 'bot50', 'top10', 'top1', 'top01']:
            col = f'tax{group}'
            if col in row.index:
                entry[f'total_rate_{group}'] = row[col]

        # By tax type for 'all' and 'top1'
        for ttype in ['salestax', 'proprestax', 'paytax', 'ditax', 'corptax', 'estatetax']:
            for group in ['all', 'bot50', 'top1']:
                col = f'{ttype}{group}'
                if col in row.index:
                    entry[f'{ttype}_{group}'] = row[col]

        # Progressivity index: top1 rate / bot50 rate
        if 'taxtop1' in row.index and 'taxbot50' in row.index:
            top1 = row['taxtop1']
            bot50 = row['taxbot50']
            if bot50 > 0:
                entry['progressivity_ratio'] = top1 / bot50

        results.append(entry)

    return pd.DataFrame(results)


def compute_progressivity_index(dist: pd.DataFrame) -> pd.DataFrame:
    """Compute a progressivity index over time.

    Progressivity = effective rate on top 1% / effective rate on bottom 50%
    A declining index means the system is becoming less progressive.
    """
    # This requires having effective tax rates by percentile group
    # If PSZ data has this structure, compute it
    # Otherwise, return empty
    return pd.DataFrame()


def analyze_tax_composition_us(macro: pd.DataFrame) -> pd.DataFrame:
    """Decompose US tax revenue by type over 100+ years.

    Key transitions:
    - Pre-1913: tariffs + excise (no income tax)
    - 1913-1940: income tax introduced, growing
    - 1940-1980: high marginal rates, income tax dominant
    - 1980-present: rate cuts, payroll tax rising, corporate declining
    """
    if macro.empty:
        return pd.DataFrame()

    # Identify tax type columns
    type_patterns = {
        'individual_income': ['individual', 'personal income', 'ind_inc'],
        'corporate_income': ['corporate', 'corp_inc', 'corporate income'],
        'payroll': ['payroll', 'social insurance', 'fica', 'social_sec'],
        'estate': ['estate', 'inheritance', 'gift'],
        'excise': ['excise', 'customs', 'tariff'],
        'property': ['property'],
        'sales': ['sales', 'vat', 'general consumption'],
    }

    found_types = {}
    for tax_type, patterns in type_patterns.items():
        for col in macro.columns:
            if any(pat in str(col).lower() for pat in patterns):
                found_types[tax_type] = col
                break

    if not found_types:
        return pd.DataFrame()

    year_col = 'year' if 'year' in macro.columns else macro.columns[0]
    result = macro[[year_col]].copy()
    result = result.rename(columns={year_col: 'year'})

    for tax_type, col in found_types.items():
        result[tax_type] = pd.to_numeric(macro[col], errors='coerce')

    result = result.dropna(subset=['year'])
    result['year'] = result['year'].astype(int)

    logger.info(f"US tax composition: {len(result)} years, types: {list(found_types.keys())}")
    return result


def analyze_effective_rate_trajectory(macro: pd.DataFrame) -> pd.DataFrame:
    """Track how average effective tax rates changed across major policy eras.

    Eras: New Deal (1933-1945), Postwar Consensus (1945-1980),
          Reagan Revolution (1981-2000), 21st Century (2001-2022)
    """
    if macro.empty:
        return pd.DataFrame()

    eras = {
        'pre_income_tax': (1900, 1912),
        'wwi_interwar': (1913, 1932),
        'new_deal_wwii': (1933, 1945),
        'postwar_consensus': (1946, 1980),
        'reagan_revolution': (1981, 2000),
        'twenty_first_century': (2001, 2022),
    }

    if 'year' not in macro.columns:
        return pd.DataFrame()

    numeric_cols = macro.select_dtypes(include=[np.number]).columns.tolist()
    if 'year' in numeric_cols:
        numeric_cols.remove('year')

    results = []
    for era_name, (start, end) in eras.items():
        era_data = macro[(macro['year'] >= start) & (macro['year'] <= end)]
        if era_data.empty:
            continue
        row = {'era': era_name, 'start': start, 'end': end, 'n_years': len(era_data)}
        for col in numeric_cols[:15]:
            row[f'{col}_mean'] = era_data[col].mean()
        results.append(row)

    return pd.DataFrame(results)


def run() -> dict:
    """Execute full US deep fiscal analysis."""
    logger.info("=" * 80)
    logger.info("A07: US DEEP FISCAL ANALYSIS (PSZ/DINA)")
    logger.info("=" * 80)

    macro = load_psz_macro()
    dist = load_psz_distributional()

    results = {}

    if not macro.empty:
        tax_trends = analyze_macro_tax_trends(macro)
        if not tax_trends.empty:
            write_single_sheet_excel(tax_trends, OUTPUT_DIR / "A07_us_tax_trends.xlsx", "TaxTrends")
            logger.info(f"US tax trends: {len(tax_trends)} years")
            results['tax_trend_years'] = len(tax_trends)

        composition = analyze_tax_composition_us(macro)
        if not composition.empty:
            write_single_sheet_excel(composition, OUTPUT_DIR / "A07_us_tax_composition.xlsx", "Composition")
            logger.info(f"US tax composition: {len(composition)} years")

        era_analysis = analyze_effective_rate_trajectory(macro)
        if not era_analysis.empty:
            write_single_sheet_excel(era_analysis, OUTPUT_DIR / "A07_us_policy_eras.xlsx", "Eras")
            logger.info(f"Policy era analysis: {len(era_analysis)} eras")

    if not dist.empty:
        incidence = analyze_distributional_incidence(dist)
        if not incidence.empty:
            write_single_sheet_excel(incidence, OUTPUT_DIR / "A07_us_tax_progressivity.xlsx", "Progressivity")
            logger.info(f"US tax progressivity: {len(incidence)} years")
            results['distributional_rows'] = len(incidence)

            # Key finding: progressivity trend
            if 'progressivity_ratio' in incidence.columns:
                early = incidence[incidence['year'] <= 1960]['progressivity_ratio'].mean()
                recent = incidence[incidence['year'] >= 2000]['progressivity_ratio'].mean()
                logger.info(f"Progressivity (top1/bot50 rate): {early:.2f} (pre-1960) → {recent:.2f} (post-2000)")

            if 'total_rate_top1' in incidence.columns:
                peak = incidence.loc[incidence['total_rate_top1'].idxmax()]
                trough = incidence.loc[incidence['total_rate_top1'].idxmin()]
                logger.info(f"Top 1% effective rate: peak {peak['total_rate_top1']:.1%} ({int(peak['year'])}), "
                           f"trough {trough['total_rate_top1']:.1%} ({int(trough['year'])})")

    logger.info("A07 COMPLETE")
    return results


if __name__ == "__main__":
    run()
