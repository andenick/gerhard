"""Download Jordà-Schularick-Taylor Macrohistory Database (v6).
18 advanced economies, 1870-2020, fiscal + financial + macro variables.
"""

import requests
import pandas as pd
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

JST_URL = "https://www.macrohistory.net/app/download/9834512569/JSTdatasetR6.dta"
OUTPUT_DIR = raw_data_dir() / "jst"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_jst():
    xlsx_path = OUTPUT_DIR / "JSTdatasetR6.xlsx"
    if xlsx_path.exists():
        logger.info(f"Already downloaded: {xlsx_path} ({xlsx_path.stat().st_size / 1e6:.1f} MB)")
    else:
        # The macrohistory.net download serves an Excel file regardless of extension
        logger.info(f"Downloading JST v6...")
        resp = requests.get(JST_URL, timeout=120)
        resp.raise_for_status()
        xlsx_path.write_bytes(resp.content)
        logger.info(f"Downloaded: {xlsx_path.stat().st_size / 1e6:.1f} MB")

    logger.info("Reading Excel file...")
    df = pd.read_excel(xlsx_path)
    logger.info(f"Full dataset: {len(df):,} rows, {len(df.columns)} columns")
    logger.info(f"Countries: {df['iso'].nunique()} — {sorted(df['iso'].unique())}")
    logger.info(f"Years: {df['year'].min()}-{df['year'].max()}")

    # Save full as parquet
    parquet_path = OUTPUT_DIR / "JSTdatasetR6.parquet"
    df.to_parquet(parquet_path, index=False)
    logger.info(f"Saved full parquet: {parquet_path.stat().st_size / 1e6:.1f} MB")

    # Extract fiscal panel
    fiscal_vars = ['iso', 'year', 'revenue', 'expenditure', 'debtgdp',
                   'stir', 'ltrate', 'cpi', 'rgdpmad', 'gdp', 'pop',
                   'iy', 'ca', 'narrowm', 'money', 'stocks', 'hpnom',
                   'tloans', 'tmort', 'thh', 'tbus',
                   'crisisJST', 'crisisJST_BVX']
    available = [v for v in fiscal_vars if v in df.columns]
    fiscal = df[available].copy()
    fiscal = fiscal.rename(columns={'iso': 'country_code'})

    # Compute derived variables
    if 'revenue' in fiscal.columns and 'expenditure' in fiscal.columns:
        fiscal['fiscal_balance'] = fiscal['revenue'] - fiscal['expenditure']
    if 'debtgdp' in fiscal.columns:
        fiscal['debt_change'] = fiscal.groupby('country_code')['debtgdp'].diff()

    fiscal_path = OUTPUT_DIR / "jst_fiscal_panel.parquet"
    fiscal.to_parquet(fiscal_path, index=False)
    logger.info(f"Fiscal panel: {len(fiscal):,} rows, {len(available)} variables")
    logger.info(f"Fiscal vars: {available}")

    # Summary
    if 'debtgdp' in fiscal.columns:
        by_decade = fiscal.copy()
        by_decade['decade'] = (by_decade['year'] // 10) * 10
        debt_by_decade = by_decade.groupby('decade')['debtgdp'].mean()
        logger.info(f"Avg debt/GDP by decade:\n{debt_by_decade.to_string()}")

    log = {
        'downloaded_at': pd.Timestamp.now().isoformat(),
        'source': JST_URL,
        'full_rows': len(df),
        'full_columns': len(df.columns),
        'countries': sorted(df['iso'].unique().tolist()),
        'year_range': [int(df['year'].min()), int(df['year'].max())],
        'fiscal_panel_rows': len(fiscal),
        'fiscal_variables': available,
    }
    with open(OUTPUT_DIR / "download_log.json", 'w') as f:
        json.dump(log, f, indent=2)

    logger.info("JST DOWNLOAD COMPLETE")
    return fiscal


if __name__ == "__main__":
    download_jst()
