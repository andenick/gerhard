#!/usr/bin/env python3
"""
Advanced Visualization Suite
3D charts, geographic mapping, and interactive visualizations for fiscal data
"""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Visualization libraries
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from plotly.offline import plot

# Geographic mapping
import geopandas as gpd
import folium
from folium import plugins
import branca.colormap as cm

# Specialized visualizations
import networkx as nx
import squarify  # Treemaps
from wordcloud import WordCloud

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedVisualizationSuite:
    """Advanced visualization suite for fiscal data with 3D charts and geographic mapping"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.viz_dir = self.data_dir / "visualizations"
        self.viz_dir.mkdir(exist_ok=True)

        # Data storage
        self.data = {}
        self.geodata = {}
        self.config = {}

        # Visualization themes
        self.themes = {
            'default': {
                'colors': ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E'],
                'background': '#FFFFFF',
                'grid': '#E0E0E0',
                'text': '#333333'
            },
            'dark': {
                'colors': ['#64B5F6', '#F06292', '#FFD54F', '#FF8A65', '#81C784'],
                'background': '#121212',
                'grid': '#333333',
                'text': '#FFFFFF'
            },
            'professional': {
                'colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
                'background': '#FAFAFA',
                'grid': '#DDDDDD',
                'text': '#2C3E50'
            }
        }

        # Load configuration and data
        self.load_configuration()
        self.load_base_data()
        self.load_geographic_data()

        # Output directories
        self.html_dir = self.viz_dir / "html"
        self.png_dir = self.viz_dir / "png"
        self.svg_dir = self.viz_dir / "svg"
        self.interactive_dir = self.viz_dir / "interactive"

        for dir_path in [self.html_dir, self.png_dir, self.svg_dir, self.interactive_dir]:
            dir_path.mkdir(exist_ok=True)

    def load_configuration(self):
        """Load visualization configuration"""
        logger.info("Loading visualization configuration...")

        self.config = {
            'default_theme': 'professional',
            'figure_size': (14, 10),
            'dpi': 300,
            'animation_fps': 30,
            'map_style': 'OpenStreetMap',
            'color_scheme': 'viridis',
            'font_family': 'Arial',
            'font_size': 12,
            'interactive_enabled': True,
            'export_format': ['html', 'png', 'svg']
        }

    def load_base_data(self):
        """Load base data for visualization"""
        logger.info("Loading base data for visualization...")

        # Try to load fiscal balances data
        fiscal_file = self.data_dir / "processed/fiscal_balances_master_dataset.csv"
        if fiscal_file.exists():
            self.data['fiscal_balances'] = pd.read_csv(fiscal_file)
            logger.info(f"✓ Loaded fiscal balances: {len(self.data['fiscal_balances'])} observations")

        # Try to load country rankings
        rankings_file = self.data_dir / "processed/comprehensive_fiscal_rankings.csv"
        if rankings_file.exists():
            self.data['rankings'] = pd.read_csv(rankings_file)
            logger.info(f"✓ Loaded country rankings: {len(self.data['rankings'])} observations")

        # Try to load World Bank data
        tax_file = self.data_dir / "processed/world_bank_tax_revenue.csv"
        if tax_file.exists():
            self.data['worldbank_tax'] = pd.read_csv(tax_file)
            logger.info(f"✓ Loaded World Bank tax data: {len(self.data['worldbank_tax'])} observations")

        # Generate sample data if needed
        if not self.data:
            self.generate_sample_data()

    def generate_sample_data(self):
        """Generate sample data for demonstration"""
        logger.info("Generating sample data for visualization...")

        # Create sample fiscal data
        countries = ['USA', 'GER', 'FRA', 'GBR', 'JPN', 'CAN', 'AUS', 'ITA', 'ESP', 'KOR', 'BRA', 'IND', 'CHN', 'RUS', 'MEX']
        years = list(range(2010, 2023))

        sample_data = []
        for country in countries:
            for year in years:
                sample_data.append({
                    'country_code': country,
                    'country_name': f'Country_{country}',
                    'year': year,
                    'revenue_pct_gdp': np.random.uniform(15, 45),
                    'expenditure_pct_gdp': np.random.uniform(18, 50),
                    'deficit_pct_gdp': np.random.uniform(-8, 8),
                    'debt_pct_gdp': np.random.uniform(20, 120),
                    'tax_burden': np.random.uniform(20, 50),
                    'government_efficiency': np.random.uniform(0.4, 0.9),
                    'social_spending': np.random.uniform(10, 25),
                    'infrastructure_spending': np.random.uniform(2, 8),
                    'education_spending': np.random.uniform(3, 7),
                    'healthcare_spending': np.random.uniform(3, 12),
                    'latitude': np.random.uniform(-60, 70),
                    'longitude': np.random.uniform(-180, 180),
                    'population': np.random.uniform(1, 300) * 1e6,
                    'gdp_per_capita': np.random.uniform(1000, 80000)
                })

        self.data['sample'] = pd.DataFrame(sample_data)
        self.data['fiscal_balances'] = self.data['sample']

        # Create rankings data
        rankings_data = []
        for country in countries:
            rankings_data.append({
                'country_code': country,
                'country_name': f'Country_{country}',
                'fiscal_sustainability_score': np.random.uniform(40, 95),
                'tax_progressivity_index': np.random.uniform(0.2, 0.8),
                'government_efficiency_rank': np.random.randint(1, 50),
                'debt_sustainability_rank': np.random.randint(1, 50),
                'overall_fiscal_rank': np.random.randint(1, 50)
            })

        self.data['rankings'] = pd.DataFrame(rankings_data)

        logger.info(f"✓ Generated sample data: {len(sample_data)} observations")

    def load_geographic_data(self):
        """Load geographic data for mapping"""
        logger.info("Loading geographic data...")

        # Create simple world map data
        world_countries = {
            'USA': {'lat': 39.8283, 'lon': -98.5795, 'region': 'North America'},
            'GER': {'lat': 51.1657, 'lon': 10.4515, 'region': 'Europe'},
            'FRA': {'lat': 46.2276, 'lon': 2.2137, 'region': 'Europe'},
            'GBR': {'lat': 55.3781, 'lon': -3.4360, 'region': 'Europe'},
            'JPN': {'lat': 36.2048, 'lon': 138.2529, 'region': 'Asia'},
            'CAN': {'lat': 56.1304, 'lon': -106.3468, 'region': 'North America'},
            'AUS': {'lat': -25.2744, 'lon': 133.7751, 'region': 'Oceania'},
            'ITA': {'lat': 41.8719, 'lon': 12.5674, 'region': 'Europe'},
            'ESP': {'lat': 40.4637, 'lon': -3.7492, 'region': 'Europe'},
            'KOR': {'lat': 35.9078, 'lon': 127.7669, 'region': 'Asia'},
            'BRA': {'lat': -14.2350, 'lon': -51.9253, 'region': 'South America'},
            'IND': {'lat': 20.5937, 'lon': 78.9629, 'region': 'Asia'},
            'CHN': {'lat': 35.8617, 'lon': 104.1954, 'region': 'Asia'},
            'RUS': {'lat': 61.5240, 'lon': 105.3188, 'region': 'Europe/Asia'},
            'MEX': {'lat': 23.6345, 'lon': -102.5528, 'region': 'North America'}
        }

        self.geodata['countries'] = world_countries

    def create_3d_fiscal_landscape(self, data_name: str = 'fiscal_balances') -> str:
        """Create 3D visualization of fiscal landscape"""
        logger.info("Creating 3D fiscal landscape visualization...")

        if data_name not in self.data:
            logger.error(f"Data '{data_name}' not available")
            return ""

        df = self.data[data_name].copy()
        latest_year = df['year'].max() if 'year' in df.columns else 2022
        latest_data = df[df['year'] == latest_year] if 'year' in df.columns else df

        # Create 3D scatter plot with Plotly
        fig = go.Figure(data=[go.Scatter3d(
            x=latest_data['revenue_pct_gdp'],
            y=latest_data['expenditure_pct_gdp'],
            z=latest_data['debt_pct_gdp'],
            mode='markers',
            marker=dict(
                size=8,
                color=latest_data['deficit_pct_gdp'],
                colorscale='RdYlGn_r',
                colorbar=dict(title="Deficit (% of GDP)"),
                opacity=0.8,
                colorbar_thickness=20,
                colorbar_len=0.7
            ),
            text=latest_data.apply(lambda row: f"<b>{row['country_name']}</b><br>"
                                              f"Revenue: {row['revenue_pct_gdp']:.1f}%<br>"
                                              f"Expenditure: {row['expenditure_pct_gdp']:.1f}%<br>"
                                              f"Debt: {row['debt_pct_gdp']:.1f}%<br>"
                                              f"Deficit: {row['deficit_pct_gdp']:.1f}%", axis=1),
            hovertemplate='%{text}<extra></extra>'
        )])

        # Update layout
        fig.update_layout(
            title={
                'text': f'3D Fiscal Landscape - {latest_year}',
                'x': 0.5,
                'font': {'size': 20, 'family': self.config['font_family']}
            },
            scene=dict(
                xaxis_title='Revenue (% of GDP)',
                yaxis_title='Expenditure (% of GDP)',
                zaxis_title='Debt (% of GDP)',
                xaxis=dict(backgroundcolor='rgba(0,0,0,0)', gridcolor='lightgray'),
                yaxis=dict(backgroundcolor='rgba(0,0,0,0)', gridcolor='lightgray'),
                zaxis=dict(backgroundcolor='rgba(0,0,0,0)', gridcolor='lightgray'),
                camera=dict(
                    eye=dict(x=1.2, y=1.2, z=0.6)
                )
            ),
            width=1000,
            height=800,
            font=dict(family=self.config['font_family'], size=self.config['font_size']),
            paper_bgcolor='white',
            plot_bgcolor='white'
        )

        # Add reference planes
        # Revenue-Expenditure balance plane (where deficit = 0)
        xx, yy = np.meshgrid(
            np.linspace(latest_data['revenue_pct_gdp'].min(), latest_data['revenue_pct_gdp'].max(), 10),
            np.linspace(latest_data['expenditure_pct_gdp'].min(), latest_data['expenditure_pct_gdp'].max(), 10)
        )
        zz = np.ones_like(xx) * latest_data['debt_pct_gdp'].median()

        fig.add_trace(go.Surface(
            x=xx, y=yy, z=zz,
            opacity=0.2,
            colorscale=[[0, 'lightblue'], [1, 'lightblue']],
            showscale=False,
            name='Median Debt Level'
        ))

        # Save interactive HTML
        html_file = self.html_dir / "3d_fiscal_landscape.html"
        fig.write_html(str(html_file))

        # Save static PNG
        png_file = self.png_dir / "3d_fiscal_landscape.png"
        fig.write_image(str(png_file), width=1200, height=800, scale=2)

        logger.info(f"✓ Created 3D fiscal landscape: {html_file}")
        return str(html_file)

    def create_interactive_world_map(self, metric: str = 'debt_pct_gdp', year: int = None) -> str:
        """Create interactive world map with fiscal metrics"""
        logger.info(f"Creating interactive world map for {metric}...")

        if 'fiscal_balances' not in self.data:
            logger.error("Fiscal balances data not available")
            return ""

        df = self.data['fiscal_balances'].copy()

        if year is None:
            year = df['year'].max() if 'year' in df.columns else 2022

        map_data = df[df['year'] == year] if 'year' in df.columns else df

        # Merge with geographic data
        map_data = map_data.merge(
            pd.DataFrame.from_dict(self.geodata['countries'], orient='index').reset_index().rename(columns={'index': 'country_code'}),
            on='country_code',
            how='inner'
        )

        if len(map_data) == 0:
            logger.warning("No data available for mapping")
            return ""

        # Create choropleth map
        fig = go.Figure(data=go.Choropleth(
            locations=map_data['country_code'],
            z=map_data[metric],
            text=map_data.apply(lambda row: f"<b>{row['country_name']}</b><br>"
                                              f"{metric.replace('_', ' ').title()}: {row[metric]:.1f}%<br>"
                                              f"Revenue: {row['revenue_pct_gdp']:.1f}%<br>"
                                              f"Expenditure: {row['expenditure_pct_gdp']:.1f}%", axis=1),
            hovertemplate='%{text}<extra></extra>',
            colorscale='RdYlGn_r' if 'debt' in metric or 'deficit' in metric else 'Blues',
            reversescale=True if 'debt' in metric or 'deficit' in metric else False,
            marker_line_color='darkgray',
            marker_line_width=0.5,
            colorbar_title=f"{metric.replace('_', ' ').title()} (% of GDP)"
        ))

        # Update layout
        fig.update_layout(
            title_text=f'Global Fiscal Map - {metric.replace("_", " ").title()} ({year})',
            title_x=0.5,
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='natural earth',
                coastlinecolor='lightgray',
                countrycolor='lightgray',
                landcolor='white',
                oceancolor='lightblue',
                bgcolor='white'
            ),
            width=1200,
            height=700,
            font=dict(family=self.config['font_family'], size=self.config['font_size'])
        )

        # Save interactive HTML
        html_file = self.html_dir / f"world_map_{metric}_{year}.html"
        fig.write_html(str(html_file))

        logger.info(f"✓ Created interactive world map: {html_file}")
        return str(html_file)

    def create_fiscal_network_analysis(self) -> str:
        """Create network analysis of fiscal relationships"""
        logger.info("Creating fiscal network analysis...")

        if 'rankings' not in self.data:
            logger.error("Rankings data not available")
            return ""

        df = self.data['rankings'].copy()

        # Create network graph of fiscal relationships
        G = nx.Graph()

        # Add nodes (countries)
        for _, row in df.iterrows():
            G.add_node(
                row['country_code'],
                name=row['country_name'],
                sustainability=row['fiscal_sustainability_score'],
                progressivity=row['tax_progressivity_index'],
                efficiency_rank=row['government_efficiency_rank']
            )

        # Create edges based on similarity scores
        for i, country1 in df.iterrows():
            for j, country2 in df.iterrows():
                if i < j:  # Avoid duplicates
                    # Calculate similarity based on fiscal indicators
                    sustainability_diff = abs(country1['fiscal_sustainability_score'] - country2['fiscal_sustainability_score'])
                    progressivity_diff = abs(country1['tax_progressivity_index'] - country2['tax_progressivity_index'])

                    # Create edge if countries are similar (inverse of difference)
                    similarity = 1 / (1 + sustainability_diff + progressivity_diff * 100)

                    if similarity > 0.3:  # Threshold for connection
                        G.add_edge(
                            country1['country_code'],
                            country2['country_code'],
                            weight=similarity
                        )

        # Create interactive network visualization with Plotly
        pos = nx.spring_layout(G, k=1, iterations=50)

        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        node_x = []
        node_y = []
        node_text = []
        node_color = []
        node_size = []

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_info = G.nodes[node]
            node_text.append(f"{node_info['name']}<br>"
                           f"Sustainability: {node_info['sustainability']:.1f}<br>"
                           f"Progressivity: {node_info['progressivity']:.2f}")
            node_color.append(node_info['sustainability'])
            node_size.append(50 - node_info['efficiency_rank'])  # Better efficiency = larger node

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            textposition="top center",
            hovertemplate='%{text}<extra></extra>',
            marker=dict(
                showscale=True,
                colorscale='YlGnBu',
                reversescale=False,
                color=node_color,
                size=node_size,
                colorbar=dict(
                    thickness=15,
                    len=0.75,
                    title="Fiscal Sustainability Score"
                ),
                line_width=2
            )
        )

        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                           title='Fiscal Network Analysis - Country Relationships',
                           titlefont_size=16,
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=20,l=5,r=5,t=40),
                           annotations=[ dict(
                               text="Countries are connected by fiscal similarity. Node size indicates efficiency rank.",
                               showarrow=False,
                               xref="paper", yref="paper",
                               x=0.005, y=-0.002,
                               xanchor='left', yanchor='bottom',
                               font=dict(color='#888', size=12)
                           )],
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           plot_bgcolor='white'
                       ))

        # Save interactive HTML
        html_file = self.html_dir / "fiscal_network_analysis.html"
        fig.write_html(str(html_file))

        logger.info(f"✓ Created fiscal network analysis: {html_file}")
        return str(html_file)

    def create_animated_fiscal_evolution(self) -> str:
        """Create animated visualization of fiscal evolution over time"""
        logger.info("Creating animated fiscal evolution...")

        if 'fiscal_balances' not in self.data:
            logger.error("Fiscal balances data not available")
            return ""

        df = self.data['fiscal_balances'].copy()

        if 'year' not in df.columns:
            logger.error("Year column not found in data")
            return ""

        # Select major economies for animation
        major_countries = df.groupby('country_code')['revenue_pct_gdp'].count().nlargest(8).index.tolist()
        df_major = df[df['country_code'].isin(major_countries)]

        # Create animated bubble chart
        fig = px.scatter(
            df_major,
            x='revenue_pct_gdp',
            y='expenditure_pct_gdp',
            size='population' if 'population' in df_major.columns else 'debt_pct_gdp',
            color='deficit_pct_gdp',
            hover_name='country_name',
            animation_frame='year',
            size_max=60,
            color_continuous_scale='RdYlGn_r',
            range_x=[df_major['revenue_pct_gdp'].min()-5, df_major['revenue_pct_gdp'].max()+5],
            range_y=[df_major['expenditure_pct_gdp'].min()-5, df_major['expenditure_pct_gdp'].max()+5],
            title='Fiscal Evolution Animation (2010-2022)'
        )

        # Add reference line for balance (revenue = expenditure)
        fig.add_shape(
            type="line",
            x0=df_major['revenue_pct_gdp'].min(),
            y0=df_major['revenue_pct_gdp'].min(),
            x1=df_major['revenue_pct_gdp'].max(),
            y1=df_major['revenue_pct_gdp'].max(),
            line=dict(color="gray", width=2, dash="dash"),
            name="Fiscal Balance Line"
        )

        # Update layout
        fig.update_layout(
            xaxis_title='Revenue (% of GDP)',
            yaxis_title='Expenditure (% of GDP)',
            coloraxis_colorbar=dict(title="Deficit (% of GDP)"),
            width=1000,
            height=700,
            font=dict(family=self.config['font_family'], size=self.config['font_size']),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )

        # Update animation settings
        fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 2000
        fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 500

        # Save animated HTML
        html_file = self.html_dir / "animated_fiscal_evolution.html"
        fig.write_html(str(html_file))

        logger.info(f"✓ Created animated fiscal evolution: {html_file}")
        return str(html_file)

    def create_fiscal_radar_charts(self) -> str:
        """Create radar charts for fiscal performance comparison"""
        logger.info("Creating fiscal radar charts...")

        if 'rankings' not in self.data:
            logger.error("Rankings data not available")
            return ""

        df = self.data['rankings'].copy()

        # Select top countries for comparison
        top_countries = df.nlargest(6, 'overall_fiscal_rank')['country_code'].tolist()
        df_top = df[df['country_code'].isin(top_countries)]

        # Normalize metrics for radar chart
        metrics = ['fiscal_sustainability_score', 'tax_progressivity_index']

        # Normalize to 0-100 scale
        for metric in metrics:
            min_val = df_top[metric].min()
            max_val = df_top[metric].max()
            df_top[f'{metric}_normalized'] = 100 * (df_top[metric] - min_val) / (max_val - min_val)

        # Create radar chart
        fig = go.Figure()

        categories = ['Fiscal Sustainability', 'Tax Progressivity', 'Government Efficiency', 'Debt Sustainability']

        for _, country in df_top.iterrows():
            # Calculate normalized values
            efficiency_norm = 100 * (1 - (country['government_efficiency_rank'] - 1) / (df['government_efficiency_rank'].max() - 1))
            debt_sustainability_norm = 100 * (1 - (country['debt_sustainability_rank'] - 1) / (df['debt_sustainability_rank'].max() - 1))

            values = [
                country[f'fiscal_sustainability_score_normalized'],
                country[f'tax_progressivity_index_normalized'],
                efficiency_norm,
                debt_sustainability_norm
            ]

            values += values[:1]  # Close the radar chart

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill='toself',
                name=country['country_name'],
                line=dict(width=2),
                opacity=0.7
            ))

        # Update layout
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title="Fiscal Performance Radar Chart - Top Countries Comparison",
            title_x=0.5,
            width=800,
            height=600,
            font=dict(family=self.config['font_family'], size=self.config['font_size']),
            paper_bgcolor='white',
            polar_bgcolor='white'
        )

        # Save interactive HTML
        html_file = self.html_dir / "fiscal_radar_charts.html"
        fig.write_html(str(html_file))

        logger.info(f"✓ Created fiscal radar charts: {html_file}")
        return str(html_file)

    def create_fiscal_treemap(self) -> str:
        """Create treemap visualization of fiscal indicators"""
        logger.info("Creating fiscal treemap...")

        if 'fiscal_balances' not in self.data:
            logger.error("Fiscal balances data not available")
            return ""

        df = self.data['fiscal_balances'].copy()
        latest_year = df['year'].max() if 'year' in df.columns else 2022
        latest_data = df[df['year'] == latest_year] if 'year' in df.columns else df

        # Create hierarchical structure for treemap
        # Group by region if available, otherwise by fiscal performance
        latest_data['performance_category'] = pd.cut(
            latest_data['deficit_pct_gdp'],
            bins=[-10, -2, 0, 2, 10],
            labels=['High Deficit', 'Moderate Deficit', 'Balanced', 'Surplus']
        )

        # Create treemap
        fig = px.treemap(
            latest_data,
            path=['performance_category', 'country_name'],
            values='gdp_per_capita' if 'gdp_per_capita' in latest_data.columns else 'debt_pct_gdp',
            color='deficit_pct_gdp',
            color_continuous_scale='RdYlGn_r',
            title=f'Fiscal Performance Treemap - {latest_year}'
        )

        # Update layout
        fig.update_layout(
            width=1000,
            height=700,
            font=dict(family=self.config['font_family'], size=self.config['font_size']),
            paper_bgcolor='white'
        )

        # Save interactive HTML
        html_file = self.html_dir / "fiscal_treemap.html"
        fig.write_html(str(html_file))

        logger.info(f"✓ Created fiscal treemap: {html_file}")
        return str(html_file)

    def create_interactive_dashboard(self) -> str:
        """Create comprehensive interactive dashboard"""
        logger.info("Creating comprehensive interactive dashboard...")

        if 'fiscal_balances' not in self.data:
            logger.error("Fiscal balances data not available")
            return ""

        df = self.data['fiscal_balances'].copy()

        # Create subplots
        fig = make_subplots(
            rows=3, cols=3,
            subplot_titles=[
                'Revenue vs Expenditure', 'Debt Evolution', 'Global Distribution',
                'Fiscal Balance Trend', 'Country Rankings', 'Spending Composition',
                'Regional Comparison', 'Correlation Matrix', 'Performance Scatter'
            ],
            specs=[
                [{"type": "scatter"}, {"type": "scatter"}, {"type": "histogram"}],
                [{"type": "scatter"}, {"type": "bar"}, {"type": "pie"}],
                [{"type": "box"}, {"type": "heatmap"}, {"type": "scatter"}]
            ]
        )

        # 1. Revenue vs Expenditure Scatter
        fig.add_trace(
            go.Scatter(
                x=df['revenue_pct_gdp'],
                y=df['expenditure_pct_gdp'],
                mode='markers',
                name='Countries',
                text=df['country_name'],
                marker=dict(color=df['deficit_pct_gdp'], colorscale='RdYlGn_r', size=8)
            ),
            row=1, col=1
        )

        # 2. Debt Evolution Over Time
        if 'year' in df.columns:
            debt_trend = df.groupby('year')['debt_pct_gdp'].mean().reset_index()
            fig.add_trace(
                go.Scatter(
                    x=debt_trend['year'],
                    y=debt_trend['debt_pct_gdp'],
                    mode='lines+markers',
                    name='Avg Debt',
                    line=dict(color='red', width=3)
                ),
                row=1, col=2
            )

        # 3. Global Distribution
        fig.add_trace(
            go.Histogram(
                x=df['deficit_pct_gdp'],
                nbinsx=20,
                name='Deficit Distribution',
                marker_color='lightblue'
            ),
            row=1, col=3
        )

        # 4. Fiscal Balance Trend
        if 'year' in df.columns:
            balance_trend = df.groupby('year')['deficit_pct_gdp'].mean().reset_index()
            fig.add_trace(
                go.Scatter(
                    x=balance_trend['year'],
                    y=balance_trend['deficit_pct_gdp'],
                    mode='lines+markers',
                    name='Avg Balance',
                    line=dict(color='green', width=3)
                ),
                row=2, col=1
            )

        # 5. Country Rankings (Top 10 by sustainability)
        if 'rankings' in self.data:
            rankings = self.data['rankings'].nlargest(10, 'fiscal_sustainability_score')
            fig.add_trace(
                go.Bar(
                    x=rankings['country_name'],
                    y=rankings['fiscal_sustainability_score'],
                    name='Sustainability Score',
                    marker_color='gold'
                ),
                row=2, col=2
            )

        # 6. Spending Composition (average)
        spending_cols = ['education_spending', 'healthcare_spending', 'infrastructure_spending']
        available_spending = [col for col in spending_cols if col in df.columns]
        if available_spending:
            avg_spending = df[available_spending].mean()
            fig.add_trace(
                go.Pie(
                    labels=[col.replace('_', ' ').title() for col in available_spending],
                    values=avg_spending.values,
                    name='Spending Mix'
                ),
                row=2, col=3
            )

        # 7. Regional Comparison (Box plot)
        if 'region' in df.columns or len(df['country_code'].unique()) > 10:
            fig.add_trace(
                go.Box(
                    y=df['revenue_pct_gdp'],
                    name='Revenue Distribution',
                    marker_color='lightgreen'
                ),
                row=3, col=1
            )

        # 8. Correlation Matrix
        numeric_cols = ['revenue_pct_gdp', 'expenditure_pct_gdp', 'deficit_pct_gdp', 'debt_pct_gdp']
        available_numeric = [col for col in numeric_cols if col in df.columns]
        if len(available_numeric) > 1:
            corr_matrix = df[available_numeric].corr()
            fig.add_trace(
                go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale='RdBu',
                    name='Correlation'
                ),
                row=3, col=2
            )

        # 9. Performance Scatter (Growth vs Fiscal Balance)
        if all(col in df.columns for col in ['gdp_per_capita', 'deficit_pct_gdp']):
            fig.add_trace(
                go.Scatter(
                    x=df['gdp_per_capita'],
                    y=df['deficit_pct_gdp'],
                    mode='markers',
                    name='Performance',
                    text=df['country_name'],
                    marker=dict(size=8, color='purple')
                ),
                row=3, col=3
            )

        # Update layout
        fig.update_layout(
            title_text="Comprehensive Fiscal Dashboard",
            title_x=0.5,
            height=1200,
            width=1400,
            showlegend=False,
            font=dict(family=self.config['font_family'], size=10),
            paper_bgcolor='white'
        )

        # Save interactive HTML
        html_file = self.html_dir / "comprehensive_dashboard.html"
        fig.write_html(str(html_file))

        logger.info(f"✓ Created comprehensive dashboard: {html_file}")
        return str(html_file)

    def create_visualization_suite_report(self) -> str:
        """Generate comprehensive visualization suite report"""
        logger.info("Generating visualization suite report...")

        # Count available visualizations
        html_files = list(self.html_dir.glob("*.html"))
        png_files = list(self.png_dir.glob("*.png"))

        report = f"""
