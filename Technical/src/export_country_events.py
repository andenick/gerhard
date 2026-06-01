"""
Export Fiscal Regime Events by Country
=======================================

Organizes fiscal events by country and generates country-specific reports.
Each country gets its own regime break documentation.

Usage:
    python export_country_events.py

Outputs:
    - data/country_events/{ISO2}_fiscal_events.json
    - data/country_events/{ISO2}_regime_breaks.md
    - data/country_events/country_summary.json

Author: Gerhard - Fiscal Analysis Platform
Created: October 2025
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ISO2 to country name mapping
COUNTRY_NAMES = {
    'AR': 'Argentina', 'BR': 'Brazil', 'MX': 'Mexico', 'CL': 'Chile',
    'GR': 'Greece', 'ES': 'Spain', 'IT': 'Italy', 'PT': 'Portugal',
    'IE': 'Ireland', 'CY': 'Cyprus', 'RU': 'Russia', 'UA': 'Ukraine',
    'VE': 'Venezuela', 'EC': 'Ecuador', 'UY': 'Uruguay', 'LB': 'Lebanon',
    'ZM': 'Zambia', 'ZW': 'Zimbabwe', 'GH': 'Ghana', 'ET': 'Ethiopia',
    'LK': 'Sri Lanka', 'PK': 'Pakistan', 'TR': 'Turkey', 'EG': 'Egypt',
    'ID': 'Indonesia', 'TH': 'Thailand', 'KR': 'Korea', 'DO': 'Dominican Republic',
    'SR': 'Suriname', 'MZ': 'Mozambique', 'BZ': 'Belize', 'CD': 'Congo',
    'NG': 'Nigeria', 'IQ': 'Iraq', 'CR': 'Costa Rica', 'BO': 'Bolivia',
    'PE': 'Peru', 'PL': 'Poland', 'US': 'United States', 'GB': 'United Kingdom',
    'DE': 'Germany', 'FR': 'France', 'CN': 'China', 'JP': 'Japan',
    'IN': 'India', 'AU': 'Australia', 'CA': 'Canada', 'ZA': 'South Africa'
}


class CountryEventExporter:
    """Export fiscal events organized by country"""

    def __init__(self):
        self.db_path = Path("data/fiscal_regime_events.db")
        self.output_dir = Path("data/country_events")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Track statistics
        self.stats = {
            'total_events': 0,
            'countries_affected': set(),
            'events_by_country': defaultdict(int),
            'regime_breaks_by_country': defaultdict(int)
        }

    def load_events(self):
        """Load all events from database"""
        if not self.db_path.exists():
            print(f"Database not found: {self.db_path}")
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT event_id, title, description, content, source_name, source_url,
                   author, published_at, collected_at, event_type, countries, region,
                   severity, impact_scope, relevance_score, keywords, entities,
                   regime_break, comparability_impact
            FROM fiscal_regime_events
            ORDER BY published_at DESC
        ''')

        events = []
        for row in cursor.fetchall():
            event = {
                'event_id': row[0],
                'title': row[1],
                'description': row[2],
                'content': row[3],
                'source_name': row[4],
                'source_url': row[5],
                'author': row[6],
                'published_at': row[7],
                'collected_at': row[8],
                'event_type': row[9],
                'countries': json.loads(row[10]) if row[10] else [],
                'region': row[11],
                'severity': row[12],
                'impact_scope': row[13],
                'relevance_score': row[14],
                'keywords': json.loads(row[15]) if row[15] else [],
                'entities': json.loads(row[16]) if row[16] else [],
                'regime_break': bool(row[17]),
                'comparability_impact': row[18]
            }
            events.append(event)

        conn.close()
        self.stats['total_events'] = len(events)

        return events

    def organize_by_country(self, events):
        """Organize events by country"""
        country_events = defaultdict(list)

        for event in events:
            countries = event['countries']

            if not countries:
                # Global events (no specific country)
                country_events['GLOBAL'].append(event)
            else:
                # Add to each mentioned country
                for country_code in countries:
                    country_events[country_code].append(event)
                    self.stats['countries_affected'].add(country_code)
                    self.stats['events_by_country'][country_code] += 1

                    if event['regime_break']:
                        self.stats['regime_breaks_by_country'][country_code] += 1

        return country_events

    def export_country_json(self, country_code, events):
        """Export events for a country to JSON"""
        output_file = self.output_dir / f"{country_code}_fiscal_events.json"

        country_data = {
            'country_code': country_code,
            'country_name': COUNTRY_NAMES.get(country_code, country_code),
            'total_events': len(events),
            'regime_breaks': sum(1 for e in events if e['regime_break']),
            'latest_event': events[0]['published_at'] if events else None,
            'exported_at': datetime.now().isoformat(),
            'events': events
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(country_data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(events)} events to: {output_file}")
        return output_file

    def export_country_markdown(self, country_code, events):
        """Export regime breaks for a country to Markdown"""
        output_file = self.output_dir / f"{country_code}_regime_breaks.md"

        country_name = COUNTRY_NAMES.get(country_code, country_code)
        regime_breaks = [e for e in events if e['regime_break']]

        md = f"# Fiscal Regime Breaks - {country_name}\n\n"
        md += f"**Country Code:** {country_code}\n"
        md += f"**Total Events:** {len(events)}\n"
        md += f"**Regime Breaks:** {len(regime_breaks)}\n"
        md += f"**Last Updated:** {datetime.now().strftime('%B %d, %Y')}\n\n"
        md += "---\n\n"

        if regime_breaks:
            md += "## Regime Break Events\n\n"
            md += "⚠️ **These events may affect fiscal data comparability**\n\n"

            for i, event in enumerate(regime_breaks, 1):
                md += f"### {i}. {event['title']}\n\n"
                md += f"**Date:** {event['published_at'][:10]}\n"
                md += f"**Type:** {event['event_type']}\n"
                md += f"**Severity:** {event['severity']}\n"
                md += f"**Comparability Impact:** {event['comparability_impact']}\n\n"

                if event['description']:
                    md += f"**Description:**\n{event['description']}\n\n"

                md += f"**Source:** [{event['source_name']}]({event['source_url']})\n\n"

                # Impact assessment
                md += "**Data Comparability Impact:**\n"
                if event['comparability_impact'] == 'complete_break':
                    md += "- ❌ **Complete break** - Data before and after this event is NOT comparable\n"
                    md += "- Use separate time series or apply adjustments\n"
                elif event['comparability_impact'] == 'major':
                    md += "- ⚠️ **Major impact** - Significant adjustments needed for comparability\n"
                    md += "- Document methodology changes and control for regime effects\n"
                elif event['comparability_impact'] == 'moderate':
                    md += "- 📝 **Moderate impact** - Some adjustments recommended\n"
                    md += "- Note this event in analysis and consider robustness checks\n"
                else:
                    md += "- ℹ️ **Minor impact** - Document event but limited comparability concerns\n"

                md += "\n---\n\n"

        # All events section
        md += "## All Fiscal Events\n\n"
        for i, event in enumerate(events, 1):
            md += f"### {i}. {event['title']}\n\n"
            md += f"- **Date:** {event['published_at'][:10]}\n"
            md += f"- **Type:** {event['event_type']}\n"
            md += f"- **Severity:** {event['severity']}\n"
            if event['regime_break']:
                md += f"- **Regime Break:** ⚠️ YES ({event['comparability_impact']})\n"
            else:
                md += f"- **Regime Break:** No\n"
            md += f"- **Source:** [{event['source_name']}]({event['source_url']})\n\n"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"Exported regime break documentation to: {output_file}")
        return output_file

    def export_summary(self):
        """Export summary of all country events"""
        summary_file = self.output_dir / "country_summary.json"

        summary = {
            'total_events': self.stats['total_events'],
            'countries_affected': list(self.stats['countries_affected']),
            'num_countries': len(self.stats['countries_affected']),
            'events_by_country': dict(self.stats['events_by_country']),
            'regime_breaks_by_country': dict(self.stats['regime_breaks_by_country']),
            'exported_at': datetime.now().isoformat()
        }

        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"\nExported summary to: {summary_file}")

        # Print summary
        print("\n" + "="*80)
        print("COUNTRY EVENT EXPORT SUMMARY")
        print("="*80)
        print(f"Total events: {summary['total_events']}")
        print(f"Countries affected: {summary['num_countries']}")
        print(f"\nEvents by country:")
        for country, count in sorted(self.stats['events_by_country'].items(), key=lambda x: -x[1]):
            country_name = COUNTRY_NAMES.get(country, country)
            regime_breaks = self.stats['regime_breaks_by_country'].get(country, 0)
            print(f"  {country} ({country_name:20s}): {count:2d} events ({regime_breaks} regime breaks)")
        print("="*80)

    def run(self):
        """Run the export process"""
        print("="*80)
        print("FISCAL REGIME EVENT EXPORT - BY COUNTRY")
        print("="*80)

        # Load events
        print("\nLoading events from database...")
        events = self.load_events()

        if not events:
            print("No events found in database.")
            return

        # Organize by country
        print(f"Organizing {len(events)} events by country...")
        country_events = self.organize_by_country(events)

        # Export each country
        print("\nExporting country-specific files...\n")
        for country_code in sorted(country_events.keys()):
            events_list = country_events[country_code]

            if country_code == 'GLOBAL':
                print(f"\nGLOBAL events: {len(events_list)}")
                # Export global events separately
                self.export_country_json('GLOBAL', events_list)
                continue

            country_name = COUNTRY_NAMES.get(country_code, country_code)
            print(f"\n{country_name} ({country_code}):")

            # Export JSON
            self.export_country_json(country_code, events_list)

            # Export Markdown
            self.export_country_markdown(country_code, events_list)

        # Export summary
        self.export_summary()

        print("\n" + "="*80)
        print("EXPORT COMPLETE")
        print("="*80)
        print(f"\nCountry files created in: {self.output_dir}")
        print("\nNext steps:")
        print("1. Review country-specific regime break documentation")
        print("2. Copy files to main project country directories")
        print("3. Update country profiles with regime break information")


def main():
    exporter = CountryEventExporter()
    exporter.run()


if __name__ == "__main__":
    main()
