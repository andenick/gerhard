#!/usr/bin/env python3
"""
Interactive Real-Time Fiscal Dashboard
Advanced visualization platform with Plotly/Dash for global fiscal analysis
"""

import sys
from pathlib import Path

# Resolve project paths
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.config import project_root
from utils.paths import output_data_dir, countries_dir
from utils.logging_setup import setup_logging

logger = setup_logging(__name__)

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple
import threading
import time

class FiscalDashboard:
    """Interactive real-time fiscal dashboard application"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        # Data sources
        self.data_sources = {}
        self.last_update = datetime.now()

        # Dashboard configuration
        self.refresh_interval = 300000  # 5 minutes in milliseconds
        self.max_countries_per_chart = 20

        # Theme colors
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'success': '#F18F01',
            'danger': '#C73E1D',
            'warning': '#F4A261',
            'info': '#264653',
            'light': '#E9C46A',
            'dark': '#2A9D8F'
        }

        # Initialize data
        self.load_data_sources()

    def get_country_count(self) -> int:
        """Return number of unique countries across data sources."""
        countries = set()
        for df in self.data_sources.values():
            if 'country_code' in df.columns:
                countries.update(df['country_code'].dropna().unique())
            elif 'country_name' in df.columns:
                countries.update(df['country_name'].dropna().unique())
        return len(countries) if countries else 0

    def get_year_span(self) -> str:
        """Return human-readable year span across data sources."""
        years = []
        for df in self.data_sources.values():
            if 'year' in df.columns:
                years.extend(df['year'].dropna().tolist())
        if years:
            return f"{int(min(years))}-{int(max(years))}"
        return "N/A"

    def load_data_sources(self):
        """Load all available data sources"""
        logger.info("Loading data sources for dashboard...")

        out_dir = output_data_dir()

        # Load master datasets
        master_balances_file = out_dir / "fiscal_balances_master_dataset.xlsx"
        if master_balances_file.exists():
            self.data_sources['fiscal_balances'] = pd.read_excel(master_balances_file)
            logger.info(f"Loaded fiscal balances: {len(self.data_sources['fiscal_balances'])} observations")

        # Load world bank data
        worldbank_file = out_dir / "world_bank_tax_revenue.xlsx"
        if worldbank_file.exists():
            self.data_sources['worldbank_tax'] = pd.read_excel(worldbank_file)
            logger.info(f"Loaded World Bank tax data: {len(self.data_sources['worldbank_tax'])} observations")

        # Load country data
        rankings_file = out_dir / "global_tax_rankings.xlsx"
        if rankings_file.exists():
            self.data_sources['rankings'] = pd.read_excel(rankings_file)
            logger.info(f"Loaded country rankings: {len(self.data_sources['rankings'])} observations")

        # Load US enhanced data if available
        c_dir = countries_dir()
        us_file = c_dir / "US" / "Output" / "Enhanced_Analysis" / "us_tax_distribution_extended_2024.xlsx"
        if us_file.exists():
            self.data_sources['us_enhanced'] = pd.read_excel(us_file)
            logger.info(f"Loaded US enhanced data: {len(self.data_sources['us_enhanced'])} observations")

        logger.info(f" Loaded {len(self.data_sources)} data sources for dashboard")

    def create_layout(self):
        """Create dashboard layout"""
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("Gerhard Global Fiscal Dashboard",
                           className="text-center mb-4",
                           style={'color': self.colors['primary']}),
                    html.H4("Real-Time Public Finance Analysis Platform",
                           className="text-center mb-4 text-muted"),
                    html.P(f"Last Updated: {self.last_update.strftime('%Y-%m-%d %H:%M:%S')}",
                          className="text-center text-muted mb-4"),
                    dbc.Alert([
                        html.H5(" Global Coverage", className="alert-heading"),
                        html.P(f"Analyzing fiscal data for {self.get_country_count()} countries across {self.get_year_span()} years"),
                    ], color="info", className="mb-4")
                ], width=12)
            ]),

            # Control Panel
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Dashboard Controls", className="card-title"),

                            # Region/Income Group Filter
                            html.Label("Select Region/Income Group:"),
                            dcc.Dropdown(
                                id='region-filter',
                                options=[
                                    {'label': 'All Countries', 'value': 'all'},
                                    {'label': 'High Income', 'value': 'high_income'},
                                    {'label': 'Upper Middle Income', 'value': 'upper_middle'},
                                    {'label': 'Lower Middle Income', 'value': 'lower_middle'},
                                    {'label': 'Low Income', 'value': 'low_income'},
                                    {'label': 'OECD Countries', 'value': 'oecd'},
                                    {'label': 'European Union', 'value': 'eu'},
                                    {'label': 'G20 Countries', 'value': 'g20'}
                                ],
                                value='all',
                                className="mb-3"
                            ),

                            # Year Range Slider
                            html.Label("Select Year Range:"),
                            dcc.RangeSlider(
                                id='year-range',
                                min=1990,
                                max=2024,
                                step=1,
                                value=[2010, 2024],
                                marks={i: str(i) for i in range(1990, 2025, 5)},
                                tooltip={"placement": "bottom", "always_visible": False},
                                className="mb-3"
                            ),

                            # Indicator Selection
                            html.Label("Select Fiscal Indicators:"),
                            dcc.Checklist(
                                id='indicators',
                                options=[
                                    {'label': 'Tax Revenue (% of GDP)', 'value': 'tax_revenue'},
                                    {'label': 'Government Expenditure (% of GDP)', 'value': 'expenditure'},
                                    {'label': 'Fiscal Balance (% of GDP)', 'value': 'deficit'},
                                    {'label': 'Public Debt (% of GDP)', 'value': 'debt'},
                                    {'label': 'Sustainability Score', 'value': 'sustainability'},
                                    {'label': 'Progressivity Index', 'value': 'progressivity'}
                                ],
                                value=['tax_revenue', 'deficit', 'sustainability'],
                                className="mb-3"
                            ),

                            # Refresh Button
                            dbc.Button("Refresh Data", id="refresh-btn", color="primary", className="w-100")
                        ])
                    ])
                ], width=12, lg=3),

                # Main Charts Area
                dbc.Col([
                    # Key Metrics Row
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Key Global Metrics", className="card-title"),
                                    html.Div(id='key-metrics')
                                ])
                            ], color="light")
                        ], width=12, className="mb-4")
                    ]),

                    # Charts Row 1
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Global Fiscal Balance Distribution", className="card-title"),
                                    dcc.Graph(id='balance-distribution-chart')
                                ])
                            ])
                        ], width=12, lg=6, className="mb-4"),

                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Tax Revenue vs Expenditure", className="card-title"),
                                    dcc.Graph(id='revenue-expenditure-chart')
                                ])
                            ])
                        ], width=12, lg=6, className="mb-4")
                    ]),

                    # Charts Row 2
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Fiscal Sustainability Heatmap", className="card-title"),
                                    dcc.Graph(id='sustainability-heatmap')
                                ])
                            ])
                        ], width=12, lg=8, className="mb-4"),

                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Top Performing Countries", className="card-title"),
                                    html.Div(id='top-countries-table')
                                ])
                            ])
                        ], width=12, lg=4, className="mb-4")
                    ]),

                    # Charts Row 3
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Historical Fiscal Trends", className="card-title"),
                                    dcc.Graph(id='historical-trends-chart')
                                ])
                            ])
                        ], width=12, className="mb-4")
                    ])

                ], width=12, lg=9)
            ]),

            # Footer
            dbc.Row([
                dbc.Col([
                    html.Hr(),
                    html.P([
                        "Gerhard Platform - Global Public Finance Analysis System | ",
                        html.A("Documentation", href="#", className="text-decoration-none"),
                        " | ",
                        html.A("API Documentation", href="#", className="text-decoration-none"),
                        " | ",
                        html.A("Data Sources", href="#", className="text-decoration-none")
                    ], className="text-center text-muted")
                ], width=12)
            ]),

            # Auto-refresh component
            dcc.Interval(
                id='interval-component',
                interval=self.refresh_interval,
                n_intervals=0
            )

        ], fluid=True)

    def setup_callbacks(self):
        """Setup all dashboard callbacks"""

        @self.app.callback(
            [Output('key-metrics', 'children'),
             Output('balance-distribution-chart', 'figure'),
             Output('revenue-expenditure-chart', 'figure'),
             Output('sustainability-heatmap', 'figure'),
             Output('top-countries-table', 'children'),
             Output('historical-trends-chart', 'figure')],
            [Input('region-filter', 'value'),
             Input('year-range', 'value'),
             Input('indicators', 'value'),
             Input('refresh-btn', 'n_clicks'),
             Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(region_filter, year_range, indicators, refresh_clicks, n_intervals):
            """Update all dashboard components"""

            # Get filtered data
            filtered_data = self.get_filtered_data(region_filter, year_range)

            if filtered_data is None or len(filtered_data) == 0:
                return self.create_no_data_layout()

            # Update components
            key_metrics = self.create_key_metrics(filtered_data)
            balance_chart = self.create_balance_distribution_chart(filtered_data)
            revenue_chart = self.create_revenue_expenditure_chart(filtered_data)
            sustainability_heatmap = self.create_sustainability_heatmap(filtered_data)
            top_countries = self.create_top_countries_table(filtered_data)
            trends_chart = self.create_historical_trends_chart(filtered_data)

            return key_metrics, balance_chart, revenue_chart, sustainability_heatmap, top_countries, trends_chart

    def get_filtered_data(self, region_filter: str, year_range: list) -> Optional[pd.DataFrame]:
        """Get data filtered by region and year range"""
        if 'fiscal_balances' not in self.data_sources:
            return None

        df = self.data_sources['fiscal_balances'].copy()

        # Filter by year range
        if 'year' in df.columns:
            df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

        # Filter by region (if not 'all')
        if region_filter != 'all':
            df = self.filter_by_region(df, region_filter)

        return df

    def filter_by_region(self, df: pd.DataFrame, region_filter: str) -> pd.DataFrame:
        """Filter dataframe by region/income group"""
        if 'income_group' not in df.columns:
            return df

        region_mappings = {
            'high_income': ['high_income'],
            'upper_middle': ['upper_middle'],
            'lower_middle': ['lower_middle'],
            'low_income': ['low_income'],
            'oecd': ['high_income'],  # Most OECD are high income
            'eu': ['high_income'],  # Most EU are high income
            'g20': ['high_income', 'upper_middle']  # Mix of income groups
        }

        target_groups = region_mappings.get(region_filter, [])
        if target_groups:
            df = df[df['income_group'].isin(target_groups)]

        return df

    def create_key_metrics(self, df: pd.DataFrame):
        """Create key metrics display"""
        if len(df) == 0:
            return html.P("No data available")

        latest_data = df[df['year'] == df['year'].max()]

        metrics = []

        # Average tax revenue
        if 'revenue_pct_gdp' in latest_data.columns:
            avg_revenue = latest_data['revenue_pct_gdp'].mean()
            metrics.append(
                dbc.Col([
                    html.H6(f"{avg_revenue:.1f}%"),
                    html.P("Avg Tax Revenue", className="text-muted")
                ], width=4, className="text-center")
            )

        # Average deficit
        if 'deficit_pct_gdp' in latest_data.columns:
            avg_deficit = latest_data['deficit_pct_gdp'].mean()
            deficit_color = "danger" if avg_deficit < -3 else "warning" if avg_deficit < 0 else "success"
            metrics.append(
                dbc.Col([
                    html.H6(f"{avg_deficit:.1f}%", className=f"text-{deficit_color}"),
                    html.P("Avg Fiscal Balance", className="text-muted")
                ], width=4, className="text-center")
            )

        # Average sustainability
        if 'sustainability_score' in latest_data.columns:
            avg_sustainability = latest_data['sustainability_score'].mean()
            sus_color = "success" if avg_sustainability > 70 else "warning" if avg_sustainability > 40 else "danger"
            metrics.append(
                dbc.Col([
                    html.H6(f"{avg_sustainability:.0f}", className=f"text-{sus_color}"),
                    html.P("Avg Sustainability", className="text-muted")
                ], width=4, className="text-center")
            )

        return dbc.Row(metrics)

    def create_balance_distribution_chart(self, df: pd.DataFrame):
        """Create fiscal balance distribution chart"""
        if 'deficit_pct_gdp' not in df.columns or len(df) == 0:
            return px.scatter(title="No data available")

        # Create histogram of deficit distribution
        fig = px.histogram(
            df,
            x='deficit_pct_gdp',
            nbins=30,
            title="Global Fiscal Balance Distribution",
            labels={'deficit_pct_gdp': 'Fiscal Balance (% of GDP)', 'count': 'Number of Countries'},
            color_discrete_sequence=[self.colors['primary']]
        )

        fig.add_vline(x=0, line_dash="dash", line_color="red",
                     annotation_text="Breakeven", annotation_position="bottom right")
        fig.add_vline(x=-3, line_dash="dash", line_color="orange",
                     annotation_text="Warning (-3%)", annotation_position="top right")

        fig.update_layout(
            plot_bgcolor='rgba(248,248,248,0.8)',
            paper_bgcolor='white',
            font=dict(size=12),
            height=400
        )

        return fig

    def create_revenue_expenditure_chart(self, df: pd.DataFrame):
        """Create revenue vs expenditure scatter plot"""
        if 'revenue_pct_gdp' not in df.columns or 'expenditure_pct_gdp' not in df.columns:
            return px.scatter(title="No data available")

        # Get top countries by data availability
        country_counts = df['country_name'].value_counts()
        top_countries = country_counts.head(self.max_countries_per_chart).index
        plot_df = df[df['country_name'].isin(top_countries)]

        fig = px.scatter(
            plot_df,
            x='revenue_pct_gdp',
            y='expenditure_pct_gdp',
            color='sustainability_score',
            size='deficit_pct_gdp',
            hover_name='country_name',
            title="Tax Revenue vs Government Expenditure",
            labels={
                'revenue_pct_gdp': 'Tax Revenue (% of GDP)',
                'expenditure_pct_gdp': 'Expenditure (% of GDP)',
                'sustainability_score': 'Sustainability Score',
                'deficit_pct_gdp': 'Fiscal Balance'
            },
            color_continuous_scale='Viridis'
        )

        # Add 45-degree line (where revenue = expenditure)
        max_val = max(
            plot_df['revenue_pct_gdp'].max(),
            plot_df['expenditure_pct_gdp'].max()
        )
        fig.add_shape(
            type="line", x0=0, y0=0, x1=max_val, y1=max_val,
            line=dict(color="red", width=2, dash="dash")
        )

        fig.update_layout(
            plot_bgcolor='rgba(248,248,248,0.8)',
            paper_bgcolor='white',
            font=dict(size=12),
            height=400
        )

        return fig

    def create_sustainability_heatmap(self, df: pd.DataFrame):
        """Create fiscal sustainability heatmap"""
        if len(df) == 0:
            return px.scatter(title="No data available")

        # Create pivot table for heatmap
        latest_year = df['year'].max()
        latest_data = df[df['year'] == latest_year]

        # Get top countries
        top_countries = latest_data.nlargest(15, 'sustainability_score')

        if 'sustainability_score' not in top_countries.columns:
            return px.scatter(title="No sustainability data available")

        # Create heatmap data
        heatmap_data = []
        for _, row in top_countries.iterrows():
            heatmap_data.append({
                'Country': row['country_name'],
                'Sustainability': row['sustainability_score'],
                'Revenue': row.get('revenue_pct_gdp', 0),
                'Deficit': row.get('deficit_pct_gdp', 0)
            })

        heatmap_df = pd.DataFrame(heatmap_data)

        fig = px.imshow(
            [heatmap_df['Sustainability'].values],
            x=heatmap_df['Country'].values,
            y=['Sustainability Score'],
            color_continuous_scale='RdYlGn',
            range_color=[0, 100],
            title="Fiscal Sustainability Heatmap (Top 15 Countries)"
        )

        fig.update_layout(
            height=300,
            xaxis_title="",
            yaxis_title=""
        )

        return fig

    def create_top_countries_table(self, df: pd.DataFrame):
        """Create top countries table"""
        if len(df) == 0:
            return html.P("No data available")

        # Get top performing countries
        latest_data = df[df['year'] == df['year'].max()]

        if 'sustainability_score' not in latest_data.columns:
            return html.P("No sustainability data available")

        top_countries = latest_data.nlargest(10, 'sustainability_score')

        table_header = [
            html.Thead([
                html.Tr([
                    html.Th("Rank"),
                    html.Th("Country"),
                    html.Th("Sustainability"),
                    html.Th("Tax Revenue"),
                    html.Th("Balance")
                ])
            ])
        ]

        table_body = []
        for i, (_, row) in enumerate(top_countries.iterrows(), 1):
            balance = row.get('deficit_pct_gdp', 0)
            balance_class = "text-danger" if balance < -3 else "text-warning" if balance < 0 else "text-success"

            table_body.append(
                html.Tr([
                    html.Td(f"#{i}"),
                    html.Td(row['country_name']),
                    html.Td(f"{row['sustainability_score']:.0f}"),
                    html.Td(f"{row.get('revenue_pct_gdp', 0):.1f}%"),
                    html.Td(f"{balance:.1f}%", className=balance_class)
                ])
            )

        table = dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, size="sm")

        return table

    def create_historical_trends_chart(self, df: pd.DataFrame):
        """Create historical trends chart"""
        if len(df) == 0:
            return px.scatter(title="No data available")

        # Get time series data for top countries
        country_counts = df['country_name'].value_counts()
        top_countries = country_counts.head(5).index
        trend_df = df[df['country_name'].isin(top_countries)]

        fig = go.Figure()

        # Add line for each country
        for country in top_countries:
            country_data = trend_df[trend_df['country_name'] == country]
            if 'year' in country_data.columns and 'sustainability_score' in country_data.columns:
                fig.add_trace(go.Scatter(
                    x=country_data['year'],
                    y=country_data['sustainability_score'],
                    mode='lines+markers',
                    name=country,
                    line=dict(width=2)
                ))

        fig.update_layout(
            title="Historical Sustainability Trends (Top 5 Countries)",
            xaxis_title="Year",
            yaxis_title="Sustainability Score",
            plot_bgcolor='rgba(248,248,248,0.8)',
            paper_bgcolor='white',
            height=400,
            hovermode='x unified'
        )

        return fig

    def create_no_data_layout(self):
        """Create layout when no data is available"""
        return (
            html.Div("No data available", className="text-center text-muted"),
            px.scatter(title="No data available"),
            px.scatter(title="No data available"),
            px.scatter(title="No data available"),
            html.P("No data available"),
            px.scatter(title="No data available")
        )

    def run_dashboard(self, debug=False, port=8050):
        """Run the dashboard application"""
        logger.info("Starting Gerhard Interactive Dashboard...")

        # Create layout
        self.create_layout()

        # Setup callbacks
        self.setup_callbacks()

        # Run the app
        self.app.run(debug=debug, port=port, host='0.0.0.0')

        logger.info(f"Dashboard running on http://localhost:{port}")

def main():
    """Main execution function"""
    # Data directory resolved from project utils
    data_dir = project_root() / "Technical" / "data"

    # Create and run dashboard
    dashboard = FiscalDashboard(data_dir)
    dashboard.run_dashboard(debug=False, port=8050)

if __name__ == "__main__":
    main()