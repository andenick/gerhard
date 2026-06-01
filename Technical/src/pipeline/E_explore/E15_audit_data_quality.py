#!/usr/bin/env python3
"""
E15: Audit Data Quality
Comprehensive data quality audit of the tax revenue dataset.
Stage: E | ID: E15
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "E15",
    "name": "Audit Data Quality",
    "stage": "E",
    "description": "Comprehensive data quality audit of tax revenue data: outliers, gaps, coverage",
    "depends_on": [],
    "inputs": [{"path": "Output/Data/world_bank_tax_revenue.xlsx", "required": True}],
    "outputs": [
        {"path": "Output/Data/data_quality_audit.xlsx"},
        {"path": "Output/Data/data_quality_flags.xlsx"},
    ],
    "timeout": 60,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()
    df = pd.read_excel(out / "world_bank_tax_revenue.xlsx")
    logger.info(f"Loaded {len(df)} rows, {df['country_code'].nunique()} countries")

    tax_col = 'tax_revenue_pct_gdp'
    valid = df[tax_col].dropna()

    # 1. Outlier detection (3x IQR)
    q1, q3 = valid.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower_bound = q1 - 3 * iqr
    upper_bound = q3 + 3 * iqr

    outlier_mask = (df[tax_col] < lower_bound) | (df[tax_col] > upper_bound)
    outliers = df[outlier_mask].copy()
    outliers['outlier_type'] = outliers[tax_col].apply(
        lambda x: 'extreme_high' if x > upper_bound else 'extreme_low'
    )
    logger.info(f"Outliers (3x IQR [{lower_bound:.1f}, {upper_bound:.1f}]): {len(outliers)}")

    # 2. Known issue flags
    known_errors = []
    # Sudan 1998-1999: confirmed data error (638% of GDP)
    sdn = df[(df['country_code'] == 'SDN') & (df[tax_col] > 100)]
    if len(sdn) > 0:
        known_errors.append({'country_code': 'SDN', 'issue': 'data_error',
                           'description': f'{len(sdn)} values >100% (max {sdn[tax_col].max():.1f}%)',
                           'recommendation': 'remove'})

    # Timor-Leste: oil revenue (valid but extreme)
    tls = df[(df['country_code'] == 'TLS') & (df[tax_col] > 100)]
    if len(tls) > 0:
        known_errors.append({'country_code': 'TLS', 'issue': 'extreme_but_valid',
                           'description': f'{len(tls)} values >100% (oil revenue)',
                           'recommendation': 'flag_keep'})

    # 3. Time series gap detection
    gap_records = []
    for cc, group in df.groupby('country_code'):
        years = sorted(group['year'].dropna().astype(int).unique())
        if len(years) >= 2:
            expected = set(range(min(years), max(years) + 1))
            actual = set(years)
            missing = sorted(expected - actual)
            if missing:
                gap_records.append({
                    'country_code': cc,
                    'series_start': min(years),
                    'series_end': max(years),
                    'series_length': len(years),
                    'gap_count': len(missing),
                    'missing_years': str(missing[:10]),
                })

    gaps_df = pd.DataFrame(gap_records)
    total_gaps = gaps_df['gap_count'].sum() if len(gaps_df) > 0 else 0
    logger.info(f"Time series gaps: {total_gaps} missing observations across {len(gaps_df)} countries")

    # 4. Series length distribution
    series_lengths = df.groupby('country_code')['year'].count().reset_index()
    series_lengths.columns = ['country_code', 'series_length']

    logger.info(f"Series length: min={series_lengths['series_length'].min()}, "
                f"max={series_lengths['series_length'].max()}, "
                f"median={series_lengths['series_length'].median():.0f}")

    # 5. Duplicate detection
    dupes = df.duplicated(subset=['country_code', 'year']).sum()
    logger.info(f"Duplicates (country+year): {dupes}")

    # 6. NaN prevalence
    nan_pct = df.isnull().mean()

    # === Build quality flags per country ===
    country_flags = series_lengths.copy()

    # Add gap info
    if len(gaps_df) > 0:
        country_flags = country_flags.merge(
            gaps_df[['country_code', 'gap_count']], on='country_code', how='left'
        )
    else:
        country_flags['gap_count'] = 0
    country_flags['gap_count'] = country_flags['gap_count'].fillna(0).astype(int)

    # Add outlier count
    outlier_counts = outliers.groupby('country_code').size().reset_index(name='outlier_count')
    country_flags = country_flags.merge(outlier_counts, on='country_code', how='left')
    country_flags['outlier_count'] = country_flags['outlier_count'].fillna(0).astype(int)

    # Quality tier
    def assign_tier(row):
        if row['series_length'] >= 25 and row['gap_count'] <= 2 and row['outlier_count'] == 0:
            return 'A'
        elif row['series_length'] >= 10 and row['gap_count'] <= 5:
            return 'B'
        else:
            return 'C'

    country_flags['quality_tier'] = country_flags.apply(assign_tier, axis=1)

    tier_counts = country_flags['quality_tier'].value_counts().sort_index()
    logger.info(f"Quality tiers: {dict(tier_counts)}")

    # Add country name
    name_map = df.drop_duplicates('country_code').set_index('country_code')['country_name']
    country_flags['country_name'] = country_flags['country_code'].map(name_map)

    # === Save outputs ===

    # Audit report (comprehensive)
    audit_data = pd.DataFrame({
        'metric': [
            'total_observations', 'total_countries', 'year_range',
            'outlier_count', 'outlier_bounds', 'total_gaps',
            'countries_with_gaps', 'duplicate_rows',
            'tier_A_countries', 'tier_B_countries', 'tier_C_countries',
            'mean_series_length', 'median_series_length',
        ],
        'value': [
            len(df), df['country_code'].nunique(), f"{df['year'].min()}-{df['year'].max()}",
            len(outliers), f"[{lower_bound:.1f}, {upper_bound:.1f}]", total_gaps,
            len(gaps_df), dupes,
            tier_counts.get('A', 0), tier_counts.get('B', 0), tier_counts.get('C', 0),
            f"{series_lengths['series_length'].mean():.1f}",
            f"{series_lengths['series_length'].median():.0f}",
        ]
    })

    write_single_sheet_excel(audit_data, out / "data_quality_audit.xlsx")
    logger.info(f"Saved data_quality_audit.xlsx")

    # Per-country flags
    write_single_sheet_excel(
        country_flags[['country_code', 'country_name', 'series_length', 'gap_count', 'outlier_count', 'quality_tier']],
        out / "data_quality_flags.xlsx"
    )
    logger.info(f"Saved data_quality_flags.xlsx ({len(country_flags)} countries)")


if __name__ == "__main__":
    run()
