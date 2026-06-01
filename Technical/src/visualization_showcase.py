"""
Visualization Showcase
Generates all graph types currently used in Gerhard fiscal reports
For review and approval of unified styles

Part of Gerhard - Global Fiscal Analysis Platform
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

OUTPUT_DIR = Path(__file__).parent.parent.parent / "Output" / "Visualization_Showcase"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_sample_data():
    """Generate sample data for all chart types"""

    # Tax revenue data (time series)
    years = np.arange(1990, 2024)
    tax_revenue = 18 + 5 * np.sin((years - 1990) / 10) + np.random.normal(0, 0.5, len(years))
    tax_data = pd.DataFrame({
        'year': years,
        'tax_revenue_pct_gdp': tax_revenue
    })

    # Expenditure data by sector
    exp_data = pd.DataFrame({
        'year': years,
        'education_gdp': 4.5 + np.random.normal(0, 0.3, len(years)),
        'health_govt_gdp': 5.2 + np.random.normal(0, 0.4, len(years)),
        'military_gdp': 2.1 + np.random.normal(0, 0.2, len(years)),
        'rd_gdp': 1.8 + np.random.normal(0, 0.15, len(years))
    })

    # Regional comparison data
    regional_data = {
        'Country A': 25.3,
        'Country B': 22.8,
        'Country C': 21.5,
        'Sample Country': 20.2,
        'Country D': 19.8,
        'Country E': 18.5,
        'Country F': 17.2,
        'Country G': 16.8,
        'Country H': 15.9,
        'Country I': 14.5
    }

    return tax_data, exp_data, regional_data


def chart_1_tax_revenue_trend(tax_data):
    """Chart Type 1: Line chart with trend line"""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot trend
    ax.plot(tax_data['year'], tax_data['tax_revenue_pct_gdp'],
            linewidth=2.5, color='#2c3e50', marker='o', markersize=4,
            label='Tax Revenue')

    # Add trend line
    z = np.polyfit(tax_data['year'], tax_data['tax_revenue_pct_gdp'], 1)
    p = np.poly1d(z)
    ax.plot(tax_data['year'], p(tax_data['year']),
            "--", color='#e74c3c', linewidth=2, alpha=0.7, label='Trend Line')

    # Formatting
    ax.set_xlabel('Year', fontweight='bold', fontsize=12)
    ax.set_ylabel('Tax Revenue (% of GDP)', fontweight='bold', fontsize=12)
    ax.set_title('Chart Type 1: Tax Revenue Trend Over Time\nLine Chart with Polynomial Trend',
                fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    # Add latest value annotation
    latest_year = tax_data['year'].iloc[-1]
    latest_value = tax_data['tax_revenue_pct_gdp'].iloc[-1]
    ax.annotate(f'{latest_value:.1f}%',
               xy=(latest_year, latest_value),
               xytext=(10, 10), textcoords='offset points',
               fontsize=11, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '01_line_chart_with_trend.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: Chart 1 - Line chart with trend")


def chart_2_expenditure_by_sector(exp_data):
    """Chart Type 2: Bar chart + Pie chart (side by side)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Get latest year data
    latest = exp_data.iloc[-1]
    sectors = {
        'Education': latest['education_gdp'],
        'Health': latest['health_govt_gdp'],
        'Military': latest['military_gdp'],
        'R&D': latest['rd_gdp']
    }

    names = list(sectors.keys())
    values = list(sectors.values())
    colors = plt.cm.Set3(range(len(names)))

    # Bar chart
    ax1.barh(names, values, color=colors)
    ax1.set_xlabel('Expenditure (% of GDP)', fontweight='bold', fontsize=12)
    ax1.set_title('Horizontal Bar Chart',
                 fontsize=14, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for i, v in enumerate(values):
        ax1.text(v + 0.1, i, f'{v:.2f}%', va='center', fontweight='bold')

    # Pie chart
    ax2.pie(values, labels=names, autopct='%1.1f%%', startangle=90, colors=colors)
    ax2.set_title('Pie Chart Distribution',
                 fontsize=14, fontweight='bold', pad=20)

    fig.suptitle('Chart Type 2: Expenditure by Sector (Latest Year)\nBar + Pie Combination',
                fontsize=16, fontweight='bold', y=0.98)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '02_bar_and_pie_chart.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: Chart 2 - Bar + Pie chart")


def chart_3_sectoral_trends(exp_data):
    """Chart Type 3: Multi-line chart for trends"""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot each sector
    sectors = {
        'education_gdp': ('Education', '#3498db'),
        'health_govt_gdp': ('Health', '#2ecc71'),
        'military_gdp': ('Military', '#e74c3c'),
        'rd_gdp': ('R&D', '#9b59b6')
    }

    for col, (label, color) in sectors.items():
        ax.plot(exp_data['year'], exp_data[col],
               linewidth=2.5, marker='o', markersize=4,
               label=label, color=color)

    ax.set_xlabel('Year', fontweight='bold', fontsize=12)
    ax.set_ylabel('Expenditure (% of GDP)', fontweight='bold', fontsize=12)
    ax.set_title('Chart Type 3: Sectoral Expenditure Trends\nMulti-Line Time Series',
                fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=11)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '03_multiline_trends.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: Chart 3 - Multi-line trends")


def chart_4_fiscal_balance(tax_data, exp_data):
    """Chart Type 4: Dual-axis chart with filled areas"""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Calculate total measured expenditure
    exp_data['total_exp'] = (exp_data['education_gdp'] + exp_data['health_govt_gdp'] +
                             exp_data['military_gdp'] + exp_data['rd_gdp'])

    # Merge data
    merged = pd.merge(tax_data, exp_data[['year', 'total_exp']], on='year')

    # Plot
    ax.plot(merged['year'], merged['tax_revenue_pct_gdp'],
           linewidth=2.5, marker='o', markersize=4,
           label='Tax Revenue', color='#27ae60')

    ax.plot(merged['year'], merged['total_exp'],
           linewidth=2.5, marker='s', markersize=4,
           label='Measured Expenditure', color='#e74c3c')

    # Fill areas
    ax.fill_between(merged['year'],
                   merged['tax_revenue_pct_gdp'],
                   merged['total_exp'],
                   where=(merged['tax_revenue_pct_gdp'] >= merged['total_exp']),
                   alpha=0.3, color='green', label='Surplus')
    ax.fill_between(merged['year'],
                   merged['tax_revenue_pct_gdp'],
                   merged['total_exp'],
                   where=(merged['tax_revenue_pct_gdp'] < merged['total_exp']),
                   alpha=0.3, color='red', label='Deficit')

    ax.set_xlabel('Year', fontweight='bold', fontsize=12)
    ax.set_ylabel('% of GDP', fontweight='bold', fontsize=12)
    ax.set_title('Chart Type 4: Fiscal Balance Analysis\nDual-Line with Filled Areas',
                fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=11)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '04_fiscal_balance_filled.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: Chart 4 - Fiscal balance with fills")


def chart_5_regional_comparison(regional_data):
    """Chart Type 5: Horizontal bar chart with highlighting"""
    fig, ax = plt.subplots(figsize=(14, 10))

    # Sort by value
    sorted_countries = sorted(regional_data.items(), key=lambda x: x[1], reverse=True)
    countries = [c[0] for c in sorted_countries]
    values = [c[1] for c in sorted_countries]

    # Highlight sample country
    colors = ['#e74c3c' if c == 'Sample Country' else '#3498db' for c in countries]

    ax.barh(countries, values, color=colors)
    ax.set_xlabel('Tax Revenue (% of GDP)', fontweight='bold', fontsize=12)
    ax.set_title('Chart Type 5: Regional Comparison\nHighlighted Bar Chart',
                fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for i, v in enumerate(values):
        ax.text(v + 0.2, i, f'{v:.1f}%', va='center', fontsize=10)

    # Add rank annotation
    rank = countries.index('Sample Country') + 1
    ax.text(0.02, 0.98, f'Sample Country Rank: #{rank} of {len(countries)}',
           transform=ax.transAxes, fontsize=12, fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5),
           verticalalignment='top')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '05_horizontal_bar_highlighted.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: Chart 5 - Horizontal bar comparison")


def chart_6_stacked_area(exp_data):
    """Chart Type 6: Stacked area chart"""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Prepare data
    sectors_order = ['education_gdp', 'health_govt_gdp', 'military_gdp', 'rd_gdp']
    labels = ['Education', 'Health', 'Military', 'R&D']

    # Stacked area plot
    ax.stackplot(exp_data['year'],
                *[exp_data[col] for col in sectors_order],
                labels=labels,
                alpha=0.7)

    ax.set_xlabel('Year', fontweight='bold', fontsize=12)
    ax.set_ylabel('Expenditure (% of GDP)', fontweight='bold', fontsize=12)
    ax.set_title('Chart Type 6: Expenditure Composition Evolution\nStacked Area Chart',
                fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '06_stacked_area_chart.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: Chart 6 - Stacked area chart")


def chart_7_dashboard(metrics):
    """Chart Type 7: Metrics dashboard grid"""
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)

    # Title
    fig.suptitle('Chart Type 7: Key Fiscal Metrics Dashboard\nGrid Layout with Boxes',
                fontsize=18, fontweight='bold', y=0.98)

    # Define metrics to display
    metric_positions = [
        ('Tax Revenue\n(% GDP)', metrics.get('tax_revenue', 20.5), (0, 0)),
        ('Education\n(% GDP)', metrics.get('education', 4.5), (0, 1)),
        ('Health\n(% GDP)', metrics.get('health', 5.2), (0, 2)),
        ('Military\n(% GDP)', metrics.get('military', 2.1), (1, 0)),
        ('R&D\n(% GDP)', metrics.get('rd', 1.8), (1, 1)),
        ('Data Coverage\n(years)', '1990-2023', (1, 2), True),
        ('Tier', '1', (2, 0), True),
        ('Region', 'Sample Region', (2, 1), True),
        ('Income Level', 'High Income', (2, 2), True)
    ]

    for item in metric_positions:
        if len(item) == 4:
            label, value, pos, is_text = item
        else:
            label, value, pos = item
            is_text = False

        ax = fig.add_subplot(gs[pos[0], pos[1]])
        ax.axis('off')

        # Draw box
        box = plt.Rectangle((0.1, 0.1), 0.8, 0.8, fill=True,
                           facecolor='#ecf0f1', edgecolor='#34495e', linewidth=2)
        ax.add_patch(box)

        # Add label
        ax.text(0.5, 0.7, label, ha='center', va='center',
               fontsize=12, fontweight='bold', transform=ax.transAxes)

        # Add value
        if is_text or value == 'N/A':
            value_str = str(value)
            fontsize = 14 if len(value_str) < 15 else 11
        else:
            value_str = f'{value:.1f}%' if isinstance(value, (int, float)) else str(value)
            fontsize = 18

        ax.text(0.5, 0.3, value_str, ha='center', va='center',
               fontsize=fontsize, fontweight='bold', transform=ax.transAxes,
               color='#2c3e50')

    plt.savefig(OUTPUT_DIR / '07_metrics_dashboard.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: Chart 7 - Metrics dashboard")


def chart_8_scatter_plot():
    """Chart Type 8: Scatter plot with annotations"""
    fig, ax = plt.subplots(figsize=(14, 10))

    # Generate sample data
    np.random.seed(42)
    n_countries = 50
    tax_revenue = np.random.normal(20, 5, n_countries)
    expenditure = tax_revenue + np.random.normal(0, 3, n_countries)
    gdp_size = np.random.uniform(100, 5000, n_countries)

    # Scatter plot
    scatter = ax.scatter(tax_revenue, expenditure, s=gdp_size/10, alpha=0.6,
                        c=gdp_size, cmap='viridis', edgecolors='black', linewidth=0.5)

    # Add 45-degree line
    lims = [
        np.min([ax.get_xlim(), ax.get_ylim()]),
        np.max([ax.get_xlim(), ax.get_ylim()]),
    ]
    ax.plot(lims, lims, 'r--', alpha=0.75, linewidth=2, label='Balanced Budget')

    # Formatting
    ax.set_xlabel('Tax Revenue (% of GDP)', fontweight='bold', fontsize=12)
    ax.set_ylabel('Government Expenditure (% of GDP)', fontweight='bold', fontsize=12)
    ax.set_title('Chart Type 8: Fiscal Balance Scatter Plot\nSize = GDP, Color = GDP Intensity',
                fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('GDP Size', fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '08_scatter_plot.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated: Chart 8 - Scatter plot")


def generate_latex_document():
    """Generate LaTeX document showcasing all visualizations"""

    latex_content = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{float}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{booktabs}

\title{\textbf{Gerhard Fiscal Analysis Platform}\\
\Large Visualization Showcase: Current Graph Styles\\
\large For Review and Approval}
\author{Generated: \today}
\date{}

\begin{document}

\maketitle

\section*{Overview}

This document showcases all 8 chart types currently used in the Gerhard fiscal analysis reports. Each visualization style is presented with its typical use case. Please review and provide feedback on:

\begin{itemize}
    \item Which styles to keep, modify, or remove
    \item Preferred color schemes
    \item Font sizes and readability
    \item Any additional chart types needed
    \item Overall aesthetic preferences
\end{itemize}

\vspace{1cm}

\section{Chart Type 1: Tax Revenue Trend}
\textbf{Use Case:} Showing historical tax revenue trends with polynomial trend line\\
\textbf{Style:} Line chart with markers and overlay trend line\\
\textbf{Colors:} Dark blue primary, red trend line, yellow annotation

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{01_line_chart_with_trend.png}
\caption{Line chart with polynomial trend overlay and value annotation}
\end{figure}

\textbf{Key Features:}
\begin{itemize}
    \item Grid background for easy value reading
    \item Circular markers on data points
    \item Dashed trend line
    \item Latest value highlighted with annotation box
\end{itemize}

\newpage

\section{Chart Type 2: Expenditure by Sector}
\textbf{Use Case:} Comparing sectoral spending for a single year\\
\textbf{Style:} Horizontal bar chart + pie chart combination\\
\textbf{Colors:} Set3 color palette (multi-color)

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{02_bar_and_pie_chart.png}
\caption{Bar and pie chart combination for sectoral breakdown}
\end{figure}

\textbf{Key Features:}
\begin{itemize}
    \item Side-by-side comparison
    \item Value labels on bars
    \item Percentage labels on pie slices
    \item Consistent colors between both charts
\end{itemize}

\newpage

\section{Chart Type 3: Sectoral Trends}
\textbf{Use Case:} Showing evolution of multiple sectors over time\\
\textbf{Style:} Multi-line time series\\
\textbf{Colors:} Distinct color per sector (blue, green, red, purple)

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{03_multiline_trends.png}
\caption{Multi-line chart for sectoral spending evolution}
\end{figure}

\textbf{Key Features:}
\begin{itemize}
    \item Four distinct colors for easy differentiation
    \item Markers on each data point
    \item Legend for sector identification
    \item Grid for value reference
\end{itemize}

\newpage

\section{Chart Type 4: Fiscal Balance}
\textbf{Use Case:} Comparing revenue vs expenditure with surplus/deficit highlighting\\
\textbf{Style:} Dual-line chart with filled areas\\
\textbf{Colors:} Green for revenue, red for expenditure, filled areas for surplus/deficit

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{04_fiscal_balance_filled.png}
\caption{Fiscal balance with filled areas showing surplus and deficit periods}
\end{figure}

\textbf{Key Features:}
\begin{itemize}
    \item Two lines for revenue and expenditure
    \item Green fill for surplus periods
    \item Red fill for deficit periods
    \item Different markers for each line (circle vs square)
\end{itemize}

\newpage

\section{Chart Type 5: Regional Comparison}
\textbf{Use Case:} Benchmarking country against regional peers\\
\textbf{Style:} Horizontal bar chart with highlighting\\
\textbf{Colors:} Blue for peers, red for focal country, yellow annotation

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{05_horizontal_bar_highlighted.png}
\caption{Horizontal bar chart with focal country highlighted}
\end{figure}

\textbf{Key Features:}
\begin{itemize}
    \item Sorted by value (descending)
    \item Focal country in contrasting color
    \item Value labels on each bar
    \item Rank annotation box
    \item Horizontal orientation for easy country name reading
\end{itemize}

\newpage

\section{Chart Type 6: Expenditure Evolution}
\textbf{Use Case:} Showing composition changes over time\\
\textbf{Style:} Stacked area chart\\
\textbf{Colors:} Default matplotlib palette with transparency

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{06_stacked_area_chart.png}
\caption{Stacked area chart showing expenditure composition evolution}
\end{figure}

\textbf{Key Features:}
\begin{itemize}
    \item Cumulative visualization
    \item Transparency (alpha = 0.7) for visual depth
    \item Legend showing sector order from bottom to top
    \item Grid for value reference
\end{itemize}

\newpage

\section{Chart Type 7: Metrics Dashboard}
\textbf{Use Case:} At-a-glance summary of key fiscal indicators\\
\textbf{Style:} Grid layout with bordered boxes\\
\textbf{Colors:} Light gray boxes with dark borders, navy text

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{07_metrics_dashboard.png}
\caption{Dashboard-style grid displaying key metrics}
\end{figure}

\textbf{Key Features:}
\begin{itemize}
    \item 3x3 grid layout
    \item Each metric in bordered box
    \item Large numeric values for quantitative metrics
    \item Text values for categorical information
    \item Consistent formatting across all boxes
\end{itemize}

\newpage

\section{Chart Type 8: Fiscal Balance Scatter}
\textbf{Use Case:} Comparing revenue vs expenditure across many countries\\
\textbf{Style:} Scatter plot with size and color encoding\\
\textbf{Colors:} Viridis colormap, 45-degree reference line

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{08_scatter_plot.png}
\caption{Scatter plot with GDP size and intensity encoding}
\end{figure}

\textbf{Key Features:}
\begin{itemize}
    \item Point size represents GDP
    \item Color intensity represents GDP (viridis scale)
    \item 45-degree line shows balanced budget
    \item Colorbar for scale reference
    \item Black borders on points for definition
\end{itemize}

\newpage

\section*{Feedback Request}

Please review all 8 chart types and provide feedback on:

\subsection*{1. Chart Selection}
\begin{itemize}
    \item Which chart types should be retained?
    \item Which should be removed?
    \item Are there additional chart types needed?
\end{itemize}

\subsection*{2. Visual Style}
\begin{itemize}
    \item Color preferences (current vs alternatives)
    \item Grid style (keep, remove, modify)
    \item Font sizes and weights
    \item Line widths and marker sizes
\end{itemize}

\subsection*{3. Specific Elements}
\begin{itemize}
    \item Annotations and labels (helpful or cluttered?)
    \item Legends (placement, size, style)
    \item Titles and axis labels (formatting preferences)
    \item Overall chart dimensions and aspect ratios
\end{itemize}

\subsection*{4. Brand Consistency}
\begin{itemize}
    \item Preferred color palette for the Gerhard platform
    \item Typography standards
    \item Logo or branding elements to include
    \item Overall aesthetic direction (modern, classic, minimalist, etc.)
\end{itemize}

\vspace{1cm}

\noindent\textbf{Next Steps:}\\
Based on your feedback, we will:
\begin{enumerate}
    \item Update the visualization module with approved styles
    \item Create a unified LaTeX template for all country reports
    \item Regenerate all 185 country reports in LaTeX format with approved visualizations
    \item Compile to PDF for final delivery
\end{enumerate}

\end{document}"""

    latex_file = OUTPUT_DIR / "visualization_showcase.tex"
    with open(latex_file, 'w', encoding='utf-8') as f:
        f.write(latex_content)

    print(f"\nLaTeX document created: {latex_file}")
    return latex_file


def main():
    """Generate all visualizations and LaTeX document"""
    print("="*70)
    print("Generating Visualization Showcase")
    print("="*70)

    # Generate sample data
    print("\nGenerating sample data...")
    tax_data, exp_data, regional_data = generate_sample_data()

    # Generate all charts
    print("\nGenerating visualizations...\n")
    chart_1_tax_revenue_trend(tax_data)
    chart_2_expenditure_by_sector(exp_data)
    chart_3_sectoral_trends(exp_data)
    chart_4_fiscal_balance(tax_data, exp_data)
    chart_5_regional_comparison(regional_data)
    chart_6_stacked_area(exp_data)

    metrics = {
        'tax_revenue': 20.5,
        'education': 4.5,
        'health': 5.2,
        'military': 2.1,
        'rd': 1.8
    }
    chart_7_dashboard(metrics)
    chart_8_scatter_plot()

    # Generate LaTeX document
    print("\nGenerating LaTeX document...")
    latex_file = generate_latex_document()

    print("\n" + "="*70)
    print("SHOWCASE GENERATION COMPLETE")
    print("="*70)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"LaTeX file: {latex_file}")
    print(f"PNG files: 8 visualizations")
    print("\nTo compile PDF:")
    print(f"  cd {OUTPUT_DIR}")
    print(f"  pdflatex visualization_showcase.tex")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
