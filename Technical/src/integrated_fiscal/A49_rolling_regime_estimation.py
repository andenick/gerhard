"""
A49: Rolling Window Regime Estimation
=======================================
Endogenously identifies when the fiscal→profit relationship changed.
Rolling OLS, Chow tests, and regime-specific Kalecki coefficients.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from scipy import stats
from scipy.stats import f as f_dist

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"


def load_panel():
    from integrated_fiscal.A43_kalecki_profit_equation import build_kalecki_panel
    return build_kalecki_panel()


def rolling_ols_coefficients(panel: pd.DataFrame, window: int = 25) -> pd.DataFrame:
    """Rolling OLS: Δirr = β₁·Δexpend_gdp + β₂·Δiy + β₃·Δca_gdp, pooled across countries."""
    panel = panel.sort_values(['iso', 'year']).copy()

    # First differences
    for col in ['irr', 'expenditure_gdp', 'iy', 'ca_gdp', 'deficit_gdp']:
        if col in panel.columns:
            panel[f'd_{col}'] = panel.groupby('iso')[col].diff()

    diff_cols = ['d_irr', 'd_expenditure_gdp', 'd_iy', 'd_ca_gdp']
    available = [c for c in diff_cols if c in panel.columns]
    if len(available) < 3:
        return pd.DataFrame()

    years = sorted(panel['year'].unique())
    results = []

    for end_year in years:
        start_year = end_year - window
        window_data = panel[(panel['year'] >= start_year) & (panel['year'] <= end_year)]
        valid = window_data[available].dropna()

        if len(valid) < 50:
            continue

        y = valid['d_irr'].values
        x_cols = [c for c in available if c != 'd_irr']
        X = valid[x_cols].values
        X_const = np.column_stack([np.ones(len(X)), X])

        try:
            betas, _, _, _ = np.linalg.lstsq(X_const, y, rcond=None)
            y_hat = X_const @ betas
            ss_res = np.sum((y - y_hat)**2)
            ss_tot = np.sum((y - y.mean())**2)
            r2 = 1 - ss_res / ss_tot
            n, k = len(y), X_const.shape[1]
            se = np.sqrt(ss_res / (n - k) * np.diag(np.linalg.inv(X_const.T @ X_const)))

            row = {'end_year': end_year, 'start_year': start_year, 'n_obs': n, 'r_squared': r2}
            for i, name in enumerate(['intercept'] + x_cols):
                row[f'beta_{name}'] = betas[i]
                row[f'se_{name}'] = se[i]
                row[f'sig_{name}'] = abs(betas[i] / se[i]) > 1.96

            results.append(row)
        except Exception:
            continue

    return pd.DataFrame(results)


def chow_structural_break_test(panel: pd.DataFrame, break_year: int) -> dict:
    """Chow test for structural break at specified year."""
    panel = panel.sort_values(['iso', 'year']).copy()

    for col in ['irr', 'expenditure_gdp', 'iy', 'ca_gdp']:
        if col in panel.columns:
            panel[f'd_{col}'] = panel.groupby('iso')[col].diff()

    diff_cols = ['d_irr', 'd_expenditure_gdp', 'd_iy', 'd_ca_gdp']
    available = [c for c in diff_cols if c in panel.columns]
    if len(available) < 3:
        return {}

    valid = panel[['year'] + available].dropna()

    pre = valid[valid['year'] <= break_year]
    post = valid[valid['year'] > break_year]
    full = valid

    if len(pre) < 30 or len(post) < 30:
        return {}

    def ssr(data):
        y = data['d_irr'].values
        x_cols = [c for c in available if c != 'd_irr']
        X = np.column_stack([np.ones(len(y)), data[x_cols].values])
        try:
            betas, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            return np.sum((y - X @ betas)**2), len(y), X.shape[1]
        except Exception:
            return np.nan, 0, 0

    ssr_full, n_full, k = ssr(full)
    ssr_pre, n_pre, _ = ssr(pre)
    ssr_post, n_post, _ = ssr(post)

    if np.isnan(ssr_full) or np.isnan(ssr_pre) or np.isnan(ssr_post):
        return {}

    ssr_split = ssr_pre + ssr_post
    f_stat = ((ssr_full - ssr_split) / k) / (ssr_split / (n_full - 2 * k))
    p_value = 1 - f_dist.cdf(f_stat, k, n_full - 2 * k)

    return {
        'break_year': break_year, 'f_stat': f_stat, 'p_value': p_value,
        'significant': p_value < 0.05, 'n_pre': n_pre, 'n_post': n_post,
    }


def sequential_break_detection(panel: pd.DataFrame) -> pd.DataFrame:
    """Test breaks at every year — find the one with highest F-statistic."""
    years_to_test = range(1965, 2010)
    results = []
    for year in years_to_test:
        result = chow_structural_break_test(panel, year)
        if result:
            results.append(result)
    return pd.DataFrame(results)


def regime_specific_estimation(panel: pd.DataFrame, break_year: int) -> pd.DataFrame:
    """Estimate Kalecki equation separately for pre and post break."""
    panel = panel.sort_values(['iso', 'year']).copy()

    for col in ['irr', 'expenditure_gdp', 'iy', 'ca_gdp', 'deficit_gdp', 'labsh']:
        if col in panel.columns:
            panel[f'd_{col}'] = panel.groupby('iso')[col].diff()

    results = []
    for regime, data in [('pre_break', panel[panel['year'] <= break_year]),
                         ('post_break', panel[panel['year'] > break_year])]:
        cols = ['d_irr', 'd_expenditure_gdp', 'd_deficit_gdp', 'd_iy', 'd_ca_gdp']
        available = [c for c in cols if c in data.columns]
        valid = data[available].dropna()
        if len(valid) < 40:
            continue

        y = valid['d_irr'].values
        x_cols = [c for c in available if c != 'd_irr']
        X = np.column_stack([np.ones(len(y)), valid[x_cols].values])

        try:
            betas, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            y_hat = X @ betas
            r2 = 1 - np.sum((y - y_hat)**2) / np.sum((y - y.mean())**2)
            n, k = len(y), X.shape[1]
            se = np.sqrt(np.sum((y - y_hat)**2) / (n - k) * np.diag(np.linalg.inv(X.T @ X)))

            row = {'regime': regime, 'break_year': break_year, 'n_obs': n, 'r_squared': r2}
            for i, name in enumerate(['intercept'] + x_cols):
                row[f'beta_{name}'] = betas[i]
                t = betas[i] / se[i]
                row[f'p_{name}'] = 2 * (1 - stats.t.cdf(abs(t), n - k))
            results.append(row)
        except Exception:
            continue

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A49: ROLLING WINDOW REGIME ESTIMATION")
    logger.info("=" * 80)

    panel = load_panel()
    if panel.empty:
        return {}

    # Rolling OLS coefficients
    rolling = rolling_ols_coefficients(panel, window=25)
    if not rolling.empty:
        write_single_sheet_excel(rolling, OUTPUT_DIR / "A49_rolling_coefficients.xlsx", "Rolling")
        logger.info(f"Rolling coefficients: {len(rolling)} windows")

        # Key: when did the spending→profit coefficient change?
        if 'beta_d_expenditure_gdp' in rolling.columns:
            early = rolling[rolling['end_year'] <= 1985]['beta_d_expenditure_gdp'].mean()
            late = rolling[rolling['end_year'] >= 2000]['beta_d_expenditure_gdp'].mean()
            logger.info(f"Spending→profit β: {early:+.4f} (windows ending ≤1985) → {late:+.4f} (≥2000)")

    # Sequential break detection
    breaks = sequential_break_detection(panel)
    if not breaks.empty:
        write_single_sheet_excel(breaks, OUTPUT_DIR / "A49_break_detection.xlsx", "Breaks")
        # Find the strongest break
        best = breaks.loc[breaks['f_stat'].idxmax()]
        logger.info(f"\nStrongest structural break: {int(best['break_year'])} "
                   f"(F={best['f_stat']:.2f}, p={best['p_value']:.4f})")

        sig_breaks = breaks[breaks['significant']]
        logger.info(f"Significant breaks (p<0.05): years {sig_breaks['break_year'].tolist()}")

        # Regime-specific estimation at best break
        regime_est = regime_specific_estimation(panel, int(best['break_year']))
        if not regime_est.empty:
            write_single_sheet_excel(regime_est, OUTPUT_DIR / "A49_regime_estimates.xlsx", "Regimes")
            logger.info(f"\nRegime-specific Kalecki at break={int(best['break_year'])}:")
            for _, row in regime_est.iterrows():
                logger.info(f"  {row['regime']:12s}: β_expend={row.get('beta_d_expenditure_gdp',0):+.4f} "
                           f"β_deficit={row.get('beta_d_deficit_gdp',0):+.4f} R²={row['r_squared']:.3f}")

    # Also test pre-specified breaks
    preset_breaks = [1973, 1979, 1991, 2000, 2008]
    preset_results = []
    for year in preset_breaks:
        result = chow_structural_break_test(panel, year)
        if result:
            preset_results.append(result)
    preset_df = pd.DataFrame(preset_results)
    if not preset_df.empty:
        write_single_sheet_excel(preset_df, OUTPUT_DIR / "A49_preset_breaks.xlsx", "PresetBreaks")
        logger.info(f"\nPre-specified break tests:")
        for _, row in preset_df.iterrows():
            sig = "***" if row['p_value'] < 0.001 else "**" if row['p_value'] < 0.01 else "*" if row['p_value'] < 0.05 else ""
            logger.info(f"  {int(row['break_year'])}: F={row['f_stat']:.2f}{sig} (p={row['p_value']:.4f})")

    logger.info("A49 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
