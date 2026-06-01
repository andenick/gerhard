"""
Master Catalogue Generator
Creates comprehensive index of all countries and their data
Project: Gerhard - Country by Country Expansion
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


class MasterCatalogueGenerator:
    """Generates master catalogue of all countries"""

    def __init__(self):
        self.countries = []
        self.load_all_countries()

    def load_all_countries(self):
        """Load configuration from all country directories"""
        logger.info("Loading country configurations...")

        for country_dir in sorted(COUNTRIES_DIR.iterdir()):
            if country_dir.is_dir():
                config_file = country_dir / "Technical" / "data" / "config.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        self.countries.append(config)

        logger.info(f"Loaded {len(self.countries)} countries")

    def generate_master_index_md(self):
        """Generate markdown master index"""
        logger.info("Generating MASTER_INDEX.md...")

        content = f"""# Master Country Index
## Gerhard - Country by Country Analysis

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
**Total Countries/Entities:** {len(self.countries)}

---

## Summary Statistics

### By Tier
"""

        # Count by tier
        tier_counts = {1: 0, 2: 0, 3: 0}
        for c in self.countries:
            tier_counts[c.get('tier', 3)] += 1

        content += f"""- **Tier 1 (Comprehensive):** {tier_counts[1]} countries
- **Tier 2 (Standard):** {tier_counts[2]} countries
- **Tier 3 (Basic):** {tier_counts[3]} countries

### By Status
"""

        # Count by status
        status_counts = {}
        for c in self.countries:
            status = c.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in sorted(status_counts.items()):
            content += f"- **{status.replace('_', ' ').title()}:** {count}\n"

        content += f"""
### Data Coverage
- **Countries with data:** {sum(1 for c in self.countries if c['data_collection']['national_data'])}
- **Total years of data:** {sum(c['data_years']['total_years'] for c in self.countries if c['data_collection']['national_data'])}
- **Average years per country:** {sum(c['data_years']['total_years'] for c in self.countries if c['data_collection']['national_data']) / len([c for c in self.countries if c['data_collection']['national_data']]):.1f}

---

## Complete Country List

| Country | Code | Tier | Years | Coverage | Latest Tax (% GDP) | Status |
|---------|------|------|-------|----------|-------------------|--------|
"""

        # Sort countries by name
        sorted_countries = sorted(self.countries, key=lambda x: x.get('country_name', ''))

        for c in sorted_countries:
            name = c.get('country_name', 'Unknown')
            code = c.get('country_code', '??')
            tier = c.get('tier', 3)
            years = c['data_years'].get('total_years', 0)
            coverage = f"{c['data_years'].get('first_year', 'N/A')}-{c['data_years'].get('last_year', 'N/A')}" if years > 0 else 'No data'
            latest_tax = c.get('tax_metrics', {}).get('latest_tax_pct_gdp', 'N/A')
            status = c.get('status', 'unknown').replace('_', ' ')

            # Format latest tax
            if isinstance(latest_tax, (int, float)):
                latest_tax_str = f"{latest_tax:.2f}%"
            else:
                latest_tax_str = "N/A"

            content += f"| {name} | {code} | {tier} | {years} | {coverage} | {latest_tax_str} | {status} |\n"

        content += f"""
---

## Tier 1 Countries (Comprehensive Analysis)

These {tier_counts[1]} countries receive the most detailed analysis including:
- Complete historical time series
- Tax structure breakdowns
- Subnational data (where applicable)
- Comprehensive PDF reports

"""

        tier1_countries = [c for c in sorted_countries if c.get('tier') == 1]
        for c in tier1_countries:
            name = c.get('country_name')
            code = c.get('country_code')
            years = c['data_years'].get('total_years', 0)
            content += f"- **{name}** ({code}): {years} years of data\n"

        content += f"""
---

## Tier 2 Countries (Standard Analysis)

These {tier_counts[2]} countries receive standard analysis:
- National tax revenue time series
- Basic tax structure
- Standard PDF reports

