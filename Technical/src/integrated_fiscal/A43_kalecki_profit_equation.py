"""
A43: Kalecki-Levy Profit Equation — Direct Empirical Test
==========================================================
Tests: Profits = f(Investment, Government Deficit, Net Exports, Labor Share).
The REVERSE channel: does government spending DRIVE profits?
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


def build_kalecki_panel() -> pd.DataFrame:
    """Merge JST + PWT into Kalecki-ready panel."""
    jst_path = raw_data_dir() / "jst" / "JSTdatasetR6.parquet"
    pwt_path = raw_data_dir() / "profit_rates" / "pwt1001_full.parquet"

    if not jst_path.exists() or not pwt_path.exists():
        return pd.DataFrame()

    jst = pd.read_parquet(jst_path)
    pwt = pd.read_parquet(pwt_path)

    # JST: normalize fiscal variables to GDP
    jst = jst.sort_values(['iso', 'year']).copy()
    for col in ['revenue', 'expenditure', 'ca']:
        if col in jst.columns and 'gdp' in jst.columns:
            jst[f'{col}_gdp'] = jst[col] / jst['gdp']
    jst['fiscal_balance_gdp'] = jst.get('revenue_gdp', 0) - jst.get('expenditure_gdp', 0)
    jst['deficit_gdp'] = -jst['fiscal_balance_gdp']  # Positive deficit = positive Kalecki contribution
    if 'cpi' in jst.columns:
        jst['inflation'] = jst.groupby('iso')['cpi'].pct_change() * 100
    if 'ltrate' in jst.columns:
        jst['real_rate'] = jst['ltrate'] - jst.get('inflation', 0)
    if 'rgdpmad' in jst.columns:
        jst['growth'] = jst.groupby('iso')['rgdpmad'].pct_change() * 100
    jst['ca_gdp'] = jst.get('ca_gdp', jst.get('ca', 0) / jst.get('gdp', 1))
    jst = jst.replace([np.inf, -np.inf], np.nan)

    # PWT: get irr, labsh, csh_i, csh_g
    pwt_sub = pwt[['countrycode', 'year', 'irr', 'labsh', 'csh_i', 'csh_g', 'rkna', 'delta']].copy()
    pwt_sub = pwt_sub.rename(columns={'countrycode': 'iso'})

    # Merge
    merged = jst.merge(pwt_sub, on=['iso', 'year'], how='inner')
    merged = merged.replace([np.inf, -np.inf], np.nan)

    logger.info(f"Kalecki panel: {len(merged)} obs, {merged['iso'].nunique()} countries, "
               f"{merged['year'].min()}-{merged['year'].max()}")
    return merged


def estimate_kalecki_identity(panel: pd.DataFrame) -> pd.DataFrame:
    """Eq 1: irr = f(iy, deficit_gdp, ca_gdp, labsh) — the Kalecki identity test."""
    if panel.empty:
        return pd.DataFrame()

    results = []

    # Levels regression (with country FE via demeaning)
    cols = ['irr', 'iy', 'deficit_gdp', 'ca_gdp', 'labsh']
    valid = panel[['iso'] + cols].dropna()
    if len(valid) < 100:
        return pd.DataFrame()

    # Demean by country (within estimator)
    demeaned = valid.copy()
    for col in cols:
        demeaned[col] = demeaned.groupby('iso')[col].transform(lambda x: x - x.mean())

    from numpy.linalg import lstsq
    y = demeaned['irr'].values
    X = demeaned[['iy', 'deficit_gdp', 'ca_gdp', 'labsh']].values
    X_const = np.column_stack([np.ones(len(X)), X])

    try:
        betas, residuals, rank, sv = lstsq(X_const, y, rcond=None)
        y_hat = X_const @ betas
        ss_res = np.sum((y - y_hat)**2)
        ss_tot = np.sum((y - y.mean())**2)
        r2 = 1 - ss_res / ss_tot
        n, k = len(y), X_const.shape[1]

        se = np.sqrt(ss_res / (n - k) * np.diag(np.linalg.inv(X_const.T @ X_const)))

        names = ['intercept', 'iy', 'deficit_gdp', 'ca_gdp', 'labsh']
        for i, name in enumerate(names):
            t_stat = betas[i] / se[i]
            p_val = 2 * (1 - stats.t.cdf(abs(t_stat), n - k))
            results.append({
                'equation': 'Levels (within FE)',
                'variable': name, 'beta': betas[i], 'se': se[i],
                't_stat': t_stat, 'p_value': p_val,
                'r_squared': r2, 'n_obs': n,
            })
    except Exception as e:
        logger.warning(f"Levels regression failed: {e}")

    # First differences regression
    panel_sorted = panel.sort_values(['iso', 'year'])
    diff_cols = {col: panel_sorted.groupby('iso')[col].diff() for col in cols}
    diff_df = pd.DataFrame(diff_cols).dropna()

    if len(diff_df) > 100:
        y_d = diff_df['irr'].values
        X_d = diff_df[['iy', 'deficit_gdp', 'ca_gdp', 'labsh']].values
        X_d_const = np.column_stack([np.ones(len(X_d)), X_d])

        try:
            betas_d, _, _, _ = lstsq(X_d_const, y_d, rcond=None)
            y_hat_d = X_d_const @ betas_d
            ss_res_d = np.sum((y_d - y_hat_d)**2)
            ss_tot_d = np.sum((y_d - y_d.mean())**2)
            r2_d = 1 - ss_res_d / ss_tot_d
            n_d, k_d = len(y_d), X_d_const.shape[1]
            se_d = np.sqrt(ss_res_d / (n_d - k_d) * np.diag(np.linalg.inv(X_d_const.T @ X_d_const)))

            for i, name in enumerate(names):
                t_stat = betas_d[i] / se_d[i]
                p_val = 2 * (1 - stats.t.cdf(abs(t_stat), n_d - k_d))
                results.append({
                    'equation': 'First Differences',
                    'variable': name, 'beta': betas_d[i], 'se': se_d[i],
                    't_stat': t_stat, 'p_value': p_val,
                    'r_squared': r2_d, 'n_obs': n_d,
                })
        except Exception as e:
            logger.warning(f"Diff regression failed: {e}")

    return pd.DataFrame(results)


def spending_vs_revenue_decomposition(panel: pd.DataFrame) -> pd.DataFrame:
    """Eq 3: Δirr = γ₁·Δexpend_gdp + γ₂·Δrev_gdp + γ₃·Δiy + γ₄·Δca_gdp."""
    if panel.empty:
        return pd.DataFrame()

    panel_sorted = panel.sort_values(['iso', 'year'])
    diff_cols = ['irr', 'expenditure_gdp', 'revenue_gdp', 'iy', 'ca_gdp']
    available = [c for c in diff_cols if c in panel.columns]
    if len(available) < 4:
        return pd.DataFrame()

    diffs = {col: panel_sorted.groupby('iso')[col].diff() for col in available}
    diff_df = pd.DataFrame(diffs).dropna()

    if len(diff_df) < 50:
        return pd.DataFrame()

    y = diff_df['irr'].values
    x_cols = [c for c in available if c != 'irr']
    X = diff_df[x_cols].values
    X_const = np.column_stack([np.ones(len(X)), X])

    results = []
    try:
        betas, _, _, _ = np.linalg.lstsq(X_const, y, rcond=None)
        y_hat = X_const @ betas
        ss_res = np.sum((y - y_hat)**2)
        ss_tot = np.sum((y - y.mean())**2)
        r2 = 1 - ss_res / ss_tot
        n, k = len(y), X_const.shape[1]
        se = np.sqrt(ss_res / (n - k) * np.diag(np.linalg.inv(X_const.T @ X_const)))

        for i, name in enumerate(['intercept'] + x_cols):
            t_stat = betas[i] / se[i]
            p_val = 2 * (1 - stats.t.cdf(abs(t_stat), n - k))
            # Standardized beta (contribution)
            std_beta = betas[i] * diff_df[name].std() / diff_df['irr'].std() if i > 0 and name in diff_df else np.nan
            results.append({
                'variable': name, 'beta': betas[i], 'se': se[i],
                't_stat': t_stat, 'p_value': p_val,
                'std_beta': std_beta, 'r_squared': r2, 'n_obs': n,
            })
    except Exception as e:
        logger.warning(f"Spending decomposition failed: {e}")

    return pd.DataFrame(results)


def regime_kalecki(panel: pd.DataFrame) -> pd.DataFrame:
    """Estimate Kalecki coefficients within each era."""
    if panel.empty:
        return pd.DataFrame()

    eras = {
        'golden_age': (1950, 1973), 'stagflation': (1974, 1982),
        'neoliberal': (1983, 2007), 'post_gfc': (2008, 2019),
    }

    results = []
    for era_name, (start, end) in eras.items():
        era = panel[(panel['year'] >= start) & (panel['year'] <= end)]
        cols = ['irr', 'iy', 'deficit_gdp', 'ca_gdp', 'labsh']
        valid = era[cols].dropna()
        if len(valid) < 30:
            continue

        y = valid['irr'].values
        X = valid[['iy', 'deficit_gdp', 'ca_gdp', 'labsh']].values
        X_const = np.column_stack([np.ones(len(X)), X])

        try:
            betas, _, _, _ = np.linalg.lstsq(X_const, y, rcond=None)
            y_hat = X_const @ betas
            r2 = 1 - np.sum((y - y_hat)**2) / np.sum((y - y.mean())**2)

            results.append({
                'era': era_name, 'n_obs': len(valid), 'r_squared': r2,
                'beta_iy': betas[1], 'beta_deficit': betas[2],
                'beta_ca': betas[3], 'beta_labsh': betas[4],
            })
        except Exception:
            continue

    return pd.DataFrame(results)


def variance_decomposition(panel: pd.DataFrame) -> pd.DataFrame:
    """How much of Δirr variance is explained by each Kalecki component?"""
    if panel.empty:
        return pd.DataFrame()

    panel_sorted = panel.sort_values(['iso', 'year'])
    cols = ['irr', 'iy', 'deficit_gdp', 'ca_gdp', 'labsh']
    diffs = {col: panel_sorted.groupby('iso')[col].diff() for col in cols}
    diff_df = pd.DataFrame(diffs).dropna()

    if len(diff_df) < 50:
        return pd.DataFrame()

    total_var = diff_df['irr'].var()
    results = []
    for col in ['iy', 'deficit_gdp', 'ca_gdp', 'labsh']:
        corr = diff_df['irr'].corr(diff_df[col])
        # Marginal R² (bivariate)
        r2_marginal = corr ** 2
        results.append({
            'component': col,
            'correlation_with_dirr': corr,
            'marginal_r_squared': r2_marginal,
            'component_std': diff_df[col].std(),
            'dirr_std': diff_df['irr'].std(),
        })

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A43: KALECKI-LEVY PROFIT EQUATION")
    logger.info("=" * 80)

    panel = build_kalecki_panel()
    if panel.empty:
        return {}

    write_single_sheet_excel(panel.head(50000), OUTPUT_DIR / "A43_kalecki_panel.xlsx", "Panel")

    # Identity regression
    identity = estimate_kalecki_identity(panel)
    if not identity.empty:
        write_single_sheet_excel(identity, OUTPUT_DIR / "A43_identity_regression.xlsx", "Identity")
        logger.info("\nKALECKI IDENTITY REGRESSION:")
        for eq_name, grp in identity.groupby('equation'):
            logger.info(f"\n  {eq_name}:")
            for _, row in grp.iterrows():
                sig = "***" if row['p_value'] < 0.001 else "**" if row['p_value'] < 0.01 else "*" if row['p_value'] < 0.05 else ""
                logger.info(f"    {row['variable']:15s}: β={row['beta']:+.4f}{sig} (t={row['t_stat']:.2f})")
            logger.info(f"    R² = {grp['r_squared'].iloc[0]:.3f}, n = {int(grp['n_obs'].iloc[0])}")

    # Spending vs revenue decomposition
    decomp = spending_vs_revenue_decomposition(panel)
    if not decomp.empty:
        write_single_sheet_excel(decomp, OUTPUT_DIR / "A43_spending_decomposition.xlsx", "Decomp")
        logger.info("\nSPENDING vs REVENUE DECOMPOSITION:")
        for _, row in decomp.iterrows():
            sig = "***" if row['p_value'] < 0.001 else "**" if row['p_value'] < 0.01 else "*" if row['p_value'] < 0.05 else ""
            logger.info(f"  {row['variable']:20s}: β={row['beta']:+.4f}{sig} std_β={row.get('std_beta',0):.3f}")

    # Regime analysis
    regime = regime_kalecki(panel)
    if not regime.empty:
        write_single_sheet_excel(regime, OUTPUT_DIR / "A43_regime_kalecki.xlsx", "Regime")
        logger.info("\nKALECKI BY REGIME:")
        for _, row in regime.iterrows():
            logger.info(f"  {row['era']:15s}: β_deficit={row['beta_deficit']:+.4f} "
                       f"β_iy={row['beta_iy']:+.4f} β_labsh={row['beta_labsh']:+.4f} R²={row['r_squared']:.3f}")

    # Variance decomposition
    var_decomp = variance_decomposition(panel)
    if not var_decomp.empty:
        write_single_sheet_excel(var_decomp, OUTPUT_DIR / "A43_variance_decomposition.xlsx", "VarDecomp")
        logger.info("\nVARIANCE DECOMPOSITION (what drives Δirr?):")
        for _, row in var_decomp.iterrows():
            logger.info(f"  {row['component']:15s}: corr={row['correlation_with_dirr']:+.3f} "
                       f"R²={row['marginal_r_squared']:.3f}")

    logger.info("\nA43 COMPLETE")
    return {'panel_rows': len(panel)}


if __name__ == "__main__":
    run()
