"""
Fiscal Regime and Sovereign Debt News Collector
================================================

Comprehensive news collection system for tracking government debt defaults,
fiscal regime changes, and institutional transformations affecting government budgets.

Focus Areas:
- Sovereign debt defaults (outright and technical)
- Debt restructuring and rule changes
- Legal/institutional changes affecting:
  * Tax systems
  * Government expenditure rules
  * Borrowing regulations
  * Accounting standards
- Fiscal regime breaks and transitions
- Constitutional changes affecting budgeting

Features:
- Multi-source news collection (News API, GDELT, archives)
- Historical coverage (1960-present, focus on developing countries)
- Regime classification and categorization
- Country-specific tracking across 200+ countries
- Integration with existing fiscal database

Author: Gerhard - Fiscal Analysis Platform
Created: October 2025
"""

import json
import time
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import requests
from dataclasses import dataclass, asdict
import logging
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fiscal_regime_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class FiscalRegimeEvent:
    """Data structure for fiscal regime events"""
    event_id: str
    title: str
    description: str
    content: str
    source_name: str
    source_url: str
    author: Optional[str]
    published_at: str
    collected_at: str

    # Event classification
    event_type: str  # default, technical_default, debt_restructuring, tax_reform,
                     # expenditure_reform, borrowing_reform, constitutional_change,
                     # accounting_change, currency_reform, fiscal_rule_change

    # Geographic
    countries: List[str]  # ISO2 country codes
    region: str

    # Severity and impact
    severity: str  # critical, major, moderate, minor
    impact_scope: str  # national, subnational, specific_tax, specific_expenditure

    # Analysis
    relevance_score: float  # 0-1
    keywords: List[str]
    entities: List[str]  # Countries, institutions, currencies mentioned

    # Integration
    regime_break: bool  # Does this event break fiscal time series?
    comparability_impact: str  # none, minor, major, complete_break

    def to_dict(self):
        return asdict(self)


