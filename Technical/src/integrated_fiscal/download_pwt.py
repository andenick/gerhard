"""Download Penn World Table 10.01 and construct profit rate proxy panel.
183 countries, 1950-2019, labor share + capital stock + output.
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

PWT_URL = "https://dataverse.nl/api/access/datafile/354098"
OUTPUT_DIR = raw_data_dir() / "profit_rates"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def download_pwt():
    xlsx_path = OUTPUT_DIR / "pwt1001.xlsx"
    if xlsx_path.exists():
        logger.info(f"Already downloaded: {xlsx_path} ({xlsx_path.stat().st_size / 1e6:.1f} MB)")
    else:
        logger.info(f"Downloading PWT 10.01...")
        resp = requests.get(PWT_URL, timeout=120, allow_redirects=True)
        resp.raise_for_status()
        xlsx_path.write_bytes(resp.content)
        logger.info(f"Downloaded: {xlsx_path.stat().st_size / 1e6:.1f} MB")

    logger.info("Reading file...")
    # The Dataverse download is actually a Stata .dta file (XML format)
    try:
        df = pd.read_stata(xlsx_path)
    except Exception:
        try:
            df = pd.read_excel(xlsx_path, sheet_name="Data")
        except Exception:
            xl = pd.ExcelFile(xlsx_path)
            logger.info(f"Sheets: {xl.sheet_names}")
            df = pd.read_excel(xlsx_path, sheet_name=xl.sheet_names[-1])

    logger.info(f"PWT panel: {len(df):,} rows, {df['countrycode'].nunique()} countries")
    logger.info(f"Years: {df['year'].min()}-{df['year'].max()}")
    logger.info(f"Columns: {df.columns.tolist()}")

    # Save full as parquet
    df.to_parquet(OUTPUT_DIR / "pwt1001_full.parquet", index=False)

    # Extract and compute profit rate proxy
    key_vars = ['countrycode', 'country', 'year', 'labsh', 'irr', 'delta',
                'rgdpna', 'rkna', 'emp', 'avh', 'ctfp', 'csh_i', 'csh_g', 'csh_x', 'csh_m']
    available = [v for v in key_vars if v in df.columns]
    panel = df[available].copy()

    if 'labsh' in panel.columns:
        panel['capital_share'] = 1 - panel['labsh']

    # PWT provides 'irr' = internal rate of return on capital (THE profit rate)
    if 'irr' in df.columns:
        panel['profit_rate_irr'] = df['irr']
        logger.info(f"Using PWT built-in IRR (internal rate of return on capital)")

    # Also compute output-capital ratio as Shaikh-style proxy
    if 'rgdpna' in panel.columns and 'rkna' in panel.columns:
        valid_mask = (panel['rkna'] > 0) & (panel['rgdpna'] > 0)
        panel.loc[valid_mask, 'output_capital_ratio'] = (
            panel.loc[valid_mask, 'rgdpna'] / panel.loc[valid_mask, 'rkna'])
        panel.loc[valid_mask, 'profit_rate_proxy'] = (
            panel.loc[valid_mask, 'capital_share'] * panel.loc[valid_mask, 'output_capital_ratio'])

    panel.to_parquet(OUTPUT_DIR / "pwt_profit_rate_panel.parquet", index=False)
    logger.info(f"Profit rate panel: {len(panel):,} rows")

    # Summary by decade
    if 'labsh' in panel.columns:
        panel['decade'] = (panel['year'] // 10) * 10
        ls_by_decade = panel.groupby('decade')['labsh'].mean()
        logger.info(f"Global avg labor share by decade:\n{ls_by_decade.to_string()}")

        if 'profit_rate_proxy' in panel.columns:
            pr_by_decade = panel.groupby('decade')['profit_rate_proxy'].mean()
            logger.info(f"Global avg profit rate proxy by decade:\n{pr_by_decade.to_string()}")

    log = {
        'downloaded_at': pd.Timestamp.now().isoformat(),
        'source': PWT_URL,
        'rows': len(df),
        'countries': int(df['countrycode'].nunique()),
        'year_range': [int(df['year'].min()), int(df['year'].max())],
        'profit_panel_rows': len(panel),
        'variables': available,
    }
    with open(OUTPUT_DIR / "download_log.json", 'w') as f:
        json.dump(log, f, indent=2)

    logger.info("PWT DOWNLOAD COMPLETE")
    return panel


if __name__ == "__main__":
    download_pwt()
