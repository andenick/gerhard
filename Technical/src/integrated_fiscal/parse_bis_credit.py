"""Parse BIS Total Credit to Non-Financial Sector (household + corporate + govt)."""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir

logger = setup_logging(__name__)

INPUT = raw_data_dir() / "bis" / "totcredit.xlsx"
OUTPUT_DIR = raw_data_dir() / "bis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run():
    logger.info("=" * 80)
    logger.info("PARSING BIS TOTAL CREDIT DATA")
    logger.info("=" * 80)

    if not INPUT.exists():
        logger.error(f"BIS file not found: {INPUT}")
        return {}

    xl = pd.ExcelFile(INPUT)
    logger.info(f"Sheets: {xl.sheet_names}")

    # The main data is in "Quarterly Series"
    target_sheet = next((s for s in xl.sheet_names if 'quarter' in s.lower()), xl.sheet_names[-1])
    logger.info(f"Reading sheet: {target_sheet}")

    # BIS has multi-row headers — read raw first
    raw = pd.read_excel(INPUT, sheet_name=target_sheet, header=None, nrows=8)
    logger.info(f"Header rows sample:")
    for i in range(min(5, len(raw))):
        non_null = [(j, str(v)[:30]) for j, v in enumerate(raw.iloc[i]) if pd.notna(v)]
        if non_null:
            logger.info(f"  Row {i}: {non_null[:6]}")

    # Read the actual data — try with header at row that looks right
    # BIS typically has: Row 0 = title, Row 1-3 = dimension headers, Row 4+ = data
    for header_row in range(5):
        try:
            df = pd.read_excel(INPUT, sheet_name=target_sheet, header=header_row)
            # Check if first column looks like dates
            first_col = df.iloc[:, 0]
            if first_col.dtype in ['datetime64[ns]', 'object']:
                dates = pd.to_datetime(first_col, errors='coerce')
                if dates.notna().sum() > 50:
                    logger.info(f"Found dates at header_row={header_row}")
                    df.iloc[:, 0] = dates
                    break
        except Exception:
            continue

    logger.info(f"Data shape: {df.shape}")
    logger.info(f"Columns (first 10): {df.columns.tolist()[:10]}")

    # Convert all data columns to numeric before saving
    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Save raw parsed
    output_path = OUTPUT_DIR / "bis_credit_raw.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"Saved raw: {output_path}")

    # Try to structure: the columns should indicate country + credit type
    # BIS column headers often encode: "Country:Sector:Unit"
    # Let's extract what we can
    col_info = []
    for col in df.columns[1:]:  # Skip date column
        col_str = str(col)
        col_info.append(col_str[:50])

    logger.info(f"Column patterns (sample): {col_info[:5]}")

    logger.info("BIS CREDIT PARSING COMPLETE")
    return {'shape': df.shape}


if __name__ == "__main__":
    run()