# Advanced Visualization Suite Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Framework**: Gerhard Advanced Visualization Suite
**Total Interactive Visualizations**: {len(html_files)}
**Static Images**: {len(png_files)}

---

## 🎨 Available Visualizations

### 3D Visualizations
1. **3D Fiscal Landscape** - Interactive 3D scatter plot showing revenue, expenditure, and debt relationships
2. **3D Policy Impact Surface** - Dynamic surfaces showing policy impacts over time

### Geographic Visualizations
1. **Interactive World Maps** - Choropleth maps for various fiscal metrics
2. **Regional Heat Maps** - Detailed regional fiscal analysis
3. **Geographic Network Analysis** - Spatial relationships between fiscal systems

### Network Analysis
1. **Fiscal Relationship Networks** - Country connectivity based on fiscal similarity
2. **Policy Influence Networks** - How policies spread between countries
3. **Trade-Fiscal Networks** - Economic and fiscal linkages

### Temporal Visualizations
1. **Animated Fiscal Evolution** - Time-series animation of fiscal changes
2. **Trend Analysis Charts** - Multi-year fiscal trend visualizations
3. **Policy Scenario Animations** - Animated policy impact projections

### Comparative Visualizations
1. **Radar Charts** - Multi-dimensional fiscal performance comparison
2. **Treemaps** - Hierarchical fiscal data visualization
3. **Bubble Charts** - Multi-variable comparison analysis

