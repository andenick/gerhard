"""
A44: VAR Lag Structure — Spending, Deficits, and Profits
=========================================================
Estimates full dynamic lag structure: does spending Granger-cause profits?
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
    """Reuse A43's panel builder."""
    from integrated_fiscal.A43_kalecki_profit_equation import build_kalecki_panel
    return build_kalecki_panel()


def run_country_var(grp: pd.DataFrame, var_cols: list, max_lags: int = 3) -> dict:
    """Estimate VAR for a single country, return Granger causality + IRF."""
    from statsmodels.tsa.api import VAR as StatsVAR

    grp = grp.sort_values('year')
    data = grp[var_cols].dropna()
    if len(data) < 25:
        return {}

    try:
        model = StatsVAR(data.values)
        # Select lag order by BIC
        best_lag = 2
        best_bic = np.inf
        for lag in range(1, max_lags + 1):
            try:
                res = model.fit(lag)
                if res.bic < best_bic:
                    best_bic = res.bic
                    best_lag = lag
            except Exception:
                continue

        result = model.fit(best_lag)

        # Granger causality tests
        granger = {}
        for i, caused in enumerate(var_cols):
            for j, causing in enumerate(var_cols):
                if i == j:
                    continue
                try:
                    test = result.test_causality(caused, [causing], kind='f')
                    granger[f'{causing}→{caused}'] = {
                        'f_stat': test.test_statistic,
                        'p_value': test.pvalue,
                        'significant': test.pvalue < 0.05,
                    }
                except Exception:
                    pass

        # IRF: 10-period
        irf = result.irf(10)
        irf_data = {}
        for i, resp in enumerate(var_cols):
            for j, shock in enumerate(var_cols):
                irf_data[f'{shock}→{resp}'] = irf.irfs[:, i, j].tolist()

        return {
            'best_lag': best_lag, 'bic': best_bic,
            'granger': granger, 'irf': irf_data,
            'n_obs': len(data),
        }
    except Exception as e:
        return {'error': str(e)}


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A44: VAR LAG STRUCTURE")
    logger.info("=" * 80)

    panel = load_panel()
    if panel.empty:
        return {}

    var_cols = ['irr', 'expenditure_gdp', 'deficit_gdp', 'iy']
    available = [c for c in var_cols if c in panel.columns]
    if len(available) < 3:
        logger.error(f"Need at least 3 VAR variables, have: {available}")
        return {}

    logger.info(f"VAR variables: {available}")

    # Country-by-country VAR
    granger_results = []
    irf_results = []

    for country, grp in panel.groupby('iso'):
        result = run_country_var(grp, available)
        if not result or 'error' in result:
            continue

        # Granger causality
        for pair, test in result.get('granger', {}).items():
            granger_results.append({
                'iso': country, 'pair': pair, 'best_lag': result['best_lag'],
                **test
            })

        # IRF: spending → profit
        key_irf = f'expenditure_gdp→irr'
        if key_irf in result.get('irf', {}):
            for t, val in enumerate(result['irf'][key_irf]):
                irf_results.append({
                    'iso': country, 't': t, 'response': 'irr',
                    'shock': 'expenditure_gdp', 'value': val,
                })
        # IRF: profit → fiscal balance
        key_irf2 = f'irr→deficit_gdp'
        if key_irf2 in result.get('irf', {}):
            for t, val in enumerate(result['irf'][key_irf2]):
                irf_results.append({
                    'iso': country, 't': t, 'response': 'deficit_gdp',
                    'shock': 'irr', 'value': val,
                })

    # Granger results
    granger_df = pd.DataFrame(granger_results)
    if not granger_df.empty:
        write_single_sheet_excel(granger_df, OUTPUT_DIR / "A44_granger_causality.xlsx", "Granger")
        # Summary: how many countries show spending→profit causality?
        spend_to_profit = granger_df[granger_df['pair'] == 'expenditure_gdp→irr']
        if not spend_to_profit.empty:
            n_sig = spend_to_profit['significant'].sum()
            logger.info(f"\nGranger: expenditure→profit significant in {n_sig}/{len(spend_to_profit)} countries")

        profit_to_fiscal = granger_df[granger_df['pair'] == 'irr→deficit_gdp']
        if not profit_to_fiscal.empty:
            n_sig2 = profit_to_fiscal['significant'].sum()
            logger.info(f"Granger: profit→deficit significant in {n_sig2}/{len(profit_to_fiscal)} countries")

        # Full matrix summary
        summary = granger_df.groupby('pair')['significant'].agg(['sum', 'count']).reset_index()
        summary.columns = ['pair', 'n_significant', 'n_total']
        write_single_sheet_excel(summary, OUTPUT_DIR / "A44_granger_summary.xlsx", "Summary")
        logger.info(f"\nGranger causality summary:")
        for _, row in summary.iterrows():
            logger.info(f"  {row['pair']:30s}: {int(row['n_significant'])}/{int(row['n_total'])} countries")

    # IRF results
    irf_df = pd.DataFrame(irf_results)
    if not irf_df.empty:
        # Average IRF across countries
        avg_irf = irf_df.groupby(['t', 'shock', 'response'])['value'].agg(['mean', 'std', 'count']).reset_index()
        write_single_sheet_excel(avg_irf, OUTPUT_DIR / "A44_average_irf.xlsx", "IRF")

        # Key: spending→profit IRF
        sp_irf = avg_irf[(avg_irf['shock'] == 'expenditure_gdp') & (avg_irf['response'] == 'irr')]
        if not sp_irf.empty:
            logger.info(f"\nIRF: 1 unit spending shock → profit rate response:")
            for _, row in sp_irf.iterrows():
                logger.info(f"  t={int(row['t']):+2d}: {row['mean']:+.4f} (±{row['std']:.4f}, n={int(row['count'])})")

    logger.info("A44 COMPLETE")
    return {'countries': len(panel['iso'].unique())}


if __name__ == "__main__":
    run()
