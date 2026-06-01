"""
A05: COFOG Functional Expenditure Analysis (Eurostat)
=====================================================
Deep analysis of government expenditure by function using the 210 MB Eurostat
COFOG dataset (27 EU countries, 1995-2023). Tests expenditure convergence
within the EU, welfare state typologies, and austerity impacts.

Data: eurostat_gov_10a_exp.tsv (Eurostat COFOG, 210 MB)
Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

EUROSTAT_FILE = raw_data_dir() / "eurostat" / "gfs" / "eurostat_gov_10a_exp.tsv"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COFOG_DIVISIONS = {
    'GF01': 'General public services',
    'GF02': 'Defence',
    'GF03': 'Public order and safety',
    'GF04': 'Economic affairs',
    'GF05': 'Environment protection',
    'GF06': 'Housing and community amenities',
    'GF07': 'Health',
    'GF08': 'Recreation, culture and religion',
    'GF09': 'Education',
    'GF10': 'Social protection',
    'GF_TOT': 'Total expenditure',
}

WELFARE_TYPOLOGIES = {
    'Social Democratic': ['DK', 'FI', 'SE', 'NO', 'IS'],
    'Continental': ['DE', 'FR', 'AT', 'BE', 'NL', 'LU'],
    'Liberal': ['IE', 'GB'],
    'Mediterranean': ['IT', 'ES', 'PT', 'EL', 'CY', 'MT'],
    'Eastern European': ['PL', 'CZ', 'HU', 'SK', 'SI', 'EE', 'LV', 'LT',
                        'BG', 'RO', 'HR'],
}


def load_eurostat_cofog() -> pd.DataFrame:
    """Load and parse the Eurostat COFOG TSV file.

    Eurostat TSV format: first column is composite key (comma-separated dimensions),
    remaining columns are years with flags.
    Format: 'freq,unit,sector,cofog99,na_item,geo\\TIME_PERIOD' then '1995 ', '1996 ', ...
    Values in first col: 'A,PC_GDP,S13,GF01,TE,AT'
    """
    if not EUROSTAT_FILE.exists():
        logger.error(f"Eurostat COFOG file not found: {EUROSTAT_FILE}")
        return pd.DataFrame()

    logger.info(f"Loading Eurostat COFOG ({EUROSTAT_FILE.stat().st_size / 1e6:.1f} MB)...")

    df = pd.read_csv(EUROSTAT_FILE, sep='\t', low_memory=False)
    logger.info(f"Raw Eurostat: {len(df):,} rows, {len(df.columns)} columns")

    first_col = df.columns[0]
    # Key structure: freq,unit,sector,cofog99,na_item,geo
    dim_names = ['freq', 'unit', 'sector', 'cofog99', 'na_item', 'geo']

    # Split composite key
    keys_split = df[first_col].str.split(',', expand=True)
    for i, name in enumerate(dim_names):
        if i < keys_split.shape[1]:
            df[name] = keys_split[i].str.strip()

    # Year columns are everything after first col
    year_cols = [c for c in df.columns[1:] if c.strip()[:4].isdigit()]
    logger.info(f"Found {len(year_cols)} year columns")

    # Filter BEFORE melting: only PC_GDP (% of GDP), sector S13 (general govt),
    # COFOG divisions, and total expenditure (TE)
    valid_cofog = list(COFOG_DIVISIONS.keys())
    mask = (
        (df['unit'] == 'PC_GDP') &
        (df['sector'] == 'S13') &
        (df['cofog99'].isin(valid_cofog)) &
        (df['na_item'] == 'TE')  # Total expenditure
    )
    filtered = df[mask].copy()
    logger.info(f"Filtered to PC_GDP + S13 + TE + COFOG divisions: {len(filtered):,} rows")

    if filtered.empty:
        # Try without na_item filter
        mask2 = (
            (df['unit'] == 'PC_GDP') &
            (df['sector'] == 'S13') &
            (df['cofog99'].isin(valid_cofog))
        )
        filtered = df[mask2].copy()
        logger.info(f"Relaxed filter (no TE): {len(filtered):,} rows")
        if not filtered.empty:
            # Pick the largest na_item category
            top_items = filtered['na_item'].value_counts().head(5)
            logger.info(f"Available na_items: {top_items.to_dict()}")
            # Use TE if available, otherwise the most common
            if 'TE' in filtered['na_item'].values:
                filtered = filtered[filtered['na_item'] == 'TE']
            else:
                best = top_items.index[0]
                filtered = filtered[filtered['na_item'] == best]
                logger.info(f"Using na_item={best}")

    if filtered.empty:
        logger.error("No data after filtering")
        return pd.DataFrame()

    # Melt to long format
    melted = filtered.melt(
        id_vars=['geo', 'cofog99', 'na_item'],
        value_vars=year_cols,
        var_name='year_raw',
        value_name='value_raw'
    )

    melted['year'] = pd.to_numeric(melted['year_raw'].str.strip(), errors='coerce')
    melted['value'] = melted['value_raw'].astype(str).str.replace(r'[^0-9.\-]', '', regex=True)
    melted['value'] = pd.to_numeric(melted['value'], errors='coerce')
    melted = melted.dropna(subset=['year', 'value'])
    melted['year'] = melted['year'].astype(int)

    logger.info(f"Parsed COFOG panel: {len(melted):,} rows, "
               f"{melted['geo'].nunique()} countries, {melted['year'].min()}-{melted['year'].max()}")
    return melted


def extract_cofog_panel(raw: pd.DataFrame) -> pd.DataFrame:
    """Extract clean COFOG panel: geo × year × division → % GDP."""
    if raw.empty:
        return pd.DataFrame()

    # After load_eurostat_cofog, raw has columns: geo, cofog99, na_item, year, value
    # Pivot to wide: one row per country-year, columns per COFOG division
    pivot = raw.pivot_table(
        index=['geo', 'year'],
        columns='cofog99',
        values='value',
        aggfunc='first'
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns={'geo': 'country_code'})

    # Rename COFOG columns
    rename_map = {k: f'cofog_{k.lower()}' for k in COFOG_DIVISIONS.keys()}
    pivot = pivot.rename(columns=rename_map)

    # Filter to actual countries (2-letter codes, exclude EU/EA aggregates)
    pivot = pivot[pivot['country_code'].str.len() == 2]

    logger.info(f"COFOG panel: {len(pivot):,} rows, {pivot['country_code'].nunique()} countries, "
               f"{pivot['year'].min()}-{pivot['year'].max()}")
    return pivot


def analyze_welfare_state_patterns(panel: pd.DataFrame) -> pd.DataFrame:
    """Compare expenditure patterns across Esping-Andersen welfare state typologies."""
    if panel.empty:
        return pd.DataFrame()

    # Map countries to typologies
    country_to_type = {}
    for ws_type, countries in WELFARE_TYPOLOGIES.items():
        for c in countries:
            country_to_type[c] = ws_type

    panel = panel.copy()
    panel['welfare_type'] = panel['country_code'].map(country_to_type)
    typed = panel.dropna(subset=['welfare_type'])

    cofog_cols = [c for c in panel.columns if c.startswith('cofog_gf')]
    if not cofog_cols:
        return pd.DataFrame()

    # Average by typology and decade
    typed['decade'] = (typed['year'] // 10) * 10
    results = typed.groupby(['welfare_type', 'decade'])[cofog_cols].mean().reset_index()

    return results


def analyze_austerity_impact(panel: pd.DataFrame) -> pd.DataFrame:
    """Measure the impact of post-2008 austerity on functional spending.

    Compare 2005-2008 average to 2012-2015 average for each country.
    Which functions got cut? Did all welfare types cut the same things?
    """
    if panel.empty:
        return pd.DataFrame()

    cofog_cols = [c for c in panel.columns if c.startswith('cofog_gf')]
    if not cofog_cols:
        return pd.DataFrame()

    pre_crisis = panel[(panel['year'] >= 2005) & (panel['year'] <= 2008)]
    austerity = panel[(panel['year'] >= 2012) & (panel['year'] <= 2015)]

    pre_avg = pre_crisis.groupby('country_code')[cofog_cols].mean()
    aust_avg = austerity.groupby('country_code')[cofog_cols].mean()

    common = pre_avg.index.intersection(aust_avg.index)
    if len(common) == 0:
        return pd.DataFrame()

    changes = (aust_avg.loc[common] - pre_avg.loc[common]).reset_index()
    changes = changes.rename(columns={c: f'{c}_change' for c in cofog_cols})

    # Add welfare type
    country_to_type = {}
    for ws_type, countries in WELFARE_TYPOLOGIES.items():
        for c in countries:
            country_to_type[c] = ws_type
    changes['welfare_type'] = changes['country_code'].map(country_to_type)

    # Add PIIGS indicator
    piigs = ['PT', 'IE', 'IT', 'EL', 'ES']
    changes['piigs'] = changes['country_code'].isin(piigs)

    return changes


def compute_eu_convergence(panel: pd.DataFrame) -> pd.DataFrame:
    """Test whether EU countries' expenditure structures are converging."""
    if panel.empty:
        return pd.DataFrame()

    cofog_cols = [c for c in panel.columns if c.startswith('cofog_gf')]
    results = []

    for year in sorted(panel['year'].unique()):
        yr_data = panel[panel['year'] == year]
        if len(yr_data) < 10:
            continue

        row = {'year': year, 'n_countries': len(yr_data)}
        for col in cofog_cols:
            valid = yr_data[col].dropna()
            if len(valid) >= 5:
                row[f'{col}_mean'] = valid.mean()
                row[f'{col}_std'] = valid.std()
                row[f'{col}_cv'] = valid.std() / valid.mean() if valid.mean() > 0 else np.nan
        results.append(row)

    return pd.DataFrame(results)


