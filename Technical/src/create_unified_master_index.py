"""
Create Unified Master Index
===========================

Generates comprehensive master index combining:
- Tax revenue data (202 countries)
- Expenditure data (164 countries)
- Country profiles and metadata
- Data coverage matrix

Created: October 10, 2025
Project: Gerhard - Fiscal Analysis
"""

import pandas as pd
import json
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import countries_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

COUNTRIES_DIR = countries_dir()
OUTPUT_DIR = countries_dir()


class UnifiedIndexCreator:
    """Create unified master index of all countries and data"""

    def __init__(self):
        self.countries = []
        self.tax_data = None
        self.expenditure_data = None

    def load_tax_data(self):
        """Load tax revenue data"""
        logger.info("Loading tax revenue data...")

        tax_file = BASE_DIR / "Output" / "Data" / "unified_international_tax_data.xlsx"
        if tax_file.exists():
            self.tax_data = pd.read_excel(tax_file)
            logger.info(f"  ✅ Loaded tax data: {len(self.tax_data):,} observations")
            logger.info(f"     Countries: {self.tax_data['country_code'].nunique()}")
        else:
            logger.warning("  ⚠️  Tax data file not found")

    def load_expenditure_summary(self):
        """Load expenditure integration summary"""
        logger.info("Loading expenditure data summary...")

        exp_summary = BASE_DIR / "expenditure_integration_summary.json"
        if exp_summary.exists():
            with open(exp_summary, 'r') as f:
                self.expenditure_data = json.load(f)
            logger.info(f"  ✅ Loaded expenditure summary")
        else:
            logger.warning("  ⚠️  Expenditure summary not found")

    def scan_countries(self):
        """Scan all country directories and gather metadata"""
        logger.info("\nScanning country directories...")

        country_dirs = sorted([d for d in COUNTRIES_DIR.iterdir() if d.is_dir() and len(d.name) in [2, 3]])
        logger.info(f"Found {len(country_dirs)} country directories")

        for country_dir in country_dirs:
            country_code = country_dir.name

            country_info = {
                'code': country_code,
                'name': None,
                'has_tax_data': False,
                'has_expenditure_data': False,
                'tax_years': None,
                'exp_years': None,
                'tax_latest': None,
                'exp_latest': None,
                'tier': None,
                'data_files': 0
            }

            # Check for tax data
            tax_file = country_dir / "Output" / "Data" / f"{country_code.lower()}_national_tax_data.xlsx"
            if tax_file.exists():
                country_info['has_tax_data'] = True
                try:
                    tax_df = pd.read_excel(tax_file)
                    if len(tax_df) > 0:
                        country_info['name'] = tax_df['country_name'].iloc[0] if 'country_name' in tax_df.columns else country_code
                        country_info['tax_years'] = len(tax_df)
                        country_info['tax_latest'] = float(tax_df['tax_revenue_pct_gdp'].iloc[-1]) if 'tax_revenue_pct_gdp' in tax_df.columns else None
                        country_info['data_files'] += 1
                except:
                    pass

            # Check for expenditure data
            exp_file = country_dir / "Output" / "Data" / f"{country_code.lower()}_government_expenditure.xlsx"
            if exp_file.exists():
                country_info['has_expenditure_data'] = True
                try:
                    exp_df = pd.read_excel(exp_file)
                    if len(exp_df) > 0:
                        if not country_info['name']:
                            country_info['name'] = exp_df['Country'].iloc[0] if 'Country' in exp_df.columns else country_code
                        country_info['exp_years'] = len(exp_df)
                        country_info['data_files'] += 1
                except:
                    pass

            # Determine tier (from config if available)
            config_file = country_dir / "Technical" / "data" / "config.json"
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        country_info['tier'] = config.get('tier', 3)
                except:
                    country_info['tier'] = 3
            else:
                country_info['tier'] = 3

            if not country_info['name']:
                country_info['name'] = country_code

            self.countries.append(country_info)

        logger.info(f"✅ Scanned {len(self.countries)} countries")

    def create_master_index_markdown(self):
        """Create unified master index in Markdown format"""
        logger.info("\nCreating unified master index (Markdown)...")

        # Sort countries by name
        sorted_countries = sorted(self.countries, key=lambda x: x['name'])

        # Statistics
        total_countries = len(sorted_countries)
        with_tax = sum(1 for c in sorted_countries if c['has_tax_data'])
        with_exp = sum(1 for c in sorted_countries if c['has_expenditure_data'])
        with_both = sum(1 for c in sorted_countries if c['has_tax_data'] and c['has_expenditure_data'])

        tier_1 = sum(1 for c in sorted_countries if c['tier'] == 1)
        tier_2 = sum(1 for c in sorted_countries if c['tier'] == 2)
        tier_3 = sum(1 for c in sorted_countries if c['tier'] == 3)

        # Build markdown
        md = f"""# Unified Master Index
## Gerhard - Global Fiscal Analysis

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Countries:** {total_countries}

---

## Summary Statistics

### Data Coverage
- **Countries with tax revenue data:** {with_tax}
- **Countries with expenditure data:** {with_exp}
- **Countries with both datasets:** {with_both}
- **Countries with either dataset:** {with_tax + with_exp - with_both}

### By Analysis Tier
- **Tier 1 (Comprehensive):** {tier_1} countries
- **Tier 2 (Standard):** {tier_2} countries
- **Tier 3 (Basic):** {tier_3} countries

### Data Files Created
- **Total data files:** {sum(c['data_files'] for c in sorted_countries)}
- **Tax data files:** {with_tax}
- **Expenditure data files:** {with_exp}

---

## Complete Country List

| Country | Code | Tier | Tax Data | Exp Data | Tax Years | Exp Years | Latest Tax (% GDP) | Status |
|---------|------|------|----------|----------|-----------|-----------|-------------------|--------|
"""

        for country in sorted_countries:
            tax_icon = "✅" if country['has_tax_data'] else "❌"
            exp_icon = "✅" if country['has_expenditure_data'] else "❌"
            tax_years = country['tax_years'] if country['tax_years'] else "-"
            exp_years = country['exp_years'] if country['exp_years'] else "-"
            tax_latest = f"{country['tax_latest']:.2f}%" if country['tax_latest'] else "-"

            status = "complete" if (country['has_tax_data'] or country['has_expenditure_data']) else "no data"

            md += f"| {country['name']} | {country['code']} | {country['tier']} | {tax_icon} | {exp_icon} | {tax_years} | {exp_years} | {tax_latest} | {status} |\n"

        md += f"""
---

## Data Coverage by Tier

### Tier 1 Countries (Comprehensive Analysis)

**Count:** {tier_1} countries

These countries receive the most detailed analysis:
- Complete historical time series (typically 30+ years)
- Tax structure breakdowns
- Expenditure by sector
- Comprehensive PDF reports

"""

        tier_1_countries = [c for c in sorted_countries if c['tier'] == 1]
        for country in tier_1_countries:
            both = "✅✅" if (country['has_tax_data'] and country['has_expenditure_data']) else ("✅ Tax" if country['has_tax_data'] else "✅ Exp")
            md += f"- **{country['name']}** ({country['code']}): {both}\n"

        md += f"""
---

### Tier 2 Countries (Standard Analysis)

**Count:** {tier_2} countries

These countries receive standard analysis:
- National tax revenue and/or expenditure time series
- Basic structure analysis
- Standard PDF reports

"""

        tier_2_countries = [c for c in sorted_countries if c['tier'] == 2]
        for country in tier_2_countries:
            both = "✅✅" if (country['has_tax_data'] and country['has_expenditure_data']) else ("✅ Tax" if country['has_tax_data'] else "✅ Exp")
            md += f"- **{country['name']}** ({country['code']}): {both}\n"

        md += """
---

## Accessing Country Data

Each country has its own directory structure:

```
Countries/[COUNTRY_CODE]/
├── Output/
│   ├── Data/              # Excel data files
│   │   ├── {code}_national_tax_data.xlsx
│   │   ├── {code}_government_expenditure.xlsx
│   │   └── {code}_*_summary.json
│   └── PDFs/              # PDF reports and charts
├── Technical/
│   ├── src/               # Country-specific scripts
│   ├── data/              # Raw and processed data
│   │   └── config.json    # Country metadata
│   └── docs/              # LaTeX sources
├── [CODE]_PROFILE.md      # Country overview
└── [CODE]_SOURCES.md      # Data sources
```

---

## Data Indicators Available

### Tax Revenue
- **Total tax revenue** (% of GDP)
- **Time coverage:** 1972-2023 (varies by country)
- **Countries:** """ + str(with_tax) + """

### Government Expenditure
- **Total government expenditure** (% of GDP)
- **Education expenditure** (% of GDP)
- **Health expenditure** (% of GDP)
- **Military expenditure** (% of GDP)
- **R&D expenditure** (% of GDP)
- **Time coverage:** 1960-2024 (varies by country and indicator)
- **Countries:** """ + str(with_exp) + """

---

## Quick Navigation

### By Region
- [Africa](#) (coming soon)
- [Americas](#) (coming soon)
- [Asia](#) (coming soon)
- [Europe](#) (coming soon)
- [Oceania](#) (coming soon)

### By Income Level
- [High Income](#) (coming soon)
- [Upper-Middle Income](#) (coming soon)
- [Lower-Middle Income](#) (coming soon)
- [Low Income](#) (coming soon)

### By Data Type
- **Both Tax & Expenditure:** """ + str(with_both) + """ countries
- **Tax Only:** """ + str(with_tax - with_both) + """ countries
- **Expenditure Only:** """ + str(with_exp - with_both) + """ countries

---

## Using the Index

### Finding a Country
1. Use Ctrl+F (Cmd+F on Mac) to search for country name or code
2. Check the table for data availability (✅ = available, ❌ = not available)
3. Navigate to `Countries/[CODE]/` directory

### Understanding Tiers
- **Tier 1:** Major economies and countries with comprehensive data
- **Tier 2:** Important countries with good data availability
- **Tier 3:** All other countries and aggregates

### Data Quality
- **Complete:** Both tax and expenditure data available
- **Partial:** Either tax or expenditure data available
- **No data:** Directory exists but no data integrated yet

---

**Index Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Project:** Gerhard - Global Fiscal Analysis Platform
**Pattern:** Publication-quality data standards

---

*For technical documentation, see `Technical/docs/`*
*For usage guides, see `Output/README.md`*
"""

        # Save markdown file
        output_file = OUTPUT_DIR / "UNIFIED_MASTER_INDEX.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md)

        logger.info(f"✅ Saved: {output_file.name}")
        return output_file

    def create_data_coverage_matrix(self):
        """Create data coverage matrix in Excel format"""
        logger.info("\nCreating data coverage matrix (Excel)...")

        # Prepare data for DataFrame
        matrix_data = []
        for country in self.countries:
            matrix_data.append({
                'Country Code': country['code'],
                'Country Name': country['name'],
                'Tier': country['tier'],
                'Tax Data Available': 'Yes' if country['has_tax_data'] else 'No',
                'Expenditure Data Available': 'Yes' if country['has_expenditure_data'] else 'No',
                'Tax Years of Coverage': country['tax_years'] if country['tax_years'] else 0,
                'Expenditure Years of Coverage': country['exp_years'] if country['exp_years'] else 0,
                'Latest Tax Revenue (% GDP)': country['tax_latest'] if country['tax_latest'] else None,
                'Total Data Files': country['data_files'],
                'Completeness': 'Both' if (country['has_tax_data'] and country['has_expenditure_data'])
                               else ('Tax Only' if country['has_tax_data']
                               else ('Expenditure Only' if country['has_expenditure_data'] else 'None'))
            })

        df = pd.DataFrame(matrix_data)

        # Sort by country name
        df = df.sort_values('Country Name')

        # Save to Excel
        output_file = OUTPUT_DIR / "DATA_COVERAGE_MATRIX.xlsx"
        write_single_sheet_excel(df, output_file, sheet_name='Coverage Matrix')

        logger.info(f"✅ Saved: {output_file.name}")
        logger.info(f"   Rows: {len(df)}")
        logger.info(f"   Columns: {len(df.columns)}")

        return output_file

    def create_summary_statistics(self):
        """Create summary statistics JSON"""
        logger.info("\nCreating summary statistics...")

        stats = {
            'generated_at': datetime.now().isoformat(),
            'total_countries': len(self.countries),
            'data_coverage': {
                'tax_revenue': sum(1 for c in self.countries if c['has_tax_data']),
                'expenditure': sum(1 for c in self.countries if c['has_expenditure_data']),
                'both_datasets': sum(1 for c in self.countries if c['has_tax_data'] and c['has_expenditure_data']),
                'either_dataset': sum(1 for c in self.countries if c['has_tax_data'] or c['has_expenditure_data'])
            },
            'by_tier': {
                'tier_1': sum(1 for c in self.countries if c['tier'] == 1),
                'tier_2': sum(1 for c in self.countries if c['tier'] == 2),
                'tier_3': sum(1 for c in self.countries if c['tier'] == 3)
            },
            'data_files': {
                'total': sum(c['data_files'] for c in self.countries),
                'tax_files': sum(1 for c in self.countries if c['has_tax_data']),
                'expenditure_files': sum(1 for c in self.countries if c['has_expenditure_data'])
            },
            'completeness': {
                'both': sum(1 for c in self.countries if c['has_tax_data'] and c['has_expenditure_data']),
                'tax_only': sum(1 for c in self.countries if c['has_tax_data'] and not c['has_expenditure_data']),
                'expenditure_only': sum(1 for c in self.countries if c['has_expenditure_data'] and not c['has_tax_data']),
                'none': sum(1 for c in self.countries if not c['has_tax_data'] and not c['has_expenditure_data'])
            }
        }

        output_file = OUTPUT_DIR / "unified_index_statistics.json"
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)

        logger.info(f"✅ Saved: {output_file.name}")

        return stats

    def run(self):
        """Execute complete index creation"""
        logger.info("="*80)
        logger.info("Unified Master Index Creation")
        logger.info("="*80 + "\n")

        # Load data
        self.load_tax_data()
        self.load_expenditure_summary()

        # Scan countries
        self.scan_countries()

        # Create outputs
        md_file = self.create_master_index_markdown()
        excel_file = self.create_data_coverage_matrix()
        stats = self.create_summary_statistics()

        # Print summary
        logger.info("\n" + "="*80)
        logger.info("✅ Unified Master Index Complete!")
        logger.info("="*80)
        logger.info(f"\nFiles created:")
        logger.info(f"  1. {md_file.name}")
        logger.info(f"  2. {excel_file.name}")
        logger.info(f"  3. unified_index_statistics.json")
        logger.info(f"\nCoverage:")
        logger.info(f"  Total countries: {stats['total_countries']}")
        logger.info(f"  With tax data: {stats['data_coverage']['tax_revenue']}")
        logger.info(f"  With expenditure data: {stats['data_coverage']['expenditure']}")
        logger.info(f"  With both: {stats['data_coverage']['both_datasets']}")
        logger.info("\nAll files saved to: Countries/")


def main():
    creator = UnifiedIndexCreator()
    creator.run()


if __name__ == "__main__":
    main()
