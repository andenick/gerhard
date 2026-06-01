#!/usr/bin/env python3
"""
P40: Clean Tax Data
Clean the primary tax dataset: remove errors, flag outliers, interpolate gaps, create balanced panel.
Stage: P | ID: P40
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "P40",
    "name": "Clean Tax Data",
    "stage": "P",
    "description": "Clean tax data: remove errors, flag outliers, interpolate gaps, create balanced panel",
    "depends_on": ["E15"],
    "inputs": [
        {"path": "Output/Data/world_bank_tax_revenue.xlsx", "required": True},
        {"path": "Output/Data/data_quality_flags.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/clean_tax_panel.xlsx"},
        {"path": "Output/Data/balanced_panel.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    df = pd.read_excel(out / "world_bank_tax_revenue.xlsx")
    flags = pd.read_excel(out / "data_quality_flags.xlsx")

    tax_col = 'tax_revenue_pct_gdp'
    initial_rows = len(df)

    # 0. Drop rows with missing country_code (WB aggregates leak through)
    nan_cc = df['country_code'].isna().sum()
    if nan_cc > 0:
        df = df.dropna(subset=['country_code']).copy()
        logger.info(f"Dropped {nan_cc} rows with missing country_code")

    # 1. Remove confirmed data errors (values > 100% of GDP are implausible for tax revenue)
    over100_mask = df[tax_col] > 100
    removed_count = over100_mask.sum()
    df = df[~over100_mask].copy()
    logger.info(f"Removed {removed_count} rows with tax > 100% GDP (Sudan, Timor-Leste oil spikes)")

    # 2. Flag but keep Timor-Leste (oil revenue is real)
    q1, q3 = df[tax_col].dropna().quantile([0.25, 0.75])
    iqr = q3 - q1
    upper = q3 + 3 * iqr
    lower = q1 - 3 * iqr

    df['is_outlier'] = (df[tax_col] > upper) | (df[tax_col] < lower)
    outlier_count = df['is_outlier'].sum()
    logger.info(f"Flagged {outlier_count} outliers (kept in data)")

    # 3. Add quality tier from flags
    df = df.merge(flags[['country_code', 'quality_tier', 'series_length', 'gap_count']],
                  on='country_code', how='left')

    # 4. Interpolate single-year gaps
    df = df.sort_values(['country_code', 'year'])
    interpolated_count = 0

    new_rows = []
    for cc, group in df.groupby('country_code'):
        years = sorted(group['year'].dropna().astype(int).unique())
        if len(years) < 2:
            continue

        full_range = range(min(years), max(years) + 1)
        existing_years = set(years)

        for yr in full_range:
            if yr not in existing_years:
                # Check if both neighbors exist (single gap)
                if (yr - 1) in existing_years and (yr + 1) in existing_years:
                    prev_val = group[group['year'] == yr - 1][tax_col].values
                    next_val = group[group['year'] == yr + 1][tax_col].values

                    if len(prev_val) > 0 and len(next_val) > 0 and not np.isnan(prev_val[0]) and not np.isnan(next_val[0]):
                        interp_val = (prev_val[0] + next_val[0]) / 2
                        country_name = group['country_name'].iloc[0]
                        qt = group['quality_tier'].iloc[0] if 'quality_tier' in group.columns else 'C'
                        sl = group['series_length'].iloc[0] if 'series_length' in group.columns else 0
                        gc = group['gap_count'].iloc[0] if 'gap_count' in group.columns else 0

                        new_rows.append({
                            'country_name': country_name,
                            'country_code': cc,
                            'year': yr,
                            tax_col: interp_val,
                            'is_outlier': False,
                            'quality_tier': qt,
                            'series_length': sl,
                            'gap_count': gc,
                            'interpolated': True,
                        })
                        interpolated_count += 1

    if new_rows:
        df['interpolated'] = False
        interp_df = pd.DataFrame(new_rows)
        df = pd.concat([df, interp_df], ignore_index=True)
        df = df.sort_values(['country_code', 'year']).reset_index(drop=True)
    else:
        df['interpolated'] = False

    logger.info(f"Interpolated {interpolated_count} single-year gaps")
    logger.info(f"Clean panel: {len(df)} rows ({initial_rows} original + {interpolated_count} interpolated - {removed_count} removed)")

    # 5. Save clean_tax_panel.xlsx
    write_single_sheet_excel(df, out / "clean_tax_panel.xlsx")
    logger.info(f"Saved clean_tax_panel.xlsx ({len(df)} rows, {df['country_code'].nunique()} countries)")

    # 6. Create balanced panel (countries with ≥10 consecutive years, no gaps)
    balanced_countries = []
    for cc, group in df.groupby('country_code'):
        group_sorted = group.sort_values('year')
        years = group_sorted['year'].values

        # Find longest consecutive run
        if len(years) < 10:
            continue

        max_run = 1
        current_run = 1
        for i in range(1, len(years)):
            if years[i] == years[i-1] + 1:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 1

        if max_run >= 10:
            balanced_countries.append(cc)

    balanced = df[df['country_code'].isin(balanced_countries)].copy()
    balanced = balanced[['country_code', 'country_name', 'year', tax_col]].dropna()

    write_single_sheet_excel(balanced, out / "balanced_panel.xlsx")
    logger.info(f"Saved balanced_panel.xlsx ({len(balanced)} rows, {len(balanced_countries)} countries with >=10 consecutive years)")


if __name__ == "__main__":
    run()