def analyze_social_protection_depth(panel: pd.DataFrame) -> pd.DataFrame:
    """Deep dive into social protection (COFOG 10) — the largest spending category."""
    if panel.empty or 'cofog_gf10' not in panel.columns:
        return pd.DataFrame()

    results = []
    for country, grp in panel.groupby('country_code'):
        grp = grp.sort_values('year')
        sp = grp['cofog_gf10'].dropna()
        if len(sp) < 5:
            continue

        # Trend analysis
        years_clean = grp.loc[sp.index, 'year'].values
        if len(years_clean) >= 5:
            slope = np.polyfit(years_clean - years_clean[0], sp.values, 1)[0]
        else:
            slope = np.nan

        # Social vs total ratio
        total = grp['cofog_gf_tot'].dropna() if 'cofog_gf_tot' in grp.columns else pd.Series()

        results.append({
            'country_code': country,
            'sp_mean': sp.mean(),
            'sp_latest': sp.iloc[-1],
            'sp_max': sp.max(),
            'sp_trend_pp_per_year': slope,
            'sp_share_of_total': (sp.mean() / total.mean() * 100) if len(total) > 0 else np.nan,
            'year_start': int(years_clean[0]),
            'year_end': int(years_clean[-1]),
        })

    return pd.DataFrame(results)


