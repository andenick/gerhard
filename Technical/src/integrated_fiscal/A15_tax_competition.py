"""
A15: Global Tax Competition — Race to the Bottom
==================================================
Tests corporate tax rate convergence, revenue consequences, and the
substitution from corporate to consumption taxes.
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
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"


def load_oecd_wide() -> pd.DataFrame:
    """Load OECD wide revenue panel with tax categories as columns."""
    fpath = OECD_DIR / "oecd_revenue_wide.parquet"
    if not fpath.exists():
        # Try the full panel
        fpath = OECD_DIR / "oecd_revenue_panel.parquet"
        if not fpath.exists():
            return pd.DataFrame()
        df = pd.read_parquet(fpath)
        # Filter to % GDP and total government, then pivot
        if 'unit' in df.columns:
            gdp_units = [u for u in df['unit'].unique() if 'GDP' in str(u).upper() or u == df['unit'].unique()[0]]
            df = df[df['unit'].isin(gdp_units[:1])]
        if 'gov_level' in df.columns:
            total_govs = [g for g in df['gov_level'].unique() if 'S13' in str(g)]
            if total_govs:
                df = df[df['gov_level'].isin(total_govs)]
        pivot = df.pivot_table(index=['country_code', 'year'], columns='tax_category',
                              values='value', aggfunc='first').reset_index()
        pivot.columns.name = None
        return pivot

    return pd.read_parquet(fpath)


def analyze_corporate_rate_convergence(panel: pd.DataFrame) -> pd.DataFrame:
    """Track sigma-convergence of corporate tax revenue."""
    # T_1200 = Corporate income tax (% GDP)
    corp_col = 'T_1200' if 'T_1200' in panel.columns else None
    if not corp_col:
        corp_cols = [c for c in panel.columns if '1200' in c or 'corp' in c.lower()]
        corp_col = corp_cols[0] if corp_cols else None

    if not corp_col:
        logger.warning("No corporate tax column found")
        return pd.DataFrame()

    results = []
    for year in sorted(panel['year'].unique()):
        yr_data = panel[panel['year'] == year][corp_col].dropna()
        if len(yr_data) < 10:
            continue
        results.append({
            'year': year,
            'n_countries': len(yr_data),
            'corp_tax_mean': yr_data.mean(),
            'corp_tax_std': yr_data.std(),
            'corp_tax_cv': yr_data.std() / yr_data.mean() if yr_data.mean() > 0 else np.nan,
            'corp_tax_min': yr_data.min(),
            'corp_tax_max': yr_data.max(),
            'corp_tax_p25': yr_data.quantile(0.25),
            'corp_tax_p75': yr_data.quantile(0.75),
        })

    return pd.DataFrame(results)


def analyze_corporate_to_vat_shift(panel: pd.DataFrame) -> pd.DataFrame:
    """Test: as corporate tax fell, did VAT/consumption tax rise?"""
    corp_col = 'T_1200' if 'T_1200' in panel.columns else None
    vat_col = 'T_5110' if 'T_5110' in panel.columns else 'T_5111' if 'T_5111' in panel.columns else None
    cons_col = 'T_5000' if 'T_5000' in panel.columns else None

    use_col = vat_col or cons_col
    if not corp_col or not use_col:
        logger.warning(f"Missing columns: corp={corp_col}, vat/cons={use_col}")
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year')
        valid = grp[['year', corp_col, use_col]].dropna()
        if len(valid) < 15:
            continue

        # Correlation in levels
        corr_levels = valid[corp_col].corr(valid[use_col])

        # Correlation in changes
        changes = valid[[corp_col, use_col]].diff().dropna()
        corr_changes = changes[corp_col].corr(changes[use_col]) if len(changes) > 5 else np.nan

        # Early vs late comparison
        mid = valid['year'].median()
        early = valid[valid['year'] <= mid]
        late = valid[valid['year'] > mid]

        results.append({
            'country_code': country,
            'n_years': len(valid),
            'corp_tax_early': early[corp_col].mean(),
            'corp_tax_late': late[corp_col].mean(),
            'corp_change': late[corp_col].mean() - early[corp_col].mean(),
            'vat_early': early[use_col].mean(),
            'vat_late': late[use_col].mean(),
            'vat_change': late[use_col].mean() - early[use_col].mean(),
            'corr_levels': corr_levels,
            'corr_changes': corr_changes,
            'substitution': (late[corp_col].mean() < early[corp_col].mean()) and
                           (late[use_col].mean() > early[use_col].mean()),
        })

    return pd.DataFrame(results)


def analyze_revenue_laffer_test(panel: pd.DataFrame) -> pd.DataFrame:
    """Test: did corporate rate cuts increase total tax revenue? (Laffer curve)"""
    corp_col = 'T_1200' if 'T_1200' in panel.columns else None
    total_col = 'T_1000' if 'T_1000' in panel.columns else None

    if not corp_col:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year')
        valid = grp[['year', corp_col]].dropna()
        if len(valid) < 15:
            continue

        # Did revenue increase as the rate proxy (revenue/GDP) changed?
        # Note: with revenue data (not rate data), we test directly
        # If corp_tax/GDP fell over time: that's evidence AGAINST Laffer
        corp_trend = np.polyfit(valid['year'] - valid['year'].min(), valid[corp_col], 1)[0]

        # Peak and trough
        peak_year = valid.loc[valid[corp_col].idxmax(), 'year']
        peak_val = valid[corp_col].max()
        latest_val = valid[corp_col].iloc[-1]

        results.append({
            'country_code': country,
            'corp_revenue_trend': corp_trend,
            'corp_peak_year': int(peak_year),
            'corp_peak_value': peak_val,
            'corp_latest_value': latest_val,
            'corp_decline_from_peak': peak_val - latest_val,
            'laffer_works': corp_trend > 0,  # If revenue is rising, cutting didn't help
        })

    return pd.DataFrame(results)


def cross_with_profit_rate(panel: pd.DataFrame) -> pd.DataFrame:
    """Test Shaikh: is tax competition an equalization mechanism?"""
    pwt_path = PWT_DIR / "pwt_profit_rate_panel.parquet"
    if not pwt_path.exists():
        return pd.DataFrame()

    pwt = pd.read_parquet(pwt_path).rename(columns={'countrycode': 'country_code'})
    corp_col = 'T_1200' if 'T_1200' in panel.columns else None
    if not corp_col:
        return pd.DataFrame()

    merged = panel[['country_code', 'year', corp_col]].merge(
        pwt[['country_code', 'year', 'irr']], on=['country_code', 'year'], how='inner')

    if merged.empty:
        return pd.DataFrame()

    # After-tax profit rate proxy
    # Assume corp_tax/GDP ≈ effective_rate * profits/GDP
    # So effective_rate ≈ corp_tax_gdp / (irr * capital_share * GDP/GDP) — simplification
    # Better: just test correlation of corp_tax with irr

    results = []
    for country, grp in merged.groupby('country_code'):
        grp = grp.dropna(subset=['irr', corp_col])
        if len(grp) < 10:
            continue

        corr = grp['irr'].corr(grp[corp_col])
        results.append({
            'country_code': country,
            'corr_irr_corp_tax': corr,
            'avg_irr': grp['irr'].mean(),
            'avg_corp_tax': grp[corp_col].mean(),
            'n_years': len(grp),
        })

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A15: GLOBAL TAX COMPETITION")
    logger.info("=" * 80)

    panel = load_oecd_wide()
    if panel.empty:
        logger.error("No OECD data")
        return {}

    logger.info(f"OECD wide panel: {len(panel)} rows, {panel['country_code'].nunique()} countries")
    logger.info(f"Tax columns: {[c for c in panel.columns if c.startswith('T_')][:10]}")

    # Corporate rate convergence
    convergence = analyze_corporate_rate_convergence(panel)
    if not convergence.empty:
        write_single_sheet_excel(convergence, OUTPUT_DIR / "A15_corp_convergence.xlsx", "Convergence")
        if len(convergence) > 5:
            early_cv = convergence[convergence['year'] <= 1985]['corp_tax_cv'].mean()
            late_cv = convergence[convergence['year'] >= 2010]['corp_tax_cv'].mean()
            logger.info(f"Corporate tax CV: {early_cv:.3f} (pre-1985) → {late_cv:.3f} (post-2010)")

    # Corporate → VAT substitution
    substitution = analyze_corporate_to_vat_shift(panel)
    if not substitution.empty:
        write_single_sheet_excel(substitution, OUTPUT_DIR / "A15_corp_vat_substitution.xlsx", "Substitution")
        n_sub = substitution['substitution'].sum()
        logger.info(f"Corporate→VAT substitution: {n_sub}/{len(substitution)} countries")

    # Laffer test
    laffer = analyze_revenue_laffer_test(panel)
    if not laffer.empty:
        write_single_sheet_excel(laffer, OUTPUT_DIR / "A15_laffer_test.xlsx", "Laffer")
        n_laffer = laffer['laffer_works'].sum()
        logger.info(f"Laffer 'works' (revenue still rising): {n_laffer}/{len(laffer)} countries")
        avg_decline = laffer['corp_decline_from_peak'].mean()
        logger.info(f"Avg corporate tax decline from peak: {avg_decline:.2f} pp GDP")

    # Profit rate cross
    profit_cross = cross_with_profit_rate(panel)
    if not profit_cross.empty:
        write_single_sheet_excel(profit_cross, OUTPUT_DIR / "A15_profit_rate_cross.xlsx", "ProfitCross")
        avg_corr = profit_cross['corr_irr_corp_tax'].mean()
        logger.info(f"Avg correlation (profit rate vs corp tax revenue): {avg_corr:.3f}")

    logger.info("A15 COMPLETE")
    return {'countries': panel['country_code'].nunique()}


if __name__ == "__main__":
    run()
