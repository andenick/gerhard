"""Parse EU Taxation Trends data (ITR, economic function, tax type, level)."""

import pandas as pd
import gzip
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

INPUT_DIR = Path(__file__).resolve().parents[3] / "Inputs" / "2026,05,05 requests" / "europa-webgate"
OUTPUT_DIR = raw_data_dir() / "eurostat" / "itr"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_eu_csv_gz(filepath: Path, name: str) -> pd.DataFrame:
    """Parse a gzipped EU Taxation Trends CSV."""
    logger.info(f"Parsing {name}: {filepath.name}")

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        df = pd.read_csv(f)

    logger.info(f"  Raw: {len(df):,} rows × {df.shape[1]} cols")
    logger.info(f"  Columns: {df.columns.tolist()}")

    # Parse composite columns — EU format has "CODE:Label" in dimension columns
    for col in df.columns:
        if df[col].dtype == object and ':' in str(df[col].iloc[0]):
            # Split "CODE:Label" into code and label
            split = df[col].str.split(':', n=1, expand=True)
            df[f'{col}_code'] = split[0].str.strip()
            df[f'{col}_label'] = split[1].str.strip() if split.shape[1] > 1 else ''

    # Clean GEO to country code
    if 'GEO_code' in df.columns:
        df['country_code'] = df['GEO_code']
    elif 'GEO' in df.columns:
        df['country_code'] = df['GEO'].str.split(':').str[0].str.strip()

    # Clean year
    if 'TIME_PERIOD' in df.columns:
        df['year'] = pd.to_numeric(df['TIME_PERIOD'], errors='coerce')

    # Clean value
    if 'OBS_VALUE' in df.columns:
        df['value'] = pd.to_numeric(df['OBS_VALUE'], errors='coerce')

    df = df.dropna(subset=['year', 'value'])
    df['year'] = df['year'].astype(int)

    logger.info(f"  Parsed: {len(df):,} rows, {df['country_code'].nunique()} countries, "
               f"{df['year'].min()}-{df['year'].max()}")

    return df


def run():
    logger.info("=" * 80)
    logger.info("PARSING EU TAXATION TRENDS DATA")
    logger.info("=" * 80)

    files = {
        'itr': ('taxud_tax_itr_en.csv.gz', 'Implicit Tax Rates'),
        'ec_func': ('taxud_tax_ec_func_en.csv.gz', 'Tax by Economic Function'),
        'tax_type': ('taxud_tax_type_en.csv.gz', 'Tax by Type'),
        'tax_level': ('taxud_tax_level_en.csv.gz', 'Tax by Government Level'),
        'vat_compl': ('taxud_vap_compl_gap_en.csv.gz', 'VAT Compliance Gap'),
        'vat_pol': ('taxud_vat_pol_gap_en.csv.gz', 'VAT Policy Gap'),
    }

    for key, (fname, desc) in files.items():
        fpath = INPUT_DIR / fname
        if not fpath.exists():
            logger.warning(f"Missing: {fname}")
            continue

        df = parse_eu_csv_gz(fpath, desc)
        if df.empty:
            continue

        output_path = OUTPUT_DIR / f"eu_{key}.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"  Saved: {output_path.name}")

        # Special processing for ITR
        if key == 'itr' and 'ITR_code' in df.columns:
            # Pivot: country × year × ITR(L, K, C)
            itr_pivot = df.pivot_table(
                index=['country_code', 'year'],
                columns='ITR_code',
                values='value',
                aggfunc='first'
            ).reset_index()
            itr_pivot.columns.name = None
            rename = {'L': 'itr_labor', 'K': 'itr_capital', 'C': 'itr_consumption'}
            itr_pivot = itr_pivot.rename(columns=rename)
            itr_pivot.to_parquet(OUTPUT_DIR / "eu_itr_wide.parquet", index=False)
            logger.info(f"  ITR wide panel: {len(itr_pivot)} rows")
            logger.info(f"  Columns: {itr_pivot.columns.tolist()}")

            # Summary
            latest = itr_pivot[itr_pivot['year'] == itr_pivot['year'].max()]
            for col in ['itr_labor', 'itr_capital', 'itr_consumption']:
                if col in latest.columns:
                    logger.info(f"  Latest avg {col}: {latest[col].mean():.1f}%")

        # Special processing for economic function
        if key == 'ec_func' and 'EF_code' in df.columns:
            # Key categories: Labour, Capital, Consumption
            main_cats = df[df['EF_code'].isin(['LB', 'KP', 'CN'])]
            if not main_cats.empty:
                ec_pivot = main_cats.pivot_table(
                    index=['country_code', 'year'],
                    columns='EF_code',
                    values='value',
                    aggfunc='first'
                ).reset_index()
                ec_pivot.columns.name = None
                rename = {'LB': 'tax_labor_mio_eur', 'KP': 'tax_capital_mio_eur',
                         'CN': 'tax_consumption_mio_eur'}
                ec_pivot = ec_pivot.rename(columns=rename)
                ec_pivot.to_parquet(OUTPUT_DIR / "eu_ec_func_wide.parquet", index=False)
                logger.info(f"  Economic function wide: {len(ec_pivot)} rows")

    logger.info("EU TAXATION TRENDS PARSING COMPLETE")


if __name__ == "__main__":
    run()