def run() -> dict:
    """Execute full COFOG functional analysis."""
    logger.info("=" * 80)
    logger.info("A05: COFOG FUNCTIONAL EXPENDITURE ANALYSIS (EUROSTAT)")
    logger.info("=" * 80)

    raw = load_eurostat_cofog()
    if raw.empty:
        return {}

    panel = extract_cofog_panel(raw)
    if panel.empty:
        logger.error("Could not extract COFOG panel from raw data")
        return {}

    write_single_sheet_excel(panel, OUTPUT_DIR / "A05_cofog_panel.xlsx", "COFOG")
    logger.info(f"Wrote COFOG panel: {len(panel):,} rows")

    welfare = analyze_welfare_state_patterns(panel)
    if not welfare.empty:
        write_single_sheet_excel(welfare, OUTPUT_DIR / "A05_welfare_typologies.xlsx", "Welfare")
        logger.info(f"Welfare state patterns: {len(welfare)} rows")

    austerity = analyze_austerity_impact(panel)
    if not austerity.empty:
        write_single_sheet_excel(austerity, OUTPUT_DIR / "A05_austerity_impact.xlsx", "Austerity")
        logger.info(f"Austerity impact: {len(austerity)} countries")
        if 'piigs' in austerity.columns:
            cofog_change_cols = [c for c in austerity.columns if c.endswith('_change')]
            piigs_cuts = austerity[austerity['piigs']][cofog_change_cols].mean()
            logger.info(f"PIIGS avg cuts: {piigs_cuts.to_dict()}")

    convergence = compute_eu_convergence(panel)
    if not convergence.empty:
        write_single_sheet_excel(convergence, OUTPUT_DIR / "A05_eu_convergence.xlsx", "Convergence")
        logger.info(f"EU convergence: {len(convergence)} years")

    sp_depth = analyze_social_protection_depth(panel)
    if not sp_depth.empty:
        write_single_sheet_excel(sp_depth, OUTPUT_DIR / "A05_social_protection.xlsx", "SocialProtection")
        logger.info(f"Social protection depth: {len(sp_depth)} countries")

    logger.info("A05 COMPLETE")
    return {
        'cofog_panel_rows': len(panel),
        'countries': panel['country_code'].nunique(),
        'welfare_typology_rows': len(welfare),
        'austerity_countries': len(austerity),
    }


if __name__ == "__main__":
    run()
