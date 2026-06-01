"""
Integrate Fiscal Regime Events with Country Directories
========================================================

Copies country-specific fiscal regime files to the main project's
country directories, ensuring each country has its own regime break
documentation.

This script:
1. Loads country-specific fiscal event files
2. Copies them to the appropriate country directories
3. Updates country profiles with regime break information
4. Creates integration summary

Usage:
    python integrate_with_countries.py

Author: Gerhard - Fiscal Analysis Platform
Created: October 2025
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


class CountryIntegrator:
    """Integrate fiscal regime events with country directories"""

    def __init__(self):
        self.country_events_dir = Path("data/country_events")
        self.main_project_dir = Path(__file__).resolve().parent.parent.parent / "Countries"

        if not self.main_project_dir.exists():
            print(f"Warning: Main project directory not found: {self.main_project_dir}")
            print("Countries/ directory not found relative to this script")

        self.stats = {
            'countries_processed': 0,
            'files_copied': 0,
            'profiles_updated': 0,
            'errors': []
        }

    def get_country_files(self):
        """Get list of country event files"""
        if not self.country_events_dir.exists():
            print(f"Country events directory not found: {self.country_events_dir}")
            print("Run export_country_events.py first")
            return []

        country_files = {}

        # Find all country-specific JSON files (exclude GLOBAL)
        for json_file in self.country_events_dir.glob("*_fiscal_events.json"):
            country_code = json_file.stem.replace('_fiscal_events', '')

            if country_code == 'GLOBAL':
                continue

            # Find corresponding markdown file
            md_file = self.country_events_dir / f"{country_code}_regime_breaks.md"

            country_files[country_code] = {
                'json': json_file,
                'markdown': md_file if md_file.exists() else None
            }

        return country_files

    def integrate_country(self, country_code, files):
        """Integrate fiscal events for a single country"""
        country_dir = self.main_project_dir / country_code

        if not country_dir.exists():
            self.stats['errors'].append(f"{country_code}: Directory not found")
            return False

        print(f"\nIntegrating {country_code}...")

        # Ensure Output/Data directory exists
        output_data_dir = country_dir / "Output" / "Data"
        output_data_dir.mkdir(parents=True, exist_ok=True)

        # Copy JSON file
        if files['json']:
            dest_json = output_data_dir / f"{country_code}_fiscal_regime_events.json"
            shutil.copy2(files['json'], dest_json)
            print(f"  [OK] Copied: {dest_json.name}")
            self.stats['files_copied'] += 1

        # Copy Markdown file
        if files['markdown']:
            dest_md = output_data_dir / f"{country_code}_regime_breaks.md"
            shutil.copy2(files['markdown'], dest_md)
            print(f"  [OK] Copied: {dest_md.name}")
            self.stats['files_copied'] += 1

        # Update country profile
        self.update_country_profile(country_code, files['json'])

        self.stats['countries_processed'] += 1
        return True

    def update_country_profile(self, country_code, json_file):
        """Update country profile with regime break information"""
        country_dir = self.main_project_dir / country_code
        profile_file = country_dir / f"{country_code}_PROFILE.md"

        if not profile_file.exists():
            self.stats['errors'].append(f"{country_code}: Profile not found")
            return

        # Load event data
        with open(json_file, 'r', encoding='utf-8') as f:
            event_data = json.load(f)

        regime_breaks = event_data['regime_breaks']
        total_events = event_data['total_events']

        # Read existing profile
        with open(profile_file, 'r', encoding='utf-8') as f:
            profile_content = f.read()

        # Check if regime break section already exists
        if '## Fiscal Regime Events' in profile_content:
            # Update existing section
            print(f"  [INFO] Regime events section already exists in profile")
            return

        # Add regime break section
        regime_section = f"\n\n---\n\n## Fiscal Regime Events\n\n"
        regime_section += f"**Total Events Tracked:** {total_events}\n"
        regime_section += f"**Regime Breaks:** {regime_breaks}\n"
        regime_section += f"**Last Updated:** {datetime.now().strftime('%B %d, %Y')}\n\n"

        if regime_breaks > 0:
            regime_section += "⚠️ **Warning:** This country has fiscal regime breaks that may affect data comparability.\n\n"
            regime_section += f"See [`{country_code}_regime_breaks.md`](Output/Data/{country_code}_regime_breaks.md) for detailed documentation.\n\n"
            regime_section += "**Impact on Analysis:**\n"
            regime_section += "- Fiscal data may not be directly comparable across regime breaks\n"
            regime_section += "- Consider separate time series or apply adjustments\n"
            regime_section += "- Document methodology changes in analysis\n"
        else:
            regime_section += "✅ No major regime breaks detected in collected news data.\n\n"
            regime_section += f"See [`{country_code}_fiscal_regime_events.json`](Output/Data/{country_code}_fiscal_regime_events.json) for all fiscal events.\n"

        # Append to profile
        with open(profile_file, 'a', encoding='utf-8') as f:
            f.write(regime_section)

        print(f"  [OK] Updated: {profile_file.name}")
        self.stats['profiles_updated'] += 1

    def create_integration_summary(self):
        """Create summary of integration"""
        summary_file = self.country_events_dir / "integration_summary.md"

        md = "# Fiscal Regime Event Integration Summary\n\n"
        md += f"**Integration Date:** {datetime.now().strftime('%B %d, %Y at %H:%M')}\n"
        md += f"**Countries Processed:** {self.stats['countries_processed']}\n"
        md += f"**Files Copied:** {self.stats['files_copied']}\n"
        md += f"**Profiles Updated:** {self.stats['profiles_updated']}\n\n"

        if self.stats['errors']:
            md += "## Errors\n\n"
            for error in self.stats['errors']:
                md += f"- ⚠️ {error}\n"
            md += "\n"

        md += "---\n\n"
        md += "## Integration Details\n\n"
        md += "Each country directory now contains:\n\n"
        md += "```\n"
        md += "Countries/{COUNTRY_CODE}/\n"
        md += "├── {COUNTRY_CODE}_PROFILE.md                    # Updated with regime info\n"
        md += "└── Output/Data/\n"
        md += "    ├── {COUNTRY_CODE}_fiscal_regime_events.json  # All fiscal events\n"
        md += "    └── {COUNTRY_CODE}_regime_breaks.md           # Regime break documentation\n"
        md += "```\n\n"

        md += "## Country-Specific Regime Breaks\n\n"
        md += "Fiscal regime breaks are now documented on a **country-by-country basis**.\n\n"
        md += "**Key Principle:** A regime break in one country (e.g., Argentina default) "
        md += "does NOT affect fiscal data comparability in other countries (e.g., Germany).\n\n"

        md += "**Example:**\n"
        md += "- Argentina 2001 default → **Only affects Argentine fiscal data**\n"
        md += "- Greece 2012 restructuring → **Only affects Greek fiscal data**\n"
        md += "- US tax reform → **Only affects US fiscal data**\n\n"

        md += "## Usage in Analysis\n\n"
        md += "When analyzing a country's fiscal data:\n\n"
        md += "1. **Check country profile** for regime break warnings\n"
        md += "2. **Review regime breaks** in `{COUNTRY}_regime_breaks.md`\n"
        md += "3. **Adjust analysis** as needed:\n"
        md += "   - Use separate time series before/after breaks\n"
        md += "   - Apply statistical adjustments\n"
        md += "   - Document methodology changes\n"
        md += "   - Control for regime effects in econometrics\n\n"

        md += "## Integration with Fiscal Database\n\n"
        md += "Regime break files are stored alongside:\n"
        md += "- Government expenditure data (`.xlsx`)\n"
        md += "- WID.world distributional data (`.csv`)\n"
        md += "- COFOG functional classification (`.xlsx`)\n"
        md += "- Country-specific source documentation\n\n"

        md += "This ensures fiscal events are immediately visible when working with country data.\n\n"

        md += "---\n\n"
        md += f"**Generated by:** `integrate_with_countries.py`\n"
        md += f"**Source:** fiscal news collector\n"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"\nCreated integration summary: {summary_file}")

    def run(self):
        """Run integration process"""
        print("="*80)
        print("FISCAL REGIME EVENT INTEGRATION WITH COUNTRY DIRECTORIES")
        print("="*80)

        # Get country files
        country_files = self.get_country_files()

        if not country_files:
            print("No country event files found. Run export_country_events.py first.")
            return

        print(f"\nFound event files for {len(country_files)} countries")

        # Integrate each country
        for country_code, files in sorted(country_files.items()):
            self.integrate_country(country_code, files)

        # Create summary
        self.create_integration_summary()

        # Print final stats
        print("\n" + "="*80)
        print("INTEGRATION COMPLETE")
        print("="*80)
        print(f"Countries processed: {self.stats['countries_processed']}")
        print(f"Files copied: {self.stats['files_copied']}")
        print(f"Profiles updated: {self.stats['profiles_updated']}")

        if self.stats['errors']:
            print(f"\nErrors: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                print(f"  - {error}")

        print("\n" + "="*80)
        print("\nCountry directories have been updated with fiscal regime information!")
        print("\nEach country now has:")
        print("  - {COUNTRY}_fiscal_regime_events.json (all events)")
        print("  - {COUNTRY}_regime_breaks.md (regime break documentation)")
        print("  - Updated country profile with regime break warnings")


def main():
    integrator = CountryIntegrator()
    integrator.run()


if __name__ == "__main__":
    main()
