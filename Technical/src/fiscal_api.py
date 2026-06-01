#!/usr/bin/env python3
"""
Fiscal Data RESTful API
Real-time data access endpoints for global fiscal analysis platform
"""

import sys
from pathlib import Path

# Resolve project paths
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.config import project_root
from utils.paths import output_data_dir
from utils.logging_setup import setup_logging

logger = setup_logging(__name__)

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from functools import wraps
import time
import traceback

class FiscalDataAPI:
    """RESTful API for fiscal data access"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for all routes

        # Configure app
        self.app.config['JSON_SORT_KEYS'] = False
        self.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

        # Data storage
        self.data_sources = {}
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.api_version = "v1"

        # Rate limiting
        self.rate_limits = {}
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_requests = 100

        # Load data
        self.load_data_sources()

        # Setup routes
        self.setup_routes()

    def load_data_sources(self):
        """Load all data sources"""
        logger.info("Loading data sources for API...")

        out_dir = output_data_dir()

        # Load fiscal balances
        balances_file = out_dir / "fiscal_balances_master_dataset.xlsx"
        if balances_file.exists():
            self.data_sources['fiscal_balances'] = pd.read_excel(balances_file)
            logger.info(f"Loaded fiscal balances: {len(self.data_sources['fiscal_balances'])} observations")

        # Load country rankings
        rankings_file = out_dir / "global_tax_rankings.xlsx"
        if rankings_file.exists():
            self.data_sources['rankings'] = pd.read_excel(rankings_file)
            logger.info(f"Loaded country rankings: {len(self.data_sources['rankings'])} observations")

        # Load tax data
        tax_file = out_dir / "world_bank_tax_revenue.xlsx"
        if tax_file.exists():
            self.data_sources['worldbank_tax'] = pd.read_excel(tax_file)
            logger.info(f"Loaded World Bank tax data: {len(self.data_sources['worldbank_tax'])} observations")

        # Load progressivity data
        progressivity_file = out_dir / "analysis_tax_progressivity.xlsx"
        if progressivity_file.exists():
            self.data_sources['progressivity'] = pd.read_excel(progressivity_file)
            logger.info(f"Loaded progressivity data: {len(self.data_sources['progressivity'])} observations")

        logger.info(f" Loaded {len(self.data_sources)} data sources for API")

    def rate_limit(self, f):
        """Rate limiting decorator"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

            now = time.time()
            window_start = now - self.rate_limit_window

            # Clean old entries
            self.rate_limits = {
                ip: times for ip, times in self.rate_limits.items()
                if any(t > window_start for t in times)
            }

            # Check rate limit
            if client_ip in self.rate_limits:
                recent_requests = [t for t in self.rate_limits[client_ip] if t > window_start]
                if len(recent_requests) >= self.rate_limit_max_requests:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Maximum {self.rate_limit_max_requests} requests per {self.rate_limit_window} seconds',
                        'retry_after': self.rate_limit_window
                    }), 429

            # Record request
            if client_ip not in self.rate_limits:
                self.rate_limits[client_ip] = []
            self.rate_limits[client_ip].append(now)

            return f(*args, **kwargs)

        return decorated_function

    def cache_response(self, key: str, data_func, timeout: int = None):
        """Cache API responses"""
        cache_key = f"{self.api_version}:{key}"

        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < (timeout or self.cache_timeout):
                return cached_data

        # Generate new data
        data = data_func()

        # Store in cache
        self.cache[cache_key] = (data, time.time())

        return data

    def setup_routes(self):
        """Setup all API routes"""

        @self.app.route('/')
        def index():
            """API root endpoint"""
            return jsonify({
                'name': 'Gerhard Fiscal Data API',
                'version': self.api_version,
                'description': 'RESTful API for global public finance analysis',
                'endpoints': self.get_available_endpoints(),
                'documentation': f'/api/{self.api_version}/docs',
                'status': 'active',
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route(f'/api/{self.api_version}/docs')
        def api_docs():
            """API documentation"""
            return jsonify({
                'title': 'Gerhard Fiscal Data API Documentation',
                'version': self.api_version,
                'base_url': request.base_url,
                'endpoints': self.get_available_endpoints(),
                'authentication': 'None required',
                'rate_limiting': {
                    'max_requests_per_minute': self.rate_limit_max_requests,
                    'window_seconds': self.rate_limit_window
                },
                'data_sources': list(self.data_sources.keys()),
                'last_updated': datetime.now().isoformat()
            })

        @self.app.route(f'/api/{self.api_version}/countries')
        @self.rate_limit
        def get_countries():
            """Get list of all countries with data"""
            def fetch_data():
                countries = []

                for source_name, df in self.data_sources.items():
                    if 'country_code' in df.columns:
                        unique_countries = df[['country_code', 'country_name']].drop_duplicates()
                        for _, row in unique_countries.iterrows():
                            country_info = {
                                'country_code': row['country_code'],
                                'country_name': row['country_name'],
                                'data_sources': []
                            }

                            # Check which sources have data for this country
                            for other_source, other_df in self.data_sources.items():
                                if 'country_code' in other_df.columns:
                                    if row['country_code'] in other_df['country_code'].values:
                                        country_info['data_sources'].append(other_source)

                            countries.append(country_info)

                # Remove duplicates and merge data sources
                unique_countries = {}
                for country in countries:
                    code = country['country_code']
                    if code not in unique_countries:
                        unique_countries[code] = country
                    else:
                        unique_countries[code]['data_sources'] = list(set(
                            unique_countries[code]['data_sources'] + country['data_sources']
                        ))

                return list(unique_countries.values())

            data = self.cache_response('countries', fetch_data, timeout=600)
            return jsonify({
                'countries': data,
                'total_count': len(data),
                'last_updated': datetime.now().isoformat()
            })

        @self.app.route(f'/api/{self.api_version}/countries/<country_code>')
        @self.rate_limit
        def get_country_data(country_code):
            """Get detailed data for a specific country"""
            def fetch_data():
                country_data = {}

                for source_name, df in self.data_sources.items():
                    if 'country_code' in df.columns:
                        country_records = df[df['country_code'] == country_code.upper()]
                        if len(country_records) > 0:
                            country_data[source_name] = country_records.to_dict('records')

                if not country_data:
                    return None

                return country_data

            data = self.cache_response(f'country_{country_code}', fetch_data, timeout=300)

            if data is None:
                return jsonify({
                    'error': 'Country not found',
                    'message': f'No data available for country code: {country_code}',
                    'available_countries': f'/api/{self.api_version}/countries'
                }), 404

            return jsonify({
                'country_code': country_code.upper(),
                'data': data,
                'last_updated': datetime.now().isoformat()
            })

        @self.app.route(f'/api/{self.api_version}/fiscal-balances')
        @self.rate_limit
        def get_fiscal_balances():
            """Get fiscal balance data"""
            def fetch_data():
                if 'fiscal_balances' not in self.data_sources:
                    return None

                df = self.data_sources['fiscal_balances']

                # Apply filters from query parameters
                filters = {}

                # Year filter
                if 'year' in request.args:
                    try:
                        year = int(request.args['year'])
                        df = df[df['year'] == year]
                        filters['year'] = year
                    except ValueError:
                        pass

                # Year range filter
                if 'year_start' in request.args and 'year_end' in request.args:
                    try:
                        start_year = int(request.args['year_start'])
                        end_year = int(request.args['year_end'])
                        df = df[(df['year'] >= start_year) & (df['year'] <= end_year)]
                        filters['year_range'] = [start_year, end_year]
                    except ValueError:
                        pass

                # Income group filter
                if 'income_group' in request.args:
                    income_group = request.args['income_group']
                    if 'income_group' in df.columns:
                        df = df[df['income_group'] == income_group]
                        filters['income_group'] = income_group

                return {
                    'data': df.to_dict('records'),
                    'filters_applied': filters,
                    'total_records': len(df)
                }

            data = self.cache_response('fiscal_balances', fetch_data, timeout=300)

            if data is None:
                return jsonify({
                    'error': 'Fiscal balances data not available',
                    'message': 'The fiscal balances dataset is not loaded'
                }), 404

            return jsonify(data)

        @self.app.route(f'/api/{self.api_version}/rankings')
        @self.rate_limit
        def get_rankings():
            """Get country rankings"""
            def fetch_data():
                if 'rankings' not in self.data_sources:
                    return None

                df = self.data_sources['rankings']

                # Sort by composite rank if available
                if 'composite_rank' in df.columns:
                    df = df.sort_values('composite_rank')
                elif 'sustainability_score' in df.columns:
                    df = df.sort_values('sustainability_score', ascending=False)

                return {
                    'rankings': df.to_dict('records'),
                    'total_countries': len(df),
                    'ranking_method': 'composite_score' if 'composite_rank' in df.columns else 'sustainability_score'
                }

            data = self.cache_response('rankings', fetch_data, timeout=300)

            if data is None:
                return jsonify({
                    'error': 'Rankings data not available',
                    'message': 'The rankings dataset is not loaded'
                }), 404

            return jsonify(data)

        @self.app.route(f'/api/{self.api_version}/statistics')
        @self.rate_limit
        def get_statistics():
            """Get global statistics"""
            def fetch_data():
                stats = {}

                # Global fiscal statistics
                if 'fiscal_balances' in self.data_sources:
                    df = self.data_sources['fiscal_balances']
                    latest_year = df['year'].max()
                    latest_data = df[df['year'] == latest_year]

                    if len(latest_data) > 0:
                        stats['global_statistics'] = {
                            'year': int(latest_year),
                            'total_countries': len(latest_data),
                            'average_tax_revenue_pct_gdp': float(latest_data['revenue_pct_gdp'].mean()) if 'revenue_pct_gdp' in latest_data.columns else None,
                            'average_deficit_pct_gdp': float(latest_data['deficit_pct_gdp'].mean()) if 'deficit_pct_gdp' in latest_data.columns else None,
                            'average_debt_pct_gdp': float(latest_data['debt_pct_gdp'].mean()) if 'debt_pct_gdp' in latest_data.columns else None,
                            'average_sustainability_score': float(latest_data['sustainability_score'].mean()) if 'sustainability_score' in latest_data.columns else None
                        }

                # Tax revenue statistics
                if 'worldbank_tax' in self.data_sources:
                    df = self.data_sources['worldbank_tax']
                    stats['tax_revenue'] = {
                        'total_records': len(df),
                        'year_range': [int(df['year'].min()), int(df['year'].max())] if 'year' in df.columns else None,
                        'countries_count': df['country_code'].nunique() if 'country_code' in df.columns else None
                    }

                # Data source status
                stats['data_sources'] = {
                    name: {
                        'records': len(df),
                        'last_updated': datetime.now().isoformat()
                    }
                    for name, df in self.data_sources.items()
                }

                return stats

            data = self.cache_response('statistics', fetch_data, timeout=600)
            return jsonify(data)

        @self.app.route(f'/api/{self.api_version}/download/<dataset>')
        def download_dataset(dataset):
            """Download dataset as file"""
            # Map dataset names to files
            out_dir = output_data_dir()
            dataset_files = {
                'fiscal_balances': out_dir / "fiscal_balances_master_dataset.xlsx",
                'rankings': out_dir / "global_tax_rankings.xlsx",
                'worldbank_tax': out_dir / "world_bank_tax_revenue.xlsx",
                'progressivity': out_dir / "analysis_tax_progressivity.xlsx"
            }

            if dataset not in dataset_files:
                return jsonify({
                    'error': 'Dataset not found',
                    'message': f'Available datasets: {list(dataset_files.keys())}'
                }), 404

            file_path = dataset_files[dataset]

            if not file_path.exists():
                return jsonify({
                    'error': 'File not found',
                    'message': f'The file for dataset {dataset} does not exist'
                }), 404

            try:
                return send_file(file_path, as_attachment=True, download_name=f'gerhard_{dataset}.xlsx')
            except Exception as e:
                logger.error(f"Error downloading file {file_path}: {e}")
                return jsonify({
                    'error': 'Download failed',
                    'message': str(e)
                }), 500

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'error': 'Not found',
                'message': 'The requested endpoint does not exist',
                'available_endpoints': self.get_available_endpoints()
            }), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            logger.error(f"Internal server error: {error}")
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }), 500

    def get_available_endpoints(self):
        """Get list of available API endpoints"""
        base_url = f"/api/{self.api_version}"
        return [
            f"{base_url}/",
            f"{base_url}/docs",
            f"{base_url}/countries",
            f"{base_url}/countries/<country_code>",
            f"{base_url}/fiscal-balances",
            f"{base_url}/rankings",
            f"{base_url}/statistics",
            f"{base_url}/download/<dataset>"
        ]

    def run_api(self, debug=False, port=5000):
        """Run the API server"""
        logger.info("Starting Gerhard Fiscal Data API...")

        logger.info(f" API loaded with {len(self.data_sources)} data sources")
        logger.info(f" Available endpoints: {len(self.get_available_endpoints())}")
        logger.info(f" Rate limiting: {self.rate_limit_max_requests} requests per {self.rate_limit_window} seconds")

        try:
            self.app.run(debug=debug, port=port, host='0.0.0.0')
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise

def main():
    """Main execution function"""
    # Data directory resolved from project utils
    data_dir = project_root() / "Technical" / "data"

    # Create and run API
    api = FiscalDataAPI(data_dir)
    api.run_api(debug=False, port=5000)

if __name__ == "__main__":
    main()