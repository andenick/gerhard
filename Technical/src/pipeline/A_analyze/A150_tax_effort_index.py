#!/usr/bin/env python3
"""
A150: Tax Effort Index
Estimate tax capacity via cross-section OLS and compute tax effort (actual/predicted)
and revenue gap (predicted - actual) for each country.
Stage: A | ID: A150
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

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A150",
    "name": "Tax Effort Index",
    "stage": "A",
    "description": "Estimate tax capacity and compute effort index and revenue gap",
    "depends_on": ["P60", "P65"],
    "inputs": [
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": False},
        {"path": "Output/Data/national_accounts_panel.xlsx", "required": False},
        {"path": "Output/Data/trade_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/tax_effort_index.xlsx"},
        {"path": "Output/Data/tax_effort_summary.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    rev_comp = read_excel_safe(out / "revenue_composition_panel.xlsx")
    natl = read_excel_safe(out / "national_accounts_panel.xlsx")
    trade = read_excel_safe(out / "trade_panel.xlsx")

    if master.empty:
        logger.error("Cannot load master_fiscal_panel.xlsx; aborting.")
        return

    # Get latest year per country from master
    master_latest = master.sort_values('year').groupby('country_code').last().reset_index()

    # Merge structural variables
    merged = master_latest[['country_code', 'country_name', 'year',
                             'tax_revenue_pct_gdp', 'gdp_per_capita_ppp',
                             'trade_pct_gdp', 'urban_pct',
                             'region', 'income_group']].copy()

    # Add agriculture from national accounts (latest year)
    if not natl.empty:
        natl_latest = natl.sort_values('year').groupby('country_code').last().reset_index()
        merged = merged.merge(natl_latest[['country_code', 'agriculture_pct_gdp']],
                              on='country_code', how='left')

    # Add trade openness from trade panel if master's is missing
    if not trade.empty:
        trade_latest = trade.sort_values('year').groupby('country_code').last().reset_index()
        if 'trade_pct_gdp' not in merged.columns or merged['trade_pct_gdp'].isna().sum() > 50:
            merged = merged.merge(trade_latest[['country_code', 'trade_pct_gdp']],
                                  on='country_code', how='left', suffixes=('', '_trade'))
            if 'trade_pct_gdp_trade' in merged.columns:
                merged['trade_pct_gdp'] = merged['trade_pct_gdp'].fillna(merged['trade_pct_gdp_trade'])
                merged.drop(columns=['trade_pct_gdp_trade'], inplace=True)

    # Prepare regression variables
    required = ['tax_pct_gdp', 'gdp_per_capita_ppp', 'trade_pct_gdp']
    merged.rename(columns={'tax_revenue_pct_gdp': 'tax_pct_gdp'}, inplace=True)

    # Log GDP per capita
    merged['log_gdp_pc'] = np.log(merged['gdp_per_capita_ppp'].clip(lower=100))

    # Filter to countries with all key variables
    reg_vars = ['tax_pct_gdp', 'log_gdp_pc', 'trade_pct_gdp']
    optional_vars = []
    if 'agriculture_pct_gdp' in merged.columns:
        reg_vars.append('agriculture_pct_gdp')
        optional_vars.append('agriculture_pct_gdp')
    if 'urban_pct' in merged.columns:
        reg_vars.append('urban_pct')
        optional_vars.append('urban_pct')

    df_reg = merged.dropna(subset=['tax_pct_gdp', 'log_gdp_pc', 'trade_pct_gdp']).copy()

    # Fill optional vars with median for regression
    for v in optional_vars:
        if v in df_reg.columns:
            df_reg[v] = df_reg[v].fillna(df_reg[v].median())

    df_reg = df_reg.dropna(subset=reg_vars)
    logger.info(f"Regression sample: {len(df_reg)} countries")

    if len(df_reg) < 20:
        logger.error("Insufficient data for OLS regression; aborting.")
        return

    # OLS estimation
    X_vars = [v for v in reg_vars if v != 'tax_pct_gdp']
    X = df_reg[X_vars].values
    y = df_reg['tax_pct_gdp'].values

    X_const = np.column_stack([np.ones(len(X)), X])
    beta, residuals, rank, sv = np.linalg.lstsq(X_const, y, rcond=None)
    predicted = X_const @ beta

    # R-squared
    ss_res = np.sum((y - predicted) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # Standard errors
    n = len(y)
    k = X_const.shape[1]
    sigma2 = ss_res / (n - k) if n > k else 1
    cov = sigma2 * np.linalg.inv(X_const.T @ X_const)
    se = np.sqrt(np.diag(cov))
    t_stats = beta / se

    coef_names = ['intercept'] + X_vars
    logger.info(f"OLS R-squared: {r_squared:.4f}")
    for name, b, s, t in zip(coef_names, beta, se, t_stats):
        logger.info(f"  {name}: coef={b:.4f}, se={s:.4f}, t={t:.2f}")

    # Tax effort and revenue gap
    df_reg['predicted_tax'] = predicted
    df_reg['tax_effort'] = df_reg['tax_pct_gdp'] / df_reg['predicted_tax']
    df_reg['revenue_gap'] = df_reg['predicted_tax'] - df_reg['tax_pct_gdp']

    # Classify effort
    df_reg['effort_category'] = pd.cut(
        df_reg['tax_effort'],
        bins=[0, 0.7, 0.9, 1.1, 1.3, float('inf')],
        labels=['Very Low (<0.7)', 'Low (0.7-0.9)', 'Average (0.9-1.1)',
                'High (1.1-1.3)', 'Very High (>1.3)']
    )

    # Output columns
    output_cols = ['country_code', 'country_name', 'year', 'region', 'income_group',
                   'tax_pct_gdp', 'predicted_tax', 'tax_effort', 'revenue_gap',
                   'effort_category', 'log_gdp_pc', 'trade_pct_gdp']
    if 'agriculture_pct_gdp' in df_reg.columns:
        output_cols.append('agriculture_pct_gdp')
    if 'urban_pct' in df_reg.columns:
        output_cols.append('urban_pct')

    output_cols = [c for c in output_cols if c in df_reg.columns]
    tax_effort_df = df_reg[output_cols].sort_values('tax_effort', ascending=False)

    write_single_sheet_excel(tax_effort_df, out / "tax_effort_index.xlsx",
                             sheet_name="Tax Effort")

    # Summary by income group and effort category
    summary_rows = []

    # By income group
    for ig, grp in df_reg.groupby('income_group'):
        if pd.isna(ig):
            continue
        summary_rows.append({
            'grouping': 'income_group',
            'group': ig,
            'n_countries': len(grp),
            'mean_actual_tax': round(grp['tax_pct_gdp'].mean(), 2),
            'mean_predicted_tax': round(grp['predicted_tax'].mean(), 2),
            'mean_effort': round(grp['tax_effort'].mean(), 3),
            'mean_revenue_gap': round(grp['revenue_gap'].mean(), 2),
            'pct_underperforming': round(100 * (grp['tax_effort'] < 0.9).mean(), 1),
        })

    # By effort category
    for cat, grp in df_reg.groupby('effort_category', observed=True):
        summary_rows.append({
            'grouping': 'effort_category',
            'group': str(cat),
            'n_countries': len(grp),
            'mean_actual_tax': round(grp['tax_pct_gdp'].mean(), 2),
            'mean_predicted_tax': round(grp['predicted_tax'].mean(), 2),
            'mean_effort': round(grp['tax_effort'].mean(), 3),
            'mean_revenue_gap': round(grp['revenue_gap'].mean(), 2),
            'pct_underperforming': np.nan,
        })

    # Add OLS coefficients
    for name, b, s, t in zip(coef_names, beta, se, t_stats):
        summary_rows.append({
            'grouping': 'ols_coefficient',
            'group': name,
            'n_countries': n,
            'mean_actual_tax': round(b, 4),
            'mean_predicted_tax': round(s, 4),
            'mean_effort': round(t, 2),
            'mean_revenue_gap': round(r_squared, 4) if name == 'intercept' else np.nan,
            'pct_underperforming': np.nan,
        })

    summary_df = pd.DataFrame(summary_rows)
    write_single_sheet_excel(summary_df, out / "tax_effort_summary.xlsx",
                             sheet_name="Tax Effort Summary")

    # Log key findings
    overperformers = df_reg[df_reg['tax_effort'] > 1.3].sort_values('tax_effort', ascending=False)
    underperformers = df_reg[df_reg['tax_effort'] < 0.7].sort_values('tax_effort')
    logger.info(f"Overperformers (effort>1.3): {len(overperformers)} countries")
    if not overperformers.empty:
        logger.info(f"  Top: {overperformers.head(5)[['country_name', 'tax_effort', 'revenue_gap']].to_string(index=False)}")
    logger.info(f"Underperformers (effort<0.7): {len(underperformers)} countries")
    if not underperformers.empty:
        logger.info(f"  Bottom: {underperformers.head(5)[['country_name', 'tax_effort', 'revenue_gap']].to_string(index=False)}")

    logger.info(f"[{MANIFEST['id']}] Complete: {len(tax_effort_df)} countries, "
                f"R2={r_squared:.3f}, mean effort={df_reg['tax_effort'].mean():.3f}")


if __name__ == "__main__":
    run()