class FiscalRegimeClassifier:
    """Classifies fiscal events by type and severity"""

    def __init__(self):
        self.event_types = self._load_event_types()
        self.severity_keywords = self._load_severity_keywords()
        self.country_patterns = self._load_country_patterns()

    def _load_event_types(self) -> Dict:
        """Define event type detection patterns"""
        return {
            'default': {
                'keywords': [
                    'sovereign default', 'debt default', 'missed payment', 'default on debt',
                    'failed to pay', 'suspended debt payments', 'moratorium',
                    'selective default', 'distressed exchange'
                ],
                'exclusions': ['avoid default', 'prevent default', 'risk of default'],
                'severity': 'critical'
            },
            'technical_default': {
                'keywords': [
                    'technical default', 'covenant breach', 'technical breach',
                    'grace period', 'missed interest payment', 'technical violation'
                ],
                'severity': 'major'
            },
            'debt_restructuring': {
                'keywords': [
                    'debt restructuring', 'debt renegotiation', 'debt relief',
                    'haircut', 'debt forgiveness', 'Paris Club', 'London Club',
                    'debt exchange', 'bond exchange', 'maturity extension',
                    'principal reduction', 'debt reprofiling'
                ],
                'severity': 'major'
            },
            'tax_reform': {
                'keywords': [
                    'tax reform', 'tax code change', 'new tax', 'tax rate change',
                    'VAT introduction', 'income tax reform', 'corporate tax reform',
                    'tax system overhaul', 'fiscal reform', 'revenue reform'
                ],
                'severity': 'moderate'
            },
            'expenditure_reform': {
                'keywords': [
                    'spending reform', 'expenditure rules', 'spending cap',
                    'budget reform', 'austerity', 'fiscal consolidation',
                    'spending cuts', 'expenditure ceiling', 'budget law'
                ],
                'severity': 'moderate'
            },
            'borrowing_reform': {
                'keywords': [
                    'debt ceiling', 'borrowing limit', 'debt rule', 'fiscal rule',
                    'balanced budget amendment', 'debt brake', 'golden rule',
                    'borrowing restriction', 'debt management reform'
                ],
                'severity': 'major'
            },
            'constitutional_change': {
                'keywords': [
                    'constitutional reform', 'constitutional amendment', 'new constitution',
                    'fiscal constitution', 'budgetary powers', 'constitutional court',
                    'federalism reform', 'decentralization', 'devolution'
                ],
                'severity': 'critical'
            },
            'accounting_change': {
                'keywords': [
                    'accounting standard change', 'accrual accounting', 'cash to accrual',
                    'GFSM 2014', 'ESA 2010', 'SNA 2008', 'accounting reform',
                    'public sector accounting', 'IPSAS adoption'
                ],
                'severity': 'major'
            },
            'currency_reform': {
                'keywords': [
                    'currency reform', 'redenomination', 'new currency',
                    'currency union', 'euro adoption', 'dollarization',
                    'currency peg change', 'exchange rate regime'
                ],
                'severity': 'critical'
            },
            'fiscal_rule_change': {
                'keywords': [
                    'fiscal framework', 'fiscal council', 'independent fiscal institution',
                    'spending review', 'medium-term budget framework',
                    'fiscal responsibility law', 'budget process reform'
                ],
                'severity': 'moderate'
            },
            'imf_program': {
                'keywords': [
                    'IMF program', 'IMF bailout', 'stand-by arrangement',
                    'extended fund facility', 'structural adjustment',
                    'IMF conditionality', 'IMF loan', 'troika'
                ],
                'severity': 'major'
            }
        }

    def _load_severity_keywords(self) -> Dict:
        """Keywords indicating event severity"""
        return {
            'critical': [
                'crisis', 'collapse', 'emergency', 'unprecedented',
                'catastrophic', 'massive', 'historic', 'dramatic'
            ],
            'major': [
                'significant', 'substantial', 'major', 'important',
                'sweeping', 'comprehensive', 'fundamental'
            ],
            'moderate': [
                'moderate', 'gradual', 'incremental', 'partial',
                'limited', 'modest', 'minor adjustment'
            ],
            'minor': [
                'minor', 'small', 'technical', 'administrative',
                'procedural', 'marginal'
            ]
        }

    def _load_country_patterns(self) -> Dict:
        """Load ISO country codes and patterns"""
        # This would load from the existing Countries directory
        # For now, include major defaults and restructurings
        return {
            'default_prone': [
                'AR', 'VE', 'GR', 'LB', 'EC', 'UY', 'RU', 'UA',
                'ZM', 'ZW', 'SR', 'BZ'
            ],
            'euro_crisis': [
                'GR', 'IE', 'PT', 'ES', 'IT', 'CY'
            ],
            'latin_america_debt_crisis': [
                'AR', 'BR', 'MX', 'CL', 'PE', 'VE', 'CO', 'EC'
            ],
            'asian_financial_crisis': [
                'TH', 'ID', 'KR', 'MY', 'PH'
            ],
            'former_soviet': [
                'RU', 'UA', 'BY', 'KZ', 'UZ', 'GE', 'AM', 'AZ',
                'MD', 'KG', 'TJ', 'TM'
            ],
            'african_defaults': [
                'ZM', 'ZW', 'GH', 'ZA', 'NG', 'EG', 'KE', 'ET'
            ]
        }

    def classify_event(self, text: str, title: str = "") -> Tuple[str, str, float]:
        """
        Classify fiscal event from text

        Returns:
            Tuple[str, str, float]: (event_type, severity, relevance_score)
        """
        combined_text = (title + " " + text).lower()
        title_lower = title.lower()

        # Detect event type
        event_scores = {}
        for event_type, config in self.event_types.items():
            score = 0

            # Check keywords (give extra weight to title matches)
            for keyword in config['keywords']:
                if keyword.lower() in combined_text:
                    # Title matches count double since title is more complete
                    if keyword.lower() in title_lower:
                        score += 2
                    else:
                        score += 1

            # Check exclusions
            if 'exclusions' in config:
                for exclusion in config['exclusions']:
                    if exclusion.lower() in combined_text:
                        score -= 0.5

            event_scores[event_type] = score

        # Get top event type
        if max(event_scores.values()) > 0:
            event_type = max(event_scores, key=event_scores.get)
            base_severity = self.event_types[event_type]['severity']
        else:
            event_type = 'unclassified'
            base_severity = 'minor'

        # Refine severity based on text
        severity_scores = {
            sev: sum(1 for kw in keywords if kw in combined_text)
            for sev, keywords in self.severity_keywords.items()
        }

        if max(severity_scores.values()) > 0:
            detected_severity = max(severity_scores, key=severity_scores.get)
            # Upgrade severity if text suggests higher impact
            severity_order = ['minor', 'moderate', 'major', 'critical']
            base_idx = severity_order.index(base_severity)
            detected_idx = severity_order.index(detected_severity)
            final_severity = severity_order[max(base_idx, detected_idx)]
        else:
            final_severity = base_severity

        # Calculate relevance score
        relevance = event_scores.get(event_type, 0) / 5.0  # Normalize
        relevance = min(1.0, relevance)

        return event_type, final_severity, relevance

    def extract_countries(self, text: str) -> List[str]:
        """Extract country mentions from text"""
        # This is simplified - would use full country name/ISO mapping
        countries = []

        # Country name patterns (simplified - would load from database)
        country_names = {
            'argentina': 'AR', 'greece': 'GR', 'venezuela': 'VE',
            'lebanon': 'LB', 'russia': 'RU', 'ukraine': 'UA',
            'ecuador': 'EC', 'uruguay': 'UY', 'zambia': 'ZM',
            'zimbabwe': 'ZW', 'turkey': 'TR', 'egypt': 'EG',
            'brazil': 'BR', 'mexico': 'MX', 'indonesia': 'ID',
            'thailand': 'TH', 'korea': 'KR', 'spain': 'ES',
            'italy': 'IT', 'portugal': 'PT', 'ireland': 'IE',
            'cyprus': 'CY', 'sri lanka': 'LK', 'pakistan': 'PK'
        }

        text_lower = text.lower()
        for country, iso2 in country_names.items():
            if country in text_lower:
                countries.append(iso2)

        return list(set(countries))  # Remove duplicates

    def assess_regime_break(self, event_type: str, severity: str) -> Tuple[bool, str]:
        """
        Assess if event causes fiscal regime break

        Returns:
            Tuple[bool, str]: (is_regime_break, comparability_impact)
        """
        regime_break_events = {
            'default': (True, 'major'),
            'constitutional_change': (True, 'major'),
            'currency_reform': (True, 'complete_break'),
            'accounting_change': (True, 'major'),
            'debt_restructuring': (True, 'moderate'),
        }

        if event_type in regime_break_events:
            is_break, impact = regime_break_events[event_type]

            # Severity can upgrade impact
            if severity == 'critical' and impact == 'moderate':
                impact = 'major'

            return is_break, impact

        # Non-breaking events
        if severity in ['critical', 'major']:
            return False, 'minor'

        return False, 'none'


