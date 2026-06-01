"""Parse UNU-WIDER GRD 2025 (196 countries, 66 columns, 3-row header)."""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

INPUT = Path(__file__).resolve().parents[3] / "Inputs" / "2026,05,05 requests" / "UNU GRD" / "UNUWIDERGRD_2025_Full.xlsx"
SHEET = "Merged"
OUTPUT_DIR = raw_data_dir() / "grd"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Column index → clean name mapping (Merged sheet from Full version)
COL_MAP = {
    0: 'identifier', 1: 'is_general', 2: 'source', 3: 'country',
    4: 'region', 5: 'income_group', 6: 'gdp_lcu_mn', 7: 'year', 8: 'iso',
    17: 'total_rev_inc_grants_inc_sc',
    18: 'total_rev_inc_grants_ex_sc',
    19: 'total_rev_ex_grants_inc_sc',
    20: 'total_rev_ex_grants_ex_sc',
    21: 'resource_revenue',
    22: 'nonresource_revenue_inc_sc',
    23: 'taxes_inc_sc',
    24: 'taxes_ex_sc',
    25: 'resource_taxes',
    26: 'nonresource_tax_inc_sc',
    27: 'nonresource_tax_ex_sc',
    28: 'direct_taxes_inc_sc_inc_resource',
    29: 'direct_taxes_inc_sc_ex_resource',
    30: 'direct_taxes_ex_sc_inc_resource',
    31: 'direct_taxes_ex_sc_ex_resource',
    32: 'income_profit_capgains_total',
    33: 'income_profit_capgains_resource',
    34: 'income_profit_capgains_nonresource',
    35: 'pit',
    36: 'cit_total',
    37: 'cit_resource',
    38: 'cit_nonresource',
    39: 'payroll_taxes',
    40: 'property_taxes',
    41: 'indirect_taxes_total',
    42: 'indirect_taxes_resource',
    43: 'indirect_taxes_nonresource',
    44: 'goods_services_total',
    45: 'goods_services_general_vat_sales',
    46: 'vat',
    47: 'excise',
    48: 'trade_taxes_total',
    49: 'trade_taxes_import',
    50: 'trade_taxes_export',
    51: 'other_taxes',
    52: 'nontax_revenue_total',
    53: 'nontax_revenue_resource',
    54: 'nontax_revenue_nonresource',
    55: 'social_contributions',
    56: 'grants',
}


def run():
    logger.info("=" * 80)
    logger.info("PARSING GRD 2025 (196 COUNTRIES)")
    logger.info("=" * 80)

    # Read Merged sheet, skipping 3 header rows
    df = pd.read_excel(INPUT, sheet_name=SHEET, header=None, skiprows=3)
    logger.info(f"Raw: {len(df):,} rows × {df.shape[1]} cols")

    # Apply column mapping
    rename = {i: name for i, name in COL_MAP.items() if i < df.shape[1]}
    df = df.rename(columns=rename)

    # Keep only mapped columns + drop unnamed
    keep = list(rename.values())
    df = df[[c for c in keep if c in df.columns]]

    # Clean
    df = df.dropna(subset=['iso'])
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)

    # Convert all revenue columns to numeric
    id_cols = ['identifier', 'is_general', 'source', 'country', 'iso',
               'region', 'income_group', 'year', 'gdp_lcu_mn']
    rev_cols = [c for c in df.columns if c not in id_cols]
    df['gdp_lcu_mn'] = pd.to_numeric(df.get('gdp_lcu_mn'), errors='coerce')
    for col in rev_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Convert LCU millions to % GDP
    gdp_valid = (df['gdp_lcu_mn'] > 0) & df['gdp_lcu_mn'].notna()
    logger.info(f"GDP available for {gdp_valid.sum()} / {len(df)} rows ({gdp_valid.mean()*100:.0f}%)")
    for col in rev_cols:
        df.loc[gdp_valid, col] = df.loc[gdp_valid, col] / df.loc[gdp_valid, 'gdp_lcu_mn'] * 100
    df.loc[~gdp_valid, rev_cols] = np.nan

    logger.info(f"Parsed: {len(df):,} rows, {df['iso'].nunique()} countries, "
               f"{df['year'].min()}-{df['year'].max()}")
    logger.info(f"Revenue columns: {len(rev_cols)}")
    logger.info(f"Income groups: {df['income_group'].value_counts().to_dict()}")
    logger.info(f"Regions: {df['region'].value_counts().to_dict()}")

    # Completeness check
    key_cols = ['taxes_inc_sc', 'pit', 'cit_total', 'vat', 'social_contributions',
                'trade_taxes_total', 'resource_revenue']
    for col in key_cols:
        if col in df.columns:
            n = df[col].notna().sum()
            logger.info(f"  {col:40s}: {n:,} obs ({n/len(df)*100:.0f}%)")

    # Save
    output_path = OUTPUT_DIR / "grd_2025_general.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved: {output_path} ({output_path.stat().st_size / 1e6:.1f} MB)")

    # Also parse Tax Effort scores
    te_path = Path(__file__).resolve().parents[3] / "Inputs" / "2026,05,05 requests" / "UNU GRD" / "Tax Effort scores_2021.xlsx"
    if te_path.exists():
        te = pd.read_excel(te_path)
        te.to_parquet(OUTPUT_DIR / "tax_effort_2021.parquet", index=False)
        logger.info(f"Tax Effort scores: {len(te)} rows, cols: {te.columns.tolist()[:8]}")

    logger.info("GRD PARSING COMPLETE")
    return {'rows': len(df), 'countries': df['iso'].nunique()}


if __name__ == "__main__":
    run()
