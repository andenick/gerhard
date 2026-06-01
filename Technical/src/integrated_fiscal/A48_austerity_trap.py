"""
A48: The Austerity Trap
========================
Identifies consolidation episodes, tests whether spending cuts damage profits,
and classifies episodes as successful vs doom-loop.
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


def identify_consolidation_episodes(panel: pd.DataFrame) -> pd.DataFrame:
    """Find episodes where expenditure/GDP fell ≥1pp over 2+ years (non-crisis)."""
    panel = panel.sort_values(['iso', 'year']).copy()
    panel['d_expend'] = panel.groupby('iso')['expenditure_gdp'].diff()

    episodes = []
    for country, grp in panel.groupby('iso'):
        grp = grp.sort_values('year')
        i = 0
        while i < len(grp) - 1:
            row = grp.iloc[i]
            if pd.isna(row.get('d_expend')) or row.get('crisisJST', 0) == 1:
                i += 1
                continue
            # Look for 2+ consecutive years of spending decline
            if row['d_expend'] < -0.005:  # >0.5pp decline
                j = i + 1
                while j < len(grp) and grp.iloc[j].get('d_expend', 0) < 0:
                    j += 1
                duration = j - i
                if duration >= 2:
                    total_cut = grp.iloc[i:j]['d_expend'].sum()
                    episodes.append({
                        'iso': country,
                        'start_year': int(grp.iloc[i]['year']),
                        'end_year': int(grp.iloc[j-1]['year']),
                        'duration': duration,
                        'total_cut': total_cut,
                        'irr_at_start': grp.iloc[i].get('irr', np.nan),
                        'debtgdp_at_start': grp.iloc[i].get('debtgdp', np.nan),
                    })
                    i = j
                else:
                    i += 1
            else:
                i += 1

    df = pd.DataFrame(episodes)
    logger.info(f"Consolidation episodes found: {len(df)}")
    return df


def classify_episodes(episodes: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Classify: successful, trap, or expansionary."""
    if episodes.empty or panel.empty:
        return episodes

    panel = panel.sort_values(['iso', 'year'])
    results = []

    for _, ep in episodes.iterrows():
        country = ep['iso']
        start = ep['start_year']
        end = ep['end_year']

        # Pre-period (2 years before)
        pre = panel[(panel['iso'] == country) & (panel['year'] >= start - 2) & (panel['year'] < start)]
        # Post-period (3 years after)
        post = panel[(panel['iso'] == country) & (panel['year'] > end) & (panel['year'] <= end + 3)]

        row = ep.to_dict()

        if not pre.empty and not post.empty:
            # Profit rate change
            irr_pre = pre['irr'].mean()
            irr_post = post['irr'].mean()
            row['irr_pre'] = irr_pre
            row['irr_post'] = irr_post
            row['irr_change'] = irr_post - irr_pre

            # Revenue change
            if 'revenue_gdp' in pre.columns:
                rev_pre = pre['revenue_gdp'].mean()
                rev_post = post['revenue_gdp'].mean()
                row['rev_change'] = rev_post - rev_pre

            # Fiscal balance change
            if 'fiscal_balance_gdp' in pre.columns:
                bal_pre = pre['fiscal_balance_gdp'].mean()
                bal_post = post['fiscal_balance_gdp'].mean()
                row['balance_change'] = bal_post - bal_pre
                row['balance_improved'] = bal_post > bal_pre

            # Growth
            if 'growth' in pre.columns:
                row['growth_pre'] = pre['growth'].mean()
                row['growth_post'] = post['growth'].mean()

            # Classification
            profit_fell = row.get('irr_change', 0) < -0.005
            revenue_fell = row.get('rev_change', 0) < -0.005
            balance_improved = row.get('balance_improved', False)

            if not profit_fell and balance_improved:
                row['classification'] = 'successful'
            elif profit_fell and revenue_fell and not balance_improved:
                row['classification'] = 'austerity_trap'
            elif not profit_fell and row.get('growth_post', 0) > row.get('growth_pre', 0):
                row['classification'] = 'expansionary'
            elif profit_fell:
                row['classification'] = 'profit_damaging'
            else:
                row['classification'] = 'ambiguous'

        results.append(row)

    return pd.DataFrame(results)


def event_study(episodes: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Average variable paths around consolidation episodes."""
    if episodes.empty or panel.empty:
        return pd.DataFrame()

    panel = panel.sort_values(['iso', 'year'])
    track_vars = ['irr', 'expenditure_gdp', 'revenue_gdp', 'fiscal_balance_gdp',
                  'iy', 'growth', 'debtgdp']
    available = [v for v in track_vars if v in panel.columns]

    results = []
    for t in range(-3, 8):
        row = {'t': t, 'n_episodes': 0}
        for var in available:
            values = []
            for _, ep in episodes.iterrows():
                country = ep['iso']
                target_year = ep['start_year'] + t
                obs = panel[(panel['iso'] == country) & (panel['year'] == target_year)]
                t0_obs = panel[(panel['iso'] == country) & (panel['year'] == ep['start_year'])]
                if not obs.empty and not t0_obs.empty:
                    v = obs[var].iloc[0]
                    v0 = t0_obs[var].iloc[0]
                    if pd.notna(v) and pd.notna(v0) and v0 != 0:
                        values.append(v - v0)  # Change from t=0
            if values:
                row[f'{var}_change'] = np.mean(values)
                row[f'{var}_n'] = len(values)
                if t == 0:
                    row['n_episodes'] = len(values)
        results.append(row)

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A48: THE AUSTERITY TRAP")
    logger.info("=" * 80)

    panel = load_panel()
    if panel.empty:
        return {}

    # Identify episodes
    episodes = identify_consolidation_episodes(panel)
    if episodes.empty:
        logger.warning("No consolidation episodes found")
        return {}

    write_single_sheet_excel(episodes, OUTPUT_DIR / "A48_consolidation_episodes.xlsx", "Episodes")

    # Classify
    classified = classify_episodes(episodes, panel)
    if not classified.empty:
        write_single_sheet_excel(classified, OUTPUT_DIR / "A48_trap_classification.xlsx", "Classification")
        counts = classified['classification'].value_counts()
        logger.info(f"\nEpisode classification:\n{counts.to_string()}")
        if 'austerity_trap' in counts:
            trap_pct = counts.get('austerity_trap', 0) / len(classified) * 100
            logger.info(f"\nAusterity trap episodes: {counts.get('austerity_trap',0)}/{len(classified)} ({trap_pct:.0f}%)")

    # Event study
    evt = event_study(episodes, panel)
    if not evt.empty:
        write_single_sheet_excel(evt, OUTPUT_DIR / "A48_event_study.xlsx", "EventStudy")
        logger.info("\nEvent study (avg change from t=0):")
        for _, row in evt.iterrows():
            t = int(row['t'])
            irr_c = row.get('irr_change', np.nan)
            exp_c = row.get('expenditure_gdp_change', np.nan)
            bal_c = row.get('fiscal_balance_gdp_change', np.nan)
            if pd.notna(irr_c):
                logger.info(f"  t={t:+2d}: Δirr={irr_c:+.4f} Δexpend={exp_c:+.4f} Δbalance={bal_c:+.4f}")

    logger.info("A48 COMPLETE")
    return {'episodes': len(episodes)}


if __name__ == "__main__":
    run()
