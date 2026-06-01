"""
Parse OECD Revenue Statistics JSON (112 MB) into structured parquet panel.
Extracts tax revenue by type for 38 OECD countries, 1965-2023.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

INPUT_FILE = raw_data_dir() / "oecd" / "revenue_stats" / "oecd_rev_comp_oecd.json"
OUTPUT_DIR = raw_data_dir() / "oecd" / "revenue_stats"


def parse_sdmx_json_v2(filepath: Path) -> pd.DataFrame:
    """Parse OECD SDMX-JSON 2.0 format into tidy DataFrame."""
    logger.info(f"Loading {filepath.stat().st_size / 1e6:.1f} MB JSON...")

    with open(filepath, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    # Navigate structure: raw['data']['dataSets'] and raw['data']['structures']
    data_section = raw.get('data', raw)
    datasets = data_section.get('dataSets', [])
    structures = data_section.get('structures', [])

    if not datasets:
        logger.error("No dataSets found")
        return pd.DataFrame()

    if not structures:
        logger.error("No structures found")
        return pd.DataFrame()

    # Get dimension metadata from structure
    structure = structures[0] if structures else {}
    dimensions = structure.get('dimensions', {}).get('observation', [])
    attributes = structure.get('attributes', {}).get('observation', [])

    logger.info(f"Dimensions: {[d.get('id') for d in dimensions]}")
    logger.info(f"Dimension sizes: {[len(d.get('values', [])) for d in dimensions]}")

    # Build dimension value lookups
    dim_lookups = []
    for dim in dimensions:
        values = dim.get('values', [])
        lookup = {}
        for i, v in enumerate(values):
            lookup[i] = {'id': v.get('id', ''), 'name': v.get('name', '')}
        dim_lookups.append({
            'id': dim.get('id', ''),
            'name': dim.get('name', ''),
            'lookup': lookup
        })

    # Parse observations
    dataset = datasets[0]
    observations = dataset.get('observations', {})
    logger.info(f"Observations: {len(observations):,}")

    if not observations:
        # Try series-based format
        series = dataset.get('series', {})
        if series:
            logger.info(f"Series-based format: {len(series)} series")
            return _parse_series_format(series, dim_lookups, dimensions)
        return pd.DataFrame()

    # Observation-keyed format: key = "0:1:2:3:4:5:6", value = [number, ...]
    rows = []
    for key, obs_value in observations.items():
        indices = [int(x) for x in key.split(':')]
        row = {}

        for i, idx in enumerate(indices):
            if i < len(dim_lookups):
                dim_info = dim_lookups[i]
                val_info = dim_info['lookup'].get(idx, {'id': str(idx), 'name': str(idx)})
                row[dim_info['id']] = val_info['id']
                if dim_info['id'] in ('TIME_PERIOD', 'YEAR'):
                    row['year'] = val_info['id']

        # Value
        if isinstance(obs_value, list) and obs_value:
            row['value'] = obs_value[0]
        elif isinstance(obs_value, (int, float)):
            row['value'] = obs_value

        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"Parsed: {len(df):,} rows, columns: {df.columns.tolist()}")
    return df


def _parse_series_format(series: dict, dim_lookups: list, dimensions: list) -> pd.DataFrame:
    """Parse series-keyed SDMX format."""
    # In series format: outer key indexes series dimensions, inner has observations
    # Series dimensions vs observation dimensions differ
    rows = []
    for series_key, series_data in series.items():
        series_indices = [int(x) for x in series_key.split(':')]
        series_attrs = {}

        # Resolve series dimensions (all except time, which is in observations)
        for i, idx in enumerate(series_indices):
            if i < len(dim_lookups):
                dim_info = dim_lookups[i]
                val_info = dim_info['lookup'].get(idx, {'id': str(idx)})
                series_attrs[dim_info['id']] = val_info['id']

        # Parse observations within series
        obs = series_data.get('observations', {})
        for time_key, obs_value in obs.items():
            row = series_attrs.copy()
            # Time dimension
            time_idx = int(time_key)
            # Find time dimension in lookups
            time_dim = next((d for d in dim_lookups if d['id'] in ('TIME_PERIOD', 'YEAR', 'Time')), None)
            if time_dim:
                time_val = time_dim['lookup'].get(time_idx, {'id': str(time_idx)})
                row['year'] = time_val['id']
            else:
                row['year'] = str(time_idx)

            if isinstance(obs_value, list) and obs_value:
                row['value'] = obs_value[0]
            rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"Parsed (series format): {len(df):,} rows")
    return df


def clean_and_structure(df: pd.DataFrame) -> pd.DataFrame:
    """Clean parsed OECD data into analysis-ready panel."""
    if df.empty:
        return df

    # Standardize column names based on actual OECD structure
    col_map = {
        'REF_AREA': 'country_code',
        'STANDARD_REVENUE': 'tax_category',
        'UNIT_MEASURE': 'unit',
        'SECTOR': 'gov_level',
        'TIME_PERIOD': 'year_str',
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Ensure year is numeric (may already exist from parsing, or use year_str)
    if 'year' not in df.columns and 'year_str' in df.columns:
        df['year'] = pd.to_numeric(df['year_str'], errors='coerce')
    elif 'year' in df.columns:
        if df['year'].dtype == object:
            df['year'] = pd.to_numeric(df['year'], errors='coerce')

    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)

    # Ensure value is numeric
    if 'value' in df.columns:
        df['value'] = pd.to_numeric(df['value'], errors='coerce')

    logger.info(f"Cleaned panel: {len(df):,} rows")
    logger.info(f"Columns: {df.columns.tolist()}")
    if 'country_code' in df.columns:
        logger.info(f"Countries: {df['country_code'].nunique()}")
    if 'year' in df.columns:
        logger.info(f"Years: {df['year'].min()}-{df['year'].max()}")
    if 'tax_category' in df.columns:
        logger.info(f"Tax categories: {df['tax_category'].nunique()}")
        logger.info(f"Sample categories: {df['tax_category'].unique()[:15].tolist()}")
    if 'measure' in df.columns:
        logger.info(f"Measures: {df['measure'].unique().tolist()}")

    return df


def run():
    logger.info("=" * 80)
    logger.info("PARSING OECD REVENUE STATISTICS (112 MB)")
    logger.info("=" * 80)

    if not INPUT_FILE.exists():
        logger.error(f"Input not found: {INPUT_FILE}")
        return

    df = parse_sdmx_json_v2(INPUT_FILE)
    if df.empty:
        logger.error("Parsing failed — no data extracted")
        return

    df = clean_and_structure(df)

    # Save full parsed panel
    output_path = OUTPUT_DIR / "oecd_revenue_panel.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved: {output_path} ({output_path.stat().st_size / 1e6:.1f} MB)")

    # If we have tax_category and measure columns, create wide panel
    if 'country_code' in df.columns and 'tax_category' in df.columns and 'year' in df.columns:
        # Filter to % GDP measure if available
        if 'measure' in df.columns:
            gdp_measures = [m for m in df['measure'].unique()
                          if 'GDP' in str(m).upper() or 'TAXGDP' in str(m).upper()]
            if gdp_measures:
                df_gdp = df[df['measure'].isin(gdp_measures)]
                logger.info(f"GDP-filtered: {len(df_gdp):,} rows (measure={gdp_measures})")
            else:
                df_gdp = df
                logger.info(f"No GDP measure filter applied (measures: {df['measure'].unique()[:5]})")
        else:
            df_gdp = df

        # Pivot: country × year × tax_categories
        if len(df_gdp) > 0:
            pivot = df_gdp.pivot_table(
                index=['country_code', 'year'],
                columns='tax_category',
                values='value',
                aggfunc='first'
            ).reset_index()
            pivot.columns.name = None
            pivot.to_parquet(OUTPUT_DIR / "oecd_revenue_wide.parquet", index=False)
            logger.info(f"Wide panel: {len(pivot):,} rows × {len(pivot.columns)} cols")
            logger.info(f"Tax columns: {[c for c in pivot.columns if c not in ['country_code','year']][:10]}")

    logger.info("OECD REVENUE PARSING COMPLETE")


if __name__ == "__main__":
    run()
