"""Download extended IMF DataMapper indicators — private debt + additional fiscal."""

import requests
import pandas as pd
import json
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

OUTPUT_DIR = raw_data_dir() / "imf" / "gfs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INDICATORS = {
    "HH_ALL": "Household debt, all instruments",
    "HH_LS": "Household debt, loans and securities",
    "NFC_ALL": "Nonfinancial corporate debt, all instruments",
    "NFC_LS": "NFC debt, loans and securities",
    "Privatedebt_all": "Private debt, all instruments",
    "PVD_LS": "Private debt, loans and securities",
    "CG_DEBT_GDP": "Central Government Debt",
    "GG_DEBT_GDP": "General Government Debt",
    "NFPS_DEBT_GDP": "Nonfinancial Public Sector Debt",
    "PS_DEBT_GDP": "Public Sector Debt",
}


def run():
    logger.info("=" * 80)
    logger.info("DOWNLOADING IMF EXTENDED INDICATORS (PRIVATE DEBT)")
    logger.info("=" * 80)

    all_data = []
    for code, name in INDICATORS.items():
        url = f"https://www.imf.org/external/datamapper/api/v1/{code}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                values = data.get("values", {}).get(code, {})
                for country, years in values.items():
                    for year, value in years.items():
                        all_data.append({
                            "country_code": country,
                            "year": int(year),
                            "indicator": code,
                            "indicator_name": name,
                            "value": float(value),
                        })
                logger.info(f"  {code:20s}: {len(values):3d} countries")
            else:
                logger.warning(f"  {code:20s}: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"  {code:20s}: {e}")
        time.sleep(0.3)

    if not all_data:
        logger.error("No data downloaded")
        return

    df = pd.DataFrame(all_data)
    logger.info(f"\nTotal: {len(df):,} obs, {df['country_code'].nunique()} countries")

    # Save long format
    df.to_parquet(OUTPUT_DIR / "imf_private_debt.parquet", index=False)

    # Wide format
    wide = df.pivot_table(index=["country_code", "year"], columns="indicator",
                         values="value", aggfunc="first").reset_index()
    wide.columns.name = None
    wide.to_parquet(OUTPUT_DIR / "imf_private_debt_wide.parquet", index=False)
    logger.info(f"Wide panel: {len(wide):,} rows × {len(wide.columns)} cols")

    # Merge with existing fiscal data
    existing_path = OUTPUT_DIR / "imf_datamapper_fiscal.parquet"
    if existing_path.exists():
        existing = pd.read_parquet(existing_path)
        combined = pd.concat([existing, df], ignore_index=True).drop_duplicates(
            subset=["country_code", "year", "indicator"])
        combined.to_parquet(existing_path, index=False)
        logger.info(f"Combined with existing: {len(combined):,} total obs")

    log = {'downloaded_at': pd.Timestamp.now().isoformat(), 'indicators': {k: v for k, v in INDICATORS.items()},
           'total_rows': len(df)}
    with open(OUTPUT_DIR / "download_extended_log.json", 'w') as f:
        json.dump(log, f, indent=2)

    logger.info("IMF EXTENDED DOWNLOAD COMPLETE")


if __name__ == "__main__":
    run()
