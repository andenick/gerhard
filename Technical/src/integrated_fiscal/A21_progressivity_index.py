"""
A21: Tax Progressivity Index Panel
====================================
Constructs composite progressivity index for 100+ countries.
Combines ETR data, composition data, and structural features.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"


def load_all_sources():
    """Load GRD + Bachas + OECD for progressivity computation."""
    sources = {}

    # GRD
    grd_path = raw_data_dir() / "grd" / "grd_2025_all.parquet"
    if grd_path.exists():
        sources['grd'] = pd.read_parquet(grd_path)

    # Bachas ETR
    bachas_path = raw_data_dir() / "bachas_etr" / "globalETR_bfjz.csv"
    if bachas_path.exists():
        sources['bachas'] = pd.read_csv(bachas_path)

    return sources


def compute_progressivity_indicators(grd: pd.DataFrame) -> pd.DataFrame:
    """Compute progressivity proxy indicators from tax composition."""
    if grd.empty:
        return pd.DataFrame()

    results = []
    for (iso, year), grp in grd.groupby(['iso', 'year']):
        row = grp.iloc[0]
        entry = {'iso': iso, 'year': year, 'country': row.get('country', ''),
                'income_group': row.get('income_group', ''), 'region': row.get('region', '')}

        total = row.get('taxes_inc_sc', 0)
        if pd.isna(total) or total <= 0:
            continue

        pit = row.get('pit', 0) or 0
        cit = row.get('cit', 0) or 0
        ssc = row.get('social_contributions', 0) or 0
        gs = row.get('goods_services', 0) or 0
        trade = row.get('trade_taxes', 0) or 0
        prop = row.get('property_taxes', 0) or 0

        entry['total_tax_gdp'] = total
        entry['pit_gdp'] = pit
        entry['cit_gdp'] = cit
        entry['ssc_gdp'] = ssc
        entry['consumption_tax_gdp'] = gs + trade

        # Progressivity indicators:
        # 1. Direct/Indirect ratio (higher = more progressive)
        direct = pit + cit + prop
        indirect = gs + trade
        entry['direct_indirect_ratio'] = direct / indirect if indirect > 0 else np.nan

        # 2. PIT share of total (higher = more progressive)
        entry['pit_share'] = pit / total * 100

        # 3. CIT/PIT ratio (higher = capital taxed more relative to labor)
        entry['cit_pit_ratio'] = cit / pit if pit > 0 else np.nan

        # 4. SSC/total (higher = more payroll-dependent = less progressive)
        entry['ssc_share'] = ssc / total * 100

        # 5. Consumption share (higher = more regressive)
        entry['consumption_share'] = (gs + trade) / total * 100

        # 6. Composite progressivity index (simple weighted)
        # Higher = more progressive
        # PIT share (progressive) - consumption share (regressive) + CIT share (progressive)
        cit_share = cit / total * 100
        entry['progressivity_score'] = entry['pit_share'] + cit_share - entry['consumption_share']

        results.append(entry)

    return pd.DataFrame(results)


def merge_with_bachas(prog: pd.DataFrame, bachas: pd.DataFrame) -> pd.DataFrame:
    """Add Bachas ETR data where available."""
    if prog.empty or bachas.empty:
        return prog

    # Bachas uses 3-letter ISO in 'country' column
    country_col = 'country' if bachas['country'].str.len().mean() == 3 else 'country_name'
    bachas_sub = bachas[['country' if 'country' in bachas.columns else country_col,
                         'year', 'ETR_L', 'ETR_K']].copy()
    if country_col != 'country':
        bachas_sub = bachas_sub.rename(columns={country_col: 'iso'})
    else:
        bachas_sub = bachas_sub.rename(columns={'country': 'iso'})

    merged = prog.merge(bachas_sub, on=['iso', 'year'], how='left')

    # Where we have ETR data, compute better progressivity
    has_etr = merged['ETR_K'].notna() & merged['ETR_L'].notna()
    merged.loc[has_etr, 'etr_progressivity'] = (
        merged.loc[has_etr, 'ETR_K'] / merged.loc[has_etr, 'ETR_L']
    )

    return merged


def track_progressivity_over_time(panel: pd.DataFrame) -> pd.DataFrame:
    """Track how progressivity changed by decade and income group."""
    if panel.empty:
        return pd.DataFrame()

    panel = panel.copy()
    panel['decade'] = (panel['year'] // 10) * 10

    score_cols = ['progressivity_score', 'direct_indirect_ratio', 'pit_share',
                 'consumption_share', 'ssc_share']
    available = [c for c in score_cols if c in panel.columns]

    results = panel.groupby(['income_group', 'decade'])[available].mean().reset_index()
    return results


def rank_countries(panel: pd.DataFrame) -> pd.DataFrame:
    """Rank countries by progressivity (latest data)."""
    if panel.empty:
        return pd.DataFrame()

    latest = panel[panel['year'] >= panel['year'].max() - 2]
    avg = latest.groupby('iso').agg({
        'country': 'first', 'income_group': 'first', 'region': 'first',
        'progressivity_score': 'mean', 'direct_indirect_ratio': 'mean',
        'pit_share': 'mean', 'consumption_share': 'mean', 'total_tax_gdp': 'mean',
    }).reset_index()

    avg = avg.sort_values('progressivity_score', ascending=False).reset_index(drop=True)
    avg['rank'] = range(1, len(avg) + 1)
    return avg


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A21: TAX PROGRESSIVITY INDEX PANEL")
    logger.info("=" * 80)

    sources = load_all_sources()
    if 'grd' not in sources:
        logger.error("No GRD data")
        return {}

    # Compute indicators
    prog = compute_progressivity_indicators(sources['grd'])
    if prog.empty:
        return {}

    # Merge with Bachas ETR
    if 'bachas' in sources:
        prog = merge_with_bachas(prog, sources['bachas'])

    write_single_sheet_excel(prog.head(50000), OUTPUT_DIR / "A21_progressivity_panel.xlsx", "Panel")
    logger.info(f"Progressivity panel: {len(prog)} rows, {prog['iso'].nunique()} countries")

    # Time trends
    time_trends = track_progressivity_over_time(prog)
    if not time_trends.empty:
        write_single_sheet_excel(time_trends, OUTPUT_DIR / "A21_progressivity_trends.xlsx", "Trends")
        logger.info(f"Progressivity trends: {len(time_trends)} rows")

    # Rankings
    rankings = rank_countries(prog)
    if not rankings.empty:
        write_single_sheet_excel(rankings, OUTPUT_DIR / "A21_progressivity_rankings.xlsx", "Rankings")
        top5 = rankings.head(5)[['iso', 'country', 'progressivity_score']].to_string(index=False)
        bot5 = rankings.tail(5)[['iso', 'country', 'progressivity_score']].to_string(index=False)
        logger.info(f"Most progressive:\n{top5}")
        logger.info(f"Least progressive:\n{bot5}")

    logger.info("A21 COMPLETE")
    return {'countries': prog['iso'].nunique()}


if __name__ == "__main__":
    run()