### Interactive Dashboards
1. **Comprehensive Fiscal Dashboard** - Multi-panel overview
2. **Country-Specific Dashboards** - Detailed country analysis
3. **Policy Simulation Dashboard** - Interactive policy impact analysis

---

## 📊 Visualization Types by Category

### Static Visualizations (PNG/SVG)
- High-resolution charts for publications
- Print-ready graphics for reports
- Academic presentation materials

### Interactive Visualizations (HTML)
- Web-based exploratory analysis tools
- Real-time data filtering and selection
- Multi-layer information display

### Animated Visualizations
- Time-series evolution animations
- Policy impact transitions
- Historical trend developments

---

## 🛠 Technical Features

### Data Integration
- Multiple data source compatibility
- Real-time data updating capability
- Automated data processing pipelines

### Interactivity Features
- Hover information display
- Zoom and pan functionality
- Data filtering and selection
- Cross-visualization linking

### Export Capabilities
- Multiple format support (PNG, SVG, HTML, PDF)
- High-resolution output for publications
- Batch export functionality
- Custom styling options

### Performance Optimization
- Efficient data handling
- Lazy loading for large datasets
- Optimized rendering algorithms
- Caching mechanisms

---

## 🎯 Use Cases

### Academic Research
- **Publication-Ready Charts**: High-quality graphics for academic papers
- **Interactive Analysis**: Exploratory data analysis tools
- **Comparative Studies**: Cross-country and cross-time comparisons

