"""
A46: Interest Rate Determination — The Endogenous Rate
========================================================
Models interest rates as DEPENDENT on profit rates (Shaikh gravitational hypothesis).
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
    result = df.copy()
    for col in cols:
        result[col] = result.groupby(group)[col].transform(lambda x: x - x.mean())
    return result


def estimate_rate_equations(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.sort_values(['iso', 'year']).copy()
    panel['irr_lag1'] = panel.groupby('iso')['irr'].shift(1)
    panel['r_minus_g'] = panel.get('real_rate', 0) - panel.get('growth', 0)

    specs = {
        'Eq1 Laubach (standard)': {'y': 'ltrate', 'x': ['debtgdp', 'growth', 'inflation']},
        'Eq2 Shaikh extension': {'y': 'ltrate', 'x': ['irr_lag1', 'debtgdp', 'stir', 'inflation']},
        'Eq3 Real rate': {'y': 'real_rate', 'x': ['irr_lag1', 'debtgdp', 'growth']},
        'Eq4 r-g spread': {'y': 'r_minus_g', 'x': ['irr_lag1', 'debtgdp', 'deficit_gdp']},
    }

    results = []
    for spec_name, spec in specs.items():
        y_col = spec['y']
        x_cols = [c for c in spec['x'] if c in panel.columns]
        if y_col not in panel.columns or len(x_cols) < 2:
            continue

        valid = panel[['iso', y_col] + x_cols].dropna()
        if len(valid) < 100:
            continue

        demeaned = demean_fe(valid, [y_col] + x_cols)
        y = demeaned[y_col].values
        X = demeaned[x_cols].values
        X_const = np.column_stack([np.ones(len(X)), X])

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
                results.append({
                    'equation': spec_name, 'dep_var': y_col,
                    'variable': name, 'beta': betas[i], 'se': se[i],
                    't_stat': t_stat, 'p_value': p_val,
                    'r_squared': r2, 'n_obs': n,
                })
        except Exception:
            continue

    return pd.DataFrame(results)


def era_rate_analysis(panel: pd.DataFrame) -> pd.DataFrame:
    """How did profit-rate-to-interest-rate pass-through change?"""
    panel = panel.sort_values(['iso', 'year']).copy()
    panel['irr_lag1'] = panel.groupby('iso')['irr'].shift(1)

    eras = {'golden_age': (1950, 1973), 'volcker': (1979, 1985),
            'great_moderation': (1986, 2007), 'zirp': (2008, 2019)}

    results = []
    for era_name, (start, end) in eras.items():
        era = panel[(panel['year'] >= start) & (panel['year'] <= end)]
        valid = era[['ltrate', 'irr_lag1']].dropna()
        if len(valid) < 20:
            continue
        slope, intercept, r, p, se = stats.linregress(valid['irr_lag1'], valid['ltrate'])
        results.append({
            'era': era_name, 'beta_irr_to_ltrate': slope,
            'r_squared': r**2, 'p_value': p, 'n_obs': len(valid),
            'avg_irr': era['irr'].mean(), 'avg_ltrate': era['ltrate'].mean(),
            'avg_real_rate': era['real_rate'].mean() if 'real_rate' in era else np.nan,
        })

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A46: INTEREST RATE DETERMINATION — ENDOGENOUS RATE")
    logger.info("=" * 80)

    panel = load_panel()
    if panel.empty:
        return {}

    # Rate equations
    equations = estimate_rate_equations(panel)
    if not equations.empty:
        write_single_sheet_excel(equations, OUTPUT_DIR / "A46_rate_equations.xlsx", "Equations")
        logger.info("INTEREST RATE EQUATIONS:")
        for eq, grp in equations.groupby('equation'):
            logger.info(f"\n  {eq} (dep={grp['dep_var'].iloc[0]}):")
            for _, row in grp.iterrows():
                sig = "***" if row['p_value'] < 0.001 else "**" if row['p_value'] < 0.01 else "*" if row['p_value'] < 0.05 else ""
                logger.info(f"    {row['variable']:15s}: β={row['beta']:+.4f}{sig}")
            logger.info(f"    R²={grp['r_squared'].iloc[0]:.3f}")

    # Era analysis
    eras = era_rate_analysis(panel)
    if not eras.empty:
        write_single_sheet_excel(eras, OUTPUT_DIR / "A46_era_rate_analysis.xlsx", "Eras")
        logger.info("\nPROFIT RATE → INTEREST RATE PASS-THROUGH BY ERA:")
        for _, row in eras.iterrows():
            sig = "***" if row['p_value'] < 0.001 else "*" if row['p_value'] < 0.05 else ""
            logger.info(f"  {row['era']:20s}: β={row['beta_irr_to_ltrate']:+.3f}{sig} "
                       f"(IRR={row['avg_irr']:.1%}, ltrate={row['avg_ltrate']:.1f}%)")

    logger.info("A46 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