"""

        tier2_countries = [c for c in sorted_countries if c.get('tier') == 2]
        for c in tier2_countries:
            name = c.get('country_name')
            code = c.get('country_code')
            years = c['data_years'].get('total_years', 0)
            content += f"- **{name}** ({code}): {years} years of data\n"

        content += """
---

## Accessing Country Data

Each country has its own directory structure:

```
Countries/[COUNTRY_CODE]/
├── Output/
│   ├── Data/              # Excel data files
│   └── PDFs/              # PDF reports and charts
├── Technical/
│   ├── src/               # Country-specific scripts
│   ├── data/              # Raw and processed data
│   └── docs/              # LaTeX sources
├── [CODE]_PROFILE.md      # Country overview
└── [CODE]_SOURCES.md      # Data sources
```

---

**Index Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Save master index
        index_file = COUNTRIES_DIR / "MASTER_INDEX.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Created MASTER_INDEX.md")

    def generate_coverage_matrix(self):
        """Generate Excel data coverage matrix"""
        logger.info("Generating data coverage matrix...")

        # Prepare data for Excel
        data = []
        for c in self.countries:
            row = {
                'Country': c.get('country_name', ''),
                'Code': c.get('country_code', ''),
                'Tier': c.get('tier', 3),
                'National_Data': 'Yes' if c['data_collection']['national_data'] else 'No',
                'Subnational_Data': 'Yes' if c['data_collection']['subnational_data'] else 'No',
                'First_Year': c['data_years'].get('first_year', 'N/A'),
                'Last_Year': c['data_years'].get('last_year', 'N/A'),
                'Total_Years': c['data_years'].get('total_years', 0),
                'Avg_Tax_PCT_GDP': c.get('tax_metrics', {}).get('average_tax_pct_gdp', 'N/A'),
                'Latest_Tax_PCT_GDP': c.get('tax_metrics', {}).get('latest_tax_pct_gdp', 'N/A'),
                'Latest_Year': c.get('tax_metrics', {}).get('latest_year', 'N/A'),
                'Status': c.get('status', 'unknown'),
                'Report_Generated': 'Yes' if c['analysis'].get('report_generated', False) else 'No'
            }
            data.append(row)

        df = pd.DataFrame(data)
        df = df.sort_values('Country')

        # Save to Excel
        output_file = COUNTRIES_DIR / "DATA_COVERAGE_MATRIX.xlsx"
        write_single_sheet_excel(df, output_file, sheet_name='Coverage')
        logger.info(f"Created DATA_COVERAGE_MATRIX.xlsx with {len(df)} countries")

    def generate_quality_tiers_doc(self):
        """Generate quality tiers documentation"""
        logger.info("Generating QUALITY_TIERS.md...")

        tier1_count = sum(1 for c in self.countries if c.get('tier') == 1)
        tier2_count = sum(1 for c in self.countries if c.get('tier') == 2)
        tier3_count = sum(1 for c in self.countries if c.get('tier') == 3)

        tier1_avg = sum(c['data_years'].get('total_years', 0) for c in self.countries if c.get('tier') == 1) / tier1_count if tier1_count > 0 else 0
        tier2_avg = sum(c['data_years'].get('total_years', 0) for c in self.countries if c.get('tier') == 2) / tier2_count if tier2_count > 0 else 0
        tier3_avg = sum(c['data_years'].get('total_years', 0) for c in self.countries if c.get('tier') == 3) / tier3_count if tier3_count > 0 else 0

        content = f"""# Data Quality Tiers
## Gerhard - Country Classification System

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}

---

## Overview

Countries are classified into three quality tiers based on:
- Economic importance
- Data availability and quality
- Subnational data existence
- OECD membership status

---

## Tier 1: Comprehensive Analysis

**Count:** {tier1_count} countries
**Average Data Years:** {tier1_avg:.1f} years

### Criteria
- OECD members or major emerging economies
- Comprehensive historical data available
- Often have subnational (federal) data
- High economic and political importance
- Complete time series coverage

### Analysis Includes
- ✅ Complete historical time series
- ✅ Detailed tax structure breakdown
- ✅ Subnational data collection (where applicable)
- ✅ Multiple visualizations (10+ charts)
- ✅ Comprehensive PDF report (15-20 pages)
- ✅ State/provincial analysis for federal systems
- ✅ Historical policy analysis

### Countries
"""

        tier1_countries = sorted([c for c in self.countries if c.get('tier') == 1], key=lambda x: x.get('country_name', ''))
        for c in tier1_countries:
            years = c['data_years'].get('total_years', 0)
            content += f"- **{c.get('country_name')}** ({c.get('country_code')}): {years} years\n"

        content += f"""
---

## Tier 2: Standard Analysis

**Count:** {tier2_count} countries
**Average Data Years:** {tier2_avg:.1f} years

### Criteria
- Emerging market economies
- Good data quality and coverage
- Complete or near-complete time series
- Some subnational data may be available
- Regional economic importance

### Analysis Includes
- ✅ National tax revenue time series
- ✅ Basic tax structure analysis
- ✅ Regional data if available
- ✅ Key visualizations (5-7 charts)
- ✅ Standard PDF report (8-12 pages)
- ✅ Historical trends analysis

### Countries
"""

        tier2_countries = sorted([c for c in self.countries if c.get('tier') == 2], key=lambda x: x.get('country_name', ''))
        for c in tier2_countries:
            years = c['data_years'].get('total_years', 0)
            content += f"- **{c.get('country_name')}** ({c.get('country_code')}): {years} years\n"

        content += f"""
---

## Tier 3: Basic Analysis

**Count:** {tier3_count} countries/entities
**Average Data Years:** {tier3_avg:.1f} years

### Criteria
- Developing economies and regional aggregates
- Limited data availability
- Gaps in time series coverage
- National level data only
- Data quality varies

### Analysis Includes
- ✅ National tax revenue data
- ✅ Available years coverage
- ✅ Basic context and summary statistics
- ✅ Essential visualizations (2-4 charts)
- ✅ Basic PDF report (4-6 pages)
- ✅ Comparative regional context

### Note
Tier 3 includes both individual countries and regional/income aggregates provided by the World Bank.

---

## Data Quality Metrics by Tier

| Metric | Tier 1 | Tier 2 | Tier 3 |
|--------|--------|--------|--------|
| Countries | {tier1_count} | {tier2_count} | {tier3_count} |
| Avg Years | {tier1_avg:.1f} | {tier2_avg:.1f} | {tier3_avg:.1f} |
| Subnational Data | Often | Sometimes | Rarely |
| Report Pages | 15-20 | 8-12 | 4-6 |
| Visualizations | 10+ | 5-7 | 2-4 |

---

**Document Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Save quality tiers doc
        quality_file = COUNTRIES_DIR / "QUALITY_TIERS.md"
        with open(quality_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info("Created QUALITY_TIERS.md")

    def generate_all(self):
        """Generate all catalogue documents"""
        logger.info("=" * 60)
        logger.info("Generating Master Catalogue")
        logger.info("=" * 60)

        self.generate_master_index_md()
        self.generate_coverage_matrix()
        self.generate_quality_tiers_doc()

        logger.info("\n" + "=" * 60)
        logger.info("Catalogue Generation Complete!")
        logger.info("=" * 60)
        logger.info("Created:")
        logger.info("  - MASTER_INDEX.md")
        logger.info("  - DATA_COVERAGE_MATRIX.xlsx")
        logger.info("  - QUALITY_TIERS.md")
        logger.info(f"Location: {COUNTRIES_DIR}")


def main():
    logger.info("Master Catalogue Generator - Gerhard Project")

    generator = MasterCatalogueGenerator()
    generator.generate_all()

    logger.info("\nCatalogue complete!")
    logger.info("Next steps:")
    logger.info("1. Review country coverage")
    logger.info("2. Begin country analysis generation")
    logger.info("3. Create country reports")


if __name__ == "__main__":
    main()