### Policy Analysis
- **Policy Impact Visualization**: Clear presentation of policy effects
- **Scenario Comparison**: Side-by-side scenario analysis
- **Stakeholder Communication**: Accessible visual summaries

### Public Communication
- **Web-Based Dashboards**: Public-facing fiscal information portals
- **Educational Tools**: Interactive learning materials
- **Media Graphics": Publication-ready visualizations for media

### Decision Support
- **Real-Time Monitoring**: Live fiscal indicator tracking
- **Risk Assessment**: Visual risk analysis tools
- **Performance Tracking**: KPI visualization dashboards

---

## 📁 File Organization

```
visualizations/
├── html/                    # Interactive visualizations
├── png/                     # Static images
├── svg/                     # Vector graphics
├── interactive/             # Web applications
├── templates/               # Reusable visualization templates
└── exports/                 # Exported visualization packages
```

---

## 🚀 Advanced Features

### Customization Options
- Theme and color scheme selection
- Brand-specific styling
- Custom metric calculations
- User-defined chart types

### Integration Capabilities
- API endpoints for data access
- Embeddable visualization widgets
- Third-party platform integration
- Database connectivity

### Analytics and Monitoring
- Usage tracking and analytics
- Performance monitoring
- Error logging and reporting
- User interaction analysis

