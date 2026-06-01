#!/usr/bin/env python3
"""
P60: Build Master Panel
Merge tax + expenditure + debt + GDP into unified fiscal panel.
Stage: P | ID: P60
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
    "id": "P60",
    "name": "Build Master Panel",
    "stage": "P",
    "description": "Merge tax + expenditure + debt + GDP into unified panel",
    "depends_on": ["P55", "P45", "P50"],
    "inputs": [
        {"path": "Output/Data/enriched_tax_panel.xlsx", "required": True},
        {"path": "Output/Data/expenditure_panel.xlsx", "required": False},
        {"path": "Output/Data/debt_panel.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/master_fiscal_panel.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    # --- Step 1: Load enriched tax panel (required) ---
    tax = read_excel_safe(out / "enriched_tax_panel.xlsx")
    if tax.empty:
        logger.error("Cannot load enriched_tax_panel.xlsx; aborting.")
        return
    logger.info(f"Enriched tax panel: {len(tax)} rows, {tax['country_code'].nunique()} countries")

    # --- Step 2: Load expenditure panel (optional) ---
    exp = read_excel_safe(out / "expenditure_panel.xlsx")
    has_exp = not exp.empty
    if has_exp:
        logger.info(f"Expenditure panel: {len(exp)} rows, {exp['country_code'].nunique()} countries")
        # Keep only expenditure-specific columns for merge
        exp_cols = ['country_code', 'year']
        for c in exp.columns:
            if c not in ['country_code', 'country_name', 'year']:
                exp_cols.append(c)
        exp_slim = exp[exp_cols].copy()
    else:
        logger.warning("Expenditure panel not found; proceeding without it.")
        exp_slim = pd.DataFrame()

    # --- Step 3: Load debt panel (optional) ---
    debt = read_excel_safe(out / "debt_panel.xlsx")
    has_debt = not debt.empty
    if has_debt:
        logger.info(f"Debt panel: {len(debt)} rows, {debt['country_code'].nunique()} countries")
        debt_cols = ['country_code', 'year']
        for c in debt.columns:
            if c not in ['country_code', 'country_name', 'year']:
                debt_cols.append(c)
        debt_slim = debt[debt_cols].copy()
    else:
        logger.warning("Debt panel not found; proceeding without it.")
        debt_slim = pd.DataFrame()

    # --- Step 4: Merge all panels ---
    # Start with enriched tax as the base (outer join to capture all country-years)
    master = tax.copy()

    if has_exp:
        pre = len(master)
        master = master.merge(exp_slim, on=['country_code', 'year'], how='outer')
        logger.info(f"After expenditure merge: {len(master)} rows (was {pre})")

    if has_debt:
        pre = len(master)
        master = master.merge(debt_slim, on=['country_code', 'year'], how='outer')
        logger.info(f"After debt merge: {len(master)} rows (was {pre})")

    # --- Step 5: Compute derived columns ---
    # Fiscal balance = tax - expenditure
    if 'tax_revenue_pct_gdp' in master.columns and 'expenditure_pct_gdp' in master.columns:
        mask = master['tax_revenue_pct_gdp'].notna() & master['expenditure_pct_gdp'].notna()
        master['fiscal_balance_pct_gdp'] = np.where(
            mask,
            master['tax_revenue_pct_gdp'] - master['expenditure_pct_gdp'],
            np.nan,
        )
        n_fb = mask.sum()
        logger.info(f"  fiscal_balance_pct_gdp computed for {n_fb} rows")

    # Tax per capita = (tax_pct_gdp / 100) * gdp_per_capita
    if 'tax_revenue_pct_gdp' in master.columns and 'gdp_per_capita_usd' in master.columns:
        mask = master['tax_revenue_pct_gdp'].notna() & master['gdp_per_capita_usd'].notna()
        master['tax_per_capita'] = np.where(
            mask,
            (master['tax_revenue_pct_gdp'] / 100) * master['gdp_per_capita_usd'],
            np.nan,
        )
        n_tpc = mask.sum()
        logger.info(f"  tax_per_capita computed for {n_tpc} rows")

    # --- Step 6: Data completeness flag ---
    has_tax = master['tax_revenue_pct_gdp'].notna() if 'tax_revenue_pct_gdp' in master.columns else pd.Series(False, index=master.index)
    has_expenditure = master['expenditure_pct_gdp'].notna() if 'expenditure_pct_gdp' in master.columns else pd.Series(False, index=master.index)
    has_debt_col = master['debt_pct_gdp'].notna() if 'debt_pct_gdp' in master.columns else pd.Series(False, index=master.index)

    domain_count = has_tax.astype(int) + has_expenditure.astype(int) + has_debt_col.astype(int)

    master['data_completeness'] = 'none'
    master.loc[domain_count == 1, 'data_completeness'] = 'single'
    master.loc[domain_count == 2, 'data_completeness'] = 'partial'
    master.loc[domain_count == 3, 'data_completeness'] = 'full'

    # Refine: if only tax, label as tax_only
    master.loc[(domain_count == 1) & has_tax, 'data_completeness'] = 'tax_only'

    logger.info(f"\nData completeness:")
    for val, cnt in master['data_completeness'].value_counts().items():
        logger.info(f"  {val}: {cnt}")

    # --- Step 7: Sort and save ---
    master = master.sort_values(['country_code', 'year']).reset_index(drop=True)

    write_single_sheet_excel(master, out / "master_fiscal_panel.xlsx")
    logger.info(f"\nSaved master_fiscal_panel.xlsx: {len(master)} rows, "
               f"{master['country_code'].nunique()} countries, {len(master.columns)} columns")
    logger.info(f"  Year range: {master['year'].min()}-{master['year'].max()}")
    logger.info(f"  Columns: {list(master.columns)}")

    logger.info(f"[{MANIFEST['id']}] Done.")


if __name__ == "__main__":
    run()
