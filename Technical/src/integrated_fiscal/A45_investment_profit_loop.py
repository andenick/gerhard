"""
A45: Investment-Profit Feedback Loop
======================================
Estimates: profits → investment → demand → profits (closed loop).
Tests profitability-led vs accelerator investment theories.
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


def load_panel():
    from integrated_fiscal.A43_kalecki_profit_equation import build_kalecki_panel
    return build_kalecki_panel()


def demean_fe(df, cols, group='iso'):
    """Apply within-transformation (country FE via demeaning)."""
    result = df.copy()
    for col in cols:
        result[col] = result.groupby(group)[col].transform(lambda x: x - x.mean())
    return result


def estimate_investment_equation(panel: pd.DataFrame) -> pd.DataFrame:
    """Eq 1: iy = f(irr(t-1), growth(t-1), real_rate, expend_gdp) + FE."""
    panel = panel.sort_values(['iso', 'year']).copy()
    panel['irr_lag1'] = panel.groupby('iso')['irr'].shift(1)
    panel['irr_lag2'] = panel.groupby('iso')['irr'].shift(2)
    panel['growth_lag1'] = panel.groupby('iso')['growth'].shift(1)

    specs = [
        ('Baseline: irr(t-1) + growth(t-1)', ['irr_lag1', 'growth_lag1']),
        ('+ real_rate', ['irr_lag1', 'growth_lag1', 'real_rate']),
        ('+ expenditure', ['irr_lag1', 'growth_lag1', 'real_rate', 'expenditure_gdp']),
        ('Profitability vs Accelerator', ['irr_lag1', 'irr_lag2', 'growth_lag1']),
    ]

    results = []
    for spec_name, x_cols in specs:
        valid_cols = ['iy'] + [c for c in x_cols if c in panel.columns]
        valid = panel[['iso'] + valid_cols].dropna()
        if len(valid) < 100:
            continue

        demeaned = demean_fe(valid, valid_cols)
        y = demeaned['iy'].values
        X_cols = [c for c in x_cols if c in demeaned.columns]
        X = demeaned[X_cols].values
        X_const = np.column_stack([np.ones(len(X)), X])

        try:
            betas, _, _, _ = np.linalg.lstsq(X_const, y, rcond=None)
            y_hat = X_const @ betas
            ss_res = np.sum((y - y_hat)**2)
            ss_tot = np.sum((y - y.mean())**2)
            r2 = 1 - ss_res / ss_tot
            n, k = len(y), X_const.shape[1]
            se = np.sqrt(ss_res / (n - k) * np.diag(np.linalg.inv(X_const.T @ X_const)))

            for i, name in enumerate(['intercept'] + X_cols):
                t_stat = betas[i] / se[i]
                p_val = 2 * (1 - stats.t.cdf(abs(t_stat), n - k))
                results.append({
                    'spec': spec_name, 'variable': name, 'beta': betas[i],
                    'se': se[i], 't_stat': t_stat, 'p_value': p_val,
                    'r_squared': r2, 'n_obs': n,
                })
        except Exception:
            continue

    return pd.DataFrame(results)


def estimate_profit_from_investment(panel: pd.DataFrame) -> pd.DataFrame:
    """Eq 2: irr = f(iy, expend_gdp, ca_gdp) + FE — closes the loop."""
    cols = ['irr', 'iy', 'expenditure_gdp', 'ca_gdp']
    available = [c for c in cols if c in panel.columns]
    valid = panel[['iso'] + available].dropna()
    if len(valid) < 100:
        return pd.DataFrame()

    demeaned = demean_fe(valid, available)
    y = demeaned['irr'].values
    X_cols = [c for c in available if c != 'irr']
    X = demeaned[X_cols].values
    X_const = np.column_stack([np.ones(len(X)), X])

    results = []
    try:
        betas, _, _, _ = np.linalg.lstsq(X_const, y, rcond=None)
        y_hat = X_const @ betas
        r2 = 1 - np.sum((y - y_hat)**2) / np.sum((y - y.mean())**2)
        n, k = len(y), X_const.shape[1]
        se = np.sqrt(np.sum((y - y_hat)**2) / (n - k) * np.diag(np.linalg.inv(X_const.T @ X_const)))

        for i, name in enumerate(['intercept'] + X_cols):
            t_stat = betas[i] / se[i]
            p_val = 2 * (1 - stats.t.cdf(abs(t_stat), n - k))
            results.append({'variable': name, 'beta': betas[i], 'se': se[i],
                          't_stat': t_stat, 'p_value': p_val, 'r_squared': r2, 'n_obs': n})
    except Exception:
        pass

    return pd.DataFrame(results)


def era_comparison(panel: pd.DataFrame) -> pd.DataFrame:
    """Did profit-investment sensitivity weaken under financialization?"""
    panel = panel.sort_values(['iso', 'year']).copy()
    panel['irr_lag1'] = panel.groupby('iso')['irr'].shift(1)

    eras = {'golden_age': (1950, 1973), 'neoliberal': (1983, 2007), 'post_gfc': (2008, 2019)}
    results = []

    for era_name, (start, end) in eras.items():
        era = panel[(panel['year'] >= start) & (panel['year'] <= end)]
        valid = era[['iy', 'irr_lag1']].dropna()
        if len(valid) < 30:
            continue
        slope, intercept, r, p, se = stats.linregress(valid['irr_lag1'], valid['iy'])
        results.append({
            'era': era_name, 'beta_irr_to_iy': slope, 'r_squared': r**2,
            'p_value': p, 'n_obs': len(valid),
        })

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A45: INVESTMENT-PROFIT FEEDBACK LOOP")
    logger.info("=" * 80)

    panel = load_panel()
    if panel.empty:
        return {}

    # Investment equation
    inv_eq = estimate_investment_equation(panel)
    if not inv_eq.empty:
        write_single_sheet_excel(inv_eq, OUTPUT_DIR / "A45_investment_equation.xlsx", "InvEq")
        logger.info("INVESTMENT EQUATION (iy = f(irr_lag, growth_lag, ...)):")
        for spec, grp in inv_eq.groupby('spec'):
            logger.info(f"\n  {spec}:")
            for _, row in grp.iterrows():
                sig = "***" if row['p_value'] < 0.001 else "**" if row['p_value'] < 0.01 else "*" if row['p_value'] < 0.05 else ""
                logger.info(f"    {row['variable']:20s}: β={row['beta']:+.4f}{sig}")
            logger.info(f"    R²={grp['r_squared'].iloc[0]:.3f}")

    # Profit from investment (closes loop)
    profit_eq = estimate_profit_from_investment(panel)
    if not profit_eq.empty:
        write_single_sheet_excel(profit_eq, OUTPUT_DIR / "A45_profit_from_investment.xlsx", "ProfitEq")
        logger.info("\nPROFIT FROM INVESTMENT (irr = f(iy, expend, ca)):")
        for _, row in profit_eq.iterrows():
            sig = "***" if row['p_value'] < 0.001 else "**" if row['p_value'] < 0.01 else "*" if row['p_value'] < 0.05 else ""
            logger.info(f"  {row['variable']:20s}: β={row['beta']:+.4f}{sig}")

    # Era comparison
    eras = era_comparison(panel)
    if not eras.empty:
        write_single_sheet_excel(eras, OUTPUT_DIR / "A45_era_comparison.xlsx", "Eras")
        logger.info("\nPROFIT→INVESTMENT SENSITIVITY BY ERA:")
        for _, row in eras.iterrows():
            sig = "***" if row['p_value'] < 0.001 else "*" if row['p_value'] < 0.05 else ""
            logger.info(f"  {row['era']:15s}: β={row['beta_irr_to_iy']:+.4f}{sig} R²={row['r_squared']:.3f}")

    logger.info("A45 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
