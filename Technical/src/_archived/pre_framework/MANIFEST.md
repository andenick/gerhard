# Pre-Framework Scripts Archive

These scripts were archived after being replaced by numbered pipeline scripts.
Archived: April 1, 2026

| Old Script | Replaced By | Pipeline Location |
|------------|------------|-------------------|
| download_tax_data.py | L00 | pipeline/L_load/L00_download_worldbank_tax.py |
| fetch_us_tax_data.py | L40 | pipeline/L_load/L40_fetch_us_tax_data.py |
| process_tax_data.py | P00 | pipeline/P_process/P00_standardize_tax_data.py |
| analyze_tax_burden.py | A00 | pipeline/A_analyze/A00_analyze_tax_burden.py |
| visualize_tax_burden.py | V00 | pipeline/V_visualize/V00_visualize_tax_burden.py |
| generate_latex_reports.py | R00 | pipeline/R_report/R00_generate_latex_reports.py |

## Scripts NOT archived (still in Technical/src/)

The following old scripts have NOT yet been replaced by pipeline equivalents:
- All remaining download_*.py (L05-L35 not yet migrated)
- All remaining analyze_*.py, visualize_*.py, create_*.py, integrate_*.py
- Utility scripts: run_pipeline.py, fiscal_api.py, etc.

These will be migrated in future waves.
