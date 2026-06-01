"""
Historical Fiscal Regime Collection Strategy
============================================

Specialized collector for historical fiscal regime events (1960-present).
Focuses on sovereign debt defaults, major restructurings, and institutional changes.

This script creates collection plans optimized for historical data sources:
- GDELT (1979-present, free)
- NYT Archive (1851-present, free with API)
- ProQuest/LexisNexis (institutional access)
- IMF/World Bank archives
- Paris Club records
- Academic databases

Key Focus:
- Complete list of sovereign defaults since 1960
- Major debt restructurings
- Constitutional fiscal changes
- Currency reforms
- IMF program adoptions

Author: Gerhard - Fiscal Analysis Platform
Created: October 2025
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalFiscalRegimeCollector:
    """Plan and execute historical fiscal regime event collection"""

    def __init__(self):
        self.output_dir = Path("data/historical_collection")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.known_defaults = self._load_known_defaults()
        self.known_restructurings = self._load_known_restructurings()
        self.known_reforms = self._load_known_reforms()

    def _load_known_defaults(self) -> List[Dict]:
        """
        Load comprehensive list of known sovereign defaults (1960-2025)

        Based on:
        - Reinhart & Rogoff (2009) "This Time Is Different"
        - S&P Sovereign Defaults Database
        - Moody's Sovereign Default Database
        - Cruces & Trebesch (2013) Sovereign Defaults Database
        """
        return [
            # 1960s
            {'country': 'BR', 'year': 1964, 'type': 'default', 'description': 'Brazil external debt default'},
            {'country': 'GH', 'year': 1966, 'type': 'default', 'description': 'Ghana external debt default'},
            {'country': 'ID', 'year': 1966, 'type': 'default', 'description': 'Indonesia external debt default'},

            # 1970s
            {'country': 'CL', 'year': 1972, 'type': 'default', 'description': 'Chile external debt default'},
            {'country': 'ZR', 'year': 1976, 'type': 'default', 'description': 'Zaire external debt default'},
            {'country': 'PE', 'year': 1976, 'type': 'default', 'description': 'Peru external debt default'},
            {'country': 'TR', 'year': 1978, 'type': 'default', 'description': 'Turkey external debt default'},

            # 1980s - Latin American Debt Crisis
            {'country': 'MX', 'year': 1982, 'type': 'default', 'description': 'Mexico debt crisis (triggers Latin American crisis)'},
            {'country': 'AR', 'year': 1982, 'type': 'default', 'description': 'Argentina external debt default'},
            {'country': 'BR', 'year': 1983, 'type': 'default', 'description': 'Brazil external debt default'},
            {'country': 'VE', 'year': 1983, 'type': 'default', 'description': 'Venezuela external debt default'},
            {'country': 'CL', 'year': 1983, 'type': 'default', 'description': 'Chile external debt default'},
            {'country': 'PE', 'year': 1984, 'type': 'default', 'description': 'Peru external debt default'},
            {'country': 'CO', 'year': 1985, 'type': 'default', 'description': 'Colombia external debt default'},
            {'country': 'BO', 'year': 1986, 'type': 'default', 'description': 'Bolivia external debt default'},
            {'country': 'EC', 'year': 1987, 'type': 'default', 'description': 'Ecuador external debt default'},
            {'country': 'CR', 'year': 1981, 'type': 'default', 'description': 'Costa Rica external debt default'},

            # 1990s - Former Soviet Union & Asia
            {'country': 'RU', 'year': 1991, 'type': 'default', 'description': 'Russia inherits Soviet debt, initial default'},
            {'country': 'RU', 'year': 1998, 'type': 'default', 'description': 'Russia domestic and external default'},
            {'country': 'UA', 'year': 1998, 'type': 'default', 'description': 'Ukraine external debt default'},
            {'country': 'ID', 'year': 1998, 'type': 'default', 'description': 'Indonesia Asian financial crisis default'},
            {'country': 'EC', 'year': 1999, 'type': 'default', 'description': 'Ecuador Brady bonds default'},
            {'country': 'PK', 'year': 1999, 'type': 'default', 'description': 'Pakistan external debt default'},

            # 2000s
            {'country': 'AR', 'year': 2001, 'type': 'default', 'description': 'Argentina massive sovereign default ($100bn)'},
            {'country': 'UR', 'year': 2003, 'type': 'default', 'description': 'Uruguay debt restructuring'},
            {'country': 'DO', 'year': 2005, 'type': 'default', 'description': 'Dominican Republic external debt restructuring'},
            {'country': 'GR', 'year': 2012, 'type': 'default', 'description': 'Greece sovereign debt restructuring (PSI)'},
            {'country': 'CY', 'year': 2013, 'type': 'default', 'description': 'Cyprus bail-in and debt restructuring'},

            # 2010s
            {'country': 'BZ', 'year': 2012, 'type': 'default', 'description': 'Belize superbond restructuring'},
            {'country': 'AR', 'year': 2014, 'type': 'technical_default', 'description': 'Argentina technical default (holdouts)'},
            {'country': 'UA', 'year': 2015, 'type': 'default', 'description': 'Ukraine external debt restructuring'},
            {'country': 'MZ', 'year': 2016, 'type': 'default', 'description': 'Mozambique hidden debt crisis'},
            {'country': 'VE', 'year': 2017, 'type': 'default', 'description': 'Venezuela PDVSA bond default'},

            # 2020s
            {'country': 'AR', 'year': 2020, 'type': 'default', 'description': 'Argentina 9th default'},
            {'country': 'LB', 'year': 2020, 'type': 'default', 'description': 'Lebanon Eurobond default'},
            {'country': 'EC', 'year': 2020, 'type': 'default', 'description': 'Ecuador bond default (COVID)'},
            {'country': 'ZM', 'year': 2020, 'type': 'default', 'description': 'Zambia first African pandemic default'},
            {'country': 'SR', 'year': 2020, 'type': 'default', 'description': 'Suriname external debt default'},
            {'country': 'BZ', 'year': 2021, 'type': 'default', 'description': 'Belize external debt restructuring'},
            {'country': 'LK', 'year': 2022, 'type': 'default', 'description': 'Sri Lanka sovereign default'},
            {'country': 'RU', 'year': 2022, 'type': 'technical_default', 'description': 'Russia technical default (sanctions)'},
            {'country': 'GH', 'year': 2022, 'type': 'default', 'description': 'Ghana external debt default'},
            {'country': 'ET', 'year': 2024, 'type': 'default', 'description': 'Ethiopia Eurobond default'},
        ]

    def _load_known_restructurings(self) -> List[Dict]:
        """Load major debt restructurings (Paris Club, Brady Plan, etc.)"""
        return [
            # Brady Plan (1989-1997)
            {'country': 'MX', 'year': 1990, 'type': 'brady_plan', 'description': 'Mexico Brady Plan restructuring'},
            {'country': 'CR', 'year': 1990, 'type': 'brady_plan', 'description': 'Costa Rica Brady bonds'},
            {'country': 'VE', 'year': 1990, 'type': 'brady_plan', 'description': 'Venezuela Brady Plan'},
            {'country': 'UR', 'year': 1991, 'type': 'brady_plan', 'description': 'Uruguay Brady bonds'},
            {'country': 'AR', 'year': 1993, 'type': 'brady_plan', 'description': 'Argentina Brady Plan'},
            {'country': 'BR', 'year': 1994, 'type': 'brady_plan', 'description': 'Brazil Brady Plan (largest)'},
            {'country': 'PL', 'year': 1994, 'type': 'brady_plan', 'description': 'Poland Brady bonds'},
            {'country': 'RU', 'year': 1997, 'type': 'brady_plan', 'description': 'Russia debt restructuring'},

            # Paris Club Major Restructurings
            {'country': 'NG', 'year': 2005, 'type': 'paris_club', 'description': 'Nigeria Paris Club $18bn debt relief'},
            {'country': 'IQ', 'year': 2004, 'type': 'paris_club', 'description': 'Iraq 80% debt reduction'},
            {'country': 'CD', 'year': 2010, 'type': 'paris_club', 'description': 'DRC HIPC completion'},

            # Recent Major Restructurings
            {'country': 'GR', 'year': 2012, 'type': 'psi', 'description': 'Greece PSI (Private Sector Involvement) -53.5% haircut'},
            {'country': 'AR', 'year': 2020, 'type': 'restructuring', 'description': 'Argentina $65bn restructuring'},
            {'country': 'ZM', 'year': 2023, 'type': 'restructuring', 'description': 'Zambia Common Framework restructuring'},
        ]

    def _load_known_reforms(self) -> List[Dict]:
        """Load major fiscal reforms and institutional changes"""
        return [
            # Currency reforms
            {'country': 'BR', 'year': 1994, 'type': 'currency_reform', 'description': 'Brazil Real Plan (end of hyperinflation)'},
            {'country': 'AR', 'year': 1991, 'type': 'currency_reform', 'description': 'Argentina Convertibility Plan'},
            {'country': 'TR', 'year': 2005, 'type': 'currency_reform', 'description': 'Turkey new lira (redenomination)'},
            {'country': 'ZW', 'year': 2009, 'type': 'currency_reform', 'description': 'Zimbabwe dollarization'},

            # Euro adoption
            {'country': 'GR', 'year': 2001, 'type': 'euro_adoption', 'description': 'Greece joins Eurozone'},
            {'country': 'SI', 'year': 2007, 'type': 'euro_adoption', 'description': 'Slovenia joins Eurozone'},
            {'country': 'SK', 'year': 2009, 'type': 'euro_adoption', 'description': 'Slovakia joins Eurozone'},
            {'country': 'EE', 'year': 2011, 'type': 'euro_adoption', 'description': 'Estonia joins Eurozone'},
            {'country': 'LV', 'year': 2014, 'type': 'euro_adoption', 'description': 'Latvia joins Eurozone'},
            {'country': 'LT', 'year': 2015, 'type': 'euro_adoption', 'description': 'Lithuania joins Eurozone'},

            # Major fiscal rules
            {'country': 'NZ', 'year': 1994, 'type': 'fiscal_rule', 'description': 'New Zealand Fiscal Responsibility Act'},
            {'country': 'GB', 'year': 1997, 'type': 'fiscal_rule', 'description': 'UK Golden Rule and Sustainable Investment Rule'},
            {'country': 'CH', 'year': 2003, 'type': 'fiscal_rule', 'description': 'Switzerland Debt Brake (constitutional)'},
            {'country': 'DE', 'year': 2009, 'type': 'fiscal_rule', 'description': 'Germany Debt Brake (constitutional amendment)'},
            {'country': 'ES', 'year': 2011, 'type': 'fiscal_rule', 'description': 'Spain constitutional balanced budget amendment'},

            # Accounting standard changes
            {'country': 'AU', 'year': 1999, 'type': 'accounting_change', 'description': 'Australia adopts accrual accounting'},
            {'country': 'GB', 'year': 2001, 'type': 'accounting_change', 'description': 'UK Resource Accounting and Budgeting'},
            {'country': 'NZ', 'year': 1991, 'type': 'accounting_change', 'description': 'New Zealand full accrual accounting'},
        ]

    def create_collection_plan(self) -> Dict:
        """
        Create comprehensive historical collection plan

        Returns detailed strategy for collecting historical fiscal events
        """
        plan = {
            'overview': {
                'time_span': '1960-2025 (65 years)',
                'primary_focus': 'Sovereign defaults and major fiscal regime changes',
                'target_events': len(self.known_defaults) + len(self.known_restructurings) + len(self.known_reforms),
                'estimated_articles': 2000,
                'completion_time': '3-6 months'
            },
            'phases': self._create_phases(),
            'sources': self._create_source_strategy(),
            'search_terms': self._create_search_terms(),
            'priority_events': self._create_priority_list(),
            'implementation': self._create_implementation_guide()
        }

        return plan

    def _create_phases(self) -> List[Dict]:
        """Create collection phases"""
        return [
            {
                'phase': 1,
                'name': 'Known Defaults Collection',
                'period': 'Days 1-30',
                'description': 'Collect articles for all known sovereign defaults',
                'target': f'{len(self.known_defaults)} events',
                'sources': ['GDELT', 'News API', 'Google News Archive'],
                'strategy': 'Search for each specific default event by country + year'
            },
            {
                'phase': 2,
                'name': 'Major Restructurings',
                'period': 'Days 31-60',
                'description': 'Collect Brady Plan, Paris Club, and major restructurings',
                'target': f'{len(self.known_restructurings)} events',
                'sources': ['NYT Archive', 'GDELT', 'IMF website'],
                'strategy': 'Focus on 1980s-1990s debt crisis era'
            },
            {
                'phase': 3,
                'name': 'Fiscal Reforms',
                'period': 'Days 61-90',
                'description': 'Currency reforms, fiscal rules, accounting changes',
                'target': f'{len(self.known_reforms)} events',
                'sources': ['Academic databases', 'Central bank archives', 'OECD'],
                'strategy': 'Legal document search + news coverage'
            },
            {
                'phase': 4,
                'name': 'Gap Filling',
                'period': 'Days 91-120',
                'description': 'Fill gaps in coverage, verify events',
                'target': 'Complete coverage of major events',
                'sources': ['ProQuest', 'LexisNexis', 'Specialized databases'],
                'strategy': 'Targeted search for missing events'
            },
            {
                'phase': 5,
                'name': 'Continuous Monitoring',
                'period': 'Ongoing',
                'description': 'Daily collection of new events',
                'target': 'Real-time coverage',
                'sources': ['News API', 'GDELT', 'RSS feeds'],
                'strategy': 'Automated daily collection'
            }
        ]

    def _create_source_strategy(self) -> Dict:
        """Create detailed source strategy"""
        return {
            'free_sources': {
                'GDELT': {
                    'coverage': '1979-present',
                    'cost': 'Free',
                    'articles_per_event': '10-50',
                    'access': 'Public API',
                    'priority': 'HIGH',
                    'implementation': 'Use GDELT 2.0 API with country + event filters'
                },
                'NYT Archive': {
                    'coverage': '1851-present',
                    'cost': 'Free (4000 requests/day)',
                    'articles_per_event': '5-20',
                    'access': 'Developer API',
                    'priority': 'HIGH',
                    'implementation': 'Search by country + "debt" + year'
                },
                'Guardian': {
                    'coverage': '1999-present',
                    'cost': 'Free (500 requests/day)',
                    'articles_per_event': '3-10',
                    'access': 'Open Platform',
                    'priority': 'MEDIUM',
                    'implementation': 'International coverage, good for Europe/UK'
                },
                'News API': {
                    'coverage': 'Last 30 days (free)',
                    'cost': 'Free tier available',
                    'articles_per_event': '5-20',
                    'access': 'REST API',
                    'priority': 'HIGH (current events)',
                    'implementation': 'Daily monitoring for new events'
                }
            },
            'institutional_sources': {
                'ProQuest': {
                    'coverage': '1970s-present',
                    'cost': 'Institutional subscription',
                    'articles_per_event': '20-100',
                    'access': 'University library',
                    'priority': 'HIGH (historical)',
                    'implementation': 'Historical newspapers database'
                },
                'LexisNexis': {
                    'coverage': '1980s-present',
                    'cost': 'Institutional subscription',
                    'articles_per_event': '30-150',
                    'access': 'Professional/academic',
                    'priority': 'HIGH (comprehensive)',
                    'implementation': 'Most comprehensive news archive'
                },
                'JSTOR': {
                    'coverage': 'Academic papers',
                    'cost': 'Institutional subscription',
                    'articles_per_event': '1-5',
                    'access': 'University library',
                    'priority': 'MEDIUM',
                    'implementation': 'Scholarly analysis of events'
                }
            },
            'official_sources': {
                'IMF': {
                    'coverage': 'IMF programs and reports',
                    'cost': 'Free',
                    'access': 'Public website',
                    'priority': 'HIGH',
                    'implementation': 'Country reports, program documents'
                },
                'World Bank': {
                    'coverage': 'Development and debt',
                    'cost': 'Free',
                    'access': 'Open data',
                    'priority': 'MEDIUM',
                    'implementation': 'Debt statistics, country briefs'
                },
                'Paris Club': {
                    'coverage': 'Debt restructurings',
                    'cost': 'Free',
                    'access': 'Public website',
                    'priority': 'HIGH',
                    'implementation': 'Official restructuring documentation'
                },
                'Central Banks': {
                    'coverage': 'National fiscal policy',
                    'cost': 'Free',
                    'access': 'Public archives',
                    'priority': 'MEDIUM',
                    'implementation': 'Speeches, reports, press releases'
                }
            }
        }

    def _create_search_terms(self) -> Dict:
        """Create optimized search terms by event type"""
        return {
            'defaults': [
                '"{country}" sovereign default',
                '"{country}" debt default {year}',
                '"{country}" missed payment',
                '"{country}" debt crisis {year}',
                '"{country}" external debt default'
            ],
            'restructurings': [
                '"{country}" debt restructuring',
                '"{country}" Brady Plan',
                '"{country}" Paris Club',
                '"{country}" debt exchange',
                '"{country}" bond haircut'
            ],
            'currency_reforms': [
                '"{country}" currency reform',
                '"{country}" redenomination',
                '"{country}" new currency',
                '"{country}" euro adoption',
                '"{country}" dollarization'
            ],
            'fiscal_rules': [
                '"{country}" fiscal rule',
                '"{country}" debt brake',
                '"{country}" balanced budget',
                '"{country}" fiscal responsibility',
                '"{country}" budget law'
            ],
            'imf_programs': [
                '"{country}" IMF program',
                '"{country}" IMF bailout',
                '"{country}" IMF loan',
                '"{country}" structural adjustment',
                '"{country}" standby arrangement'
            ]
        }

    def _create_priority_list(self) -> List[Dict]:
        """Create prioritized list of events to collect"""
        # Combine all events and prioritize
        all_events = []

        # Defaults (highest priority)
        for event in self.known_defaults:
            event['priority'] = 'critical' if event['year'] >= 2000 else 'high'
            event['category'] = 'default'
            all_events.append(event)

        # Restructurings
        for event in self.known_restructurings:
            event['priority'] = 'high'
            event['category'] = 'restructuring'
            all_events.append(event)

        # Reforms
        for event in self.known_reforms:
            event['priority'] = 'medium'
            event['category'] = 'reform'
            all_events.append(event)

        # Sort by priority and year
        priority_order = {'critical': 0, 'high': 1, 'medium': 2}
        all_events.sort(key=lambda x: (priority_order[x['priority']], -x['year']))

        return all_events

    def _create_implementation_guide(self) -> Dict:
        """Create step-by-step implementation guide"""
        return {
            'week_1': {
                'tasks': [
                    'Set up API keys for News API, NYT, Guardian',
                    'Test GDELT queries for recent defaults',
                    'Create country-specific search term templates',
                    'Initialize database with known events list'
                ],
                'deliverable': 'Working collection system for free sources'
            },
            'week_2_4': {
                'tasks': [
                    'Collect articles for all post-2000 defaults (Phase 1)',
                    'Verify event dates and details',
                    'Extract key quotes and facts',
                    'Tag articles with event types and countries'
                ],
                'deliverable': '500+ articles for recent defaults'
            },
            'week_5_8': {
                'tasks': [
                    'Collect 1980s-1990s debt crisis articles (Phase 2)',
                    'Focus on Latin American debt crisis',
                    'Brady Plan documentation',
                    'Paris Club restructurings'
                ],
                'deliverable': '800+ articles for historical defaults'
            },
            'week_9_12': {
                'tasks': [
                    'Collect fiscal reform events (Phase 3)',
                    'Currency reforms, fiscal rules, accounting changes',
                    'Cross-reference with official sources',
                    'Verify dates with academic literature'
                ],
                'deliverable': '400+ articles for reforms'
            },
            'week_13_plus': {
                'tasks': [
                    'Institutional access for pre-1980 events (if available)',
                    'Gap filling for under-covered countries',
                    'Quality review and verification',
                    'Set up daily monitoring for new events'
                ],
                'deliverable': 'Complete historical database + ongoing monitoring'
            }
        }

    def save_plan(self, output_path: Optional[Path] = None):
        """Save collection plan to JSON"""
        if not output_path:
            output_path = self.output_dir / "historical_collection_plan.json"

        plan = self.create_collection_plan()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved collection plan to: {output_path}")

        # Also create markdown summary
        self._create_markdown_summary(plan, output_path.with_suffix('.md'))

    def _create_markdown_summary(self, plan: Dict, output_path: Path):
        """Create human-readable markdown summary"""
        md = f"""# Historical Fiscal Regime Collection Plan

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview

