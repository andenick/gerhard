"""
A50: Extended Structural Model — Simultaneous Equations
========================================================
The full 7-equation system with feedback: profit rate ↔ spending ↔ investment ↔ interest rates.
Estimation: 2SLS equation-by-equation, then counterfactual simulations.
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
    panel = build_kalecki_panel()
    if panel.empty:
        return pd.DataFrame()
    # Add lagged variables
    panel = panel.sort_values(['iso', 'year']).copy()
    for col in ['irr', 'debtgdp', 'expenditure_gdp', 'growth', 'iy']:
        if col in panel.columns:
            panel[f'{col}_lag1'] = panel.groupby('iso')[col].shift(1)
    return panel


def estimate_2sls_equation(panel: pd.DataFrame, dep_var: str, endog: list,
                           exog: list, instruments: list, name: str) -> dict:
    """Estimate one structural equation using 2SLS (manually)."""
    all_vars = [dep_var] + endog + exog + instruments
    available = [v for v in all_vars if v in panel.columns]
    valid = panel[['iso'] + [v for v in available if v in panel.columns]].dropna()

    if len(valid) < 100:
        return {'equation': name, 'status': 'insufficient_data'}

    # Demean for FE
    for col in [dep_var] + endog + exog:
        if col in valid.columns:
            valid[col] = valid.groupby('iso')[col].transform(lambda x: x - x.mean())

    y = valid[dep_var].values
    all_x = [c for c in endog + exog if c in valid.columns]
    X = valid[all_x].values

    # If we have instruments, do 2SLS; otherwise OLS
    inst_available = [c for c in instruments if c in valid.columns]
    if inst_available and endog:
        # Stage 1: regress endogenous on instruments + exog
        Z = valid[[c for c in inst_available + exog if c in valid.columns]].values
        Z_const = np.column_stack([np.ones(len(Z)), Z])

        # Predict endogenous
        X_hat = np.zeros_like(X)
        for i, col in enumerate(all_x):
            if col in endog:
                try:
                    beta_1st, _, _, _ = np.linalg.lstsq(Z_const, valid[col].values, rcond=None)
                    X_hat[:, i] = Z_const @ beta_1st
                except Exception:
                    X_hat[:, i] = valid[col].values
            else:
                X_hat[:, i] = valid[col].values

        # Stage 2: regress y on predicted X
        X_2sls = np.column_stack([np.ones(len(X_hat)), X_hat])
    else:
        X_2sls = np.column_stack([np.ones(len(X)), X])

    try:
        betas, _, _, _ = np.linalg.lstsq(X_2sls, y, rcond=None)
        y_hat = X_2sls @ betas
        ss_res = np.sum((y - y_hat)**2)
        ss_tot = np.sum((y - y.mean())**2)
        r2 = 1 - ss_res / ss_tot
        n, k = len(y), X_2sls.shape[1]
        se = np.sqrt(ss_res / (n - k) * np.diag(np.linalg.inv(X_2sls.T @ X_2sls)))

        result = {'equation': name, 'dep_var': dep_var, 'r_squared': r2, 'n_obs': n, 'status': 'ok'}
        for i, var_name in enumerate(['intercept'] + all_x):
            result[f'beta_{var_name}'] = betas[i]
            result[f'se_{var_name}'] = se[i]
            t = betas[i] / se[i]
            result[f'p_{var_name}'] = 2 * (1 - stats.t.cdf(abs(t), n - k))

        return result
    except Exception as e:
        return {'equation': name, 'status': f'failed: {e}'}


def estimate_full_system(panel: pd.DataFrame) -> pd.DataFrame:
    """Estimate all 7 equations of the structural system."""
    equations = [
        {
            'name': 'Eq1: Profit Rate (Kalecki)',
            'dep_var': 'irr',
            'endog': ['iy', 'deficit_gdp'],
            'exog': ['ca_gdp', 'labsh'],
            'instruments': ['iy_lag1', 'expenditure_gdp_lag1', 'growth_lag1'],
        },
        {
            'name': 'Eq2: Investment',
            'dep_var': 'iy',
            'endog': [],
            'exog': ['irr_lag1', 'real_rate', 'expenditure_gdp', 'growth_lag1'],
            'instruments': [],
        },
        {
            'name': 'Eq3: Government Expenditure',
            'dep_var': 'expenditure_gdp',
            'endog': [],
            'exog': ['debtgdp_lag1', 'growth', 'ltrate'],
            'instruments': [],
        },
        {
            'name': 'Eq4: Fiscal Balance',
            'dep_var': 'fiscal_balance_gdp',
            'endog': ['irr'],
            'exog': ['growth', 'debtgdp_lag1', 'expenditure_gdp'],
            'instruments': ['irr_lag1', 'ca_gdp'],
        },
        {
            'name': 'Eq5: Debt Accumulation',
            'dep_var': 'debtgdp',
            'endog': [],
            'exog': ['debtgdp_lag1', 'fiscal_balance_gdp', 'growth', 'real_rate'],
            'instruments': [],
        },
        {
            'name': 'Eq6: Interest Rate',
            'dep_var': 'ltrate',
            'endog': [],
            'exog': ['irr_lag1', 'stir', 'debtgdp', 'inflation'],
            'instruments': [],
        },
        {
            'name': 'Eq7: Labor Share',
            'dep_var': 'labsh',
            'endog': ['irr'],
            'exog': ['iy', 'growth'],
            'instruments': ['irr_lag1', 'debtgdp_lag1'],
        },
    ]

    results = []
    for eq in equations:
        result = estimate_2sls_equation(panel, **eq)
        results.append(result)

    return pd.DataFrame(results)


def compute_counterfactual_austerity(panel: pd.DataFrame, system: pd.DataFrame) -> pd.DataFrame:
    """Counterfactual: what if expenditure/GDP stayed at 1980 level?"""
    if panel.empty:
        return pd.DataFrame()

    # Get 1980 expenditure level per country
    ref = panel[panel['year'] == 1980].groupby('iso')['expenditure_gdp'].mean()
    if ref.empty:
        ref = panel[panel['year'] <= 1982].groupby('iso')['expenditure_gdp'].mean()

    # Actual vs counterfactual spending trajectory
    results = []
    for country, grp in panel[panel['year'] >= 1980].groupby('iso'):
        grp = grp.sort_values('year')
        ref_exp = ref.get(country, np.nan)
        if pd.isna(ref_exp):
            continue

        for _, row in grp.iterrows():
            actual_exp = row.get('expenditure_gdp', np.nan)
            if pd.isna(actual_exp):
                continue

            spending_gap = ref_exp - actual_exp  # Positive = austerity (spent less than 1980)

            # Use Kalecki coefficient (from A43: β_expenditure ≈ -0.12) to estimate profit impact
            kalecki_beta = -0.12  # From A43 first differences
            profit_impact = spending_gap * kalecki_beta  # How much lower is profit rate due to austerity?

            results.append({
                'iso': country, 'year': int(row['year']),
                'actual_expenditure': actual_exp,
                'counterfactual_expenditure': ref_exp,
                'spending_gap': spending_gap,
                'estimated_profit_impact': profit_impact,
                'actual_irr': row.get('irr', np.nan),
                'counterfactual_irr': row.get('irr', 0) - profit_impact,
            })

    return pd.DataFrame(results)


def compute_chain_multipliers(system: pd.DataFrame) -> pd.DataFrame:
    """Compute the total system multiplier from spending to profits through all channels."""
    if system.empty:
        return pd.DataFrame()

    # Extract key betas
    betas = {}
    for _, row in system.iterrows():
        eq_name = row['equation']
        for col in row.index:
            if col.startswith('beta_') and col != 'beta_intercept':
                var = col.replace('beta_', '')
                betas[f"{eq_name}|{var}"] = row[col]

    multipliers = []

    # Direct channel: spending → profit (Eq1 via deficit)
    direct = betas.get('Eq1: Profit Rate (Kalecki)|deficit_gdp', np.nan)
    multipliers.append({'channel': 'Direct: deficit → profit', 'multiplier': direct})

    # Investment channel: spending → demand → investment → profit
    inv_from_expend = betas.get('Eq2: Investment|expenditure_gdp', np.nan)
    profit_from_inv = betas.get('Eq1: Profit Rate (Kalecki)|iy', np.nan)
    if pd.notna(inv_from_expend) and pd.notna(profit_from_inv):
        indirect_inv = inv_from_expend * profit_from_inv
        multipliers.append({'channel': 'Investment: spend → invest → profit', 'multiplier': indirect_inv})

    # Interest rate channel: spending → debt → rate → investment → profit
    rate_from_debt = betas.get('Eq6: Interest Rate|debtgdp', np.nan)
    inv_from_rate = betas.get('Eq2: Investment|real_rate', np.nan)
    if pd.notna(rate_from_debt) and pd.notna(inv_from_rate) and pd.notna(profit_from_inv):
        indirect_rate = rate_from_debt * inv_from_rate * profit_from_inv
        multipliers.append({'channel': 'Rate: debt → rate → invest → profit', 'multiplier': indirect_rate})

    # Labor share channel: profit → labor share (feedback)
    labsh_from_irr = betas.get('Eq7: Labor Share|irr', np.nan)
    profit_from_labsh = betas.get('Eq1: Profit Rate (Kalecki)|labsh', 0)
    if pd.notna(labsh_from_irr) and pd.notna(profit_from_labsh):
        feedback = labsh_from_irr * profit_from_labsh
        multipliers.append({'channel': 'Feedback: profit → labsh → profit', 'multiplier': feedback})

    # Total
    total = sum(m['multiplier'] for m in multipliers if pd.notna(m['multiplier']))
    multipliers.append({'channel': 'TOTAL SYSTEM MULTIPLIER', 'multiplier': total})

    return pd.DataFrame(multipliers)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A50: EXTENDED STRUCTURAL MODEL")
    logger.info("=" * 80)

    panel = load_panel()
    if panel.empty:
        return {}

    logger.info(f"Panel: {len(panel)} obs, {panel['iso'].nunique()} countries")

    # Estimate full system
    system = estimate_full_system(panel)
    if not system.empty:
        write_single_sheet_excel(system, OUTPUT_DIR / "A50_system_estimates.xlsx", "System")
        logger.info("\n7-EQUATION STRUCTURAL SYSTEM:")
        for _, row in system.iterrows():
            if row['status'] != 'ok':
                logger.info(f"  {row['equation']}: {row['status']}")
                continue
            logger.info(f"\n  {row['equation']} (R²={row['r_squared']:.3f}, n={int(row['n_obs'])}):")
            for col in row.index:
                if col.startswith('beta_') and col != 'beta_intercept':
                    var = col.replace('beta_', '')
                    p_col = col.replace('beta_', 'p_')
                    p = row.get(p_col, 1)
                    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
                    logger.info(f"    {var:25s}: β={row[col]:+.4f}{sig}")

    # Chain multipliers
    multipliers = compute_chain_multipliers(system)
    if not multipliers.empty:
        write_single_sheet_excel(multipliers, OUTPUT_DIR / "A50_chain_multipliers.xlsx", "Multipliers")
        logger.info("\nSYSTEM CHAIN MULTIPLIERS:")
        for _, row in multipliers.iterrows():
            if pd.notna(row['multiplier']):
                logger.info(f"  {row['channel']:45s}: {row['multiplier']:+.4f}")

    # Austerity counterfactual
    counterfactual = compute_counterfactual_austerity(panel, system)
    if not counterfactual.empty:
        write_single_sheet_excel(counterfactual.head(50000), OUTPUT_DIR / "A50_counterfactual_austerity.xlsx", "Counterfactual")
        # Average austerity impact by decade
        counterfactual['decade'] = (counterfactual['year'] // 10) * 10
        by_decade = counterfactual.groupby('decade').agg({
            'spending_gap': 'mean', 'estimated_profit_impact': 'mean',
            'iso': 'count'
        }).reset_index().rename(columns={'iso': 'n_obs'})
        write_single_sheet_excel(by_decade, OUTPUT_DIR / "A50_counterfactual_decades.xlsx", "Decades")
        logger.info("\nAUSTERITY COUNTERFACTUAL (if spending stayed at 1980 level):")
        for _, row in by_decade.iterrows():
            logger.info(f"  {int(row['decade'])}s: avg spending gap={row['spending_gap']:+.3f}, "
                       f"profit impact={row['estimated_profit_impact']:+.4f}")

    logger.info("\n" + "=" * 80)
    logger.info("STRUCTURAL MODEL COMPLETE")
    logger.info("The full circular system: Profits ↔ Spending ↔ Investment ↔ Interest Rates")
    logger.info("=" * 80)
    logger.info("A50 COMPLETE")
    return {'equations': len(system)}


if __name__ == "__main__":
    run()
