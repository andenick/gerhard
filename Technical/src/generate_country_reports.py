"""
Country Report Generator
Generates LaTeX PDF reports for individual countries
Project: Gerhard - Country by Country Expansion
"""

import pandas as pd
import json
import subprocess
from pathlib import Path
import sys
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import countries_dir

logger = setup_logging(__name__)

COUNTRIES_DIR = countries_dir()


class CountryReportGenerator:
    """Generates LaTeX reports for individual countries"""

    def __init__(self, country_code, country_name, tier):
        self.country_code = country_code
        self.country_name = country_name
        self.tier = tier
        self.country_dir = COUNTRIES_DIR / country_code
        self.data = None
        self.analysis = None
        self.config = None

    def load_data(self):
        """Load all necessary data"""
        # Load country data
        data_file = self.country_dir / "Output" / "Data" / f"{self.country_code.lower()}_national_tax_data.xlsx"
        if data_file.exists():
            self.data = pd.read_excel(data_file)

        # Load analysis results
        analysis_file = self.country_dir / "Technical" / "data" / "analysis_results.json"
        if analysis_file.exists():
            with open(analysis_file, 'r') as f:
                self.analysis = json.load(f)

        # Load config
        config_file = self.country_dir / "Technical" / "data" / "config.json"
        with open(config_file, 'r') as f:
            self.config = json.load(f)

        return self.data is not None

    def generate_latex_tier1(self):
        """Generate comprehensive LaTeX report for Tier 1 countries"""
        stats = self.analysis.get('summary_statistics', {})
        trends = self.analysis.get('trends', {})
        comp = self.analysis.get('global_comparison', {})

        latex_content = rf"""
\documentclass[11pt,a4paper]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{hyperref}}
\usepackage{{float}}
\usepackage{{caption}}

\title{{\textbf{{{self.country_name}\\Tax System Analysis}}}}
\author{{Gerhard Project}}
\date{{\today}}

\begin{{document}}

\maketitle

\section*{{Executive Summary}}

This report provides a comprehensive analysis of the tax system in \textbf{{{self.country_name}}} based on {stats.get('total_years', 0)} years of data from {stats.get('first_year', 'N/A')} to {stats.get('last_year', 'N/A')}.

\subsection*{{Key Findings}}

\begin{{itemize}}
    \item \textbf{{Average Tax Revenue:}} {stats.get('mean', 0):.2f}\% of GDP
    \item \textbf{{Latest Tax Revenue ({comp.get('comparison_year', 'N/A')}):}} {comp.get('country_value', 0):.2f}\% of GDP
    \item \textbf{{Trend:}} {trends.get('trend_direction', 'N/A')} ({trends.get('percent_change', 0):.1f}\% change overall)
    \item \textbf{{Global Position:}} {comp.get('relative_position', 'N/A')} (difference: {comp.get('difference', 0):.2f} percentage points)
\end{{itemize}}

\section{{Tax Revenue Overview}}

\subsection{{Historical Time Series}}

Figure 1 shows the complete time series of tax revenue as a percentage of GDP for {self.country_name} from {stats.get('first_year', 'N/A')} to {stats.get('last_year', 'N/A')}.

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{{../PDFs/{self.country_code.lower()}_01_time_series.png}}
    \caption{{Tax Revenue as Percentage of GDP: {self.country_name}, {stats.get('first_year', 'N/A')}-{stats.get('last_year', 'N/A')}}}
\end{{figure}}

The data shows a {trends.get('trend_direction', 'stable').lower()} trend over the time period, with tax revenue {'increasing' if trends.get('slope', 0) > 0 else 'decreasing'} at an average rate of {abs(trends.get('slope', 0)):.3f} percentage points per year.

\subsection{{Summary Statistics}}

Table 1 presents key summary statistics for tax revenue in {self.country_name}.

\begin{{table}}[H]
    \centering
    \caption{{Tax Revenue Statistics: {self.country_name}}}
    \begin{{tabular}}{{ll}}
        \toprule
        \textbf{{Metric}} & \textbf{{Value}} \\
        \midrule
        Mean & {stats.get('mean', 0):.2f}\% \\
        Median & {stats.get('median', 0):.2f}\% \\
        Standard Deviation & {stats.get('std', 0):.2f}\% \\
        Minimum & {stats.get('min', 0):.2f}\% \\
        Maximum & {stats.get('max', 0):.2f}\% \\
        Range & {stats.get('max', 0) - stats.get('min', 0):.2f}\% \\
        \bottomrule
    \end{{tabular}}
\end{{table}}

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{{../PDFs/{self.country_code.lower()}_03_statistics.png}}
    \caption{{Statistical Summary: {self.country_name}}}
\end{{figure}}

\section{{Trends and Analysis}}

\subsection{{Long-term Trends}}

Over the {stats.get('total_years', 0)}-year period analyzed, tax revenue in {self.country_name} has shown a {trends.get('trend_direction', 'stable').lower()} trend. The total change from {stats.get('first_year', 'N/A')} to {stats.get('last_year', 'N/A')} was {trends.get('total_change', 0):.2f} percentage points, representing a {trends.get('percent_change', 0):.1f}\% change.

\subsection{{Decade Analysis}}

Figure 3 shows the evolution of tax revenue across different decades, providing insight into how taxation has changed over time.

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{{../PDFs/{self.country_code.lower()}_02_decade_comparison.png}}
    \caption{{Average Tax Revenue by Decade: {self.country_name}}}
\end{{figure}}

\subsection{{Year-over-Year Changes}}

Figure 4 illustrates the year-over-year changes in tax revenue, highlighting periods of significant policy shifts or economic changes.

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{{../PDFs/{self.country_code.lower()}_04_yoy_change.png}}
    \caption{{Year-over-Year Changes: {self.country_name}}}
\end{{figure}}

\section{{International Comparison}}

Compared to the world average, {self.country_name} has {'higher' if comp.get('difference', 0) > 0 else 'lower'} tax revenue relative to GDP. In {comp.get('comparison_year', 'N/A')}, {self.country_name}'s tax revenue was {comp.get('country_value', 0):.2f}\% of GDP, compared to the world average of {comp.get('world_value', 0):.2f}\%, a difference of {abs(comp.get('difference', 0)):.2f} percentage points.

This places {self.country_name} {comp.get('relative_position', '').lower()} in terms of tax revenue collection relative to economic output.

\section{{Data Sources and Methodology}}

\subsection{{Data Sources}}

The data used in this analysis comes from the World Bank World Development Indicators database, specifically the indicator GC.TAX.TOTL.GD.ZS (Tax revenue as \% of GDP). This indicator includes all compulsory transfers to the central government for public purposes.

\subsection{{Coverage}}

\begin{{itemize}}
    \item \textbf{{Time Period:}} {stats.get('first_year', 'N/A')}-{stats.get('last_year', 'N/A')}
    \item \textbf{{Data Points:}} {stats.get('data_points', 0)} years
    \item \textbf{{Data Quality Tier:}} {self.tier} (Comprehensive)
\end{{itemize}}

\subsection{{Limitations}}

\begin{{itemize}}
    \item Data represents central government tax revenue only; subnational taxes may not be fully captured
    \item Tax revenue definition may vary slightly across countries and over time
    \item Some years may have missing or estimated data
    \item Does not include non-tax revenue or social security contributions in all cases
\end{{itemize}}

\section{{Conclusions}}

{self.country_name} has demonstrated a {trends.get('trend_direction', 'stable').lower()} trend in tax revenue over the past {stats.get('total_years', 0)} years. With an average tax revenue of {stats.get('mean', 0):.2f}\% of GDP, the country is positioned {comp.get('relative_position', '').lower()} relative to the global average.

The {'increase' if trends.get('slope', 0) > 0 else 'decrease'} in tax revenue of {abs(trends.get('percent_change', 0)):.1f}\% over this period reflects {'expanding' if trends.get('slope', 0) > 0 else 'contracting'} fiscal capacity relative to economic output.

\vspace{{1cm}}

\noindent\rule{{\textwidth}}{{0.4pt}}

\begin{{center}}
\small
\textit{{Report generated by Claude Code for the Gerhard Project}}\\
\textit{{Data source: World Bank World Development Indicators}}\\
\textit{{\today}}
\end{{center}}

\end{{document}}
"""
        return latex_content

    def generate_latex_tier2(self):
        """Generate standard LaTeX report for Tier 2 countries"""
        stats = self.analysis.get('summary_statistics', {})
        trends = self.analysis.get('trends', {})
        comp = self.analysis.get('global_comparison', {})

        latex_content = rf"""
\documentclass[11pt,a4paper]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{hyperref}}
\usepackage{{float}}

\title{{\textbf{{{self.country_name}\\Tax Revenue Analysis}}}}
\author{{Gerhard Project}}
\date{{\today}}

\begin{{document}}

\maketitle

\section*{{Executive Summary}}

Analysis of tax revenue in \textbf{{{self.country_name}}} based on {stats.get('total_years', 0)} years of data ({stats.get('first_year', 'N/A')}-{stats.get('last_year', 'N/A')}).

\textbf{{Key Statistics:}}
\begin{{itemize}}
    \item Average: {stats.get('mean', 0):.2f}\% of GDP
    \item Latest ({comp.get('comparison_year', 'N/A')}): {comp.get('country_value', 0):.2f}\% of GDP
    \item Trend: {trends.get('trend_direction', 'N/A')}
    \item vs World: {comp.get('relative_position', 'N/A')}
\end{{itemize}}

\section{{Tax Revenue Overview}}

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{{../PDFs/{self.country_code.lower()}_01_time_series.png}}
    \caption{{Tax Revenue as \% of GDP: {self.country_name}}}
\end{{figure}}

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{{../PDFs/{self.country_code.lower()}_02_decade_comparison.png}}
    \caption{{Decade Comparison: {self.country_name}}}
\end{{figure}}

\section{{Summary Statistics}}

\begin{{table}}[H]
    \centering
    \begin{{tabular}}{{ll}}
        \toprule
        \textbf{{Metric}} & \textbf{{Value}} \\
        \midrule
        Mean & {stats.get('mean', 0):.2f}\% \\
        Median & {stats.get('median', 0):.2f}\% \\
        Min/Max & {stats.get('min', 0):.2f}\% / {stats.get('max', 0):.2f}\% \\
        \bottomrule
    \end{{tabular}}
\end{{table}}

\section{{International Comparison}}

{self.country_name} is {comp.get('relative_position', '').lower()} with {comp.get('country_value', 0):.2f}\% compared to world average of {comp.get('world_value', 0):.2f}\%.

\section{{Data Source}}

World Bank World Development Indicators (GC.TAX.TOTL.GD.ZS).

\vspace{{1cm}}
\noindent\rule{{\textwidth}}{{0.4pt}}
\begin{{center}}
\small\textit{{Gerhard Project - \today}}
\end{{center}}

\end{{document}}
"""
        return latex_content

    def generate_latex_tier3(self):
        """Generate basic LaTeX report for Tier 3 countries"""
        stats = self.analysis.get('summary_statistics', {})
        comp = self.analysis.get('global_comparison', {})

        latex_content = rf"""
\documentclass[11pt,a4paper]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{float}}

\title{{\textbf{{{self.country_name}}}}}
\author{{Gerhard Project}}
\date{{\today}}

\begin{{document}}

\maketitle

\section*{{Tax Revenue Summary}}

\textbf{{Coverage:}} {stats.get('first_year', 'N/A')}-{stats.get('last_year', 'N/A')} ({stats.get('total_years', 0)} years)

\textbf{{Average Tax Revenue:}} {stats.get('mean', 0):.2f}\% of GDP

\begin{{figure}}[H]
    \centering
    \includegraphics[width=0.9\textwidth]{{../PDFs/{self.country_code.lower()}_01_time_series.png}}
\end{{figure}}

\begin{{table}}[H]
    \centering
    \begin{{tabular}}{{ll}}
        \toprule
        Mean & {stats.get('mean', 0):.2f}\% \\
        Min/Max & {stats.get('min', 0):.2f}\% / {stats.get('max', 0):.2f}\% \\
        \bottomrule
    \end{{tabular}}
\end{{table}}

\textit{{Data: World Bank WDI}}

\end{{document}}
"""
        return latex_content

    def compile_latex(self, latex_content):
        """Compile LaTeX to PDF"""
        # Save LaTeX source
        docs_dir = self.country_dir / "Technical" / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        tex_file = docs_dir / f"{self.country_code.lower()}_report.tex"
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        # Compile with pdflatex
        try:
            # Run pdflatex twice for references
            for _ in range(2):
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', f'{self.country_code.lower()}_report.tex'],
                    cwd=docs_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

            # Move PDF to Output/PDFs
            pdf_source = docs_dir / f"{self.country_code.lower()}_report.pdf"
            pdf_dest = self.country_dir / "Output" / "PDFs" / f"{self.country_code}_Tax_Analysis_Report.pdf"

            if pdf_source.exists():
                shutil.copy(pdf_source, pdf_dest)
                logger.info(f"  Generated PDF report")

                # Clean up auxiliary files
                for ext in ['.aux', '.log', '.out']:
                    aux_file = docs_dir / f"{self.country_code.lower()}_report{ext}"
                    if aux_file.exists():
                        aux_file.unlink()

                return True
            else:
                logger.warning(f"  PDF compilation failed")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"  LaTeX compilation timeout")
            return False
        except FileNotFoundError:
            logger.error(f"  pdflatex not found - PDF not generated")
            return False
        except Exception as e:
            logger.error(f"  Error compiling PDF: {e}")
            return False

    def generate_report(self):
        """Generate complete report for country"""
        logger.info(f"Generating report for {self.country_name} ({self.country_code}) - Tier {self.tier}")

        if not self.load_data():
            logger.warning(f"  No data available")
            return False

        # Generate LaTeX based on tier
        if self.tier == 1:
            latex_content = self.generate_latex_tier1()
        elif self.tier == 2:
            latex_content = self.generate_latex_tier2()
        else:
            latex_content = self.generate_latex_tier3()

        # Compile to PDF
        success = self.compile_latex(latex_content)

        if success:
            # Update config
            config_file = self.country_dir / "Technical" / "data" / "config.json"
            with open(config_file, 'r') as f:
                config = json.load(f)

            config['analysis']['report_generated'] = True
            config['status'] = 'complete'

            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

        return success


