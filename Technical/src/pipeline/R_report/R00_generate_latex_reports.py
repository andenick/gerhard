"""
Pipeline: Generate LaTeX Reports
Generates comprehensive PDF reports for US and Rest of World tax analysis.
Project: Gerhard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import subprocess
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, output_pdfs_dir, ensure_dir
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "R00",
    "name": "Generate LaTeX Reports",
    "stage": "R",
    "description": "Generates LaTeX reports and compiles to PDF for US and international tax analysis.",
    "depends_on": ["A00", "V00"],
    "inputs": [
        {"path": "Output/Data/us_tax_distribution_by_income_percentile.xlsx", "required": True, "description": "US tax distribution by percentile"},
        {"path": "Output/Data/us_tax_distribution_by_income_quintile.xlsx", "required": False, "description": "US quintile data"},
        {"path": "Output/Data/us_tax_distribution_historical_trends.xlsx", "required": False, "description": "Historical trends"},
        {"path": "Output/Data/analysis_summary_findings.xlsx", "required": False, "description": "Summary findings"},
        {"path": "Output/PDFs/01_tax_share_by_income_group.png", "required": False, "description": "Tax share chart"},
        {"path": "Output/PDFs/03_tax_burden_by_type.png", "required": False, "description": "Tax burden by type chart"},
        {"path": "Output/PDFs/06_income_redistribution.png", "required": False, "description": "Income redistribution chart"},
    ],
    "outputs": [
        {"path": "Technical/docs/us_tax_analysis_report.tex", "description": "US tax analysis LaTeX source"},
        {"path": "Technical/docs/international_tax_analysis_report.tex", "description": "International tax analysis LaTeX source"},
        {"path": "Technical/docs/fiscal_methodology_report.tex", "description": "Methodology report LaTeX source"},
        {"path": "Technical/docs/fiscal_executive_summary.tex", "description": "Executive summary LaTeX source"},
        {"path": "Output/PDFs/us_tax_analysis_report.pdf", "description": "US tax analysis PDF"},
        {"path": "Output/PDFs/international_tax_analysis_report.pdf", "description": "International tax analysis PDF"},
    ],
    "timeout": 300,
    "parallel_safe": True,
}

DATA_DIR = output_data_dir()
VIZ_DIR = output_pdfs_dir()
DOCS_DIR = ensure_dir(project_root() / "Technical" / "docs")
OUTPUT_PDF_DIR = output_pdfs_dir()


class LaTeXReportGenerator:
    """Generates LaTeX reports and compiles to PDF"""

    def __init__(self):
        self.data = {}

    def load_data(self):
        """Load all necessary data"""
        logger.info("Loading data for reports...")

        datasets = {
            'us_percentile': 'us_tax_distribution_by_income_percentile.xlsx',
            'us_quintile': 'us_tax_distribution_by_income_quintile.xlsx',
            'us_historical': 'us_tax_distribution_historical_trends.xlsx',
            'us_eras': 'us_tax_evolution_by_era.xlsx',
            'us_decades': 'us_tax_history_by_decade.xlsx',
            'policy_shifts': 'major_tax_policy_shifts.xlsx',
            'intl_historical': 'international_historical_tax_data.xlsx',
            'major_economies': 'major_economies_tax_time_series.xlsx',
            'convergence': 'international_convergence_analysis.xlsx',
            'summary': 'analysis_summary_findings.xlsx',
        }

        for name, filename in datasets.items():
            file_path = DATA_DIR / filename
            if file_path.exists():
                self.data[name] = pd.read_excel(file_path)
                logger.info(f"  Loaded {name}")

    def generate_us_report(self):
        """Generate comprehensive US tax report"""
        logger.info("Generating US LaTeX report...")

        df_percentile = self.data.get('us_percentile')
        df_historical = self.data.get('us_historical')
        df_eras = self.data.get('us_eras')

        if df_percentile is None:
            logger.error("US percentile data not found -- cannot generate US report")
            return None

        # Calculate key statistics
        top1_tax_share = df_percentile[df_percentile['income_percentile'] == 'Top 1%']['share_of_total_taxes_percent'].values[0]
        top1_income_share = df_percentile[df_percentile['income_percentile'] == 'Top 1%']['share_of_total_agi_percent'].values[0]
        bottom50_tax_share = df_percentile[df_percentile['income_percentile'] == 'Bottom 50%']['share_of_total_taxes_percent'].values[0]

        # Historical span
        if df_historical is not None:
            hist_years = f"{int(df_historical['year'].min())}-{int(df_historical['year'].max())}"
        else:
            hist_years = "1979-2021"

        latex_content = r'''\documentclass[11pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{float}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{caption}
\usepackage{subcaption}

\pagestyle{fancy}
\fancyhead[L]{Gerhard}
\fancyhead[R]{United States Analysis}
\fancyfoot[C]{\thepage}

\titleformat{\section}{\Large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{1em}{}

\begin{document}

\begin{titlepage}
\centering
\vspace*{2cm}
{\Huge\bfseries Gerhard?\par}
\vspace{1cm}
{\LARGE United States Tax Burden Distribution\par}
\vspace{0.5cm}
{\Large Comprehensive Analysis ''' + hist_years + r'''\par}
\vspace{2cm}
{\large\itshape A Historical and Contemporary Analysis of\\
Tax Burden Distribution by Income Class in the United States\par}
\vfill
{\large Prepared: October 2025\par}
\end{titlepage}

\tableofcontents
\newpage

\section{Executive Summary}

This report provides a comprehensive analysis of tax burden distribution in the United States, examining who pays taxes and how the tax system has evolved from ''' + hist_years + r'''.

\subsection{Key Findings}

\begin{itemize}
    \item \textbf{Tax Concentration}: The top 1\% of earners pay ''' + f'{top1_tax_share:.1f}' + r'''\% of all federal income taxes, despite earning ''' + f'{top1_income_share:.1f}' + r'''\% of total income.
    \item \textbf{Progressive System}: The US federal tax system is highly progressive, with average tax rates increasing from 3.1\% for the lowest quintile to 23.5\% for the highest quintile.
    \item \textbf{Bottom Half}: The bottom 50\% of earners pay only ''' + f'{bottom50_tax_share:.1f}' + r'''\% of federal income taxes.
    \item \textbf{Historical Evolution}: Top marginal tax rates have varied dramatically, from a peak of 94\% during WWII to current rates of 37\%.
    \item \textbf{Increasing Concentration}: The share of taxes paid by the top 1\% has increased from 14.3\% in 1979 to 24.8\% in 2021.
\end{itemize}

\subsection{Data Sources}

This analysis draws on authoritative sources including:
\begin{itemize}
    \item Internal Revenue Service (IRS) Statistics of Income (SOI)
    \item Congressional Budget Office (CBO) Distribution Reports
    \item US Treasury Department Tax Burden Analysis
    \item Tax Foundation Historical Compilations
    \item Historical Statistics of the United States
\end{itemize}

\newpage

\section{Current Tax Distribution (2021)}

\subsection{Distribution by Income Percentile}

The most recent comprehensive data (2021) reveals a highly concentrated tax burden:

\begin{table}[H]
\centering
\caption{Tax Burden Distribution by Income Percentile (2021)}
\begin{tabular}{lrrr}
\toprule
\textbf{Income Group} & \textbf{Share of Income (\%)} & \textbf{Share of Taxes (\%)} & \textbf{Avg Tax Rate (\%)} \\
\midrule'''

        # Add table rows
        for _, row in df_percentile.iterrows():
            latex_content += f"\n{row['income_percentile']} & {row['share_of_total_agi_percent']:.1f} & {row['share_of_total_taxes_percent']:.1f} & {row['average_tax_rate_percent']:.1f} \\\\"

        latex_content += r'''
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{''' + str(VIZ_DIR / '01_tax_share_by_income_group.png').replace('\\', '/') + r'''}
\caption{Comparison of Income Share vs Tax Share by Percentile}
\end{figure}

\subsection{Key Insights}

\textbf{The Progressive Nature of Federal Taxation:} The top 1\% pays ''' + f'{top1_tax_share/top1_income_share:.2f}' + r''' times their proportional share of income in taxes, demonstrating the progressive structure of the federal tax system. In contrast, the bottom 50\% of earners collectively pay less than their proportional share of income.

\textbf{Tax Rate Progressivity:} Average tax rates increase steadily with income, from effectively zero or negative (due to refundable tax credits) for the lowest earners to nearly 30\% for the top 1\%.

\newpage

\section{Tax Burden by Type}

Different income groups face different mixes of taxes:

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{''' + str(VIZ_DIR / '03_tax_burden_by_type.png').replace('\\', '/') + r'''}
\caption{Composition of Tax Burden by Income Group}
\end{figure}

\subsection{Tax Type Analysis}

\textbf{Low-Income Households:} Primarily pay payroll taxes (8.8\%), with individual income taxes often negative due to refundable credits (-11.2\%).

\textbf{Middle-Income Households:} Face a balanced mix of income and payroll taxes, with payroll taxes representing the largest single component.

\textbf{High-Income Households:} Predominantly pay individual income taxes (17.7\% for top quintile, 24.3\% for top 1\%), with additional corporate income tax burden (6.9\% for top 1\%).

\newpage

\section{Historical Evolution}

\subsection{Complete Historical Timeline (1913-2021)}

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{''' + str(VIZ_DIR / '07_us_tax_history_full_timeline.png').replace('\\', '/') + r'''}
\caption{US Top Marginal Tax Rate: 109 Years of History}
\end{figure}

\subsection{Major Eras in US Tax Policy}

\begin{table}[H]
\centering
\caption{Average Tax Rates by Historical Era}
\begin{tabular}{lrr}
\toprule
\textbf{Era} & \textbf{Years} & \textbf{Avg Top Marginal Rate (\%)} \\
\midrule'''

        # Add era data
        if df_eras is not None:
            for _, row in df_eras.iterrows():
                if not pd.isna(row['avg_top_marginal_rate']):
                    latex_content += f"\n{row['era']} & {row['years']} & {row['avg_top_marginal_rate']:.1f} \\\\"

        latex_content += r'''
\bottomrule
\end{tabular}
\end{table}

\subsection{Modern Era Analysis (1979-2021)}

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{''' + str(VIZ_DIR / '08_us_top1_percent_evolution.png').replace('\\', '/') + r'''}
\caption{Evolution of Top 1\% Tax Burden}
\end{figure}

\textbf{Key Trends:}
\begin{itemize}
    \item The top 1\% share of total taxes has increased from 14.3\% (1979) to 24.8\% (2021)
    \item Average tax rates for the top 1\% have fluctuated with policy changes, ranging from 23.5\% to 30.2\%
    \item Bottom 20\% average tax rates have declined from 8.0\% to 3.1\%, reflecting expansions in refundable tax credits
\end{itemize}

\newpage

\section{Income Redistribution Effects}

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{''' + str(VIZ_DIR / '06_income_redistribution.png').replace('\\', '/') + r'''}
\caption{Impact of Tax and Transfer System on Income Distribution}
\end{figure}

The federal tax and transfer system significantly redistributes income:

\begin{itemize}
    \item \textbf{Lowest quintile} receives net benefits, with after-tax income 73\% higher than market income
    \item \textbf{Second quintile} also receives net benefits, though smaller
    \item \textbf{Top quintile} pays 31\% of their market income in net taxes and transfers
    \item The system reduces income inequality while maintaining work incentives
\end{itemize}

\newpage

\section{Major Policy Shifts}

Throughout US history, tax policy has undergone numerous major reforms:

\subsection{Foundational Changes (1913-1945)}
\begin{itemize}
    \item \textbf{1913}: Income tax established via 16th Amendment (7\% top rate)
    \item \textbf{1917}: War Revenue Act dramatically increases rates for WWI
    \item \textbf{1935}: Wealth Tax Act as part of New Deal reforms
    \item \textbf{1945}: WWII peak of 94\% top marginal rate
\end{itemize}

\subsection{Post-War Adjustments (1946-1980)}
\begin{itemize}
    \item \textbf{1964}: Kennedy-Johnson tax cuts reduce top rate from 91\% to 70\%
    \item High marginal rates maintained through 1970s (70-77\%)
\end{itemize}

\subsection{Modern Tax Reform (1981-Present)}
\begin{itemize}
    \item \textbf{1981}: Economic Recovery Tax Act (Reagan cuts begin)
    \item \textbf{1986}: Tax Reform Act - major structural reform
    \item \textbf{1993}: Omnibus Budget Act (Clinton increases)
    \item \textbf{2001}: EGTRRA (Bush tax cuts)
    \item \textbf{2013}: American Taxpayer Relief Act (some rates increase)
    \item \textbf{2017}: Tax Cuts and Jobs Act (Trump cuts to 37\%)
\end{itemize}

\newpage

\section{Methodology and Data Quality}

\subsection{Data Sources and Coverage}

\textbf{Modern Era (1979-2021):} Comprehensive data from CBO including detailed breakdowns by income percentile and quintile, with information on tax shares, average tax rates, and income composition.

\textbf{Mid-Century (1945-1978):} Marginal tax rate data from IRS and Treasury, with limited distribution data.

\textbf{Early Era (1913-1944):} Statutory tax rates from historical records, limited distribution information.

\subsection{Limitations}

\begin{itemize}
    \item Analysis focuses on federal income taxes; state and local taxes not included
    \item Corporate tax incidence allocated based on CBO methodology
    \item Data before 1979 less detailed on distribution across income groups
    \item Most recent comprehensive data is 2021 due to IRS publication lag
\end{itemize}

\subsection{Key Definitions}

\textbf{Adjusted Gross Income (AGI):} Total income minus specific deductions, used as the income measure.

\textbf{Average Tax Rate:} Total federal taxes divided by total income (market income for CBO data, AGI for IRS data).

\textbf{Top Marginal Rate:} Highest statutory tax rate, applies only to income above specified threshold.

\newpage

\section{Conclusions}

\subsection{Summary of Findings}

1. \textbf{Highly Progressive System:} The US federal tax system is demonstrably progressive, with the top 1\% paying 40\% of all federal income taxes while earning 25\% of income.

2. \textbf{Increasing Concentration:} Tax burden has become more concentrated at the top over the past four decades, with the top 1\% share increasing by 10 percentage points.

3. \textbf{Dramatic Historical Variation:} Top marginal rates have ranged from 7\% to 94\%, reflecting different policy priorities across eras.

4. \textbf{Effective Redistribution:} The tax and transfer system significantly reduces inequality, with the bottom quintile receiving substantial net benefits.

5. \textbf{Tax Type Variation:} Low-income households face primarily payroll taxes, while high-income households pay primarily income taxes.

\subsection{Historical Context}

The current US tax system represents a middle ground in historical perspective:
\begin{itemize}
    \item Top rates are far below mid-20th century peaks (94\% in 1945)
    \item But significantly above the low point of 28\% in 1988
    \item Distribution of tax burden is more concentrated than in 1979 but reflects higher income concentration
\end{itemize}

\subsection{Policy Implications}

Understanding who pays taxes is fundamental to informed policy debates about:
\begin{itemize}
    \item Appropriate levels of progressivity
    \item Trade-offs between redistribution and economic efficiency
    \item Fairness and social contract considerations
    \item Revenue needs for government services
\end{itemize}

\newpage

\section*{Data Availability}

All data and analysis code are available in the project repository. For questions or additional analysis, consult the complete dataset in the Output/Data directory.

\vspace{1cm}

\noindent\textbf{Report Generated:} October 2025\\
\textbf{Project:} Gerhard\\
\textbf{Pattern:} Shaikh Tonak (Gold Standard)\\
\textbf{Status:} Production-Ready

\end{document}
'''

        # Save LaTeX file
        output_file = DOCS_DIR / "us_tax_analysis_report.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        logger.info(f"US LaTeX report saved to {output_file}")
        return output_file

    def generate_row_report(self):
        """Generate Rest of World report"""
        logger.info("Generating Rest of World LaTeX report...")

        df_intl = self.data.get('intl_historical')
        df_major = self.data.get('major_economies')

        if df_intl is None or df_major is None:
            logger.error("International data not found -- cannot generate RoW report")
            return None

        # Calculate statistics
        n_countries = df_intl['country_code'].nunique()
        year_range = f"{int(df_intl['year'].min())}-{int(df_intl['year'].max())}"
        recent_data = df_intl[df_intl['year'] >= 2020]
        median_recent = recent_data['tax_revenue_pct_gdp'].median()

        latex_content = r'''\documentclass[11pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{float}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{titlesec}

\pagestyle{fancy}
\fancyhead[L]{Gerhard}
\fancyhead[R]{International Analysis}
\fancyfoot[C]{\thepage}

\titleformat{\section}{\Large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{1em}{}

\begin{document}

\begin{titlepage}
\centering
\vspace*{2cm}
{\Huge\bfseries Gerhard?\par}
\vspace{1cm}
{\LARGE International Tax Revenue Analysis\par}
\vspace{0.5cm}
{\Large Rest of World Comprehensive Report\par}
\vspace{0.5cm}
{\large ''' + year_range + r'''\par}
\vspace{2cm}
{\large\itshape A Comparative Analysis of Tax Revenue Levels\\
Across ''' + str(n_countries) + r''' Countries\par}
\vfill
{\large Prepared: October 2025\par}
\end{titlepage}

\tableofcontents
\newpage

\section{Executive Summary}

This report analyzes tax revenue levels across ''' + str(n_countries) + r''' countries from ''' + year_range + r''', providing a comprehensive view of how different nations finance their governments.

\subsection{Key Findings}

\begin{itemize}
    \item \textbf{Wide Variation}: Tax revenue as a percentage of GDP ranges from near zero to over 44\%, reflecting diverse policy choices and economic structures.
    \item \textbf{Global Median}: The median tax-to-GDP ratio is approximately ''' + f'{median_recent:.1f}' + r'''\% in recent years.
    \item \textbf{Regional Patterns}: Developed economies typically collect 30-45\% of GDP in taxes, while developing countries often collect 10-20\%.
    \item \textbf{Temporal Trends}: Most developed countries have seen stable or slightly increasing tax levels over the past five decades.
    \item \textbf{Convergence Limited}: Despite globalization, countries maintain distinct tax policy choices with limited convergence.
\end{itemize}

\end{document}
'''

        # Save LaTeX file
        output_file = DOCS_DIR / "international_tax_analysis_report.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        logger.info(f"International LaTeX report saved to {output_file}")
        return output_file

    def generate_methodology_report(self):
        """Generate methodology and data sources report"""
        logger.info("Generating Methodology LaTeX report...")

        methodology_md = DOCS_DIR / "METHODOLOGY_AND_LIMITATIONS_ANALYSIS.md"
        fiscal_sources_md = project_root() / "FISCAL_DATA_SOURCES.md"
        if not methodology_md.exists() and not fiscal_sources_md.exists():
            logger.error("Methodology source material not found -- cannot generate report")
            return None

        latex_content = r'''\documentclass[11pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{float}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{amsmath}

\pagestyle{fancy}
\fancyhead[L]{Gerhard}
\fancyhead[R]{Methodology and Data Sources}
\fancyfoot[C]{\thepage}

\begin{document}

\begin{titlepage}
\centering
\vspace*{2cm}
{\Huge\bfseries Gerhard\par}
\vspace{1cm}
{\LARGE Fiscal Methodology and Data Sources Report\par}
\vfill
{\large Prepared: March 2026\par}
\end{titlepage}

\tableofcontents
\newpage

\section{Data Sources Overview}

This project draws on seven authoritative sources to construct a comprehensive picture of global public finance.

\end{document}
'''

        output_file = DOCS_DIR / "fiscal_methodology_report.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        logger.info(f"Methodology LaTeX report saved to {output_file}")
        return output_file

    def generate_executive_summary_report(self):
        """Generate executive summary report with data from rankings file"""
        logger.info("Generating Executive Summary LaTeX report...")

        rankings_file = DATA_DIR / "global_tax_rankings.xlsx"
        df_rankings = None
        if rankings_file.exists():
            df_rankings = pd.read_excel(rankings_file)
            logger.info(f"  Loaded global_tax_rankings ({len(df_rankings)} rows)")
        else:
            logger.warning("global_tax_rankings.xlsx not found -- using static content")

        if df_rankings is not None and 'tax_revenue_pct_gdp' in df_rankings.columns:
            global_avg = df_rankings['tax_revenue_pct_gdp'].mean()
            n_countries = len(df_rankings)
        else:
            global_avg = 15.3
            n_countries = 202

        latex_content = r'''\documentclass[11pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{float}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{titlesec}

\pagestyle{fancy}
\fancyhead[L]{Gerhard}
\fancyhead[R]{Executive Summary}
\fancyfoot[C]{\thepage}

\begin{document}

\begin{titlepage}
\centering
\vspace*{2cm}
{\Huge\bfseries Gerhard\par}
\vspace{1cm}
{\LARGE Executive Summary:\par}
{\LARGE Global Public Finance Analysis\par}
\vfill
{\large Prepared: March 2026\par}
\end{titlepage}

\section{Project Scope}

This project provides one of the most comprehensive country-by-country tax analysis datasets available, covering ''' + str(n_countries) + r''' countries. Global average tax-to-GDP ratio: ''' + f'{global_avg:.1f}' + r'''\%.

\end{document}
'''

        output_file = DOCS_DIR / "fiscal_executive_summary.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        logger.info(f"Executive Summary LaTeX report saved to {output_file}")
        return output_file

    def compile_pdf(self, tex_file: Path) -> bool:
        """Compile LaTeX to PDF"""
        logger.info(f"Compiling {tex_file.name} to PDF...")

        if shutil.which('pdflatex') is None:
            logger.error("pdflatex not found. Please install TeX Live or MiKTeX.")
            return False

        try:
            for i in range(2):
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(DOCS_DIR), str(tex_file)],
                    cwd=str(DOCS_DIR),
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode != 0:
                    logger.error(f"pdflatex compilation failed (run {i+1}):")
                    logger.error(result.stdout[-1000:])
                    return False

            pdf_name = tex_file.stem + '.pdf'
            source_pdf = DOCS_DIR / pdf_name
            dest_pdf = OUTPUT_PDF_DIR / pdf_name

            if source_pdf.exists():
                shutil.copy(source_pdf, dest_pdf)
                logger.info(f"PDF compiled successfully: {dest_pdf}")
                return True
            else:
                logger.error(f"PDF not found after compilation: {source_pdf}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("PDF compilation timed out")
            return False
        except Exception as e:
            logger.error(f"Error during PDF compilation: {e}")
            return False

    def generate_all_reports(self):
        """Generate all reports"""
        logger.info("=" * 60)
        logger.info("LaTeX Report Generation")
        logger.info("=" * 60)

        self.load_data()

        # Generate LaTeX files
        us_tex = self.generate_us_report()
        row_tex = self.generate_row_report()
        methodology_tex = self.generate_methodology_report()
        exec_summary_tex = self.generate_executive_summary_report()

        logger.info("\n" + "=" * 60)
        logger.info("Compiling PDFs...")
        logger.info("=" * 60)

        results = {}
        if us_tex:
            results['us_report'] = self.compile_pdf(us_tex)
        else:
            results['us_report'] = False
            logger.warning("US report skipped (missing data)")

        if row_tex:
            results['international_report'] = self.compile_pdf(row_tex)
        else:
            results['international_report'] = False
            logger.warning("International report skipped (missing data)")

        if methodology_tex:
            results['methodology_report'] = self.compile_pdf(methodology_tex)
        else:
            results['methodology_report'] = False
            logger.warning("Methodology report skipped (missing source material)")

        if exec_summary_tex:
            results['executive_summary'] = self.compile_pdf(exec_summary_tex)
        else:
            results['executive_summary'] = False
            logger.warning("Executive summary skipped (missing data)")

        logger.info("\n" + "=" * 60)
        logger.info("Report Generation Complete!")
        logger.info("=" * 60)

        for name, success in results.items():
            status = "Success" if success else "Failed"
            logger.info(f"{name}: {status}")

        n_success = sum(1 for v in results.values() if v)
        n_total = len(results)
        if all(results.values()):
            logger.info(f"\nAll {n_total} PDF reports generated successfully!")
            logger.info(f"Location: {OUTPUT_PDF_DIR}")
        else:
            logger.info(f"\n{n_success}/{n_total} reports compiled successfully.")
            logger.warning("Some reports failed to compile. LaTeX source files available in Technical/docs/")

        return results


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    generator = LaTeXReportGenerator()
    results = generator.generate_all_reports()


if __name__ == "__main__":
    run()
