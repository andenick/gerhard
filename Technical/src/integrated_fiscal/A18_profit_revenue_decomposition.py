"""
A18: Profit Rate → Tax Revenue Decomposition (THE DISSERTATION TEST)
=====================================================================
Decomposes how profit rate changes transmit into fiscal deterioration:
corporate tax channel, income tax channel, consumption tax channel.
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

OECD_DIR = raw_data_dir() / "oecd" / "revenue_stats"
PWT_DIR = raw_data_dir() / "profit_rates"
IMF_DIR = raw_data_dir() / "imf" / "gfs"
PSZ_DIR = raw_data_dir() / "us_dina"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"


def load_oecd_tax_components() -> pd.DataFrame:
    """Load OECD revenue by tax type (wide format)."""
    fpath = OECD_DIR / "oecd_revenue_wide.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    return pd.read_parquet(fpath)


def load_pwt() -> pd.DataFrame:
    fpath = PWT_DIR / "pwt_profit_rate_panel.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_parquet(fpath).rename(columns={'countrycode': 'country_code'})
    return df[['country_code', 'year', 'irr', 'labsh']].dropna(subset=['irr'])


def load_psz_taxrates() -> pd.DataFrame:
    """Load PSZ US tax rates by type."""
    fpath = PSZ_DIR / "PSZ2022_DistributionalSeries.xlsx"
    if not fpath.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(fpath, sheet_name="taxrates")
        return df
    except Exception:
        return pd.DataFrame()


def channel_decomposition_oecd(oecd: pd.DataFrame, pwt: pd.DataFrame) -> pd.DataFrame:
    """Regress each tax component on profit rate to identify transmission channels."""
    if oecd.empty or pwt.empty:
        return pd.DataFrame()

    # Key tax categories
    tax_channels = {
        'T_1200': 'corporate_tax',  # Corporate income tax → direct profit channel
        'T_1100': 'personal_income_tax',  # Individual income → employment/wage channel
        'T_2000': 'social_contributions',  # SSC → employment channel
        'T_5000': 'consumption_tax',  # VAT/goods → consumption/demand channel
        'T_1000': 'total_income_tax',  # All income taxes
    }

    available_channels = {k: v for k, v in tax_channels.items() if k in oecd.columns}
    if not available_channels:
        return pd.DataFrame()

    merged = oecd.merge(pwt, on=['country_code', 'year'], how='inner')
    if len(merged) < 50:
        return pd.DataFrame()

    logger.info(f"Merged OECD+PWT: {len(merged)} rows, {merged['country_code'].nunique()} countries")

    results = []
    for tax_code, channel_name in available_channels.items():
        # Panel regression: Δtax_component = α + β*Δirr + γ*controls + ε
        panel_data = merged[['country_code', 'year', tax_code, 'irr']].dropna()
        if len(panel_data) < 30:
            continue

        # Compute changes
        panel_data = panel_data.sort_values(['country_code', 'year'])
        panel_data['d_tax'] = panel_data.groupby('country_code')[tax_code].diff()
        panel_data['d_irr'] = panel_data.groupby('country_code')['irr'].diff()
        panel_data['irr_lag1'] = panel_data.groupby('country_code')['irr'].shift(1)

        valid = panel_data[['d_tax', 'd_irr', 'irr_lag1']].dropna()
        if len(valid) < 20:
            continue

        # Contemporaneous
        slope_contemp, _, r_contemp, p_contemp, _ = stats.linregress(valid['d_irr'], valid['d_tax'])

        # Lagged
        valid2 = panel_data[['d_tax', 'irr_lag1']].dropna()
        slope_lag, _, r_lag, p_lag, _ = stats.linregress(valid2['irr_lag1'], valid2['d_tax'])

        # Level correlation
        levels = panel_data[['irr', tax_code]].dropna()
        corr_levels = levels['irr'].corr(levels[tax_code])

        results.append({
            'channel': channel_name,
            'tax_code': tax_code,
            'n_obs': len(valid),
            'beta_contemporaneous': slope_contemp,
            'r2_contemporaneous': r_contemp ** 2,
            'p_contemporaneous': p_contemp,
            'beta_lagged': slope_lag,
            'r2_lagged': r_lag ** 2,
            'p_lagged': p_lag,
            'corr_levels': corr_levels,
            'significant_contemp': p_contemp < 0.05,
            'significant_lag': p_lag < 0.05,
        })

    return pd.DataFrame(results)


def us_107yr_decomposition(psz: pd.DataFrame, pwt: pd.DataFrame) -> pd.DataFrame:
    """Decompose US profit-fiscal relationship 1913-2019 using PSZ."""
    if psz.empty or pwt.empty:
        return pd.DataFrame()

    # Get US profit rate from PWT
    us_pwt = pwt[pwt['country_code'] == 'USA'][['year', 'irr']].copy()
    if us_pwt.empty:
        return pd.DataFrame()

    # PSZ has: taxall, corptaxall, ditaxall, paytaxall, salestaxall, proprestaxall, estatetaxall
    tax_types = {
        'taxall': 'total_effective_rate',
        'corptaxall': 'corporate_rate',
        'ditaxall': 'income_tax_rate',
        'paytaxall': 'payroll_rate',
        'salestaxall': 'sales_tax_rate',
        'proprestaxall': 'property_rate',
        'estatetaxall': 'estate_rate',
    }

    available = {k: v for k, v in tax_types.items() if k in psz.columns}
    if not available:
        return pd.DataFrame()

    psz_sub = psz[['year'] + list(available.keys())].copy()
    psz_sub = psz_sub.rename(columns=available)

    merged = psz_sub.merge(us_pwt, on='year', how='inner')
    if merged.empty:
        return pd.DataFrame()

    logger.info(f"US PSZ+PWT merged: {len(merged)} years ({merged['year'].min()}-{merged['year'].max()})")

    # Compute correlations and regressions for each tax type vs profit rate
    results = []
    for tax_name in available.values():
        valid = merged[['year', 'irr', tax_name]].dropna()
        if len(valid) < 20:
            continue

        # Level correlation
        corr = valid['irr'].corr(valid[tax_name])

        # Changes
        d_irr = valid['irr'].diff()
        d_tax = valid[tax_name].diff()
        both = pd.DataFrame({'d_irr': d_irr, 'd_tax': d_tax}).dropna()

        if len(both) > 10:
            slope, _, r, p, _ = stats.linregress(both['d_irr'], both['d_tax'])
        else:
            slope, r, p = np.nan, np.nan, np.nan

        # Era comparison
        pre_1980 = valid[valid['year'] <= 1980]
        post_1980 = valid[valid['year'] > 1980]

        results.append({
            'tax_type': tax_name,
            'corr_with_irr': corr,
            'beta_changes': slope,
            'r2_changes': r ** 2 if not np.isnan(r) else np.nan,
            'p_changes': p,
            'avg_pre_1980': pre_1980[tax_name].mean() if len(pre_1980) > 5 else np.nan,
            'avg_post_1980': post_1980[tax_name].mean() if len(post_1980) > 5 else np.nan,
            'change_1980': (post_1980[tax_name].mean() - pre_1980[tax_name].mean())
                if len(pre_1980) > 5 and len(post_1980) > 5 else np.nan,
        })

    return pd.DataFrame(results)


def cross_country_sensitivity(pwt: pd.DataFrame) -> pd.DataFrame:
    """How sensitive is each country's fiscal position to profit rate changes?"""
    imf_path = IMF_DIR / "imf_fiscal_wide_v2.parquet"
    if not imf_path.exists() or pwt.empty:
        return pd.DataFrame()

    imf = pd.read_parquet(imf_path)
    # Find revenue column
    rev_col = next((c for c in imf.columns if 'GGR' in c or 'G01_GDP' in c and 'X' not in c), None)
    if not rev_col:
        return pd.DataFrame()

    merged = imf[['country_code', 'year', rev_col]].merge(
        pwt, on=['country_code', 'year'], how='inner')
    merged = merged.rename(columns={rev_col: 'revenue_gdp'})

    if len(merged) < 50:
        return pd.DataFrame()

    results = []
    for country, grp in merged.groupby('country_code'):
        grp = grp.sort_values('year').dropna(subset=['irr', 'revenue_gdp'])
        if len(grp) < 10:
            continue

        # Regression: Δrevenue = α + β*Δirr
        d_rev = grp['revenue_gdp'].diff()
        d_irr = grp['irr'].diff()
        both = pd.DataFrame({'d_rev': d_rev, 'd_irr': d_irr}).dropna()
        if len(both) < 8:
            continue
        if both['d_irr'].std() == 0 or both['d_rev'].std() == 0:
            continue

        slope, _, r, p, _ = stats.linregress(both['d_irr'], both['d_rev'])
        results.append({
            'country_code': country,
            'n_years': len(both),
            'sensitivity_beta': slope,
            'sensitivity_r2': r ** 2,
            'sensitivity_p': p,
            'avg_irr': grp['irr'].mean(),
            'avg_revenue': grp['revenue_gdp'].mean(),
            'highly_sensitive': abs(slope) > 0.5 and p < 0.05,
        })

    return pd.DataFrame(results)


