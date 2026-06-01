#!/usr/bin/env python3
"""
E20: Cross-Source Validation
Validate internal consistency of master fiscal panel.
Stage: E | ID: E20
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "E20",
    "name": "Cross-Source Validation",
    "stage": "E",
    "description": "Validate internal consistency of master fiscal panel",
    "depends_on": ["P60"],
    "inputs": [{"path": "Output/Data/master_fiscal_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/cross_source_validation.xlsx"}],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    # --- Load master panel ---
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    if master.empty:
        logger.error("Cannot load master_fiscal_panel.xlsx; aborting.")
        return
    logger.info(f"Master panel: {len(master)} rows, {master['country_code'].nunique()} countries")

    flags = []

    # =========================================================================
    # Check 1: Fiscal balance consistency
    # fiscal_balance should approximately equal tax - expenditure
    # =========================================================================
    if all(c in master.columns for c in ['fiscal_balance_pct_gdp', 'tax_revenue_pct_gdp', 'expenditure_pct_gdp']):
        mask = (
            master['fiscal_balance_pct_gdp'].notna()
            & master['tax_revenue_pct_gdp'].notna()
            & master['expenditure_pct_gdp'].notna()
        )
        subset = master[mask].copy()
        expected = subset['tax_revenue_pct_gdp'] - subset['expenditure_pct_gdp']
        actual = subset['fiscal_balance_pct_gdp']
        diff = (actual - expected).abs()
        bad = diff > 0.01  # tolerance for floating point

        for idx in subset[bad].index:
            row = master.loc[idx]
            flags.append({
                'country_code': row['country_code'],
                'year': row['year'],
                'check_name': 'fiscal_balance_consistency',
                'expected': f"tax({row['tax_revenue_pct_gdp']:.2f}) - exp({row['expenditure_pct_gdp']:.2f})",
                'actual': f"{row['fiscal_balance_pct_gdp']:.2f}",
                'flag': 'inconsistent',
            })

        n_checked = mask.sum()
        n_bad = bad.sum()
        logger.info(f"Check 1 - Fiscal balance consistency: {n_checked} checked, {n_bad} inconsistent")

    # =========================================================================
    # Check 2: Debt should be positive
    # =========================================================================
    if 'debt_pct_gdp' in master.columns:
        mask = master['debt_pct_gdp'].notna()
        negative_debt = master[mask & (master['debt_pct_gdp'] < 0)]

        for idx in negative_debt.index:
            row = master.loc[idx]
            flags.append({
                'country_code': row['country_code'],
                'year': row['year'],
                'check_name': 'negative_debt',
                'expected': '> 0',
                'actual': f"{row['debt_pct_gdp']:.2f}",
                'flag': 'anomaly',
            })

        logger.info(f"Check 2 - Negative debt: {len(negative_debt)} anomalies out of {mask.sum()} observations")

    # =========================================================================
    # Check 3: GDP per capita should correlate with tax (development effect)
    # Countries with high GDP per capita should generally have higher tax
    # =========================================================================
    if all(c in master.columns for c in ['gdp_per_capita_usd', 'tax_revenue_pct_gdp']):
        mask = master['gdp_per_capita_usd'].notna() & master['tax_revenue_pct_gdp'].notna()
        subset = master[mask]

        if len(subset) > 30:
            corr = subset['gdp_per_capita_usd'].corr(subset['tax_revenue_pct_gdp'])
            logger.info(f"Check 3 - GDP-tax correlation: {corr:.3f} (expected positive)")

            if corr < 0:
                flags.append({
                    'country_code': 'ALL',
                    'year': 0,
                    'check_name': 'gdp_tax_correlation',
                    'expected': 'positive correlation',
                    'actual': f"r = {corr:.3f}",
                    'flag': 'warning',
                })

            # Flag extreme outliers: very rich but very low tax
            rich = subset['gdp_per_capita_usd'] > subset['gdp_per_capita_usd'].quantile(0.9)
            low_tax = subset['tax_revenue_pct_gdp'] < 10
            outliers = subset[rich & low_tax]

            for idx in outliers.index:
                row = master.loc[idx]
                flags.append({
                    'country_code': row['country_code'],
                    'year': row['year'],
                    'check_name': 'rich_low_tax',
                    'expected': 'high GDP => moderate/high tax',
                    'actual': f"GDP/cap ${row['gdp_per_capita_usd']:,.0f}, tax {row['tax_revenue_pct_gdp']:.1f}%",
                    'flag': 'anomaly',
                })

            logger.info(f"  Rich + low tax outliers: {len(outliers)}")

    # =========================================================================
    # Check 4: High tax countries should have high expenditure
    # =========================================================================
    if all(c in master.columns for c in ['tax_revenue_pct_gdp', 'expenditure_pct_gdp']):
        mask = master['tax_revenue_pct_gdp'].notna() & master['expenditure_pct_gdp'].notna()
        subset = master[mask]

        high_tax = subset[subset['tax_revenue_pct_gdp'] > 35]
        low_exp = high_tax[high_tax['expenditure_pct_gdp'] < 20]

        for idx in low_exp.index:
            row = master.loc[idx]
            flags.append({
                'country_code': row['country_code'],
                'year': row['year'],
                'check_name': 'high_tax_low_expenditure',
                'expected': 'tax > 35% => expenditure > 20%',
                'actual': f"tax {row['tax_revenue_pct_gdp']:.1f}%, exp {row['expenditure_pct_gdp']:.1f}%",
                'flag': 'anomaly',
            })

        logger.info(f"Check 4 - High tax + low expenditure: {len(low_exp)} anomalies "
                   f"(out of {len(high_tax)} high-tax observations)")

    # =========================================================================
    # Check 5: Very low tax countries funding spending
    # Countries with tax < 10% and also very low debt might have data issues
    # =========================================================================
    if all(c in master.columns for c in ['tax_revenue_pct_gdp', 'debt_pct_gdp']):
        mask = (
            master['tax_revenue_pct_gdp'].notna()
            & master['debt_pct_gdp'].notna()
        )
        subset = master[mask]
        low_tax_low_debt = subset[
            (subset['tax_revenue_pct_gdp'] < 10) & (subset['debt_pct_gdp'] < 10)
        ]

        for idx in low_tax_low_debt.index:
            row = master.loc[idx]
            flags.append({
                'country_code': row['country_code'],
                'year': row['year'],
                'check_name': 'low_tax_low_debt',
                'expected': 'low tax => some debt or other revenue',
                'actual': f"tax {row['tax_revenue_pct_gdp']:.1f}%, debt {row['debt_pct_gdp']:.1f}%",
                'flag': 'info',
            })

        logger.info(f"Check 5 - Low tax + low debt: {len(low_tax_low_debt)} observations")

    # --- Build output ---
    if flags:
        flags_df = pd.DataFrame(flags)
        flags_df = flags_df[['country_code', 'year', 'check_name', 'expected', 'actual', 'flag']]
        flags_df = flags_df.sort_values(['check_name', 'country_code', 'year']).reset_index(drop=True)
    else:
        flags_df = pd.DataFrame(columns=['country_code', 'year', 'check_name', 'expected', 'actual', 'flag'])

    write_single_sheet_excel(flags_df, out / "cross_source_validation.xlsx")

    # --- Summary ---
    logger.info(f"\n{'='*60}")
    logger.info(f"Validation Summary")
    logger.info(f"{'='*60}")
    logger.info(f"Total flags: {len(flags_df)}")
    if len(flags_df) > 0:
        logger.info(f"\nBy check:")
        for check, cnt in flags_df['check_name'].value_counts().items():
            logger.info(f"  {check}: {cnt}")
        logger.info(f"\nBy flag type:")
        for ftype, cnt in flags_df['flag'].value_counts().items():
            logger.info(f"  {ftype}: {cnt}")

    logger.info(f"\nSaved cross_source_validation.xlsx: {len(flags_df)} flags")
    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
