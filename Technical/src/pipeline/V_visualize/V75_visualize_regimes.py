#!/usr/bin/env python3
"""
V75: Visualize Fiscal Regime Taxonomy
World map scatter by regime type and grouped bar of regime profiles.
Stage: V | ID: V75
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, output_pdfs_dir
from utils.data_io import read_excel_safe

logger = setup_logging(__name__)

MANIFEST = {
    "id": "V75",
    "name": "Visualize Fiscal Regimes",
    "stage": "V",
    "description": "World map and regime profiles visualization",
    "depends_on": ["A135"],
    "inputs": [
        {"path": "Output/Data/fiscal_regime_taxonomy.xlsx", "required": True},
        {"path": "Output/Data/regime_summary_statistics.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/PDFs/regime_world_map.png"},
        {"path": "Output/PDFs/regime_profiles.png"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# Regime colors
REGIME_COLORS = {
    'Nordic Welfare': '#1f77b4',
    'Continental European': '#2ca02c',
    'Anglo-Saxon Liberal': '#ff7f0e',
    'Developmental': '#9467bd',
    'Petro-State': '#8c564b',
    'Agrarian Developing': '#d62728',
    'Debt-Constrained': '#e377c2',
    'Mixed/Transitional': '#7f7f7f',
}

# Approximate lat/lon for major economies (for scatter map)
COUNTRY_COORDS = {
    'USA': (39.8, -98.6), 'GBR': (54.0, -2.0), 'FRA': (46.6, 2.3), 'DEU': (51.2, 10.4),
    'JPN': (36.2, 138.3), 'CHN': (35.9, 104.2), 'IND': (20.6, 79.0), 'BRA': (-14.2, -51.9),
    'RUS': (61.5, 105.3), 'CAN': (56.1, -106.3), 'AUS': (-25.3, 133.8), 'ZAF': (-30.6, 22.9),
    'MEX': (23.6, -102.6), 'IDN': (-0.8, 113.9), 'KOR': (35.9, 127.8), 'TUR': (39.0, 35.2),
    'SAU': (23.9, 45.1), 'ARG': (-38.4, -63.6), 'NGA': (9.1, 8.7), 'EGY': (26.8, 30.8),
    'SWE': (60.1, 18.6), 'NOR': (60.5, 8.5), 'DNK': (56.3, 9.5), 'FIN': (61.9, 25.7),
    'NLD': (52.1, 5.3), 'BEL': (50.5, 4.5), 'AUT': (47.5, 14.6), 'CHE': (46.8, 8.2),
    'ITA': (41.9, 12.6), 'ESP': (40.5, -3.7), 'PRT': (39.4, -8.2), 'GRC': (39.1, 21.8),
    'POL': (51.9, 19.1), 'CZE': (49.8, 15.5), 'COL': (4.6, -74.3), 'CHL': (-35.7, -71.5),
    'PER': (-9.2, -75.0), 'VEN': (6.4, -66.6), 'IRQ': (33.2, 43.7), 'IRN': (32.4, 53.7),
    'ARE': (23.4, 53.8), 'KWT': (29.3, 47.5), 'QAT': (25.4, 51.2), 'PAK': (30.4, 69.3),
    'BGD': (23.7, 90.4), 'VNM': (14.1, 108.3), 'THA': (15.9, 100.9), 'MYS': (4.2, 101.9),
    'PHL': (12.9, 121.8), 'KEN': (-0.0, 37.9), 'GHA': (7.9, -1.0), 'ETH': (9.1, 40.5),
    'TZA': (-6.4, 34.9), 'UGA': (1.4, 32.3), 'MOZ': (-18.7, 35.5), 'NZL': (-40.9, 174.9),
    'IRL': (53.1, -8.2), 'ISR': (31.0, 34.9), 'SGP': (1.4, 103.8), 'HKG': (22.4, 114.1),
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out_pdfs = output_pdfs_dir()
    out_data = output_data_dir()

    taxonomy = read_excel_safe(out_data / "fiscal_regime_taxonomy.xlsx")
    summary = read_excel_safe(out_data / "regime_summary_statistics.xlsx")

    if taxonomy.empty:
        logger.error("Cannot load fiscal_regime_taxonomy.xlsx; aborting.")
        return

    # ── 1. World Map Scatter ──
    fig, ax = plt.subplots(figsize=(16, 9))

    # Plot countries with known coordinates
    plotted = 0
    for regime in REGIME_COLORS:
        subset = taxonomy[
            (taxonomy['fiscal_regime'] == regime) &
            (taxonomy['country_code'].isin(COUNTRY_COORDS))
        ]
        if subset.empty:
            continue
        lats = [COUNTRY_COORDS[cc][0] for cc in subset['country_code']]
        lons = [COUNTRY_COORDS[cc][1] for cc in subset['country_code']]
        ax.scatter(lons, lats, c=REGIME_COLORS[regime], label=regime,
                   s=80, alpha=0.8, edgecolors='black', linewidth=0.5, zorder=5)
        # Label major economies
        for _, row in subset.iterrows():
            cc = row['country_code']
            if cc in COUNTRY_COORDS:
                lat, lon = COUNTRY_COORDS[cc]
                ax.annotate(cc, (lon, lat), fontsize=6, ha='center', va='bottom',
                            xytext=(0, 4), textcoords='offset points')
                plotted += 1

    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 80)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Fiscal Regime Classification of Major Economies', fontsize=16, fontweight='bold')
    ax.legend(loc='lower left', fontsize=8, framealpha=0.9, ncol=2)
    ax.axhline(y=0, color='lightgray', linewidth=0.5, zorder=1)
    ax.axvline(x=0, color='lightgray', linewidth=0.5, zorder=1)

    plt.tight_layout()
    fig.savefig(out_pdfs / "regime_world_map.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Saved regime_world_map.png ({plotted} countries plotted)")

    # ── 2. Regime Profiles: Grouped Bar ──
    if summary.empty:
        logger.warning("No summary statistics; skipping profiles chart.")
        return

    fig, ax = plt.subplots(figsize=(14, 8))

    profile_vars = ['tax_pct_gdp_mean', 'expenditure_pct_gdp_mean', 'debt_pct_gdp_mean']
    profile_labels = ['Tax/GDP (%)', 'Expenditure/GDP (%)', 'Debt/GDP (%)']
    available_vars = [v for v in profile_vars if v in summary.columns]
    available_labels = [profile_labels[profile_vars.index(v)] for v in available_vars]

    if not available_vars:
        logger.warning("No summary variables available for profiles chart.")
        return

    regimes = summary.sort_values('n_countries', ascending=False)['fiscal_regime'].tolist()
    x = np.arange(len(regimes))
    width = 0.25
    n_bars = len(available_vars)

    for i, (var, label) in enumerate(zip(available_vars, available_labels)):
        vals = [summary[summary['fiscal_regime'] == r][var].values[0]
                if r in summary['fiscal_regime'].values and not pd.isna(
                    summary[summary['fiscal_regime'] == r][var].values[0])
                else 0
                for r in regimes]
        offset = (i - n_bars / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, label=label, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(regimes, rotation=35, ha='right', fontsize=9)
    ax.set_ylabel('Percent of GDP')
    ax.set_title('Fiscal Regime Profiles: Tax, Expenditure, and Debt', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)

    # Add country count annotations
    for i, regime in enumerate(regimes):
        n = summary[summary['fiscal_regime'] == regime]['n_countries'].values[0]
        ax.annotate(f'n={int(n)}', (i, 0), fontsize=7, ha='center', va='top',
                    xytext=(0, -5), textcoords='offset points', color='gray')

    plt.tight_layout()
    fig.savefig(out_pdfs / "regime_profiles.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Saved regime_profiles.png")

    logger.info(f"[{MANIFEST['id']}] Complete")


if __name__ == "__main__":
    run()
