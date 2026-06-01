"""Parse IMF World Revenue Longitudinal Database (WoRLD) 2026."""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

INPUT = Path(__file__).resolve().parents[3] / "Inputs" / "2026,05,05 requests" / "world-imf2026.xlsx"
OUTPUT_DIR = raw_data_dir() / "imf" / "world"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run():
    logger.info("=" * 80)
    logger.info("PARSING IMF WoRLD 2026")
    logger.info("=" * 80)

    xl = pd.ExcelFile(INPUT)
    logger.info(f"Sheets: {xl.sheet_names}")

    # Read Data sheet
    df = pd.read_excel(INPUT, sheet_name="Data")
    logger.info(f"Data sheet: {df.shape}")
    logger.info(f"Columns: {df.columns.tolist()[:15]}")

    # Check if it's wide (years as columns) or long
    # Look for year-like column names
    year_cols = [c for c in df.columns if str(c).isdigit() and 1950 < int(str(c)) < 2030]
    if year_cols:
        logger.info(f"Wide format detected: {len(year_cols)} year columns ({year_cols[0]}-{year_cols[-1]})")
        # Find identifier columns
        id_cols = [c for c in df.columns if c not in year_cols]
        logger.info(f"ID columns: {id_cols[:10]}")

        # Melt to long format
        df_long = df.melt(id_vars=id_cols, value_vars=year_cols,
                         var_name='year', value_name='value')
        df_long['year'] = pd.to_numeric(df_long['year'], errors='coerce').astype(int)
        df_long['value'] = pd.to_numeric(df_long['value'], errors='coerce')
        df_long = df_long.dropna(subset=['value'])

        logger.info(f"Long format: {len(df_long):,} rows")
    else:
        # Already long format or different structure
        logger.info(f"Trying long format...")
        df_long = df.copy()
        # Find year column
        for col in df.columns:
            vals = pd.to_numeric(df[col], errors='coerce')
            if vals.between(1950, 2030).sum() > 100:
                df_long = df_long.rename(columns={col: 'year'})
                break

    # Identify country and indicator columns
    if 'year' in df_long.columns:
        logger.info(f"Years: {df_long['year'].min()}-{df_long['year'].max()}")

    # Find country code column
    for col in df_long.columns:
        if df_long[col].dtype == object:
            sample = df_long[col].dropna().head(10)
            if sample.str.len().mean() < 4 and sample.str.len().mean() >= 2:
                df_long = df_long.rename(columns={col: 'country_code'})
                logger.info(f"Country code column: {col} → country_code "
                           f"({df_long['country_code'].nunique()} unique)")
                break

    # Save
    output_path = OUTPUT_DIR / "world_2026.parquet"
    df_long.to_parquet(output_path, index=False)
    logger.info(f"Saved: {output_path} ({output_path.stat().st_size / 1e6:.1f} MB)")

    # Also try to pivot if there's an indicator column
    indicator_cols = [c for c in df_long.columns if 'indicator' in c.lower() or 'variable' in c.lower()
                     or 'category' in c.lower() or 'item' in c.lower()]
    if indicator_cols:
        ind_col = indicator_cols[0]
        logger.info(f"Indicators ({ind_col}): {df_long[ind_col].nunique()} unique")
        logger.info(f"  Sample: {df_long[ind_col].unique()[:10].tolist()}")

    logger.info("IMF WoRLD PARSING COMPLETE")
    return {'rows': len(df_long)}


if __name__ == "__main__":
    run()
