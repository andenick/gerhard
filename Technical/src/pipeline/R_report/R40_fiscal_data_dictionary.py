"""
Pipeline: Fiscal Data Dictionary
Auto-generates comprehensive data dictionary by scanning all panel files.
Project: Gerhard
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

MANIFEST = {
    "id": "R40",
    "name": "Fiscal Data Dictionary",
    "stage": "R",
    "description": "Auto-generates a data dictionary by scanning all panel Excel files.",
    "depends_on": ["P65", "P70", "P75", "P80", "P85", "P90", "P95", "P97", "P98"],
    "inputs": [
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True, "description": "Master fiscal panel"},
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": False, "description": "Revenue composition"},
        {"path": "Output/Data/expenditure_composition_panel.xlsx", "required": False, "description": "Expenditure composition"},
        {"path": "Output/Data/bop_panel.xlsx", "required": False, "description": "Balance of payments"},
        {"path": "Output/Data/exchange_rate_panel.xlsx", "required": False, "description": "Exchange rates"},
        {"path": "Output/Data/trade_panel.xlsx", "required": False, "description": "Trade composition"},
        {"path": "Output/Data/debt_composition_panel.xlsx", "required": False, "description": "Debt composition"},
        {"path": "Output/Data/social_outcomes_panel.xlsx", "required": False, "description": "Social outcomes"},
        {"path": "Output/Data/national_accounts_panel.xlsx", "required": False, "description": "National accounts"},
        {"path": "Output/Data/clean_tax_panel.xlsx", "required": False, "description": "Cleaned tax panel"},
        {"path": "Output/Data/balanced_panel.xlsx", "required": False, "description": "Balanced panel"},
        {"path": "Output/Data/enriched_tax_panel.xlsx", "required": False, "description": "Enriched tax panel"},
        {"path": "Output/Data/aggregates_panel.xlsx", "required": False, "description": "Aggregates panel"},
    ],
    "outputs": [
        {"path": "Output/Data/fiscal_data_dictionary.xlsx", "description": "Comprehensive data dictionary"},
    ],
    "timeout": 180,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")
    out = output_data_dir()

    panels = [
        ('master_fiscal_panel.xlsx', 'Master fiscal panel with tax, expenditure, debt, GDP'),
        ('revenue_composition_panel.xlsx', 'Tax revenue breakdown by type'),
        ('expenditure_composition_panel.xlsx', 'Government spending by economic and functional category'),
        ('bop_panel.xlsx', 'Balance of payments: current account, FDI, remittances'),
        ('exchange_rate_panel.xlsx', 'Exchange rates, REER, inflation, deflators'),
        ('trade_panel.xlsx', 'Trade composition, terms of trade, structure type'),
        ('debt_composition_panel.xlsx', 'External debt by type, maturity, creditor'),
        ('social_outcomes_panel.xlsx', 'Health, education, inequality, poverty'),
        ('national_accounts_panel.xlsx', 'GDP components and sector value added'),
        ('clean_tax_panel.xlsx', 'Cleaned tax panel with quality flags'),
        ('balanced_panel.xlsx', 'Balanced panel for econometrics'),
        ('enriched_tax_panel.xlsx', 'Tax panel with GDP and macro data'),
        ('aggregates_panel.xlsx', 'Regional and income group aggregates'),
    ]

    rows = []
    panels_found = 0

    for filename, description in panels:
        filepath = out / filename
        if not filepath.exists():
            logger.warning(f"  Panel not found: {filename}")
            continue

        panels_found += 1
        try:
            df = pd.read_excel(filepath)
            logger.info(f"  Scanning {filename}: {len(df)} rows, {len(df.columns)} columns")

            for col in df.columns:
                entry = {
                    'panel': filename,
                    'panel_description': description,
                    'column': col,
                    'dtype': str(df[col].dtype),
                    'non_null_count': int(df[col].notna().sum()),
                    'null_pct': round(df[col].isna().mean() * 100, 1),
                    'n_unique': int(df[col].nunique()) if df[col].dtype == 'object' else None,
                    'min_value': float(df[col].min()) if pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any() else None,
                    'max_value': float(df[col].max()) if pd.api.types.is_numeric_dtype(df[col]) and df[col].notna().any() else None,
                    'sample_values': str(df[col].dropna().head(3).tolist()),
                }
                rows.append(entry)
        except Exception as e:
            logger.error(f"  Error scanning {filename}: {e}")

    if not rows:
        logger.error("No panel data found, cannot create data dictionary")
        return

    dict_df = pd.DataFrame(rows)
    output_path = out / 'fiscal_data_dictionary.xlsx'
    write_single_sheet_excel(dict_df, output_path, sheet_name='DataDictionary')

    logger.info(f"[R40] Complete: {len(dict_df)} entries across {panels_found} panels")
    logger.info(f"  Output: {output_path}")


if __name__ == "__main__":
    run()
