"""Download US OMB Historical Tables — federal fiscal data 1789-2029.
Tables 1.1, 2.1, 3.1, 7.1 cover receipts, outlays by source/function, and debt.
"""

import requests
import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

OUTPUT_DIR = raw_data_dir() / "us_hsus" / "omb_historical_tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OMB_TABLES = {
    'table_1_1': {
        'url': 'https://www.whitehouse.gov/wp-content/uploads/2024/03/hist01z1.xlsx',
        'desc': 'Summary of Receipts, Outlays, and Surpluses/Deficits',
    },
    'table_2_1': {
        'url': 'https://www.whitehouse.gov/wp-content/uploads/2024/03/hist02z1.xlsx',
        'desc': 'Receipts by Source',
    },
    'table_3_1': {
        'url': 'https://www.whitehouse.gov/wp-content/uploads/2024/03/hist03z1.xlsx',
        'desc': 'Outlays by Superfunction and Function',
    },
    'table_7_1': {
        'url': 'https://www.whitehouse.gov/wp-content/uploads/2024/03/hist07z1.xlsx',
        'desc': 'Federal Debt at End of Year',
    },
}


def download_table(name: str, url: str) -> Path:
    fpath = OUTPUT_DIR / f"{name}.xlsx"
    if fpath.exists():
        logger.info(f"Already have: {fpath.name}")
        return fpath

    logger.info(f"Downloading {name}...")
    try:
        resp = requests.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        fpath.write_bytes(resp.content)
        logger.info(f"Saved: {fpath.name} ({len(resp.content) / 1024:.0f} KB)")
    except Exception as e:
        logger.warning(f"Failed to download {name}: {e}")
        # Try alternate URL pattern
        alt_url = url.replace('/2024/03/', '/2025/03/')
        try:
            resp = requests.get(alt_url, timeout=30, allow_redirects=True)
            resp.raise_for_status()
            fpath.write_bytes(resp.content)
            logger.info(f"Saved (alt URL): {fpath.name}")
        except Exception as e2:
            logger.error(f"Both URLs failed for {name}: {e2}")
            return None
    return fpath


def parse_omb_excel(fpath: Path) -> pd.DataFrame:
    """Parse an OMB historical table Excel file.

    OMB files have: title rows, then header row with year labels,
    then data rows with category labels in col A and values in subsequent cols.
    OR they have years as rows and categories as columns.
    """
    if fpath is None or not fpath.exists():
        return pd.DataFrame()

    try:
        # Try reading raw to understand structure
        raw = pd.read_excel(fpath, header=None, nrows=10)
        logger.info(f"Parsing {fpath.name}: shape={raw.shape}")

        # OMB tables typically have fiscal years as the first column
        # and data categories across the top or as row labels
        # Try standard pandas read with header detection
        df = pd.read_excel(fpath, header=None)

        # Find the row that contains year-like values (1789, 1934, etc.)
        year_row = None
        year_col = None

        # Check if years are in a column (long format)
        for col_idx in range(min(3, df.shape[1])):
            col_vals = pd.to_numeric(df.iloc[:, col_idx], errors='coerce')
            year_like = col_vals.between(1700, 2030)
            if year_like.sum() > 20:
                year_col = col_idx
                break

        if year_col is not None:
            # Long format: years in a column
            # Find header row (row before first year)
            first_year_idx = df.iloc[:, year_col].apply(
                lambda x: pd.to_numeric(x, errors='coerce')).between(1700, 2030).idxmax()
            header_idx = max(0, first_year_idx - 1)

            df_clean = df.iloc[first_year_idx:].copy()
            df_clean.columns = df.iloc[header_idx].tolist()
            df_clean = df_clean.reset_index(drop=True)

            # Rename first column to 'year'
            cols = df_clean.columns.tolist()
            cols[year_col] = 'year'
            df_clean.columns = cols
            df_clean['year'] = pd.to_numeric(df_clean['year'], errors='coerce')
            df_clean = df_clean.dropna(subset=['year'])
            df_clean['year'] = df_clean['year'].astype(int)

            # Convert all other columns to numeric
            for col in df_clean.columns:
                if col != 'year':
                    df_clean[col] = pd.to_numeric(
                        df_clean[col].astype(str).str.replace(',', '').str.strip(),
                        errors='coerce')

            return df_clean
        else:
            # Wide format: years across columns, categories in rows
            # Find header row with years
            for idx in range(min(10, len(df))):
                row_vals = pd.to_numeric(df.iloc[idx], errors='coerce')
                if row_vals.between(1700, 2030).sum() > 5:
                    year_row = idx
                    break

            if year_row is not None:
                headers = df.iloc[year_row]
                df_clean = df.iloc[year_row + 1:].copy()
                df_clean.columns = headers
                df_clean = df_clean.reset_index(drop=True)
                return df_clean

        logger.warning(f"Could not parse structure of {fpath.name}")
        return df

    except Exception as e:
        logger.error(f"Error parsing {fpath.name}: {e}")
        return pd.DataFrame()


def build_us_fiscal_panel(parsed_tables: dict) -> pd.DataFrame:
    """Combine parsed OMB tables into unified US fiscal panel."""
    # Start with whatever we successfully parsed
    panels = []

    for name, df in parsed_tables.items():
        if df.empty:
            continue
        if 'year' in df.columns:
            logger.info(f"{name}: {len(df)} rows, years {df['year'].min()}-{df['year'].max()}")
            panels.append((name, df))
        else:
            logger.info(f"{name}: parsed {df.shape} but no year column identified")

    if not panels:
        return pd.DataFrame()

    # Use table_1_1 as base if available
    base_name, base = panels[0]
    result = base[['year']].drop_duplicates().sort_values('year').reset_index(drop=True)

    for name, df in panels:
        if 'year' in df.columns:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if 'year' in numeric_cols:
                numeric_cols.remove('year')
            # Prefix columns with table name to avoid conflicts
            renamed = df[['year'] + numeric_cols].copy()
            renamed.columns = ['year'] + [f"{name}_{c}" for c in numeric_cols]
            result = result.merge(renamed, on='year', how='outer')

    result = result.sort_values('year').reset_index(drop=True)
    return result


def run():
    logger.info("=" * 80)
    logger.info("DOWNLOADING OMB HISTORICAL TABLES")
    logger.info("=" * 80)

    parsed = {}
    for name, info in OMB_TABLES.items():
        fpath = download_table(name, info['url'])
        df = parse_omb_excel(fpath)
        parsed[name] = df
        if not df.empty:
            logger.info(f"{name}: {df.shape}")

    # Build combined panel
    combined = build_us_fiscal_panel(parsed)
    if not combined.empty:
        combined.to_parquet(OUTPUT_DIR / "omb_fiscal_panel.parquet", index=False)
        logger.info(f"Combined US fiscal panel: {len(combined)} years, "
                   f"{len(combined.columns)} columns")
        logger.info(f"Year range: {combined['year'].min()}-{combined['year'].max()}")

    # Save individual parsed tables
    for name, df in parsed.items():
        if not df.empty:
            df.to_parquet(OUTPUT_DIR / f"{name}_parsed.parquet", index=False)

    log = {
        'downloaded_at': pd.Timestamp.now().isoformat(),
        'tables': {name: {'rows': len(df), 'cols': len(df.columns)}
                  for name, df in parsed.items()},
    }
    with open(OUTPUT_DIR / "download_log.json", 'w') as f:
        json.dump(log, f, indent=2)

    logger.info("OMB DOWNLOAD COMPLETE")


if __name__ == "__main__":
    run()
