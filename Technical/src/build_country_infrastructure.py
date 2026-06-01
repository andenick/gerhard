"""
Country Infrastructure Builder
Creates directory structure and foundational files for all countries
Project: Gerhard - Country by Country Expansion
"""

import pandas as pd
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, countries_dir

logger = setup_logging(__name__)

COUNTRIES_DIR = countries_dir()
DATA_DIR = output_data_dir()


class CountryInfrastructureBuilder:
    """Builds complete directory structure for country-by-country analysis"""

    def __init__(self):
        self.country_list = self.load_country_list()
        self.quality_tiers = self.assign_quality_tiers()

    def load_country_list(self):
        """Load list of all countries from World Bank data"""
        logger.info("Loading country list from data...")

        # Load from existing international data
        intl_file = DATA_DIR / "international_historical_tax_data.xlsx"
        if intl_file.exists():
            df = pd.read_excel(intl_file)

            # Parse country_name which is stored as string representation of dict
            import ast
            df['country_dict'] = df['country_name'].apply(ast.literal_eval)
            df['country_code'] = df['country_dict'].apply(lambda x: x['id'])
            df['country_name_clean'] = df['country_dict'].apply(lambda x: x['value'])

            countries = df[['country_code', 'country_name_clean']].drop_duplicates()
            countries = countries.sort_values('country_name_clean')
            countries = countries.rename(columns={'country_name_clean': 'country_name'})

            logger.info(f"Loaded {len(countries)} countries")
            return countries.to_dict('records')
        else:
            logger.error("International data file not found")
            return []

    def assign_quality_tiers(self):
        """Assign quality tiers to countries"""
        logger.info("Assigning quality tiers...")

        # Tier 1: Comprehensive (OECD + major emerging) - using 2-letter ISO codes
        tier1 = [
            'US', 'CA',  # North America
            'GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'SE', 'NO',
            'DK', 'FI', 'CH', 'AT', 'IE', 'PT', 'GR', 'PL',  # Europe
            'JP', 'KR', 'AU', 'NZ',  # Asia-Pacific developed
            'MX', 'BR', 'AR', 'CL',  # Latin America major
            'CN', 'IN', 'ID', 'TR',  # Asia major emerging
            'ZA', 'RU'  # Other major
        ]

        # Tier 2: Standard (other emerging markets) - using 2-letter ISO codes
        tier2 = [
            'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO',  # Latin America
            'TH', 'MY', 'PH', 'VN', 'PK', 'BD', 'LK',  # Asia emerging
            'EG', 'NG', 'KE', 'ET', 'TZ', 'UG', 'GH',  # Africa
            'CZ', 'HU', 'RO', 'BG', 'HR', 'SK', 'SI',  # Central/Eastern Europe
            'IL', 'SA', 'AE', 'QA', 'KW',  # Middle East
        ]

        # Tier 3: Basic (all others)
        tier3 = []  # Will be assigned to anything not in Tier 1 or 2

        tiers = {}
        for country in self.country_list:
            code = country['country_code']
            if code in tier1:
                tiers[code] = 1
            elif code in tier2:
                tiers[code] = 2
            else:
                tiers[code] = 3

        logger.info(f"Assigned tiers: {sum(1 for t in tiers.values() if t == 1)} Tier 1, "
                   f"{sum(1 for t in tiers.values() if t == 2)} Tier 2, "
                   f"{sum(1 for t in tiers.values() if t == 3)} Tier 3")

        return tiers

    def create_country_directory(self, country_code, country_name):
        """Create directory structure for a single country"""
        country_dir = COUNTRIES_DIR / country_code

        # Create directory tree
        dirs = [
            country_dir / "Output" / "Data",
            country_dir / "Output" / "PDFs",
            country_dir / "Technical" / "src",
            country_dir / "Technical" / "data" / "raw",
            country_dir / "Technical" / "data" / "processed",
            country_dir / "Technical" / "data" / "subnational",
            country_dir / "Technical" / "docs",
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        return country_dir

    def create_country_profile(self, country_code, country_name, tier):
        """Create initial country profile markdown"""
        country_dir = COUNTRIES_DIR / country_code

        profile_content = f"""# {country_name} Tax System Profile

**Country Code:** {country_code}
**Data Quality Tier:** {tier}
**Last Updated:** 2025-10-06
**Status:** Infrastructure Created

---

## Overview

### Basic Information
- **Country Name:** {country_name}
- **ISO Code:** {country_code}
- **Data Tier:** {tier} {'(Comprehensive)' if tier == 1 else '(Standard)' if tier == 2 else '(Basic)'}

### Government Structure
- Type: [To be determined]
- Fiscal System: [Federal/Unitary - To be determined]
- Subnational Entities: [To be determined]

---

## Data Availability

### National Level
- **Tax Revenue Data:** [Years available to be determined]
- **GDP Data:** [Available]
- **Population Data:** [Available]
- **Tax Structure:** [To be collected]

### Subnational Level
- **Available:** [To be determined]
- **Entities:** [To be catalogued]
- **Coverage:** [To be assessed]

---

## Tax System Overview

### Revenue Structure
- Total tax revenue as % of GDP: [To be calculated]
- Latest year available: [To be determined]
- Historical trend: [To be analyzed]

### Major Tax Types
- Income taxes: [To be documented]
- Consumption taxes: [To be documented]
- Property taxes: [To be documented]
- Other: [To be documented]

---

## Analysis Status

### Completed
- [x] Directory structure created
- [ ] National data collected
- [ ] Subnational data collected (if applicable)
- [ ] Historical time series compiled
- [ ] Analysis performed
- [ ] Visualizations created
- [ ] PDF report generated

### Data Sources
[To be documented]

### Quality Assessment
- Data completeness: [To be assessed]
- Time series coverage: [To be assessed]
- Reliability: [To be assessed]

---

## Key Findings

[To be populated after analysis]

---

## Report

- **PDF Report:** Not yet generated
- **Data Files:** 0 created
- **Visualizations:** 0 created

---

**Profile created:** 2025-10-06
**Profile last updated:** 2025-10-06
**Analysis Status:** Pending
"""

        profile_file = country_dir / f"{country_code}_PROFILE.md"
        with open(profile_file, 'w', encoding='utf-8') as f:
            f.write(profile_content)

        logger.info(f"  Created profile for {country_name}")

    def create_sources_template(self, country_code, country_name):
        """Create data sources template"""
        country_dir = COUNTRIES_DIR / country_code

        sources_content = f"""# {country_name} Data Sources

**Country Code:** {country_code}
**Last Updated:** 2025-10-06

---

## Primary Data Sources

### International Databases

**World Bank World Development Indicators**
- **Indicator:** GC.TAX.TOTL.GD.ZS (Tax revenue % of GDP)
- **Coverage:** [Years to be determined]
- **URL:** https://data.worldbank.org/indicator/GC.TAX.TOTL.GD.ZS?locations={country_code}
- **Quality:** [To be assessed]

**IMF World Revenue Longitudinal Database**
- **Coverage:** [To be determined]
- **URL:** https://data.imf.org/
- **Quality:** [To be assessed]

**OECD Revenue Statistics** {'(if applicable)' if country_code in ['USA', 'GBR', 'DEU', 'FRA', 'ITA', 'ESP', 'JPN', 'KOR', 'AUS', 'CAN', 'NZL', 'CHE', 'NOR', 'SWE', 'DNK', 'FIN', 'NLD', 'BEL', 'AUT', 'IRL', 'PRT', 'GRC', 'POL', 'CZE', 'HUN', 'MEX', 'TUR', 'CHL', 'ISR'] else '(not applicable)'}
- **Coverage:** [To be determined]
- **URL:** https://stats.oecd.org/
- **Quality:** [To be assessed]

---

## National Sources

### Official Statistics Agency
- **Name:** [To be identified]
- **Website:** [To be found]
- **Data Available:** [To be catalogued]

### Tax Administration
- **Name:** [To be identified]
- **Website:** [To be found]
- **Data Available:** [To be catalogued]

### Ministry of Finance
- **Name:** [To be identified]
- **Website:** [To be found]
- **Publications:** [To be catalogued]

---

## Subnational Sources

[To be identified if country has federal/decentralized structure]

---

## Academic and Research Sources

### Research Papers
[To be added]

### International Organizations
- OECD country reports
- IMF country reports
- World Bank country analysis

---

## Data Quality Notes

### Strengths
[To be documented]

### Limitations
[To be documented]

### Gaps
[To be documented]

---

**Document created:** 2025-10-06
**Last updated:** 2025-10-06
"""

        sources_file = country_dir / f"{country_code}_SOURCES.md"
        with open(sources_file, 'w', encoding='utf-8') as f:
            f.write(sources_content)

    def create_config_file(self, country_code, country_name, tier):
        """Create JSON configuration file for country"""
        country_dir = COUNTRIES_DIR / country_code

        config = {
            "country_code": country_code,
            "country_name": country_name,
            "tier": tier,
            "created_date": "2025-10-06",
            "status": "infrastructure_created",
            "data_collection": {
                "national_data": False,
                "subnational_data": False,
                "historical_data": False
            },
            "analysis": {
                "completed": False,
                "report_generated": False,
                "visualizations_created": False
            },
            "subnational": {
                "has_subnational": None,
                "entity_count": 0,
                "entities": []
            },
            "data_years": {
                "first_year": None,
                "last_year": None,
                "total_years": 0
            }
        }

        config_file = country_dir / "Technical" / "data" / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    def build_all_infrastructure(self):
        """Build infrastructure for all countries"""
        logger.info("=" * 60)
        logger.info("Building Country Infrastructure")
        logger.info("=" * 60)

        # Create Countries directory
        COUNTRIES_DIR.mkdir(parents=True, exist_ok=True)

        created_count = 0
        for country in self.country_list:
            country_code = country['country_code']
            country_name = country['country_name']
            tier = self.quality_tiers.get(country_code, 3)

            try:
                logger.info(f"Creating infrastructure for {country_name} ({country_code}) - Tier {tier}")

                # Create directories
                self.create_country_directory(country_code, country_name)

                # Create profile
                self.create_country_profile(country_code, country_name, tier)

                # Create sources template
                self.create_sources_template(country_code, country_name)

                # Create config
                self.create_config_file(country_code, country_name, tier)

                created_count += 1

            except Exception as e:
                logger.error(f"  Error creating {country_name}: {e}")

        logger.info("\n" + "=" * 60)
        logger.info(f"Infrastructure Creation Complete!")
        logger.info("=" * 60)
        logger.info(f"Created infrastructure for {created_count} countries")
        logger.info(f"Location: {COUNTRIES_DIR}")

        # Create summary stats
        tier_counts = {1: 0, 2: 0, 3: 0}
        for tier in self.quality_tiers.values():
            tier_counts[tier] += 1

        logger.info(f"\nTier Distribution:")
        logger.info(f"  Tier 1 (Comprehensive): {tier_counts[1]} countries")
        logger.info(f"  Tier 2 (Standard): {tier_counts[2]} countries")
        logger.info(f"  Tier 3 (Basic): {tier_counts[3]} countries")

        return created_count


def main():
    logger.info("Country Infrastructure Builder - Gerhard Project")

    builder = CountryInfrastructureBuilder()
    count = builder.build_all_infrastructure()

    logger.info(f"\nSuccessfully created infrastructure for {count} countries")
    logger.info("Next steps:")
    logger.info("1. Run country data collection scripts")
    logger.info("2. Generate country analyses")
    logger.info("3. Create country reports")
    logger.info("4. Build master catalogue")


if __name__ == "__main__":
    main()