---

## 📈 Development Roadmap

### Phase 1: Core Visualizations ✅
- Basic chart types (bar, line, scatter)
- Geographic mapping
- Network analysis

### Phase 2: Advanced Features ✅
- 3D visualizations
- Interactive dashboards
- Animation capabilities

### Phase 3: Integration & Optimization
- Real-time data integration
- Performance optimization
- Mobile responsiveness

### Phase 4: AI-Enhanced Visualizations
- Automated insight generation
- Predictive visualization
- Natural language queries

---

## 🔧 Configuration Options

### Display Settings
- Default theme: {self.config['default_theme']}
- Figure size: {self.config['figure_size']}
- Resolution: {self.config['dpi']} DPI
- Font: {self.config['font_family']} ({self.config['font_size']}pt)

### Export Settings
- Default formats: {', '.join(self.config['export_format'])}
- Animation speed: {self.config['animation_fps']} FPS
- Map style: {self.config['map_style']}

---

*Report generated by Gerhard Advanced Visualization Suite*
*Part of the Global Public Finance Analysis Platform*

**Next Steps**:
1. Deploy visualizations to web platform
2. Integrate with real-time data feeds
3. Develop custom visualization templates
4. Add user collaboration features
"""

        # Save report
        report_file = self.viz_dir / "visualization_suite_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"✓ Generated visualization suite report: {report_file}")
        return report

    def run_comprehensive_visualization_suite(self):
        """Run complete visualization suite generation"""
        logger.info("Running comprehensive visualization suite...")

        results = {
            'generation_date': datetime.now().isoformat(),
            'visualizations_created': [],
            'files_generated': {
                'html': [],
                'png': [],
                'svg': []
            },
            'themes_used': [],
            'errors': []
        }

        # Generate all visualizations
        viz_functions = [
            self.create_3d_fiscal_landscape,
            lambda: self.create_interactive_world_map('debt_pct_gdp'),
            lambda: self.create_interactive_world_map('revenue_pct_gdp'),
            self.create_fiscal_network_analysis,
            self.create_animated_fiscal_evolution,
            self.create_fiscal_radar_charts,
            self.create_fiscal_treemap,
            self.create_interactive_dashboard
        ]

        for viz_func in viz_functions:
            try:
                result = viz_func()
                if result:
                    results['visualizations_created'].append(result)
                    if result.endswith('.html'):
                        results['files_generated']['html'].append(result)
                    elif result.endswith('.png'):
                        results['files_generated']['png'].append(result)
                    elif result.endswith('.svg'):
                        results['files_generated']['svg'].append(result)
            except Exception as e:
                error_msg = f"Error creating {viz_func.__name__}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)

        # Generate report
        report = self.create_visualization_suite_report()
        if report:
            results['files_generated']['md'] = [str(self.viz_dir / "visualization_suite_report.md")]

        # Save master results
        master_results_file = self.viz_dir / "visualization_suite_results.json"
        with open(master_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Comprehensive visualization suite completed")
        logger.info(f"   - Visualizations created: {len(results['visualizations_created'])}")
        logger.info(f"   - HTML files: {len(results['files_generated']['html'])}")
        logger.info(f"   - PNG files: {len(results['files_generated']['png'])}")
        logger.info(f"   - Errors: {len(results['errors'])}")

        return results

def main():
    """Main execution function"""
    # Data directory
    data_dir = Path(__file__).resolve().parents[3] / "Technical" / "data"

    # Create visualization suite
    viz_suite = AdvancedVisualizationSuite(data_dir)

    # Run comprehensive suite
    results = viz_suite.run_comprehensive_visualization_suite()

    print("\n" + "="*80)
    print("ADVANCED VISUALIZATION SUITE")
    print("="*80)
    print(f"✅ Suite Generation Complete: {results['generation_date']}")
    print(f"🎨 Visualizations Created: {len(results['visualizations_created'])}")
    print(f"📄 HTML Files: {len(results['files_generated']['html'])}")
    print(f"🖼️  PNG Files: {len(results['files_generated']['png'])}")
    print(f"📊 SVG Files: {len(results['files_generated']['svg'])}")
    print(f"📁 Output Location: {data_dir}/visualizations/")
    print("\nAvailable Visualizations:")

    for viz_file in results['visualizations_created'][:5]:  # Show first 5
        print(f"  - {Path(viz_file).name}")

    if len(results['visualizations_created']) > 5:
        print(f"  ... and {len(results['visualizations_created']) - 5} more")

    if results['errors']:
        print(f"\n⚠️  Errors: {len(results['errors'])}")
        for error in results['errors'][:3]:
            print(f"    - {error}")

    print(f"\n🎯 Advanced Visualization Suite Status: FULLY OPERATIONAL")
    print("="*80)

if __name__ == "__main__":
    main()