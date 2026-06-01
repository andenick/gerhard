"""
A10: Debt Dynamics Decomposition
=================================
Decomposes changes in debt/GDP into: primary balance effect, snowball effect
(r-g), GDP growth effect, and stock-flow adjustment. Identifies which force
drives debt accumulation in different country groups and eras.

Data: WDI debt + national accounts + fiscal panels (200 countries, 1970-2024)
Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, processed_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

PROCESSED_DIR = processed_data_dir()
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_debt_and_macro() -> pd.DataFrame:
    """Load debt, fiscal, and national accounts data for decomposition."""
    from utils.paths import raw_data_dir
    panels = {}

    # Load freshly-downloaded macro data (GDP growth, debt/GDP, inflation)
    macro_dir = raw_data_dir() / "worldbank" / "macro"
    macro_combined = macro_dir / "wb_macro_combined.csv"
    if macro_combined.exists():
        macro = pd.read_csv(macro_combined)
        macro['year'] = pd.to_numeric(macro['year'], errors='coerce')
        panels['macro'] = macro
        logger.info(f"Loaded macro combined: {len(macro):,} rows, cols: {macro.columns.tolist()}")

    for name in ['wdi_debt_detail', 'wdi_fiscal_detail', 'wdi_national_accounts']:
        fpath = PROCESSED_DIR / f"{name}.xlsx"
        if fpath.exists():
            df = pd.read_excel(fpath)
            panels[name] = df
            logger.info(f"Loaded {name}: {len(df):,} rows")

    if not panels:
        logger.error("No panels found")
        return pd.DataFrame()

    for name, df in panels.items():
        logger.info(f"{name} columns: {df.columns.tolist()[:12]}")

    return panels


def find_columns(df: pd.DataFrame, keywords: list) -> str:
    """Find first column matching any keyword."""
    for kw in keywords:
        matches = [c for c in df.columns if kw.lower() in c.lower()]
        if matches:
            return matches[0]
    return None


def build_decomposition_panel(panels: dict) -> pd.DataFrame:
    """Build unified panel with debt, growth, and fiscal balance variables."""
    # Use freshly-downloaded macro data as primary source
    result_dfs = []

    # Macro combined has: country_code, year, gdp_growth, central_gov_debt_gdp, inflation_cpi, gdp_per_capita
    macro_df = panels.get('macro', pd.DataFrame())
    if not macro_df.empty and 'central_gov_debt_gdp' in macro_df.columns:
        subset = macro_df[['country_code', 'year']].copy()
        if 'central_gov_debt_gdp' in macro_df.columns:
            subset['debt_gdp'] = pd.to_numeric(macro_df['central_gov_debt_gdp'], errors='coerce')
        if 'gdp_growth' in macro_df.columns:
            subset['gdp_growth'] = pd.to_numeric(macro_df['gdp_growth'], errors='coerce')
        if 'inflation_cpi' in macro_df.columns:
            subset['inflation'] = pd.to_numeric(macro_df['inflation_cpi'], errors='coerce')
        subset = subset.dropna(subset=['country_code', 'year'])
        subset['year'] = subset['year'].astype(int)
        result_dfs.append(subset)
        logger.info(f"Macro panel contributes: debt for {subset['debt_gdp'].notna().sum()}, "
                   f"growth for {subset['gdp_growth'].notna().sum()} obs")

    # Also get fiscal balance from wdi_fiscal_detail
    for name, df in panels.items():
        if df.empty or name == 'macro':
            continue

        cc_col = find_columns(df, ['country_code', 'iso3', 'country'])
        yr_col = find_columns(df, ['year'])

        if not cc_col or not yr_col:
            continue

        df = df.rename(columns={cc_col: 'country_code', yr_col: 'year'})
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df = df.dropna(subset=['year'])
        df['year'] = df['year'].astype(int)

        if 'fiscal' in name:
            rev_col = find_columns(df, ['revenue', 'GC.REV', 'tax_rev'])
            exp_col = find_columns(df, ['expense', 'GC.XPN', 'expenditure'])
            if rev_col and exp_col:
                subset = df[['country_code', 'year', rev_col, exp_col]].copy()
                subset = subset.rename(columns={rev_col: 'revenue_gdp', exp_col: 'expense_gdp'})
                subset['revenue_gdp'] = pd.to_numeric(subset['revenue_gdp'], errors='coerce')
                subset['expense_gdp'] = pd.to_numeric(subset['expense_gdp'], errors='coerce')
                subset['fiscal_balance'] = subset['revenue_gdp'] - subset['expense_gdp']
                result_dfs.append(subset)

    if not result_dfs:
        return pd.DataFrame()

    # Merge all on country_code + year
    merged = result_dfs[0]
    for df in result_dfs[1:]:
        merged = merged.merge(df, on=['country_code', 'year'], how='outer')

    merged = merged.sort_values(['country_code', 'year']).reset_index(drop=True)
    # Remove aggregates (keep only 3-letter country codes)
    merged = merged[merged['country_code'].str.len() <= 3]

    logger.info(f"Decomposition panel: {len(merged):,} rows, {merged['country_code'].nunique()} countries")
    logger.info(f"Variables available: {[c for c in merged.columns if c not in ['country_code', 'year']]}")
    return merged


def decompose_debt_changes(panel: pd.DataFrame) -> pd.DataFrame:
    """Standard debt dynamics decomposition:

    Δd = (r-g)/(1+g) * d(-1) - pb + sfa

    Where:
    - d = debt/GDP
    - r = effective interest rate on debt
    - g = nominal GDP growth
    - pb = primary balance/GDP
    - sfa = stock-flow adjustment (residual)

    Without explicit interest rates, decompose into:
    - Growth effect: -g/(1+g) * d(-1)   [GDP growth eroding debt ratio]
    - Primary balance: -pb               [fiscal effort]
    - Residual: everything else (interest + SFA + valuation)
    """
    if 'debt_gdp' not in panel.columns:
        logger.warning("No debt_gdp column — cannot decompose")
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year').copy()
        if len(grp) < 5:
            continue

        grp['debt_change'] = grp['debt_gdp'].diff()
        grp['debt_lag'] = grp['debt_gdp'].shift(1)

        for idx in range(1, len(grp)):
            row = grp.iloc[idx]
            prev = grp.iloc[idx - 1]

            debt_change = row.get('debt_change')
            debt_lag = prev.get('debt_gdp')

            if pd.isna(debt_change) or pd.isna(debt_lag):
                continue

            # Growth effect
            g = row.get('gdp_growth')
            if pd.notna(g):
                g_decimal = g / 100 if abs(g) > 1 else g
                growth_effect = -g_decimal / (1 + g_decimal) * debt_lag
            else:
                growth_effect = np.nan

            # Primary balance effect
            pb = row.get('fiscal_balance')
            pb_effect = -pb if pd.notna(pb) else np.nan

            # Residual (captures interest + stock-flow adjustment)
            if pd.notna(growth_effect) and pd.notna(pb_effect):
                residual = debt_change - growth_effect - pb_effect
            else:
                residual = np.nan

            results.append({
                'country_code': country,
                'year': int(row['year']),
                'debt_gdp': row['debt_gdp'],
                'debt_change': debt_change,
                'growth_effect': growth_effect,
                'primary_balance_effect': pb_effect,
                'residual_interest_sfa': residual,
                'gdp_growth': g,
                'fiscal_balance': pb,
            })

    return pd.DataFrame(results)


def summarize_decomposition_by_era(decomp: pd.DataFrame) -> pd.DataFrame:
    """Summarize debt drivers by era."""
    if decomp.empty:
        return pd.DataFrame()

    eras = {
        'pre_oil_crisis': (1970, 1973),
        'stagflation': (1974, 1982),
        'great_moderation': (1983, 2007),
        'gfc': (2008, 2012),
        'low_rates': (2013, 2019),
        'pandemic': (2020, 2024),
    }

    decomp = decomp.copy()
    decomp['era'] = 'other'
    for era_name, (start, end) in eras.items():
        mask = (decomp['year'] >= start) & (decomp['year'] <= end)
        decomp.loc[mask, 'era'] = era_name

    driver_cols = ['debt_change', 'growth_effect', 'primary_balance_effect', 'residual_interest_sfa']
    available = [c for c in driver_cols if c in decomp.columns]

    results = decomp[decomp['era'] != 'other'].groupby('era')[available].agg(
        ['mean', 'median', 'std', 'count']).reset_index()
    results.columns = ['_'.join(c).strip('_') for c in results.columns]

    return results


def identify_debt_explosions(decomp: pd.DataFrame) -> pd.DataFrame:
    """Identify episodes where debt/GDP rose rapidly (>10pp in 3 years)."""
    if decomp.empty:
        return pd.DataFrame()

    episodes = []
    for country, grp in decomp.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 5:
            continue

        # Rolling 3-year debt change
        grp = grp.copy()
        grp['debt_3yr_change'] = grp['debt_gdp'].diff(3)

        explosions = grp[grp['debt_3yr_change'] > 10]
        for _, row in explosions.iterrows():
            # What drove it?
            window = grp[(grp['year'] >= row['year'] - 2) & (grp['year'] <= row['year'])]
            episodes.append({
                'country_code': country,
                'year': int(row['year']),
                'debt_3yr_change': row['debt_3yr_change'],
                'debt_level': row['debt_gdp'],
                'avg_growth_effect': window['growth_effect'].mean(),
                'avg_pb_effect': window['primary_balance_effect'].mean(),
                'avg_residual': window['residual_interest_sfa'].mean(),
                'primary_driver': _identify_primary_driver(window),
            })

    return pd.DataFrame(episodes)


def _identify_primary_driver(window: pd.DataFrame) -> str:
    """Identify which decomposition component drove the debt increase."""
    drivers = {
        'growth_collapse': window['growth_effect'].mean() if 'growth_effect' in window else 0,
        'fiscal_deficit': window['primary_balance_effect'].mean() if 'primary_balance_effect' in window else 0,
        'interest_burden': window['residual_interest_sfa'].mean() if 'residual_interest_sfa' in window else 0,
    }
    # Filter out NaN
    drivers = {k: v for k, v in drivers.items() if pd.notna(v)}
    if not drivers:
        return 'unknown'
    return max(drivers, key=lambda k: abs(drivers[k]))


def compute_debt_sustainability_zones(panel: pd.DataFrame) -> pd.DataFrame:
    """Classify country-years into debt sustainability zones.

    Zone A (Safe): debt < 60%, declining or stable
    Zone B (Caution): debt 60-90%, or rising fast
    Zone C (Danger): debt > 90%, or rising > 5pp/year
    Zone D (Crisis): debt > 120%, or rising > 10pp/year
    """
    if 'debt_gdp' not in panel.columns:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 3:
            continue

        grp = grp.copy()
        grp['debt_change'] = grp['debt_gdp'].diff()
        grp['debt_trend_3yr'] = grp['debt_gdp'].rolling(3).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 3 else np.nan)

        for _, row in grp.iterrows():
            debt = row['debt_gdp']
            change = row.get('debt_change', np.nan)
            trend = row.get('debt_trend_3yr', np.nan)

            if pd.isna(debt):
                continue

            if debt > 120 or (pd.notna(change) and change > 10):
                zone = 'D_crisis'
            elif debt > 90 or (pd.notna(change) and change > 5):
                zone = 'C_danger'
            elif debt > 60 or (pd.notna(trend) and trend > 2):
                zone = 'B_caution'
            else:
                zone = 'A_safe'

            results.append({
                'country_code': country,
                'year': int(row['year']),
                'debt_gdp': debt,
                'debt_change': change,
                'zone': zone,
            })

    return pd.DataFrame(results)


def run() -> dict:
    """Execute full debt dynamics decomposition."""
    logger.info("=" * 80)
    logger.info("A10: DEBT DYNAMICS DECOMPOSITION")
    logger.info("=" * 80)

    panels = load_debt_and_macro()
    if not panels:
        return {}

    merged = build_decomposition_panel(panels)
    if merged.empty:
        logger.error("Could not build decomposition panel")
        return {}

    write_single_sheet_excel(merged, OUTPUT_DIR / "A10_debt_macro_panel.xlsx", "Panel")
    logger.info(f"Wrote base panel: {len(merged):,} rows")

    # Decomposition
    decomp = decompose_debt_changes(merged)
    if not decomp.empty:
        write_single_sheet_excel(decomp, OUTPUT_DIR / "A10_debt_decomposition.xlsx", "Decomposition")
        logger.info(f"Debt decomposition: {len(decomp):,} obs")

        # By era
        era_summary = summarize_decomposition_by_era(decomp)
        if not era_summary.empty:
            write_single_sheet_excel(era_summary, OUTPUT_DIR / "A10_decomp_by_era.xlsx", "Eras")
            logger.info(f"Era summary: {len(era_summary)} era-groups")

        # Explosions
        explosions = identify_debt_explosions(decomp)
        if not explosions.empty:
            write_single_sheet_excel(explosions, OUTPUT_DIR / "A10_debt_explosions.xlsx", "Explosions")
            logger.info(f"Debt explosions (>10pp/3yr): {len(explosions)} episodes")

    # Sustainability zones
    zones = compute_debt_sustainability_zones(merged)
    if not zones.empty:
        write_single_sheet_excel(zones, OUTPUT_DIR / "A10_sustainability_zones.xlsx", "Zones")
        zone_dist = zones.groupby(['year', 'zone']).size().unstack(fill_value=0)
        logger.info(f"Sustainability zones: {len(zones):,} obs")
        # Latest year distribution
        latest_year = zones['year'].max()
        latest = zones[zones['year'] == latest_year]['zone'].value_counts()
        logger.info(f"Latest ({latest_year}) zone distribution: {latest.to_dict()}")

    logger.info("A10 COMPLETE")
    return {'decomp_obs': len(decomp) if not decomp.empty else 0}


if __name__ == "__main__":
    run()