class BulkReportGenerator:
    """Generate reports for multiple countries"""

    def __init__(self):
        self.countries = self.load_country_list()

    def load_country_list(self):
        """Load list of all countries"""
        countries = []
        for country_dir in sorted(COUNTRIES_DIR.iterdir()):
            if country_dir.is_dir():
                config_file = country_dir / "Technical" / "data" / "config.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        if config['data_collection']['national_data']:
                            countries.append({
                                'code': config['country_code'],
                                'name': config['country_name'],
                                'tier': config.get('tier', 3)
                            })
        return countries

    def generate_tier_reports(self, tier, limit=None):
        """Generate reports for specific tier"""
        logger.info("=" * 60)
        logger.info(f"Generating Tier {tier} Reports")
        logger.info("=" * 60)

        tier_countries = [c for c in self.countries if c['tier'] == tier]
        logger.info(f"Found {len(tier_countries)} Tier {tier} countries")

        if limit:
            tier_countries = tier_countries[:limit]
            logger.info(f"Limiting to first {limit} countries")

        generated = 0
        for country in tier_countries:
            try:
                generator = CountryReportGenerator(country['code'], country['name'], country['tier'])
                if generator.generate_report():
                    generated += 1
            except Exception as e:
                logger.error(f"Error generating report for {country['name']}: {e}")

        logger.info(f"\nCompleted {generated}/{len(tier_countries)} reports")
        return generated

    def generate_all_reports(self):
        """Generate reports for all countries"""
        logger.info("=" * 60)
        logger.info("Generating All Country Reports")
        logger.info("=" * 60)

        total = 0
        total += self.generate_tier_reports(1)
        total += self.generate_tier_reports(2)
        total += self.generate_tier_reports(3)

        logger.info("\n" + "=" * 60)
        logger.info("All Reports Generated!")
        logger.info("=" * 60)
        logger.info(f"Total reports generated: {total}")
        return total


def main():
    logger.info("Country Report Generator - Gerhard Project")

    generator = BulkReportGenerator()

    # Start with Tier 1 countries (test batch of 5)
    logger.info("\nGenerating Tier 1 reports (test batch)...")
    generator.generate_tier_reports(1)

    logger.info("\nTest batch complete!")
    logger.info("Review PDFs, then run full generation")


if __name__ == "__main__":
    main()
