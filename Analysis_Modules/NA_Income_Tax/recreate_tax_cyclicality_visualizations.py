#!/usr/bin/env python3
"""
Recreate Tax Revenue Cyclicality Visualizations
Based on Nicholas Anderson's paper: "Tax Revenue Cyclicality: The U.S. Example"

This script recreates all figures from the paper using the original data from
NSSR_IncomeTaxData_NA.xlsx
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import seaborn as sns
import os

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Create output directory
output_dir = "tax_cyclicality_figures"
os.makedirs(output_dir, exist_ok=True)

# Read the main data file
excel_file = 'NSSR_IncomeTaxData_NA.xlsx'

print("="*80)
print("RECREATING TAX REVENUE CYCLICALITY VISUALIZATIONS")
print("From: 'Tax Revenue Cyclicality: The U.S. Example' by Nicholas Anderson")
print("="*80)

# ==============================================================================
# FIGURE 1: U.S. Federal Government Revenue from 1927-1941, with Unemployment
# ==============================================================================

def create_figure_1():
    """
    Figure 1: Great Depression Revenue with Unemployment Rate
    Shows dramatic drop in income tax revenue as unemployment soared
    """
    print("\nCreating Figure 1: Revenue 1927-1941 with Unemployment...")

    # Read Great Depression data
    df = pd.read_excel(excel_file, sheet_name='DATA USED FOR PAPER', header=None)

    # Extract data (row 1 has section header, row 2 onwards have data labels and values)
    years = df.iloc[1, 2:17].values
    total_receipts = df.iloc[2, 2:17].values / 1e9  # Convert to billions
    income_tax = df.iloc[3, 2:17].values / 1e9
    not_income_tax = df.iloc[4, 2:17].values / 1e9
    unemployment = df.iloc[5, 2:17].values * 100  # Convert to percentage

    fig, ax1 = plt.subplots(figsize=(16, 9))

    # Plot revenue components as stacked bars
    width = 0.6
    ax1.bar(years, income_tax, width, label='Income Tax', color='#2E86AB', alpha=0.8)
    ax1.bar(years, not_income_tax, width, bottom=income_tax,
            label='Other Revenue', color='#A23B72', alpha=0.8)

    ax1.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Federal Revenue (Billions $)', fontsize=14, fontweight='bold')
    ax1.set_title('U.S. Federal Government Revenue (1927-1941)\nThe Great Depression and Income Tax Collapse',
                  fontsize=16, fontweight='bold', pad=20)
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=11)

    # Create second y-axis for unemployment
    ax2 = ax1.twinx()
    ax2.plot(years, unemployment, color='#F18F01', marker='o', linewidth=3,
             markersize=8, label='Unemployment Rate', linestyle='--')
    ax2.set_ylabel('Unemployment Rate (%)', fontsize=14, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor='#F18F01')
    ax2.legend(loc='upper right', fontsize=11)

    # Add annotations for key events
    ax2.annotate('Stock Market Crash\nOct 1929', xy=(1929, 3.2), xytext=(1929, 15),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=10, ha='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax2.annotate('Peak Unemployment\n24.9%', xy=(1933, 24.9), xytext=(1935, 22),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=10, ha='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax1.annotate('Income Tax Revenue\nFell 60%\n($2.4B -> $0.7B)', xy=(1932, 1.0), xytext=(1929, 3.5),
                arrowprops=dict(arrowstyle='->', color='darkblue', lw=2),
                fontsize=10, ha='center', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_1_revenue_unemployment_1927_1941.png',
                dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: figure_1_revenue_unemployment_1927_1941.png")
    plt.close()


# ==============================================================================
# FIGURE 2: U.S. Federal Government Revenue from 1927-1941, with Nominal GDP
# ==============================================================================

def create_figure_2():
    """
    Figure 2: Great Depression Revenue with Nominal GDP
    Shows revenue moving with GDP - procyclical pattern
    """
    print("\nCreating Figure 2: Revenue 1927-1941 with Nominal GDP...")

    df = pd.read_excel(excel_file, sheet_name='DATA USED FOR PAPER', header=None)

    years = df.iloc[1, 2:17].values
    total_receipts = df.iloc[2, 2:17].values / 1e9
    income_tax = df.iloc[3, 2:17].values / 1e9
    not_income_tax = df.iloc[4, 2:17].values / 1e9
    nominal_gdp = df.iloc[7, 2:17].values / 1e9

    fig, ax1 = plt.subplots(figsize=(16, 9))

    # Plot revenue components
    width = 0.6
    ax1.bar(years, income_tax, width, label='Income Tax', color='#2E86AB', alpha=0.8)
    ax1.bar(years, not_income_tax, width, bottom=income_tax,
            label='Other Revenue', color='#A23B72', alpha=0.8)

    ax1.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Federal Revenue (Billions $)', fontsize=14, fontweight='bold')
    ax1.set_title('U.S. Federal Government Revenue (1927-1941)\nRevenue Tracks GDP - Evidence of Procyclicality',
                  fontsize=16, fontweight='bold', pad=20)
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=11)
    ax1.set_ylim(0, 8)

    # Create second y-axis for GDP
    ax2 = ax1.twinx()
    ax2.plot(years, nominal_gdp, color='#06A77D', marker='s', linewidth=3,
             markersize=8, label='Nominal GDP', linestyle='-')
    ax2.set_ylabel('Nominal GDP (Billions $)', fontsize=14, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor='#06A77D')
    ax2.legend(loc='upper right', fontsize=11)
    ax2.set_ylim(0, 140)

    # Add annotations
    ax2.annotate('GDP Collapse\n$105B -> $57B (46%)', xy=(1932, 60), xytext=(1930, 90),
                arrowprops=dict(arrowstyle='->', color='darkgreen', lw=2),
                fontsize=10, ha='center', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    ax1.annotate('Revenue follows\nGDP down', xy=(1933, 2), xytext=(1931, 5),
                arrowprops=dict(arrowstyle='->', color='darkblue', lw=2),
                fontsize=10, ha='center', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_2_revenue_gdp_1927_1941.png',
                dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: figure_2_revenue_gdp_1927_1941.png")
    plt.close()


# ==============================================================================
# FIGURE 3: Federal Revenue by Type as % of Total (1820-2020)
# Four Eras of Taxation
# ==============================================================================

def create_figure_3():
    """
    Figure 3: Historical Tax Composition showing Four Eras
    - Customs Duties Era (1790-1862)
    - Excise Tax Era (1862-1913)
    - Income Tax Era (1913-1945)
    - Decline of Income Tax / Rise of Payroll Era (1945-Present)
    """
    print("\nCreating Figure 3: Four Eras of US Taxation (1820-2020)...")

    df = pd.read_excel(excel_file, sheet_name='DATA USED FOR PAPER', header=None)

    # Extract Hungerford data (row 50 onwards)
    # Row 50 has "Hungerford" header, actual data starts at row 51
    years_row = 50

    # Find where the year data starts (should be in columns after first blank columns)
    # The years should be in the row labeled "Hungerford"
    year_start_col = 2

    # Get years - they should be in row index around where we see "Hungerford"
    # Let's extract from row 58 which has "Hungerford as % of Total"
    pct_start_row = 58

    # Read the data more carefully
    # Years are in the columns, starting from column 2
    years = df.iloc[years_row, year_start_col:year_start_col+186].values

    # Revenue types as % of total (starting at row 58)
    customs_pct = df.iloc[59, year_start_col:year_start_col+186].values
    income_pct = df.iloc[60, year_start_col:year_start_col+186].values
    social_ins_pct = df.iloc[61, year_start_col:year_start_col+186].values
    excise_pct = df.iloc[62, year_start_col:year_start_col+186].values
    public_lands_pct = df.iloc[63, year_start_col:year_start_col+186].values

    # Clean data - remove NaN values
    valid_idx = pd.notna(years) & pd.notna(customs_pct)
    years_clean = years[valid_idx].astype(int)
    customs_clean = pd.to_numeric(customs_pct[valid_idx], errors='coerce')
    income_clean = pd.to_numeric(income_pct[valid_idx], errors='coerce')
    social_ins_clean = pd.to_numeric(social_ins_pct[valid_idx], errors='coerce')
    excise_clean = pd.to_numeric(excise_pct[valid_idx], errors='coerce')
    public_lands_clean = pd.to_numeric(public_lands_pct[valid_idx], errors='coerce')

    # Replace NaN with 0
    customs_clean = np.nan_to_num(customs_clean, 0)
    income_clean = np.nan_to_num(income_clean, 0)
    social_ins_clean = np.nan_to_num(social_ins_clean, 0)
    excise_clean = np.nan_to_num(excise_clean, 0)
    public_lands_clean = np.nan_to_num(public_lands_clean, 0)

    # Create stacked area chart
    fig, ax = plt.subplots(figsize=(20, 10))

    ax.fill_between(years_clean, 0, customs_clean,
                     label='Customs Duties', color='#1f77b4', alpha=0.8)
    ax.fill_between(years_clean, customs_clean,
                     customs_clean + income_clean,
                     label='Income Tax', color='#ff7f0e', alpha=0.8)
    ax.fill_between(years_clean, customs_clean + income_clean,
                     customs_clean + income_clean + social_ins_clean,
                     label='Social Insurance & Retirement', color='#2ca02c', alpha=0.8)
    ax.fill_between(years_clean, customs_clean + income_clean + social_ins_clean,
                     customs_clean + income_clean + social_ins_clean + excise_clean,
                     label='Excise Tax', color='#d62728', alpha=0.8)
    ax.fill_between(years_clean,
                     customs_clean + income_clean + social_ins_clean + excise_clean,
                     customs_clean + income_clean + social_ins_clean + excise_clean + public_lands_clean,
                     label='Sale of Public Lands', color='#9467bd', alpha=0.8)

    # Add era labels
    ax.axvspan(1820, 1862, alpha=0.1, color='gray', label='_nolegend_')
    ax.text(1841, 95, 'Customs Duties Era\n(1790-1862)', ha='center',
            fontsize=12, fontweight='bold', bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    ax.axvspan(1862, 1913, alpha=0.1, color='lightblue', label='_nolegend_')
    ax.text(1887, 95, 'Excise Tax Era\n(1862-1913)', ha='center',
            fontsize=12, fontweight='bold', bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    ax.axvspan(1913, 1945, alpha=0.1, color='lightyellow', label='_nolegend_')
    ax.text(1929, 95, 'Income Tax Era\n(1913-1945)', ha='center',
            fontsize=12, fontweight='bold', bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    ax.axvspan(1945, 2020, alpha=0.1, color='lightgreen', label='_nolegend_')
    ax.text(1982, 95, 'Decline of Income Tax Era\nRise of Payroll Taxes (1945-Present)', ha='center',
            fontsize=12, fontweight='bold', bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('Percentage of Total Federal Revenue (%)', fontsize=14, fontweight='bold')
    ax.set_title('Four Eras of U.S. Federal Taxation (1820-2020)\nFederal Government Revenue Composition',
                 fontsize=18, fontweight='bold', pad=20)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='center left', fontsize=11)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_3_four_eras_taxation_1820_2020.png',
                dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: figure_3_four_eras_taxation_1820_2020.png")
    plt.close()


# ==============================================================================
# FIGURE 4: Correlation by decade - Total Receipts vs GDP (1800-2020)
# ==============================================================================

def create_figure_4():
    """
    Figure 4: 10-Year Rolling Correlation of Total Receipts and Nominal GDP
    Shows persistent positive correlation = procyclical revenue
    """
    print("\nCreating Figure 4: Correlation of Total Receipts vs GDP by Decade...")

    df = pd.read_excel(excel_file, sheet_name='DATA USED FOR PAPER', header=None)

    # Find correlation data - row 103 has "Correlation" header
    # Row 104 has "NGDP and Total Receipts" label
    corr_start_col = 2

    # Extract years and correlation values
    years = df.iloc[103, corr_start_col:corr_start_col+23].values
    correlations = df.iloc[104, corr_start_col:corr_start_col+23].values

    # Clean data
    valid_idx = pd.notna(years) & pd.notna(correlations)
    years_clean = years[valid_idx]
    corr_clean = pd.to_numeric(correlations[valid_idx], errors='coerce')

    fig, ax = plt.subplots(figsize=(16, 9))

    # Create bar chart with color coding
    colors = ['#d62728' if c < 0 else '#2ca02c' for c in corr_clean]
    bars = ax.bar(range(len(years_clean)), corr_clean, color=colors, alpha=0.8, edgecolor='black')

    ax.set_xticks(range(len(years_clean)))
    ax.set_xticklabels([f"{int(y)}-{int(y)+10}" if pd.notna(y) else '' for y in years_clean],
                       rotation=45, ha='right')
    ax.set_xlabel('Decade', fontsize=14, fontweight='bold')
    ax.set_ylabel('Correlation Coefficient', fontsize=14, fontweight='bold')
    ax.set_title('10-Year Correlation: Total Federal Receipts vs Nominal GDP (1800-2020)\nEvidence of Procyclical Tax Revenue',
                 fontsize=16, fontweight='bold', pad=20)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(-1, 1)

    # Add legend
    green_patch = mpatches.Patch(color='#2ca02c', label='Positive Correlation (Procyclical)', alpha=0.8)
    red_patch = mpatches.Patch(color='#d62728', label='Negative Correlation (Countercyclical)', alpha=0.8)
    ax.legend(handles=[green_patch, red_patch], fontsize=11, loc='lower right')

    # Add annotation
    ax.text(0.02, 0.98, 'After 1820, Total Receipts remain\npositively correlated with GDP\n-> Procyclical Revenue',
            transform=ax.transAxes, fontsize=12, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_4_correlation_receipts_gdp_by_decade.png',
                dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: figure_4_correlation_receipts_gdp_by_decade.png")
    plt.close()


# ==============================================================================
# FIGURE 5: Correlation by decade - Total Receipts vs Unemployment (1900-2020)
# ==============================================================================

def create_figure_5():
    """
    Figure 5: 10-Year Rolling Correlation of Total Receipts and Unemployment Rate
    Negative correlation confirms procyclical pattern (revenue falls when unemployment rises)
    """
    print("\nCreating Figure 5: Correlation of Total Receipts vs Unemployment by Decade...")

    df = pd.read_excel(excel_file, sheet_name='DATA USED FOR PAPER', header=None)

    # Row 173 has "Correlation" header for unemployment data
    # Row 174 has "Avg Unempl and Total Receipts"
    corr_start_col = 2

    years = df.iloc[173, corr_start_col:corr_start_col+12].values
    correlations = df.iloc[174, corr_start_col:corr_start_col+12].values

    # Clean data
    valid_idx = pd.notna(years) & pd.notna(correlations)
    years_clean = years[valid_idx]
    corr_clean = pd.to_numeric(correlations[valid_idx], errors='coerce')

    fig, ax = plt.subplots(figsize=(14, 9))

    # Create bar chart - negative correlation is procyclical for unemployment
    colors = ['#2ca02c' if c < 0 else '#d62728' for c in corr_clean]
    bars = ax.bar(range(len(years_clean)), corr_clean, color=colors, alpha=0.8, edgecolor='black')

    ax.set_xticks(range(len(years_clean)))
    ax.set_xticklabels([f"{int(y)}-{int(y)+10}" if pd.notna(y) else '' for y in years_clean],
                       rotation=45, ha='right')
    ax.set_xlabel('Decade', fontsize=14, fontweight='bold')
    ax.set_ylabel('Correlation Coefficient', fontsize=14, fontweight='bold')
    ax.set_title('10-Year Correlation: Total Federal Receipts vs Unemployment Rate (1900-2020)\nNegative Correlation Confirms Procyclical Pattern',
                 fontsize=16, fontweight='bold', pad=20)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(-1, 1)

    # Add legend
    green_patch = mpatches.Patch(color='#2ca02c', label='Negative Correlation\n(Revenue ↓ when Unemployment ↑) = Procyclical', alpha=0.8)
    red_patch = mpatches.Patch(color='#d62728', label='Positive Correlation\n(Revenue ↑ when Unemployment ↑) = Countercyclical', alpha=0.8)
    ax.legend(handles=[green_patch, red_patch], fontsize=11, loc='upper right')

    # Add annotation
    ax.text(0.02, 0.02, 'Negative correlation throughout sample period\n-> Revenue falls when unemployment rises\n-> Procyclical Tax Revenue',
            transform=ax.transAxes, fontsize=12, verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_5_correlation_receipts_unemployment_by_decade.png',
                dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: figure_5_correlation_receipts_unemployment_by_decade.png")
    plt.close()


# ==============================================================================
# FIGURE 6: Income Tax Correlation vs GDP & Unemployment (1930-2020)
# ==============================================================================

def create_figure_6():
    """
    Figure 6: Income Tax specifically is strongly procyclical
    Positive correlation with GDP, negative with unemployment
    """
    print("\nCreating Figure 6: Income Tax Correlation vs GDP & Unemployment...")

    df = pd.read_excel(excel_file, sheet_name='DATA USED FOR PAPER', header=None)

    # Income tax correlation data
    # Row 204 has "Correlation" header
    # Row 205 has "Income Tax vs NGDP"
    # Row 206 has "(-) Income Tax vs Unempl Rate" (negative of correlation, for display)
    corr_start_col = 2

    years = df.iloc[204, corr_start_col:corr_start_col+10].values
    corr_gdp = df.iloc[205, corr_start_col:corr_start_col+10].values
    corr_unempl_neg = df.iloc[206, corr_start_col:corr_start_col+10].values  # This is negative of actual

    # Clean data
    valid_idx = pd.notna(years) & pd.notna(corr_gdp)
    years_clean = years[valid_idx]
    corr_gdp_clean = pd.to_numeric(corr_gdp[valid_idx], errors='coerce')
    corr_unempl_clean = pd.to_numeric(corr_unempl_neg[valid_idx], errors='coerce')

    fig, ax = plt.subplots(figsize=(14, 9))

    x = np.arange(len(years_clean))
    width = 0.35

    bars1 = ax.bar(x - width/2, corr_gdp_clean, width, label='Income Tax vs GDP',
                   color='#1f77b4', alpha=0.8, edgecolor='black')
    bars2 = ax.bar(x + width/2, corr_unempl_clean, width,
                   label='(-) Income Tax vs Unemployment Rate',
                   color='#ff7f0e', alpha=0.8, edgecolor='black')

    ax.set_xticks(x)
    ax.set_xticklabels([f"{int(y)}-{int(y)+10}" if pd.notna(y) else '' for y in years_clean],
                       rotation=45, ha='right')
    ax.set_xlabel('Decade', fontsize=14, fontweight='bold')
    ax.set_ylabel('Correlation Coefficient', fontsize=14, fontweight='bold')
    ax.set_title('10-Year Correlation: Income Tax vs GDP & Unemployment (1930-2020)\nIncome Tax Is Strongly Procyclical',
                 fontsize=16, fontweight='bold', pad=20)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(fontsize=11, loc='lower right')
    ax.set_ylim(-1, 1)

    # Add annotation
    ax.text(0.02, 0.98, 'Income Tax shows consistent procyclical pattern:\n' +
                        '[OK] Positive correlation with GDP\n' +
                        '[OK] Negative correlation with Unemployment\n' +
                        '-> Tax revenue moves WITH the economy',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_6_income_tax_correlation_gdp_unemployment.png',
                dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: figure_6_income_tax_correlation_gdp_unemployment.png")
    plt.close()


# ==============================================================================
# FIGURE 7: Social Insurance Tax Correlation vs GDP & Unemployment (1950-2020)
# ==============================================================================

def create_figure_7():
    """
    Figure 7: Social Insurance/Payroll Taxes - initially cyclical, now acyclical
    Lost procyclical pattern after 1960s-70s
    """
    print("\nCreating Figure 7: Social Insurance Tax Correlation vs GDP & Unemployment...")

    df = pd.read_excel(excel_file, sheet_name='DATA USED FOR PAPER', header=None)

    # Social insurance correlation data
    # Row 238 has "Correlation" header
    # Row 239 has "Social Ins. vs NGDP"
    # Row 240 has "(-) Social Ins. vs Unempl Rate"
    corr_start_col = 2

    years = df.iloc[238, corr_start_col:corr_start_col+8].values
    corr_gdp = df.iloc[239, corr_start_col:corr_start_col+8].values
    corr_unempl_neg = df.iloc[240, corr_start_col:corr_start_col+8].values

    # Clean data
    valid_idx = pd.notna(years) & pd.notna(corr_gdp)
    years_clean = years[valid_idx]
    corr_gdp_clean = pd.to_numeric(corr_gdp[valid_idx], errors='coerce')
    corr_unempl_clean = pd.to_numeric(corr_unempl_neg[valid_idx], errors='coerce')

    fig, ax = plt.subplots(figsize=(14, 9))

    x = np.arange(len(years_clean))
    width = 0.35

    bars1 = ax.bar(x - width/2, corr_gdp_clean, width,
                   label='Social Insurance Tax vs GDP',
                   color='#2ca02c', alpha=0.8, edgecolor='black')
    bars2 = ax.bar(x + width/2, corr_unempl_clean, width,
                   label='(-) Social Insurance Tax vs Unemployment',
                   color='#d62728', alpha=0.8, edgecolor='black')

    ax.set_xticks(x)
    ax.set_xticklabels([f"{int(y)}-{int(y)+10}" if pd.notna(y) else '' for y in years_clean],
                       rotation=45, ha='right')
    ax.set_xlabel('Decade', fontsize=14, fontweight='bold')
    ax.set_ylabel('Correlation Coefficient', fontsize=14, fontweight='bold')
    ax.set_title('10-Year Correlation: Social Insurance/Payroll Tax vs GDP & Unemployment (1950-2020)\nFrom Procyclical to Acyclical',
                 fontsize=16, fontweight='bold', pad=20)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(fontsize=11, loc='upper right')
    ax.set_ylim(-1, 1)

    # Add annotation
    ax.text(0.02, 0.98, 'Payroll Taxes initially cyclical (1950s)\n' +
                        'Correlation disappeared in 1960s-70s\n' +
                        '-> Now neither procyclical nor countercyclical',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_7_social_insurance_correlation_gdp_unemployment.png',
                dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: figure_7_social_insurance_correlation_gdp_unemployment.png")
    plt.close()


# ==============================================================================
# FIGURE 8: Customs Duties Correlation vs GDP (1810-1940)
# ==============================================================================

def create_figure_8():
    """
    Figure 8: Customs Duties also showed procyclical tendencies
    Especially clear after 1880
    """
    print("\nCreating Figure 8: Customs Duties Correlation vs GDP...")

    df = pd.read_excel(excel_file, sheet_name='DATA USED FOR PAPER', header=None)

    # Customs duties correlation data
    # Row 126 has "Correlation" header
    # Row 127 has "NGDP and Customs Duties"
    corr_start_col = 2

    years = df.iloc[126, corr_start_col:corr_start_col+14].values
    correlations = df.iloc[127, corr_start_col:corr_start_col+14].values

    # Clean data
    valid_idx = pd.notna(years) & pd.notna(correlations)
    years_clean = years[valid_idx]
    corr_clean = pd.to_numeric(correlations[valid_idx], errors='coerce')

    fig, ax = plt.subplots(figsize=(14, 9))

    # Create bar chart with color coding
    colors = ['#d62728' if c < 0 else '#2ca02c' for c in corr_clean]
    bars = ax.bar(range(len(years_clean)), corr_clean, color=colors, alpha=0.8, edgecolor='black')

    ax.set_xticks(range(len(years_clean)))
    ax.set_xticklabels([f"{int(y)}-{int(y)+10}" if pd.notna(y) else '' for y in years_clean],
                       rotation=45, ha='right')
    ax.set_xlabel('Decade', fontsize=14, fontweight='bold')
    ax.set_ylabel('Correlation Coefficient', fontsize=14, fontweight='bold')
    ax.set_title('10-Year Correlation: Customs Duties vs Nominal GDP (1810-1940)\nCustoms Duties Also Procyclical, Especially After 1880',
                 fontsize=16, fontweight='bold', pad=20)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(-1, 1)

    # Add legend
    green_patch = mpatches.Patch(color='#2ca02c', label='Positive Correlation (Procyclical)', alpha=0.8)
    red_patch = mpatches.Patch(color='#d62728', label='Negative Correlation (Countercyclical)', alpha=0.8)
    ax.legend(handles=[green_patch, red_patch], fontsize=11, loc='upper right')

    # Add annotation
    ax.text(0.02, 0.02, 'Mixed pattern before 1860\n' +
                        'Consistently positive correlation after 1880\n' +
                        '-> Procyclical, though weaker than Income Tax',
            transform=ax.transAxes, fontsize=11, verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f'{output_dir}/figure_8_customs_duties_correlation_gdp.png',
                dpi=300, bbox_inches='tight')
    print(f"  [OK] Saved: figure_8_customs_duties_correlation_gdp.png")
    plt.close()


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    print("\nGenerating all figures from Tax Revenue Cyclicality paper...\n")

    try:
        create_figure_1()  # Great Depression with Unemployment
        create_figure_2()  # Great Depression with GDP
        create_figure_3()  # Four Eras of Taxation
        create_figure_4()  # Total Receipts vs GDP correlation by decade
        create_figure_5()  # Total Receipts vs Unemployment correlation by decade
        create_figure_6()  # Income Tax correlations
        create_figure_7()  # Social Insurance correlations
        create_figure_8()  # Customs Duties correlations

        print("\n" + "="*80)
        print("ALL FIGURES GENERATED SUCCESSFULLY!")
        print("="*80)
        print(f"\nOutput directory: {os.path.abspath(output_dir)}")
        print("\nFigures created:")
        print("  1. figure_1_revenue_unemployment_1927_1941.png")
        print("  2. figure_2_revenue_gdp_1927_1941.png")
        print("  3. figure_3_four_eras_taxation_1820_2020.png")
        print("  4. figure_4_correlation_receipts_gdp_by_decade.png")
        print("  5. figure_5_correlation_receipts_unemployment_by_decade.png")
        print("  6. figure_6_income_tax_correlation_gdp_unemployment.png")
        print("  7. figure_7_social_insurance_correlation_gdp_unemployment.png")
        print("  8. figure_8_customs_duties_correlation_gdp.png")

    except Exception as e:
        print(f"\n[ERROR] Error generating figures: {e}")
        import traceback
        traceback.print_exc()
