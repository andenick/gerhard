"""
Historical Fiscal Event Collection Runner
==========================================

Executes the historical collection plan to gather articles on 75 known fiscal events.
Uses NYT Archive API for historical coverage (1851-present).

Usage:
    python run_historical_collection.py --start 0 --limit 10

    # Or run all events
    python run_historical_collection.py

Author: Gerhard - Fiscal Analysis Platform
Created: October 2025
"""

import csv
import json
import logging
import time
import argparse
from pathlib import Path
from datetime import datetime
from fiscal_regime_news_collector import FiscalRegimeNewsCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalCollectionRunner:
    """Execute historical collection plan"""

    def __init__(self):
        self.collector = FiscalRegimeNewsCollector()
        self.known_events_path = Path("data/historical_collection/known_fiscal_events.csv")
        self.stats = {
            'start_time': datetime.now().isoformat(),
            'events_processed': 0,
            'articles_collected': 0,
            'events_saved': 0,
            'events_by_type': {},
            'countries_found': set()
        }

    def load_known_events(self):
        """Load known fiscal events from CSV"""
        events = []

        if not self.known_events_path.exists():
            logger.error(f"Known events file not found: {self.known_events_path}")
            return events

        with open(self.known_events_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                events.append(row)

        logger.info(f"Loaded {len(events)} known events")
        return events

    def create_search_queries(self, event):
        """Create search queries for a fiscal event"""
        country = event['country']
        year = event['year']
        event_type = event['type']
        description = event['description']

        # Map ISO2 codes to full country names
        country_names = {
            'AR': 'Argentina', 'BR': 'Brazil', 'MX': 'Mexico', 'CL': 'Chile',
            'GR': 'Greece', 'ES': 'Spain', 'IT': 'Italy', 'PT': 'Portugal',
            'IE': 'Ireland', 'CY': 'Cyprus', 'RU': 'Russia', 'UA': 'Ukraine',
            'VE': 'Venezuela', 'EC': 'Ecuador', 'UY': 'Uruguay', 'LB': 'Lebanon',
            'ZM': 'Zambia', 'ZW': 'Zimbabwe', 'GH': 'Ghana', 'ET': 'Ethiopia',
            'LK': 'Sri Lanka', 'PK': 'Pakistan', 'TR': 'Turkey', 'EG': 'Egypt',
            'ID': 'Indonesia', 'TH': 'Thailand', 'KR': 'Korea', 'DO': 'Dominican Republic',
            'SR': 'Suriname', 'MZ': 'Mozambique', 'BZ': 'Belize', 'CD': 'Congo',
            'NG': 'Nigeria', 'IQ': 'Iraq', 'CR': 'Costa Rica', 'BO': 'Bolivia',
            'PE': 'Peru', 'PL': 'Poland', 'US': 'United States'
        }

        country_name = country_names.get(country, country)

        queries = []

        # Default-specific queries
        if 'default' in event_type:
            queries.extend([
                f"{country_name} debt default",
                f"{country_name} sovereign default",
                f"{country_name} default {year}",
                f"{country_name} debt crisis"
            ])

        # Restructuring-specific queries
        elif 'restructuring' in event_type or 'psi' in event_type:
            queries.extend([
                f"{country_name} debt restructuring",
                f"{country_name} bond restructuring",
                f"{country_name} debt relief"
            ])

        # Paris Club queries
        elif 'paris_club' in event_type:
            queries.extend([
                f"{country_name} Paris Club",
                f"{country_name} debt forgiveness"
            ])

        # Fiscal reform queries
        elif 'reform' in event_type:
            queries.extend([
                f"{country_name} fiscal reform",
                f"{country_name} tax reform",
                f"{country_name} budget reform"
            ])

        # Generic fallback
        if not queries:
            queries.append(f"{country_name} debt {year}")

        return queries[:2]  # Limit to 2 queries per event to manage API rate limits

    def collect_for_event(self, event):
        """Collect articles for a single fiscal event"""
        country = event['country']
        year = int(event['year'])
        description = event['description']

        logger.info(f"\n{'='*80}")
        logger.info(f"Collecting: {country} {year} - {description}")
        logger.info(f"{'='*80}")

        queries = self.create_search_queries(event)
        all_articles = []

        # Collect from NYT Archive for the event year
        for query in queries:
            logger.info(f"Searching NYT Archive for: '{query}' in {year}")

            # Search the event year and the year after (for coverage lag)
            for search_year in [year, year + 1]:
                for month in range(1, 13):
                    try:
                        articles = self.collector.collect_from_nyt_archive(
                            search_term=query,
                            year=search_year,
                            month=month
                        )
                        all_articles.extend(articles)

                        # NYT API rate limit: 10 requests/minute
                        time.sleep(6)  # 6 seconds between requests = 10/minute

                        if len(articles) > 0:
                            logger.info(f"  Found {len(articles)} articles in {search_year}-{month:02d}")

                    except Exception as e:
                        logger.error(f"Error collecting from NYT Archive: {e}")
                        continue

        logger.info(f"Total articles collected for this event: {len(all_articles)}")
        return all_articles

    def process_and_save(self, articles):
        """Process articles and save events to database"""
        saved_count = 0

        for article in articles:
            event = self.collector.process_article(article, source='nyt')

            if event:
                if self.collector.save_event(event):
                    saved_count += 1
                    self.stats['events_by_type'][event.event_type] = \
                        self.stats['events_by_type'].get(event.event_type, 0) + 1
                    self.stats['countries_found'].update(event.countries)

        return saved_count

    def run(self, start_index=0, limit=None):
        """Run historical collection"""
        logger.info("="*80)
        logger.info("HISTORICAL FISCAL EVENT COLLECTION")
        logger.info("="*80)

        # Load known events
        known_events = self.load_known_events()

        if not known_events:
            logger.error("No known events loaded. Exiting.")
            return

        # Apply start/limit
        if limit:
            events_to_process = known_events[start_index:start_index + limit]
        else:
            events_to_process = known_events[start_index:]

        logger.info(f"\nProcessing {len(events_to_process)} events (starting at index {start_index})")
        logger.info(f"Estimated time: {len(events_to_process) * 2} minutes (with rate limiting)")

        # Process each event
        for i, event in enumerate(events_to_process):
            logger.info(f"\n[{i+1}/{len(events_to_process)}] Processing: {event['country']} {event['year']}")

            try:
                # Collect articles
                articles = self.collect_for_event(event)
                self.stats['articles_collected'] += len(articles)

                # Process and save
                saved_count = self.process_and_save(articles)
                self.stats['events_saved'] += saved_count

                self.stats['events_processed'] += 1

                logger.info(f"Saved {saved_count} events from this collection")

            except Exception as e:
                logger.error(f"Error processing event: {e}")
                continue

        # Final statistics
        self.stats['end_time'] = datetime.now().isoformat()
        self.stats['countries_found'] = list(self.stats['countries_found'])

        self.print_summary()
        self.save_stats()

    def print_summary(self):
        """Print collection summary"""
        print("\n" + "="*80)
        print("COLLECTION SUMMARY")
        print("="*80)
        print(f"Events processed: {self.stats['events_processed']}")
        print(f"Articles collected: {self.stats['articles_collected']}")
        print(f"Events saved to database: {self.stats['events_saved']}")
        print(f"\nEvents by type:")
        for event_type, count in sorted(self.stats['events_by_type'].items()):
            print(f"  {event_type}: {count}")
        print(f"\nCountries found: {len(self.stats['countries_found'])}")
        if self.stats['countries_found']:
            print(f"  {', '.join(sorted(self.stats['countries_found']))}")
        print("="*80)

    def save_stats(self):
        """Save collection statistics"""
        stats_path = Path("data/historical_collection/collection_stats.json")
        stats_path.parent.mkdir(parents=True, exist_ok=True)

        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)

        logger.info(f"\nStatistics saved to: {stats_path}")


def main():
    parser = argparse.ArgumentParser(description='Run historical fiscal event collection')
    parser.add_argument('--start', type=int, default=0,
                       help='Start index in known events list (default: 0)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Number of events to process (default: all)')
    args = parser.parse_args()

    runner = HistoricalCollectionRunner()
    runner.run(start_index=args.start, limit=args.limit)


if __name__ == "__main__":
    main()