class FiscalRegimeNewsCollector:
    """Main collector for fiscal regime and debt events"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.classifier = FiscalRegimeClassifier()
        self.db_path = Path("data/fiscal_regime_events.db")
        self.init_database()

        # Load API keys
        self._load_api_keys()

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)

        # Default configuration
        return {
            'collection_settings': {
                'max_articles_per_query': 20,
                'relevance_threshold': 0.15,  # Lowered for News API's short content
                'date_range_years': 65,  # 1960-2025
                'focus_on_defaults': True
            },
            'search_terms': self._get_default_search_terms(),
            'sources': {
                'newsapi': {'enabled': True, 'priority': 1},
                'gdelt': {'enabled': True, 'priority': 2},
                'nyt_archive': {'enabled': True, 'priority': 3},
                'guardian': {'enabled': True, 'priority': 4}
            }
        }

    def _get_default_search_terms(self) -> List[str]:
        """Get default search terms for fiscal regime events"""
        return [
            # Defaults and debt crises
            'sovereign debt default',
            'government default debt',
            'debt restructuring',
            'debt moratorium',
            'Paris Club debt',
            'IMF bailout',
            'debt crisis',

            # Technical defaults
            'technical default',
            'missed debt payment',
            'grace period debt',

            # Fiscal reforms
            'tax reform legislation',
            'fiscal constitution',
            'budget law reform',
            'fiscal rule',
            'debt ceiling',

            # Accounting changes
            'accounting standard change',
            'accrual accounting government',
            'GFSM 2014 adoption',

            # Currency reforms
            'currency reform',
            'redenomination',
            'euro adoption',

            # Country-specific high-value terms
            'Argentina debt', 'Greece debt crisis', 'Venezuela default',
            'Lebanon default', 'Zambia restructuring', 'Sri Lanka debt'
        ]

    def _load_api_keys(self):
        """Load news API keys from environment variables (optionally via a local .env)."""
        import os
        # Load a local .env if python-dotenv is available (optional convenience).
        try:
            from dotenv import load_dotenv
            env_file = Path('.env')
            if env_file.exists():
                load_dotenv(env_file)
                logger.info(f"Loaded local .env: {env_file}")
        except ImportError:
            logger.warning("python-dotenv not installed; reading keys directly from environment")

        # Read keys from the environment (set NEWS_API_KEY, NYT_API_KEY, etc.).
        self.config.setdefault('api_keys', {})
        self.config['api_keys']['NEWS_API_KEY'] = os.getenv('NEWS_API_KEY')
        self.config['api_keys']['NYT_API_KEY'] = os.getenv('NYT_API_KEY')
        self.config['api_keys']['GUARDIAN_API_KEY'] = os.getenv('GUARDIAN_API_KEY')
        self.config['api_keys']['CONGRESS_GOV_API_KEY'] = os.getenv('CONGRESS_GOV_API_KEY')

    def _load_local_env(self):
        """Fallback: Load API keys from local .env file"""
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        self.config.setdefault('api_keys', {})[key] = value
            logger.info("Loaded API keys from local .env file")
        else:
            logger.warning("No API keys file found. Please configure API keys.")

    def init_database(self):
        """Initialize fiscal regime events database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fiscal_regime_events (
                event_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                content TEXT,
                source_name TEXT,
                source_url TEXT UNIQUE,
                author TEXT,
                published_at TEXT,
                collected_at TEXT,

                event_type TEXT,
                countries TEXT,
                region TEXT,

                severity TEXT,
                impact_scope TEXT,
                relevance_score REAL,

                keywords TEXT,
                entities TEXT,

                regime_break BOOLEAN,
                comparability_impact TEXT,

                verified BOOLEAN DEFAULT 0,
                notes TEXT
            )
        ''')

        # Index for fast lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON fiscal_regime_events(countries)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON fiscal_regime_events(event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_published ON fiscal_regime_events(published_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_regime_break ON fiscal_regime_events(regime_break)')

        conn.commit()
        conn.close()

        logger.info(f"Initialized database: {self.db_path}")

    def collect_from_newsapi(self, search_term: str, date_from: Optional[str] = None) -> List[Dict]:
        """Collect news from News API"""
        if 'NEWS_API_KEY' not in self.config.get('api_keys', {}):
            logger.warning("News API key not configured, skipping News API")
            return []

        api_key = self.config['api_keys']['NEWS_API_KEY']
        base_url = "https://newsapi.org/v2/everything"

        # Date range (News API free tier: last month only)
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        params = {
            'q': search_term,
            'from': date_from,
            'sortBy': 'relevancy',
            'pageSize': self.config['collection_settings']['max_articles_per_query'],
            'language': 'en',
            'apiKey': api_key
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'ok':
                articles = data.get('articles', [])
                logger.info(f"Collected {len(articles)} articles for '{search_term}' from News API")
                return articles
            else:
                logger.error(f"News API error: {data.get('message')}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for News API: {e}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error in News API collection: {e}")
            return []

    def process_article(self, article: Dict, source: str = 'newsapi') -> Optional[FiscalRegimeEvent]:
        """Process raw article into FiscalRegimeEvent"""
        try:
            # Extract basic info
            title = article.get('title', '')
            description = article.get('description', '')
            content = article.get('content', description)
            source_url = article.get('url', '')

            # Skip if no substantive content
            if not title and not description:
                return None

            # Classify event
            event_type, severity, relevance_score = self.classifier.classify_event(
                content, title
            )

            # Check relevance threshold
            if relevance_score < self.config['collection_settings']['relevance_threshold']:
                return None

            # Extract countries
            countries = self.classifier.extract_countries(title + " " + content)

            # Assess regime break
            regime_break, comparability_impact = self.classifier.assess_regime_break(
                event_type, severity
            )

            # Generate unique ID
            event_id = hashlib.md5(source_url.encode()).hexdigest()

            # Create event
            event = FiscalRegimeEvent(
                event_id=event_id,
                title=title,
                description=description,
                content=content,
                source_name=article.get('source', {}).get('name', source),
                source_url=source_url,
                author=article.get('author'),
                published_at=article.get('publishedAt', datetime.now().isoformat()),
                collected_at=datetime.now().isoformat(),
                event_type=event_type,
                countries=countries,
                region=self._determine_region(countries),
                severity=severity,
                impact_scope='national' if countries else 'global',
                relevance_score=relevance_score,
                keywords=self._extract_keywords(title + " " + content),
                entities=countries,  # Could be expanded with NER
                regime_break=regime_break,
                comparability_impact=comparability_impact
            )

            return event

        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None

    def _determine_region(self, countries: List[str]) -> str:
        """Determine region from country list"""
        if not countries:
            return 'global'

        # Simplified region mapping
        regions = {
            'latin_america': ['AR', 'BR', 'MX', 'CL', 'CO', 'PE', 'VE', 'EC', 'UY', 'PY', 'BO'],
            'europe': ['GR', 'ES', 'IT', 'PT', 'IE', 'CY', 'DE', 'FR', 'GB', 'NL', 'BE'],
            'asia': ['CN', 'JP', 'IN', 'ID', 'TH', 'MY', 'PH', 'KR', 'VN', 'PK', 'LK'],
            'africa': ['ZA', 'NG', 'EG', 'KE', 'GH', 'ET', 'ZM', 'ZW'],
            'middle_east': ['TR', 'SA', 'AE', 'IL', 'LB', 'JO', 'IQ'],
            'former_soviet': ['RU', 'UA', 'BY', 'KZ', 'UZ', 'GE', 'AM', 'AZ']
        }

        for region, region_countries in regions.items():
            if any(c in region_countries for c in countries):
                return region

        return 'other'

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from text"""
        # Simplified keyword extraction
        keywords = []

        keyword_patterns = [
            r'\b(default|restructuring|bailout|crisis|reform|austerity)\b',
            r'\b(IMF|World Bank|Paris Club|troika)\b',
            r'\b(bond|debt|fiscal|budget|tax)\b'
        ]

        text_lower = text.lower()
        for pattern in keyword_patterns:
            matches = re.findall(pattern, text_lower)
            keywords.extend(matches)

        return list(set(keywords))[:10]  # Top 10 unique keywords

    def save_event(self, event: FiscalRegimeEvent) -> bool:
        """Save event to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO fiscal_regime_events
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
            ''', (
                event.event_id,
                event.title,
                event.description,
                event.content,
                event.source_name,
                event.source_url,
                event.author,
                event.published_at,
                event.collected_at,
                event.event_type,
                json.dumps(event.countries),
                event.region,
                event.severity,
                event.impact_scope,
                event.relevance_score,
                json.dumps(event.keywords),
                json.dumps(event.entities),
                event.regime_break,
                event.comparability_impact
            ))

            conn.commit()
            conn.close()

            logger.info(f"Saved event: {event.event_id} - {event.title[:50]}")
            return True

        except sqlite3.IntegrityError:
            logger.debug(f"Event already exists: {event.event_id}")
            return False

        except Exception as e:
            logger.error(f"Error saving event: {e}")
            return False

    def run_collection(self, search_terms: Optional[List[str]] = None,
                      date_from: Optional[str] = None) -> Dict:
        """
        Run news collection

        Args:
            search_terms: List of terms to search (defaults to config)
            date_from: Start date for collection (YYYY-MM-DD)

        Returns:
            Dict with collection statistics
        """
        if not search_terms:
            search_terms = self.config['search_terms']

        stats = {
            'start_time': datetime.now().isoformat(),
            'search_terms_used': len(search_terms),
            'articles_collected': 0,
            'events_saved': 0,
            'events_by_type': {},
            'countries_found': set()
        }

        for search_term in search_terms:
            logger.info(f"Collecting for search term: '{search_term}'")

            # Collect from News API
            articles = self.collect_from_newsapi(search_term, date_from)
            stats['articles_collected'] += len(articles)

            # Process each article
            for article in articles:
                event = self.process_article(article)

                if event:
                    if self.save_event(event):
                        stats['events_saved'] += 1
                        stats['events_by_type'][event.event_type] = \
                            stats['events_by_type'].get(event.event_type, 0) + 1
                        stats['countries_found'].update(event.countries)

            # Rate limiting
            time.sleep(1)

        stats['end_time'] = datetime.now().isoformat()
        stats['countries_found'] = list(stats['countries_found'])

        logger.info(f"Collection complete: {stats['events_saved']} events saved")

        return stats


def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Fiscal Regime News Collector - Starting")
    logger.info("=" * 60)

    collector = FiscalRegimeNewsCollector()

    # Run collection
    stats = collector.run_collection()

    # Print summary
    print("\n" + "=" * 60)
    print("COLLECTION SUMMARY")
    print("=" * 60)
    print(f"Articles collected: {stats['articles_collected']}")
    print(f"Events saved: {stats['events_saved']}")
    print(f"\nEvents by type:")
    for event_type, count in stats['events_by_type'].items():
        print(f"  {event_type}: {count}")
    print(f"\nCountries found: {len(stats['countries_found'])}")
    if stats['countries_found']:
        print(f"  {', '.join(sorted(stats['countries_found']))}")
    print("=" * 60)


if __name__ == "__main__":
    main()
