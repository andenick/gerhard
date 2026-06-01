"""Standardized data I/O utilities for Gerhard."""
import pandas as pd
from pathlib import Path
from .logging_setup import setup_logging

logger = setup_logging(__name__)


def write_single_sheet_excel(
    df: pd.DataFrame,
    filepath: Path,
    sheet_name: str = "Data",
    index: bool = False
) -> None:
    """Write a DataFrame to Excel with exactly one sheet.

    Enforces the one-sheet-per-file Excel standard.

    Args:
        df: DataFrame to write
        filepath: Output path (.xlsx)
        sheet_name: Name for the single sheet
        index: Whether to include the index
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=index)

        # Auto-adjust column widths
        worksheet = writer.sheets[sheet_name]
        for column in worksheet.columns:
            max_length = 0
            col_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except (TypeError, AttributeError):
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[col_letter].width = adjusted_width

    logger.info(f"Wrote {len(df)} rows to {filepath}")


def read_excel_safe(filepath: Path, **kwargs) -> pd.DataFrame:
    """Read an Excel file with error handling.

    Args:
        filepath: Path to Excel file
        **kwargs: Additional arguments passed to pd.read_excel

    Returns:
        DataFrame, or empty DataFrame if file not found
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.warning(f"File not found: {filepath}")
        return pd.DataFrame()

    try:
        return pd.read_excel(filepath, **kwargs)
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return pd.DataFrame()
