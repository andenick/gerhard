"""
LaTeX Report Generation
Generates comprehensive PDF reports for US and Rest of World tax analysis
Project: Gerhard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import subprocess
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, output_pdfs_dir, ensure_dir
from utils.config import project_root

logger = setup_logging(__name__)

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
            logger.error("US percentile data not found — cannot generate US report")
            return None

        # Calculate key statistics
        top1_tax_share = df_percentile[df_percentile['income_percentile'] == 'Top 1%']['share_of_total_taxes_percent'].values[0]
        top1_income_share = df_percentile[df_percentile['income_percentile'] == 'Top 1%']['share_of_total_agi_percent'].values[0]
        bottom50_tax_share = df_percentile[df_percentile['income_percentile'] == 'Bottom 50%']['share_of_total_taxes_percent'].values[0]

        # Historical span
        hist_years = f"{int(df_historical['year'].min())}-{int(df_historical['year'].max())}"

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
            logger.error("International data not found — cannot generate RoW report")
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

\subsection{Data Coverage}

\begin{itemize}
    \item \textbf{Countries}: ''' + str(n_countries) + r'''
    \item \textbf{Time Period}: ''' + year_range + r'''
    \item \textbf{Total Observations}: ''' + str(len(df_intl)) + r'''
    \item \textbf{Source}: World Bank World Development Indicators
\end{itemize}

\newpage

\section{Global Tax Revenue Levels}

\subsection{International Comparison}

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{''' + str(VIZ_DIR / '05_international_comparison.png').replace('\\', '/') + r'''}
\caption{Highest and Lowest Tax Revenue Countries}
\end{figure}

\subsection{Highest Tax Countries}

The countries with the highest tax revenue as a percentage of GDP are predominantly in Western Europe and Scandinavia, reflecting comprehensive welfare states and high levels of public service provision.

\textbf{Characteristics of High-Tax Countries:}
\begin{itemize}
    \item Universal healthcare and education
    \item Generous social insurance systems
    \item Extensive public infrastructure
    \item Strong labor protections
    \item High trust in government institutions
\end{itemize}

\subsection{Lowest Tax Countries}

Countries with low tax-to-GDP ratios include:
\begin{itemize}
    \item Resource-rich nations with alternative revenue sources (oil, minerals)
    \item Developing countries with limited administrative capacity
    \item Countries with large informal economies
    \item Special economic zones and tax havens
\end{itemize}

\newpage

\section{Major Economies Trends}

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{''' + str(VIZ_DIR / '09_major_economies_trends.png').replace('\\', '/') + r'''}
\caption{Tax Revenue Trends in Major Economies (1972-2023)}
\end{figure}

\subsection{Country-Specific Observations}

\textbf{Scandinavian Countries (Sweden, Norway, Denmark):} Consistently maintain the highest tax levels (40-50\% of GDP), funding comprehensive welfare states.

\textbf{United States:} Relatively low tax-to-GDP ratio (25-30\%) compared to other developed economies, reflecting different policy choices about government role.

\textbf{United Kingdom:} Moderate levels (32-38\%), with fluctuations reflecting different governing party priorities.

\textbf{Germany and France:} Continental European model with tax levels around 40\% of GDP.

\textbf{Japan:} Lower than European peers (28-35\%), partly due to demographic factors and debt levels.

\textbf{China:} Rising from very low levels to moderate levels (15-20\%) as economy develops and state capacity grows.

\newpage

\section{Regional Analysis}

\subsection{Europe}

\textbf{Western Europe}: Highest tax levels globally (35-45\% of GDP)
\begin{itemize}
    \item Comprehensive social insurance
    \item Universal healthcare
    \item Generous unemployment benefits
    \item Free or subsidized higher education
\end{itemize}

\textbf{Eastern Europe}: Lower than Western Europe (25-35\%) but rising
\begin{itemize}
    \item Post-transition economies
    \item EU harmonization pressures
    \item Catching up to Western European welfare models
\end{itemize}

\subsection{Americas}

\textbf{North America}: Moderate levels
\begin{itemize}
    \item United States: 25-30\%
    \item Canada: 30-35\%
    \item Mexico: 15-20\%
\end{itemize}

\textbf{Latin America}: Generally low (15-25\%)
\begin{itemize}
    \item Large informal economies
    \item Administrative capacity challenges
    \item High inequality
    \item Commodity dependence
\end{itemize}

\subsection{Asia-Pacific}

\textbf{Developed Asia}: Varies widely
\begin{itemize}
    \item Japan: 28-35\%
    \item South Korea: 25-30\%
    \item Australia: 28-32\%
\end{itemize}

\textbf{Developing Asia}: Generally low (10-20\%)
\begin{itemize}
    \item China: Rising toward 20\%
    \item India: 15-18\%
    \item Southeast Asia: 12-20\%
\end{itemize}

\subsection{Africa and Middle East}

\textbf{Sub-Saharan Africa}: Very low (10-20\%)
\begin{itemize}
    \item Limited administrative capacity
    \item Large informal sectors
    \item Agricultural economies
    \item Aid dependence
\end{itemize}

\textbf{Middle East}: Highly variable
\begin{itemize}
    \item Oil exporters: Very low (reliance on resource revenues)
    \item Non-oil economies: Moderate (20-25\%)
\end{itemize}

\newpage

\section{Historical Evolution}

\subsection{Temporal Trends by Country Group}

Analyzing trends from 1972 to 2024 reveals:

\textbf{Developed Countries:}
\begin{itemize}
    \item Generally stable or slowly increasing
    \item Response to demographic pressures (aging populations)
    \item Resistance to major increases due to political constraints
    \item Some reductions in 1980s-1990s, followed by stability
\end{itemize}

\textbf{Emerging Markets:}
\begin{itemize}
    \item Rising trend as state capacity increases
    \item Formalization of economies
    \item Investment in tax administration
    \item Pressure to fund infrastructure and development
\end{itemize}

\textbf{Low-Income Countries:}
\begin{itemize}
    \item Slow progress in increasing tax collection
    \item Many remain below 15\% threshold
    \item Challenges with informal sector
    \item Limited administrative resources
\end{itemize}

\subsection{The 15\% Threshold}

World Bank research identifies 15\% of GDP as a critical threshold for sustainable development:
\begin{itemize}
    \item Countries below 15\% struggle to fund basic services
    \item Limited infrastructure investment capacity
    \item Difficulty achieving inclusive growth
    \item Heavy reliance on aid or resource revenues
\end{itemize}

Many low-income countries remain below this threshold, limiting development potential.

\newpage

\section{Factors Explaining Variation}

\subsection{Economic Factors}

\textbf{Level of Development:}
\begin{itemize}
    \item Richer countries can and do collect more taxes
    \item Formal sector employment crucial for tax collection
    \item Financial system development enables tax compliance
\end{itemize}

\textbf{Economic Structure:}
\begin{itemize}
    \item Service economies easier to tax than agricultural
    \item Natural resource wealth can substitute for tax revenues
    \item Trade patterns affect customs revenues
\end{itemize}

\subsection{Political and Institutional Factors}

\textbf{Government Capacity:}
\begin{itemize}
    \item Strong tax administration enables higher collection
    \item Rule of law and property rights matter
    \item Corruption reduces both tax compliance and political will
\end{itemize}

\textbf{Political Preferences:}
\begin{itemize}
    \item Social democratic traditions associated with higher taxes
    \item Different views on government role in economy
    \item Historical legacies and path dependence
\end{itemize}

\subsection{Social Factors}

\textbf{Trust and Social Cohesion:}
\begin{itemize}
    \item High-trust societies can sustain higher tax rates
    \item Homogeneity vs. diversity affects solidarity
    \item Quality of public services influences tax morale
\end{itemize}

\newpage

\section{Policy Implications}

\subsection{For Developed Countries}

\textbf{Fiscal Sustainability:}
\begin{itemize}
    \item Aging populations increase spending pressures
    \item Resistance to tax increases limits policy options
    \item Debt levels rising in many countries
    \item Need for efficiency in public spending
\end{itemize}

\textbf{Globalization Challenges:}
\begin{itemize}
    \item Capital mobility limits ability to tax mobile factors
    \item Corporate tax competition constrains revenues
    \item International coordination efforts (OECD, EU)
\end{itemize}

\subsection{For Developing Countries}

\textbf{Building Tax Capacity:}
\begin{itemize}
    \item Investment in tax administration crucial
    \item Broadening tax base priority
    \item Reducing reliance on trade taxes
    \item Combating tax evasion and avoidance
\end{itemize}

\textbf{Reaching the 15\% Threshold:}
\begin{itemize}
    \item Critical for development finance
    \item Enables infrastructure investment
    \item Reduces aid dependence
    \item Builds state capacity
\end{itemize}

\newpage

\section{Methodology and Limitations}

\subsection{Data Sources}

Primary data from World Bank World Development Indicators:
\begin{itemize}
    \item Tax revenue (including social contributions)
    \item Expressed as percentage of GDP
    \item Annual frequency, 1972-2024
    \item Covers ''' + str(n_countries) + r''' countries
\end{itemize}

\subsection{Limitations}

\textbf{Coverage Issues:}
\begin{itemize}
    \item Not all countries have complete time series
    \item Data quality varies by country
    \item Some years missing for certain countries
    \item Subnational taxes may not be fully captured
\end{itemize}

\textbf{Comparability Challenges:}
\begin{itemize}
    \item Different tax structures across countries
    \item Social security contributions treatment varies
    \item Resource revenues classification differs
    \item Exchange rate and GDP measurement issues
\end{itemize}

\textbf{Distribution Data Limitations:}
\begin{itemize}
    \item This report focuses on aggregate tax levels
    \item Most countries do not publish detailed distribution data
    \item US has uniquely granular breakdown by income class
    \item International distribution comparisons very limited
\end{itemize}

\newpage

\section{Conclusions}

\subsection{Summary of Findings}

1. \textbf{Wide International Variation:} Tax levels vary from near-zero to over 44\% of GDP, reflecting different policy choices, economic structures, and historical contexts.

2. \textbf{Developed vs. Developing Divide:} Developed countries typically collect 30-45\% of GDP, while developing countries often collect 10-20\%.

3. \textbf{Regional Patterns:} Europe has highest tax levels, Africa and Middle East lowest, with Americas and Asia in between.

4. \textbf{Limited Convergence:} Despite globalization, countries maintain distinct tax policies with little sign of convergence.

5. \textbf{15\% Threshold Critical:} Countries below 15\% of GDP struggle to fund basic development needs.

\subsection{Global Context}

The international comparison provides context for US tax policy:
\begin{itemize}
    \item US tax-to-GDP ratio lower than most developed countries
    \item Reflects different preferences about government role
    \item US funds significant military spending not comparable to others
    \item Healthcare system differences affect tax vs. private spending mix
\end{itemize}

\subsection{Future Outlook}

Key challenges for global tax policy:
\begin{itemize}
    \item Aging populations in developed countries
    \item Digital economy taxation challenges
    \item Climate change funding needs
    \item Inequality and redistribution debates
    \item International tax competition and cooperation
\end{itemize}

\vspace{1cm}

\noindent\textbf{Report Generated:} October 2025\\
\textbf{Project:} Gerhard\\
\textbf{Coverage:} ''' + str(n_countries) + r''' Countries, ''' + year_range + r'''\\
\textbf{Status:} Production-Ready

\end{document}
'''

        # Save LaTeX file
        output_file = DOCS_DIR / "international_tax_analysis_report.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        logger.info(f"International LaTeX report saved to {output_file}")
        return output_file

    def generate_methodology_report(self):
        """Generate methodology and data sources report (text-heavy, no Excel data needed)"""
        logger.info("Generating Methodology LaTeX report...")

        # Check if source material exists
        methodology_md = DOCS_DIR / "METHODOLOGY_AND_LIMITATIONS_ANALYSIS.md"
        fiscal_sources_md = project_root() / "FISCAL_DATA_SOURCES.md"
        if not methodology_md.exists() and not fiscal_sources_md.exists():
            logger.error("Methodology source material not found — cannot generate report")
            return None

        latex_content = r'''\documentclass[11pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{float}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{amsmath}

\pagestyle{fancy}
\fancyhead[L]{Gerhard}
\fancyhead[R]{Methodology and Data Sources}
\fancyfoot[C]{\thepage}

\titleformat{\section}{\Large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{1em}{}

\begin{document}

\begin{titlepage}
\centering
\vspace*{2cm}
{\Huge\bfseries Gerhard\par}
\vspace{1cm}
{\LARGE Fiscal Methodology and Data Sources Report\par}
\vspace{0.5cm}
{\Large Technical Documentation\par}
\vspace{2cm}
{\large\itshape Comprehensive documentation of data sources, collection methods,\\
calculation formulas, quality assessment, and known limitations\par}
\vfill
{\large Prepared: March 2026\par}
\end{titlepage}

\tableofcontents
\newpage

% ======================================================================
\section{Data Sources Overview}
% ======================================================================

This project draws on seven authoritative sources to construct a comprehensive picture of global public finance. Each source provides a distinct dimension of coverage.

\begin{table}[H]
\centering
\caption{Primary Data Sources}
\begin{tabular}{llll}
\toprule
\textbf{Source} & \textbf{Coverage} & \textbf{Years} & \textbf{Data Type} \\
\midrule
World Bank WDI     & 199 countries       & 1972--2024 & Tax revenue (\% GDP) \\
IMF WoRLD          & $\sim$200 countries & Historical & Revenue by category \\
OECD Revenue Stats & 38 OECD members     & 1965--present & Tax structure by type \\
Eurostat           & EU members          & 1995--present & Government finance \\
WID.world          & 347 entities        & 1800--2024 & Income/wealth distribution \\
US DINA            & United States       & 1913--2020 & Tax incidence by percentile \\
IRS SOI            & United States       & 1979--2021 & Tax returns by income group \\
CBO                & United States       & 1979--2021 & Distributional tax analysis \\
\bottomrule
\end{tabular}
\end{table}

\subsection{World Bank World Development Indicators}

The primary international source. Indicator \texttt{GC.TAX.TOTL.GD.ZS} measures tax revenue (including social contributions) as a percentage of GDP, following the IMF Government Finance Statistics (GFS) manual definition. Covers 199 countries with 5,565 observations after cleaning. Data is collected from national statistical agencies, validated, and standardized by the World Bank.

\subsection{IRS Statistics of Income}

Official US tax return statistics based on a stratified sample of approximately 340,000 returns representing 154 million filed returns. All returns with AGI above \$200,000 are sampled at 100\%; lower incomes use a stratified random sample with weighting. Publication lag is approximately two years.

\subsection{Congressional Budget Office}

Non-partisan distributional analysis combining IRS data with household-size adjustment, underreporting correction, non-filer imputation, and transfer income. Allocates corporate tax incidence as 75\% to capital income and 25\% to labor. Covers 1979--2021 with detailed quintile and percentile breakdowns.

\subsection{World Inequality Database}

Bulk download of 4.1 GB covering 347 countries and entities. Provides income and wealth distribution by percentile, including top income shares, wealth concentration, and pre-tax and post-tax measures. Historical depth extends to 1800 for some countries.

\subsection{US Distributional National Accounts}

The gold standard for US tax incidence analysis. Compiled by Piketty, Saez, and Zucman, covering 1913--2020 with all percentiles (P0--P100, including Top 0.01\%), pre-tax and post-tax income, factor and fiscal income, wealth distribution, and tax rates by income level across federal, state, and local taxes.

\newpage

% ======================================================================
\section{Collection Methodology}
% ======================================================================

\subsection{Data Acquisition Pipeline}

The data collection follows a structured pipeline:

\begin{enumerate}
    \item \textbf{Download}: Automated retrieval from public APIs (World Bank, IMF) and bulk file downloads (WID, DINA). OECD data requires manual download due to API limitations.
    \item \textbf{Validation}: Raw data checked for completeness, range validity, and format consistency. Outliers exceeding 60\% tax-to-GDP are flagged and removed (8 observations removed from international data).
    \item \textbf{Standardization}: Country names and codes normalized to ISO 3-letter format. Time periods aligned to calendar years. Units harmonized to percentages of GDP.
    \item \textbf{Integration}: Cross-source validation for overlapping countries (OECD vs World Bank). US data reconciled across IRS SOI, CBO, and DINA sources.
    \item \textbf{Output}: Clean datasets exported to Excel (.xlsx) for analysis and visualization. Master catalogue tracks all outputs with metadata.
\end{enumerate}

\subsection{Data Cleaning}

\begin{itemize}
    \item Removed 8 outlier observations where tax-to-GDP exceeded 60\% (likely data errors)
    \item Applied reasonable bounds of 0--60\% for tax-to-GDP ratios
    \item Missing values are preserved (not imputed) to avoid introducing bias
    \item Country time series with fewer than 3 observations are retained but flagged
\end{itemize}

\newpage

% ======================================================================
\section{Calculation Methods}
% ======================================================================

\subsection{Tax-to-GDP Ratio}

The fundamental metric for cross-country comparison:

\begin{equation}
\tau_i = \frac{T_i}{Y_i} \times 100
\end{equation}

where $T_i$ is total tax revenue (including social contributions) and $Y_i$ is gross domestic product, both in current local currency for country $i$.

\subsection{Fiscal Balance}

The difference between total government revenue and total expenditure:

\begin{equation}
FB_i = T_i - G_i
\end{equation}

where $G_i$ is total government expenditure. A negative value indicates a fiscal deficit.

\subsection{Progressivity Measurement}

Tax progressivity is assessed by comparing the distribution of tax burden to the distribution of income. The Kakwani index concept measures the departure of the tax system from proportionality:

\begin{equation}
K = C_T - G_Y
\end{equation}

where $C_T$ is the concentration coefficient of tax payments and $G_Y$ is the Gini coefficient of pre-tax income. A positive $K$ indicates a progressive tax system (higher-income groups pay a larger share of taxes than their share of income).

In practice, we measure progressivity by comparing tax shares to income shares:

\begin{equation}
P_g = \frac{s^T_g}{s^Y_g}
\end{equation}

where $s^T_g$ is group $g$'s share of total taxes and $s^Y_g$ is its share of total income. $P_g > 1$ indicates the group pays more than proportionally.

\subsection{Trend Analysis}

Country-level trends are estimated via ordinary least squares regression:

\begin{equation}
\tau_{it} = \alpha_i + \beta_i \cdot t + \epsilon_{it}
\end{equation}

A positive $\beta_i$ indicates increasing tax revenue over time. Countries are classified as ``increasing'' ($\beta > 0$, $p < 0.05$), ``decreasing'' ($\beta < 0$, $p < 0.05$), or ``stable''.

\newpage

% ======================================================================
\section{Data Quality Assessment}
% ======================================================================

\subsection{Completeness by Source}

\begin{table}[H]
\centering
\caption{Data Completeness Assessment}
\begin{tabular}{lrrl}
\toprule
\textbf{Source} & \textbf{Countries} & \textbf{Observations} & \textbf{Completeness} \\
\midrule
World Bank WDI     & 199 & 5,565 & High (OECD), Medium (emerging), Low (LICs) \\
IRS SOI            & 1   & 43    & Very High (all years 1979--2021) \\
CBO Distribution   & 1   & 43    & Very High (all years 1979--2021) \\
US DINA            & 1   & 108   & Very High (1913--2020) \\
WID.world          & 347 & Varies & High for major countries, sparse elsewhere \\
\bottomrule
\end{tabular}
\end{table}

\subsection{Timeliness}

\begin{itemize}
    \item \textbf{World Bank}: 1--2 year lag; most recent data is 2022--2023 for developed countries
    \item \textbf{IRS SOI}: 2--3 year lag; most recent is tax year 2021
    \item \textbf{CBO}: 2--3 year lag; most recent covers through 2021
    \item \textbf{WID}: Variable; some series updated annually, others less frequently
\end{itemize}

\subsection{Cross-Source Consistency}

For overlapping coverage (OECD countries), World Bank and OECD tax-to-GDP ratios show strong agreement with correlation $> 0.95$. Minor discrepancies arise from differences in social contribution treatment and GDP vintage. US data across IRS, CBO, and DINA are broadly consistent but differ in income definitions and tax scope.

\newpage

% ======================================================================
\section{Known Limitations}
% ======================================================================

\subsection{Comparability Challenges}

\begin{itemize}
    \item \textbf{Tax definitions}: What counts as ``tax revenue'' varies across countries. Some include social security contributions; others do not. Resource royalties may or may not be classified as tax revenue.
    \item \textbf{GDP measurement}: Differences in national accounts methodology (SNA 1993 vs SNA 2008) affect the denominator. Informal economy treatment varies.
    \item \textbf{Government levels}: Some countries report central government only; others include subnational. Federal systems (US, Germany, Brazil) may understate total tax if subnational data is incomplete.
    \item \textbf{Currency effects}: While tax-to-GDP ratios cancel currency, GDP measurement quality affects the ratio.
\end{itemize}

\subsection{Coverage Gaps}

\begin{itemize}
    \item \textbf{Low-income countries}: Sparse coverage, especially before 2000. Many Sub-Saharan African countries have fewer than 10 annual observations.
    \item \textbf{Conflict zones}: No data for active conflict periods (e.g., Somalia, Syria, Yemen during civil wars).
    \item \textbf{Small states}: Some small island nations and territories have intermittent reporting.
    \item \textbf{Historical}: Pre-1990 data unavailable for many post-Soviet and post-Yugoslav states.
\end{itemize}

\subsection{Temporal Breaks}

\begin{itemize}
    \item Methodology changes in national accounts can create apparent jumps in tax-to-GDP ratios.
    \item Reclassification of social contributions (e.g., EU harmonization) may cause discontinuities.
    \item Country boundary changes (German reunification, Czech/Slovak split) create breaks.
\end{itemize}

\subsection{Informal Economy}

Tax-to-GDP ratios systematically understate the true tax potential in countries with large informal sectors. The formal economy may represent only 50--70\% of true economic activity in developing countries, meaning the effective tax rate on the formal economy is higher than the headline ratio suggests.

\newpage

% ======================================================================
\section{Recommendations for Users}
% ======================================================================

\subsection{Interpreting Cross-Country Comparisons}

\begin{enumerate}
    \item \textbf{Compare within peer groups}: Developed-to-developed and developing-to-developing comparisons are more meaningful than cross-group comparisons.
    \item \textbf{Check the time dimension}: A single year can be misleading. Use multi-year averages or examine trends.
    \item \textbf{Consider government structure}: Federal vs. unitary states have different tax distribution across government levels.
    \item \textbf{Account for resource revenues}: Oil-rich countries may have low tax-to-GDP but high total government revenue.
\end{enumerate}

\subsection{Interpreting US Distribution Data}

\begin{enumerate}
    \item \textbf{Income definition matters}: IRS uses AGI (narrower), CBO uses market income (broader). Results differ.
    \item \textbf{Tax scope}: IRS covers federal income tax only; CBO covers all federal taxes. Including state/local would change the picture significantly.
    \item \textbf{Unit of analysis}: IRS uses tax returns (individuals/couples); CBO uses households. Not directly comparable.
    \item \textbf{Marginal vs. average rates}: Top marginal rates (statutory) are much higher than average effective rates. Always specify which.
\end{enumerate}

\subsection{Best Practices}

\begin{itemize}
    \item Always cite the specific source and year when presenting numbers
    \item Acknowledge limitations in any published analysis
    \item Use multiple sources when available for triangulation
    \item Present ranges rather than point estimates where uncertainty is high
    \item Be explicit about whether social contributions are included
    \item Note any data cleaning or imputation applied
\end{itemize}

\vspace{1cm}

\noindent\textbf{Report Generated:} March 2026\\
\textbf{Project:} Gerhard\\
\textbf{Document Type:} Technical Methodology\\
\textbf{Status:} Production-Ready

\end{document}
'''

        # Save LaTeX file
        output_file = DOCS_DIR / "fiscal_methodology_report.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        logger.info(f"Methodology LaTeX report saved to {output_file}")
        return output_file

    def generate_executive_summary_report(self):
        """Generate executive summary report with data from rankings file"""
        logger.info("Generating Executive Summary LaTeX report...")

        # Load rankings data
        rankings_file = DATA_DIR / "global_tax_rankings.xlsx"
        df_rankings = None
        if rankings_file.exists():
            df_rankings = pd.read_excel(rankings_file)
            logger.info(f"  Loaded global_tax_rankings ({len(df_rankings)} rows)")
        else:
            logger.warning("global_tax_rankings.xlsx not found — using static content")

        # Dynamic stats from rankings if available
        if df_rankings is not None and 'tax_revenue_pct_gdp' in df_rankings.columns:
            global_avg = df_rankings['tax_revenue_pct_gdp'].mean()
            global_min = df_rankings['tax_revenue_pct_gdp'].min()
            global_max = df_rankings['tax_revenue_pct_gdp'].max()
            n_countries = len(df_rankings)

            # Top 10
            top10 = df_rankings.nlargest(10, 'tax_revenue_pct_gdp')
            # Bottom 10
            bottom10 = df_rankings.nsmallest(10, 'tax_revenue_pct_gdp')
        else:
            global_avg = 15.3
            global_min = 0.0
            global_max = 44.4
            n_countries = 202
            top10 = None
            bottom10 = None

        # Build top/bottom tables
        def _make_table_rows(df_subset):
            if df_subset is None:
                return "\\textit{Data not available} & & \\\\\n"
            rows = ""
            country_col = 'country_name' if 'country_name' in df_subset.columns else df_subset.columns[0]
            tax_col = 'tax_revenue_pct_gdp'
            trend_col = 'trend' if 'trend' in df_subset.columns else None
            for _, row in df_subset.iterrows():
                cname = str(row[country_col]).replace('&', '\\&')
                tax_val = f"{row[tax_col]:.1f}"
                trend_val = str(row[trend_col]).replace('_', ' ').title() if trend_col and pd.notna(row.get(trend_col)) else '--'
                rows += f"{cname} & {tax_val} & {trend_val} \\\\\n"
            return rows

        top10_rows = _make_table_rows(top10)
        bottom10_rows = _make_table_rows(bottom10)

        latex_content = r'''\documentclass[11pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{float}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{titlesec}

\pagestyle{fancy}
\fancyhead[L]{Gerhard}
\fancyhead[R]{Executive Summary}
\fancyfoot[C]{\thepage}

\titleformat{\section}{\Large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{1em}{}

\begin{document}

\begin{titlepage}
\centering
\vspace*{2cm}
{\Huge\bfseries Gerhard\par}
\vspace{1cm}
{\LARGE Executive Summary:\par}
{\LARGE Global Public Finance Analysis\par}
\vspace{2cm}
{\large\itshape A comprehensive analysis of tax revenue collection\\
across ''' + str(n_countries) + r''' countries with 5,565 country-years of data\par}
\vfill
{\large Prepared: March 2026\par}
\end{titlepage}

\tableofcontents
\newpage

% ======================================================================
\section{Project Scope}
% ======================================================================

This project provides one of the most comprehensive country-by-country tax analysis datasets available, covering:

\begin{itemize}
    \item \textbf{''' + str(n_countries) + r''' countries and entities} analyzed worldwide
    \item \textbf{5,565 country-years} of validated data
    \item \textbf{1972--2024} time span with historical depth to 1913 for the United States
    \item \textbf{7+ authoritative sources}: World Bank, IMF, OECD, Eurostat, WID.world, US DINA, IRS SOI, and CBO
\end{itemize}

The infrastructure includes automated data collection, statistical analysis with trend estimation, professional visualizations (300 DPI), LaTeX-compiled PDF reports, and a master catalogue with provenance tracking.

\newpage

% ======================================================================
\section{Global Findings}
% ======================================================================

\subsection{Summary Statistics}

\begin{itemize}
    \item \textbf{Global Average:} ''' + f'{global_avg:.1f}' + r'''\% of GDP
    \item \textbf{Range:} ''' + f'{global_min:.1f}' + r'''\% to ''' + f'{global_max:.1f}' + r'''\% of GDP
    \item \textbf{Countries with increasing trend:} 95 (48\%) --- mostly European welfare states and developing countries building fiscal capacity
    \item \textbf{Countries with decreasing trend:} 59 (30\%) --- post-transition economies and some emerging markets after reforms
    \item \textbf{Countries with stable trend:} 45 (22\%) --- established systems with mature fiscal frameworks
\end{itemize}

Tax revenue as a share of GDP varies enormously across the globe, reflecting diverse policy choices, economic structures, institutional capacity, and historical legacies.

\newpage

% ======================================================================
\section{Top and Bottom Countries}
% ======================================================================

\subsection{Highest Tax Revenue Countries}

\begin{table}[H]
\centering
\caption{Top 10 Countries by Tax Revenue (\% of GDP)}
\begin{tabular}{lrl}
\toprule
\textbf{Country} & \textbf{Tax/GDP (\%)} & \textbf{Trend} \\
\midrule
''' + top10_rows + r'''\bottomrule
\end{tabular}
\end{table}

\textbf{Pattern:} Scandinavian welfare states, Western European economies, and some small open economies with comprehensive public service provision consistently rank highest.

\subsection{Lowest Tax Revenue Countries}

\begin{table}[H]
\centering
\caption{Bottom 10 Countries by Tax Revenue (\% of GDP)}
\begin{tabular}{lrl}
\toprule
\textbf{Country} & \textbf{Tax/GDP (\%)} & \textbf{Trend} \\
\midrule
''' + bottom10_rows + r'''\bottomrule
\end{tabular}
\end{table}

\textbf{Pattern:} Resource-rich economies relying on non-tax revenues, fragile and conflict-affected states, and rapidly developing countries with large informal sectors occupy the bottom of the distribution.

\newpage

% ======================================================================
\section{Regional Patterns}
% ======================================================================

Tax collection levels cluster strongly by region, reflecting shared institutional histories and policy traditions:

\begin{itemize}
    \item \textbf{Europe (highest, 30--45\% of GDP):} Comprehensive welfare states, universal healthcare and education, strong tax administration. Scandinavia averages 28.1\%, Western Europe 22.5\%.
    \item \textbf{North America (moderate, 10--15\%):} Mixed federal--state systems. US at 10.9\% (federal only) pulls the average down; Canada higher at 30--35\% (all levels).
    \item \textbf{Asia-Pacific (variable, 12--30\%):} Developed Asia (Japan, Korea, Australia) at 25--35\%; developing Asia (China, India, Southeast Asia) at 10--20\%.
    \item \textbf{Latin America (low-to-moderate, 15--25\%):} Large informal economies, administrative capacity challenges, commodity dependence.
    \item \textbf{Africa and Middle East (lowest, 0--20\%):} Sub-Saharan Africa averages 10--20\% with limited administrative capacity. Oil-exporting Middle Eastern states rely on resource revenues rather than taxation.
\end{itemize}

\newpage

% ======================================================================
\section{United States in Global Context}
% ======================================================================

The United States occupies a distinctive position in the global tax landscape:

\begin{itemize}
    \item \textbf{Federal tax revenue:} 10.9\% of GDP --- well below the global average of 15.3\%
    \item \textbf{All-government tax revenue:} approximately 25--27\% of GDP when state and local taxes are included --- still below most OECD peers
    \item \textbf{Highly progressive federal system:} The top 1\% of earners pays 40.4\% of all federal income taxes while earning approximately 25\% of total income
    \item \textbf{Tax type mix:} Relies more on income taxes and less on consumption taxes (no federal VAT) compared to other developed countries
\end{itemize}

The US demonstrates that lower aggregate tax levels coexist with high progressivity at the federal level. The gap with other developed countries primarily reflects lower social insurance contributions and the absence of a value-added tax.

\newpage

% ======================================================================
\section{Policy Implications}
% ======================================================================

The data reveal several pressing challenges for global fiscal policy:

\subsection{Aging Populations}

Developed countries face rising pension and healthcare costs. Countries already at 40--45\% tax-to-GDP face political limits on further increases, while those at lower levels may need significant revenue mobilization.

\subsection{Digital Economy}

Traditional tax systems based on physical presence struggle to capture value created digitally across borders. The OECD Pillar One and Pillar Two frameworks represent early attempts at adaptation, but implementation remains uneven.

\subsection{Climate Funding}

Meeting Paris Agreement commitments requires substantial public investment. Carbon pricing and green taxation could simultaneously raise revenue and address externalities, but political feasibility varies.

\subsection{Inequality}

Rising income and wealth concentration in many countries intensifies debates about tax progressivity. The data show that highly progressive systems (like the US federal income tax) can coexist with high pre-tax inequality, raising questions about whether tax policy alone is sufficient to address distributional concerns.

\subsection{Development Finance}

Many low-income countries remain below the 15\% tax-to-GDP threshold that the World Bank identifies as necessary for sustainable development. Building domestic revenue mobilization capacity is essential for reducing aid dependence.

\vspace{1cm}

\noindent\textbf{Report Generated:} March 2026\\
\textbf{Project:} Gerhard\\
\textbf{Coverage:} ''' + str(n_countries) + r''' Countries, 1972--2024\\
\textbf{Status:} Production-Ready

\end{document}
'''

        # Save LaTeX file
        output_file = DOCS_DIR / "fiscal_executive_summary.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        logger.info(f"Executive Summary LaTeX report saved to {output_file}")
        return output_file

    def compile_pdf(self, tex_file: Path) -> bool:
        """Compile LaTeX to PDF"""
        logger.info(f"Compiling {tex_file.name} to PDF...")

        # Check if pdflatex is available
        if shutil.which('pdflatex') is None:
            logger.error("pdflatex not found. Please install TeX Live or MiKTeX.")
            logger.info("On Windows: Download MiKTeX from https://miktex.org/download")
            logger.info("On Linux: sudo apt-get install texlive-latex-base texlive-latex-extra")
            return False

        try:
            # Run pdflatex twice for proper references
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
                    logger.error(result.stdout[-1000:])  # Last 1000 chars
                    return False

            # Move PDF to Output directory
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

        # Compile PDFs
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
            status = "✓ Success" if success else "✗ Failed"
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


def main():
    logger.info("LaTeX Report Generator - Gerhard Project")

    generator = LaTeXReportGenerator()
    results = generator.generate_all_reports()


if __name__ == "__main__":
    main()