- **Time Span:** {plan['overview']['time_span']}
- **Target Events:** {plan['overview']['target_events']}
- **Estimated Articles:** {plan['overview']['estimated_articles']}
- **Completion Time:** {plan['overview']['completion_time']}

## Known Events to Collect

### Sovereign Defaults: {len(self.known_defaults)}
### Debt Restructurings: {len(self.known_restructurings)}
### Fiscal Reforms: {len(self.known_reforms)}

## Collection Phases

"""
        for phase in plan['phases']:
            md += f"### Phase {phase['phase']}: {phase['name']}\n\n"
            md += f"- **Period:** {phase['period']}\n"
            md += f"- **Target:** {phase['target']}\n"
            md += f"- **Sources:** {', '.join(phase['sources'])}\n"
            md += f"- **Strategy:** {phase['strategy']}\n\n"

        md += "\n## Top Priority Events (First 20)\n\n"
        md += "| Country | Year | Type | Description | Priority |\n"
        md += "|---------|------|------|-------------|----------|\n"

        for event in plan['priority_events'][:20]:
            md += f"| {event['country']} | {event['year']} | {event['type']} | {event['description']} | {event['priority']} |\n"

        md += "\n## Data Sources\n\n"
        md += "### Free Sources (Immediate Access)\n\n"
        for source, details in plan['sources']['free_sources'].items():
            md += f"**{source}**\n"
            md += f"- Coverage: {details['coverage']}\n"
            md += f"- Priority: {details['priority']}\n"
            md += f"- Implementation: {details['implementation']}\n\n"

        md += "\n### Institutional Sources (Optional)\n\n"
        for source, details in plan['sources']['institutional_sources'].items():
            md += f"**{source}**\n"
            md += f"- Coverage: {details['coverage']}\n"
            md += f"- Cost: {details['cost']}\n"
            md += f"- Priority: {details['priority']}\n\n"

        md += "\n## Implementation Timeline\n\n"
        for week, details in plan['implementation'].items():
            md += f"### {week.replace('_', ' ').title()}\n\n"
            md += "**Tasks:**\n"
            for task in details['tasks']:
                md += f"- {task}\n"
            md += f"\n**Deliverable:** {details['deliverable']}\n\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)

        logger.info(f"Saved markdown summary to: {output_path}")

    def export_events_to_csv(self, output_path: Optional[Path] = None):
        """Export known events to CSV for reference"""
        if not output_path:
            output_path = self.output_dir / "known_fiscal_events.csv"

        import csv

        all_events = self._create_priority_list()

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['country', 'year', 'type', 'description', 'priority', 'category'])
            writer.writeheader()
            writer.writerows(all_events)

        logger.info(f"Exported {len(all_events)} events to: {output_path}")


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Historical Fiscal Regime Collector - Planning")
    logger.info("=" * 60)

    collector = HistoricalFiscalRegimeCollector()

    # Create collection plan
    logger.info("\nGenerating collection plan...")
    collector.save_plan()

    # Export known events
    logger.info("\nExporting known events...")
    collector.export_events_to_csv()

    logger.info("\n" + "=" * 60)
    logger.info("Planning complete!")
    logger.info("=" * 60)
    logger.info("\nGenerated files:")
    logger.info("  - data/historical_collection/historical_collection_plan.json")
    logger.info("  - data/historical_collection/historical_collection_plan.md")
    logger.info("  - data/historical_collection/known_fiscal_events.csv")
    logger.info("\nNext steps:")
    logger.info("  1. Review the collection plan")
    logger.info("  2. Set up API keys (.env file)")
    logger.info("  3. Run fiscal_regime_news_collector.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