def policy_counterfactual(psz: pd.DataFrame) -> pd.DataFrame:
    """What if corporate tax rates hadn't been cut since their peak?"""
    if psz.empty:
        return pd.DataFrame()

    if 'corptaxall' not in psz.columns:
        return pd.DataFrame()

    psz = psz.copy()
    # Find peak corporate tax rate
    peak_idx = psz['corptaxall'].idxmax()
    peak_year = int(psz.loc[peak_idx, 'year'])
    peak_rate = psz.loc[peak_idx, 'corptaxall']

    logger.info(f"US corporate tax peak: {peak_rate:.1%} in {peak_year}")

    # Counterfactual: if rate stayed at peak level
    psz['corp_counterfactual'] = peak_rate
    psz['corp_revenue_loss'] = psz['corp_counterfactual'] - psz['corptaxall']
    psz['corp_revenue_loss'] = psz['corp_revenue_loss'].clip(lower=0)

    # Cumulative revenue lost since peak
    post_peak = psz[psz['year'] > peak_year].copy()
    if post_peak.empty:
        return pd.DataFrame()

    post_peak['cumulative_loss'] = post_peak['corp_revenue_loss'].cumsum()

    # Annual averages by decade
    post_peak['decade'] = (post_peak['year'] // 10) * 10
    decade_avg = post_peak.groupby('decade').agg({
        'corptaxall': 'mean',
        'corp_counterfactual': 'first',
        'corp_revenue_loss': 'mean',
        'cumulative_loss': 'last',
    }).reset_index()

    decade_avg['decade_revenue_loss_pct_national_income'] = decade_avg['corp_revenue_loss'] * 100

    return decade_avg


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A18: PROFIT RATE → TAX REVENUE DECOMPOSITION")
    logger.info("=" * 80)

    oecd = load_oecd_tax_components()
    pwt = load_pwt()
    psz = load_psz_taxrates()

    # Channel decomposition (OECD panel)
    channels = channel_decomposition_oecd(oecd, pwt)
    if not channels.empty:
        write_single_sheet_excel(channels, OUTPUT_DIR / "A18_channel_decomposition.xlsx", "Channels")
        logger.info("Channel decomposition:")
        for _, row in channels.iterrows():
            sig = "*" if row['significant_contemp'] else ""
            logger.info(f"  {row['channel']:25s}: β={row['beta_contemporaneous']:+.4f}{sig} "
                       f"(R²={row['r2_contemporaneous']:.3f})")

    # US 107-year decomposition
    us_decomp = us_107yr_decomposition(psz, pwt)
    if not us_decomp.empty:
        write_single_sheet_excel(us_decomp, OUTPUT_DIR / "A18_us_107yr_decomposition.xlsx", "US_Decomp")
        logger.info("\nUS 107-year decomposition:")
        for _, row in us_decomp.iterrows():
            logger.info(f"  {row['tax_type']:25s}: corr={row['corr_with_irr']:+.3f}, "
                       f"pre-1980={row.get('avg_pre_1980',0):.1%}, "
                       f"post-1980={row.get('avg_post_1980',0):.1%}")

    # Cross-country sensitivity
    sensitivity = cross_country_sensitivity(pwt)
    if not sensitivity.empty:
        write_single_sheet_excel(sensitivity, OUTPUT_DIR / "A18_cross_country_sensitivity.xlsx", "Sensitivity")
        n_sensitive = sensitivity['highly_sensitive'].sum()
        logger.info(f"\nCross-country revenue sensitivity to profit rate: "
                   f"{n_sensitive}/{len(sensitivity)} highly sensitive")
        avg_beta = sensitivity['sensitivity_beta'].mean()
        logger.info(f"Avg sensitivity β: {avg_beta:.3f} (1pp IRR change → {avg_beta:.3f}pp revenue change)")

    # Policy counterfactual
    counterfactual = policy_counterfactual(psz)
    if not counterfactual.empty:
        write_single_sheet_excel(counterfactual, OUTPUT_DIR / "A18_policy_counterfactual.xlsx", "Counterfactual")
        logger.info("\nUS corporate tax counterfactual (if rates hadn't been cut):")
        for _, row in counterfactual.iterrows():
            logger.info(f"  {int(row['decade'])}s: actual={row['corptaxall']:.1%}, "
                       f"counterfactual={row['corp_counterfactual']:.1%}, "
                       f"annual loss={row['corp_revenue_loss']:.1%} of national income")

    logger.info("\nA18 COMPLETE")
    return {'channels': len(channels), 'us_decomp': len(us_decomp)}


if __name__ == "__main__":
    run()
