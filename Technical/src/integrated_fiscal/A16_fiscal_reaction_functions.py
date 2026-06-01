"""
A16: Fiscal Reaction Functions
================================
Standard Bohn (1998) + Shaikh extension with profit rate.
Tests whether fiscal sustainability depends on profit rate regime.
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


def load_panel() -> pd.DataFrame:
    """Load merged fiscal + macro + profit panel."""
    imf_path = raw_data_dir() / "imf" / "gfs" / "imf_fiscal_wide_v2.parquet"
    wb_path = raw_data_dir() / "worldbank" / "macro" / "wb_macro_combined.csv"
    pwt_path = raw_data_dir() / "profit_rates" / "pwt_profit_rate_panel.parquet"

    dfs = []
    if imf_path.exists():
        imf = pd.read_parquet(imf_path)
        # Get fiscal balance and debt
        bal_col = next((c for c in imf.columns if 'GGXCNL' in c), None)
        debt_col = next((c for c in imf.columns if 'XWDG' in c and 'N' not in c.split('_')[-1]), None)
        if bal_col and debt_col:
            imf_sub = imf[['country_code', 'year', bal_col, debt_col]].rename(
                columns={bal_col: 'fiscal_balance', debt_col: 'debt_gdp'})
            dfs.append(imf_sub)

    if wb_path.exists():
        wb = pd.read_csv(wb_path)
        wb['year'] = pd.to_numeric(wb['year'], errors='coerce')
        dfs.append(wb[['country_code', 'year', 'gdp_growth']].dropna())

    if pwt_path.exists():
        pwt = pd.read_parquet(pwt_path).rename(columns={'countrycode': 'country_code'})
        dfs.append(pwt[['country_code', 'year', 'irr']].dropna())

    if not dfs:
        return pd.DataFrame()

    result = dfs[0]
    for df in dfs[1:]:
        result = result.merge(df, on=['country_code', 'year'], how='outer')

    result = result.dropna(subset=['country_code', 'year'])
    result['year'] = result['year'].astype(int)
    return result.sort_values(['country_code', 'year'])


def estimate_bohn_standard(panel: pd.DataFrame) -> pd.DataFrame:
    """Standard Bohn: fiscal_balance = α + β*debt(-1) + γ*growth + ε"""
    if 'fiscal_balance' not in panel.columns or 'debt_gdp' not in panel.columns:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year').copy()
        grp['debt_lag'] = grp['debt_gdp'].shift(1)

        cols = ['fiscal_balance', 'debt_lag']
        if 'gdp_growth' in grp.columns:
            cols.append('gdp_growth')

        valid = grp[cols].dropna()
        if len(valid) < 12:
            continue

        # Regression
        y = valid['fiscal_balance']
        X = valid[['debt_lag']]
        if 'gdp_growth' in valid.columns:
            X = valid[['debt_lag', 'gdp_growth']]

        # OLS manually
        X_const = np.column_stack([np.ones(len(X)), X.values])
        try:
            betas = np.linalg.lstsq(X_const, y.values, rcond=None)[0]
            y_hat = X_const @ betas
            residuals = y.values - y_hat
            r2 = 1 - np.sum(residuals**2) / np.sum((y.values - y.values.mean())**2)

            # Significance of debt coefficient
            n = len(y)
            k = X_const.shape[1]
            se = np.sqrt(np.sum(residuals**2) / (n - k) * np.diag(np.linalg.inv(X_const.T @ X_const)))
            t_stat = betas[1] / se[1]
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - k))

            results.append({
                'country_code': country,
                'n_years': len(valid),
                'beta_debt': betas[1],
                'beta_debt_t': t_stat,
                'beta_debt_p': p_value,
                'beta_growth': betas[2] if len(betas) > 2 else np.nan,
                'r_squared': r2,
                'sustainable': betas[1] > 0 and p_value < 0.05,
            })
        except Exception:
            continue

    return pd.DataFrame(results)


def estimate_shaikh_extended(panel: pd.DataFrame) -> pd.DataFrame:
    """Extended: fiscal_balance = α + β₁*debt(-1) + β₂*irr + β₃*growth + ε"""
    required = ['fiscal_balance', 'debt_gdp', 'irr']
    if not all(c in panel.columns for c in required):
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year').copy()
        grp['debt_lag'] = grp['debt_gdp'].shift(1)

        cols = ['fiscal_balance', 'debt_lag', 'irr']
        if 'gdp_growth' in grp.columns:
            cols.append('gdp_growth')

        valid = grp[cols].dropna()
        if len(valid) < 12:
            continue

        y = valid['fiscal_balance'].values
        x_cols = [c for c in cols if c != 'fiscal_balance']
        X = valid[x_cols].values
        X_const = np.column_stack([np.ones(len(X)), X])

        try:
            betas = np.linalg.lstsq(X_const, y, rcond=None)[0]
            y_hat = X_const @ betas
            residuals = y - y_hat
            r2 = 1 - np.sum(residuals**2) / np.sum((y - y.mean())**2)

            n, k = len(y), X_const.shape[1]
            se = np.sqrt(np.sum(residuals**2) / (n - k) * np.diag(np.linalg.inv(X_const.T @ X_const)))

            row = {
                'country_code': country, 'n_years': len(valid), 'r_squared': r2,
                'beta_intercept': betas[0],
            }
            for i, col in enumerate(x_cols):
                row[f'beta_{col}'] = betas[i + 1]
                row[f'se_{col}'] = se[i + 1]
                t = betas[i + 1] / se[i + 1]
                row[f'p_{col}'] = 2 * (1 - stats.t.cdf(abs(t), n - k))

            # Key tests
            row['profit_rate_significant'] = row.get('p_irr', 1) < 0.05
            row['profit_positive'] = row.get('beta_irr', 0) > 0
            results.append(row)
        except Exception:
            continue

    return pd.DataFrame(results)


def rolling_window_reaction(panel: pd.DataFrame, window: int = 15) -> pd.DataFrame:
    """Time-varying reaction function coefficients."""
    if 'fiscal_balance' not in panel.columns or 'debt_gdp' not in panel.columns:
        return pd.DataFrame()

    results = []
    # Pool all countries for each window
    years = sorted(panel['year'].unique())

    for end_year in years:
        start_year = end_year - window
        window_data = panel[(panel['year'] >= start_year) & (panel['year'] <= end_year)].copy()
        window_data['debt_lag'] = window_data.groupby('country_code')['debt_gdp'].shift(1)

        valid = window_data[['fiscal_balance', 'debt_lag']].dropna()
        if len(valid) < 30:
            continue

        slope, intercept, r, p, se = stats.linregress(valid['debt_lag'], valid['fiscal_balance'])
        results.append({
            'end_year': end_year,
            'window_start': start_year,
            'n_obs': len(valid),
            'beta_debt': slope,
            'beta_debt_p': p,
            'r_squared': r ** 2,
        })

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A16: FISCAL REACTION FUNCTIONS")
    logger.info("=" * 80)

    panel = load_panel()
    if panel.empty:
        logger.error("No data")
        return {}

    logger.info(f"Panel: {len(panel):,} rows, {panel['country_code'].nunique()} countries")
    logger.info(f"Variables: {[c for c in panel.columns if c not in ['country_code','year']]}")

    # Standard Bohn
    bohn = estimate_bohn_standard(panel)
    if not bohn.empty:
        write_single_sheet_excel(bohn, OUTPUT_DIR / "A16_bohn_standard.xlsx", "Bohn")
        n_sust = bohn['sustainable'].sum()
        logger.info(f"Bohn sustainable: {n_sust}/{len(bohn)} countries (β_debt > 0, p < 0.05)")
        logger.info(f"Avg β_debt: {bohn['beta_debt'].mean():.4f}")

    # Shaikh extended
    shaikh = estimate_shaikh_extended(panel)
    if not shaikh.empty:
        write_single_sheet_excel(shaikh, OUTPUT_DIR / "A16_shaikh_extended.xlsx", "ShaikhExtended")
        n_profit_sig = shaikh['profit_rate_significant'].sum()
        n_profit_pos = shaikh['profit_positive'].sum()
        logger.info(f"Profit rate significant: {n_profit_sig}/{len(shaikh)} countries")
        logger.info(f"Profit rate positive (revenue channel): {n_profit_pos}/{len(shaikh)}")
        if 'beta_irr' in shaikh.columns:
            logger.info(f"Avg β_irr: {shaikh['beta_irr'].mean():.4f}")

    # Rolling window
    rolling = rolling_window_reaction(panel)
    if not rolling.empty:
        write_single_sheet_excel(rolling, OUTPUT_DIR / "A16_rolling_reaction.xlsx", "Rolling")
        logger.info(f"Rolling window: {len(rolling)} year-windows")
        if len(rolling) > 5:
            early = rolling[rolling['end_year'] <= 2000]['beta_debt'].mean()
            late = rolling[rolling['end_year'] >= 2010]['beta_debt'].mean()
            logger.info(f"Avg β_debt: {early:.4f} (pre-2000) → {late:.4f} (post-2010)")

    logger.info("A16 COMPLETE")
    return {'bohn_countries': len(bohn) if not bohn.empty else 0}


if __name__ == "__main__":
    run()
