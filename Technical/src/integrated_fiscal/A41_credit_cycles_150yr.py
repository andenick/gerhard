"""
A41: Credit Cycles and Fiscal Crises — The 150-Year Pattern
=============================================================
Identifies the canonical 4-phase cycle: expansion → peak → crisis → austerity.
Averages across 88 banking crises in 18 countries over 150 years.
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


def load_jst():
    fpath = raw_data_dir() / "jst" / "JSTdatasetR6.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    return pd.read_parquet(fpath)


def canonical_crisis_event_study(jst: pd.DataFrame) -> pd.DataFrame:
    """Average all 88 banking crises: what happens t-5 to t+10?"""
    if jst.empty or 'crisisJST' not in jst.columns:
        return pd.DataFrame()

    jst = jst.sort_values(['iso', 'year']).copy()
    # Normalize credit to GDP
    if 'tloans' in jst.columns and 'gdp' in jst.columns:
        jst['credit_gdp'] = jst['tloans'] / jst['gdp']
    if 'thh' in jst.columns and 'gdp' in jst.columns:
        jst['hh_credit_gdp'] = jst['thh'] / jst['gdp']

    # Find crisis starts
    jst['crisis_start'] = (jst['crisisJST'] == 1) & (jst.groupby('iso')['crisisJST'].shift(1) != 1)
    events = jst[jst['crisis_start']]
    logger.info(f"Banking crisis events: {len(events)}")

    # For each variable, compute average path around crisis
    vars_to_track = {
        'credit_gdp': 'Private Credit/GDP',
        'debtgdp': 'Public Debt/GDP',
        'revenue': 'Government Revenue (LCU)',
        'expenditure': 'Government Expenditure (LCU)',
    }
    available = {k: v for k, v in vars_to_track.items() if k in jst.columns}

    results = []
    for t in range(-5, 11):
        row = {'t': t, 'n_events': 0}
        for var, label in available.items():
            values = []
            for _, event in events.iterrows():
                country = event['iso']
                crisis_year = event['year']
                target_year = crisis_year + t
                obs = jst[(jst['iso'] == country) & (jst['year'] == target_year)]
                if not obs.empty and pd.notna(obs[var].iloc[0]):
                    # Normalize to t=0 value
                    t0_obs = jst[(jst['iso'] == country) & (jst['year'] == crisis_year)]
                    if not t0_obs.empty and t0_obs[var].iloc[0] != 0:
                        values.append(obs[var].iloc[0] / t0_obs[var].iloc[0])
            if values:
                row[f'{var}_indexed'] = np.mean(values)
                row[f'{var}_n'] = len(values)
                if t == 0:
                    row['n_events'] = len(values)
        results.append(row)

    return pd.DataFrame(results)


def measure_cycle_amplitude(jst: pd.DataFrame) -> pd.DataFrame:
    """Has the credit cycle gotten larger over time?"""
    if jst.empty or 'tloans' not in jst.columns or 'gdp' not in jst.columns:
        return pd.DataFrame()

    jst = jst.copy()
    jst['credit_gdp'] = jst['tloans'] / jst['gdp']
    jst = jst.replace([np.inf, -np.inf], np.nan)

    results = []
    for country, grp in jst.groupby('iso'):
        grp = grp.sort_values('year').dropna(subset=['credit_gdp'])
        if len(grp) < 30:
            continue
        # Credit volatility by era
        for era_name, (start, end) in [('pre_wwi', (1870, 1913)), ('interwar', (1919, 1938)),
                                        ('golden_age', (1946, 1973)), ('neoliberal', (1980, 2007)),
                                        ('post_gfc', (2008, 2020))]:
            era = grp[(grp['year'] >= start) & (grp['year'] <= end)]
            if len(era) < 10:
                continue
            results.append({
                'iso': country, 'era': era_name,
                'credit_gdp_mean': era['credit_gdp'].mean(),
                'credit_gdp_std': era['credit_gdp'].std(),
                'credit_gdp_max': era['credit_gdp'].max(),
                'credit_growth_vol': era['credit_gdp'].diff().std(),
            })

    return pd.DataFrame(results)


def four_phase_identification(jst: pd.DataFrame) -> pd.DataFrame:
    """Classify each country-year into cycle phase."""
    if jst.empty:
        return pd.DataFrame()

    jst = jst.sort_values(['iso', 'year']).copy()
    if 'tloans' in jst.columns and 'gdp' in jst.columns:
        jst['credit_gdp'] = jst['tloans'] / jst['gdp']
        jst['credit_growth'] = jst.groupby('iso')['credit_gdp'].pct_change()
    jst = jst.replace([np.inf, -np.inf], np.nan)

    results = []
    for _, row in jst.iterrows():
        phase = 'unknown'
        credit_g = row.get('credit_growth', np.nan)
        crisis = row.get('crisisJST', 0)
        debt_g = np.nan

        if crisis == 1:
            phase = 'crisis'
        elif pd.notna(credit_g):
            if credit_g > 0.03:
                phase = 'expansion'
            elif credit_g < -0.02:
                phase = 'deleveraging'
            else:
                phase = 'stable'

        results.append({
            'iso': row.get('iso', ''), 'year': row.get('year', 0),
            'phase': phase, 'credit_growth': credit_g,
            'credit_gdp': row.get('credit_gdp', np.nan),
            'debtgdp': row.get('debtgdp', np.nan),
        })

    df = pd.DataFrame(results)
    return df


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A41: CREDIT CYCLES — 150-YEAR PATTERN")
    logger.info("=" * 80)

    jst = load_jst()
    if jst.empty:
        return {}

    # Canonical event study
    event_study = canonical_crisis_event_study(jst)
    if not event_study.empty:
        write_single_sheet_excel(event_study, OUTPUT_DIR / "A41_crisis_event_study.xlsx", "EventStudy")
        logger.info("Canonical banking crisis pattern (indexed to t=0):")
        for _, row in event_study.iterrows():
            t = int(row['t'])
            credit = row.get('credit_gdp_indexed', np.nan)
            debt = row.get('debtgdp_indexed', np.nan)
            if pd.notna(credit) and pd.notna(debt):
                logger.info(f"  t={t:+3d}: credit={credit:.2f}x  debt={debt:.2f}x")

    # Cycle amplitude
    amplitude = measure_cycle_amplitude(jst)
    if not amplitude.empty:
        write_single_sheet_excel(amplitude, OUTPUT_DIR / "A41_cycle_amplitude.xlsx", "Amplitude")
        era_avg = amplitude.groupby('era')['credit_gdp_mean'].mean()
        logger.info(f"\nAvg credit/GDP by era:\n{era_avg.to_string()}")

    # Phase classification
    phases = four_phase_identification(jst)
    if not phases.empty:
        write_single_sheet_excel(phases.head(50000), OUTPUT_DIR / "A41_cycle_phases.xlsx", "Phases")
        phase_counts = phases['phase'].value_counts()
        logger.info(f"\nPhase distribution (all country-years):\n{phase_counts.to_string()}")

    logger.info("A41 COMPLETE")
    return {}


if __name__ == "__main__":
    run()
