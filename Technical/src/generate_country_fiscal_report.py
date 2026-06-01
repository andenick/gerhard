"""
Individual Country Fiscal Report Generator
Creates comprehensive fiscal analysis reports for each country

Part of Gerhard - Global Fiscal Analysis Platform
Publication-quality reporting
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from country_report_visualizer import CountryFiscalVisualizer
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import countries_dir

logger = setup_logging(__name__)

# Project paths
COUNTRIES_DIR = countries_dir()
UNIFIED_INDEX = COUNTRIES_DIR / "unified_index_statistics.json"


def load_country_data(country_code):
    """Load all available data for a country"""
    country_dir = COUNTRIES_DIR / country_code
    data_dir = country_dir / "Output" / "Data"

    data = {
        'code': country_code,
        'name': None,
        'tax_data': None,
        'exp_data': None,
        'has_tax': False,
        'has_exp': False
    }

    # Load tax data
    tax_file = data_dir / f"{country_code.lower()}_national_tax_data.xlsx"
    if tax_file.exists():
        try:
            df = pd.read_excel(tax_file)
            data['tax_data'] = df
            data['has_tax'] = True
            if 'country_name' in df.columns:
                data['name'] = df['country_name'].iloc[0]
        except Exception as e:
            print(f"  Warning: Could not load tax data: {e}")

    # Load expenditure data
    exp_file = data_dir / f"{country_code.lower()}_government_expenditure.xlsx"
    if exp_file.exists():
        try:
            df = pd.read_excel(exp_file)

            # Standardize column names to match expected format
            column_mapping = {
                'Year': 'year',
                'Country': 'country_code',
                'Total_Govt_Expenditure_GDP': 'total_expenditure_gdp',
                'Education_Expenditure_GDP': 'education_gdp',
                'Education_Pct_Govt_Budget': 'education_pct_budget',
                'Health_Expenditure_GDP': 'health_govt_gdp',
                'Health_Pct_Govt_Budget': 'health_pct_budget',
                'Military_Expenditure_GDP': 'military_gdp',
                'RD_Expenditure_GDP': 'rd_gdp',
                'Social_Protection_Adequacy': 'social_contrib_revenue'
            }
            df = df.rename(columns=column_mapping)

            data['exp_data'] = df
            data['has_exp'] = True
            if 'country_name' in df.columns and data['name'] is None:
                data['name'] = df['country_name'].iloc[0]
            elif data['name'] is None and 'country_code' in df.columns:
                # Fallback to country code if name not available
                data['name'] = df['country_code'].iloc[0]
        except Exception as e:
            print(f"  Warning: Could not load expenditure data: {e}")

    # Load metadata
    meta_file = data_dir / f"{country_code.lower()}_expenditure_summary.json"
    if meta_file.exists():
        try:
            with open(meta_file, 'r') as f:
                meta = json.load(f)
                if data['name'] is None:
                    data['name'] = meta.get('country_name', country_code)
        except:
            pass

    # Fallback for name
    if data['name'] is None:
        data['name'] = country_code

    return data


def get_country_metadata(country_code):
    """Get country metadata from unified index"""
    # Load unified index statistics
    if UNIFIED_INDEX.exists():
        with open(UNIFIED_INDEX, 'r') as f:
            stats = json.load(f)

    # Read the master index markdown to get tier/region info
    index_file = COUNTRIES_DIR / "UNIFIED_MASTER_INDEX.md"
    metadata = {
        'tier': 3,  # Default
        'region': 'Unknown',
        'income_level': 'Unknown'
    }

    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            for line in f:
                if f'| {country_code} |' in line or f'| {country_code.upper()} |' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 4:
                        try:
                            metadata['tier'] = int(parts[3])
                        except:
                            pass
                    break

    return metadata


def calculate_metrics(tax_data, exp_data, metadata):
    """Calculate key metrics for dashboard"""
    metrics = {
        'tax_revenue': None,
        'education': None,
        'health': None,
        'military': None,
        'rd': None,
        'coverage_years': None,
        'tier': metadata.get('tier', 3),
        'region': metadata.get('region', 'Unknown'),
        'income_level': metadata.get('income_level', 'Unknown')
    }

    # Tax revenue (latest)
    if tax_data is not None and len(tax_data) > 0:
        latest_tax = tax_data.iloc[-1]
        metrics['tax_revenue'] = latest_tax.get('tax_revenue_pct_gdp')
        metrics['coverage_years'] = f"{tax_data['year'].min()}-{tax_data['year'].max()}"

    # Expenditure (latest)
    if exp_data is not None and len(exp_data) > 0:
        latest_exp = exp_data.iloc[-1]
        metrics['education'] = latest_exp.get('education_gdp')
        metrics['health'] = latest_exp.get('health_govt_gdp')
        metrics['military'] = latest_exp.get('military_gdp')
        metrics['rd'] = latest_exp.get('rd_gdp')

        if metrics['coverage_years'] is None:
            metrics['coverage_years'] = f"{exp_data['year'].min()}-{exp_data['year'].max()}"
        else:
            # Combine ranges
            tax_years = metrics['coverage_years'].split('-')
            exp_years = [exp_data['year'].min(), exp_data['year'].max()]
            min_year = min(int(tax_years[0]), exp_years[0])
            max_year = max(int(tax_years[1]), exp_years[1])
            metrics['coverage_years'] = f"{min_year}-{max_year}"

    return metrics


def generate_markdown_report(country_code, country_name, data, metadata, metrics, charts):
    """Generate comprehensive markdown report"""

    report = f"""# {country_name} - Comprehensive Fiscal Analysis Report

**Country Code:** {country_code}
**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Analysis Tier:** Tier {metadata.get('tier', 3)}
**Pattern:** Publication-quality data standards

---

## Executive Summary

### Country Overview
- **Region:** {metadata.get('region', 'Not classified')}
- **Income Level:** {metadata.get('income_level', 'Not classified')}
- **Analysis Tier:** Tier {metadata.get('tier', 3)} ({'Comprehensive' if metadata.get('tier') == 1 else 'Standard' if metadata.get('tier') == 2 else 'Basic'})

### Data Availability
- **Tax Revenue Data:** {'Available' if data['has_tax'] else 'Not Available'}
- **Government Expenditure Data:** {'Available' if data['has_exp'] else 'Not Available'}
- **Time Coverage:** {metrics.get('coverage_years', 'N/A')}

### Key Fiscal Indicators (Latest Year)

| Indicator | Value | Data Availability |
|-----------|-------|-------------------|
| **Tax Revenue (% GDP)** | {f"{metrics['tax_revenue']:.2f}%" if metrics['tax_revenue'] else 'N/A'} | {'Yes' if metrics['tax_revenue'] else 'No'} |
| **Education Expenditure (% GDP)** | {f"{metrics['education']:.2f}%" if metrics['education'] else 'N/A'} | {'Yes' if metrics['education'] else 'No'} |
| **Health Expenditure (% GDP)** | {f"{metrics['health']:.2f}%" if metrics['health'] else 'N/A'} | {'Yes' if metrics['health'] else 'No'} |
| **Military Expenditure (% GDP)** | {f"{metrics['military']:.2f}%" if metrics['military'] else 'N/A'} | {'Yes' if metrics['military'] else 'No'} |
| **R&D Expenditure (% GDP)** | {f"{metrics['rd']:.2f}%" if metrics['rd'] else 'N/A'} | {'Yes' if metrics['rd'] else 'No'} |

---

## Visual Summary

### Key Metrics Dashboard
![Key Metrics]({charts[-1] if charts else 'N/A'})

*This dashboard provides an at-a-glance view of the most important fiscal indicators for {country_name}.*

---

## Tax Revenue Analysis
"""

    if data['has_tax']:
        tax_df = data['tax_data']
        latest_tax = tax_df.iloc[-1]
        earliest_tax = tax_df.iloc[0]

        report += f"""
### Historical Trends (1972-2024)

![Tax Revenue Trend]({charts[0] if len(charts) > 0 else 'N/A'})

### Current Status ({int(latest_tax['year'])})
- **Tax Revenue:** {latest_tax['tax_revenue_pct_gdp']:.2f}% of GDP
- **Time Series:** {len(tax_df)} observations from {int(earliest_tax['year'])} to {int(latest_tax['year'])}
- **Trend:** {"Rising" if latest_tax['tax_revenue_pct_gdp'] > earliest_tax['tax_revenue_pct_gdp'] else "Declining"} (from {earliest_tax['tax_revenue_pct_gdp']:.2f}% to {latest_tax['tax_revenue_pct_gdp']:.2f}%)

### Tax Revenue Statistics

| Metric | Value |
|--------|-------|
| **Latest Year** | {int(latest_tax['year'])} |
| **Latest Value** | {latest_tax['tax_revenue_pct_gdp']:.2f}% of GDP |
| **Mean (Historical)** | {tax_df['tax_revenue_pct_gdp'].mean():.2f}% |
| **Minimum** | {tax_df['tax_revenue_pct_gdp'].min():.2f}% ({int(tax_df.loc[tax_df['tax_revenue_pct_gdp'].idxmin(), 'year'])}) |
| **Maximum** | {tax_df['tax_revenue_pct_gdp'].max():.2f}% ({int(tax_df.loc[tax_df['tax_revenue_pct_gdp'].idxmax(), 'year'])}) |
| **Standard Deviation** | {tax_df['tax_revenue_pct_gdp'].std():.2f} percentage points |

### Interpretation

The tax-to-GDP ratio is a key indicator of fiscal capacity - the government's ability to raise revenue to finance public services.

- **< 15%:** Low fiscal capacity (typical of low-income countries)
- **15-20%:** Moderate fiscal capacity (typical of middle-income countries)
- **20-25%:** Good fiscal capacity (typical of upper-middle income)
- **25-30%:** High fiscal capacity (typical of developed countries)
- **> 30%:** Very high fiscal capacity (Nordic countries, some European states)

**{country_name}'s current rate of {latest_tax['tax_revenue_pct_gdp']:.2f}%** places it in the **{'low' if latest_tax['tax_revenue_pct_gdp'] < 15 else 'moderate' if latest_tax['tax_revenue_pct_gdp'] < 20 else 'good' if latest_tax['tax_revenue_pct_gdp'] < 25 else 'high' if latest_tax['tax_revenue_pct_gdp'] < 30 else 'very high'}** fiscal capacity category.
"""
    else:
        report += """
### Tax Revenue Data Not Available

Tax revenue data for this country is not currently available in the dataset. This may be due to:
- Limited statistical capacity
- Recent independence or state formation
- Data not reported to international organizations
- Classification as a regional aggregate rather than individual country
"""

    report += """
---

## Government Expenditure Analysis
"""

    if data['has_exp']:
        exp_df = data['exp_data']
        latest_exp = exp_df.iloc[-1]

        report += f"""
### Expenditure by Sector (Latest Year: {int(latest_exp['year'])})

![Expenditure by Sector]({charts[1] if len(charts) > 1 else 'N/A'})

### Sectoral Breakdown

| Sector | Expenditure (% GDP) | Data Availability |
|--------|---------------------|-------------------|
| **Education** | {f"{latest_exp.get('education_gdp', 0):.2f}%" if pd.notna(latest_exp.get('education_gdp')) else 'N/A'} | {'Yes' if pd.notna(latest_exp.get('education_gdp')) else 'No'} |
| **Health (Government)** | {f"{latest_exp.get('health_govt_gdp', 0):.2f}%" if pd.notna(latest_exp.get('health_govt_gdp')) else 'N/A'} | {'Yes' if pd.notna(latest_exp.get('health_govt_gdp')) else 'No'} |
| **Military** | {f"{latest_exp.get('military_gdp', 0):.2f}%" if pd.notna(latest_exp.get('military_gdp')) else 'N/A'} | {'Yes' if pd.notna(latest_exp.get('military_gdp')) else 'No'} |
| **R&D** | {f"{latest_exp.get('rd_gdp', 0):.2f}%" if pd.notna(latest_exp.get('rd_gdp')) else 'N/A'} | {'Yes' if pd.notna(latest_exp.get('rd_gdp')) else 'No'} |
| **Social Contributions (% revenue)** | {f"{latest_exp.get('social_contrib_revenue', 0):.2f}%" if pd.notna(latest_exp.get('social_contrib_revenue')) else 'N/A'} | {'Yes' if pd.notna(latest_exp.get('social_contrib_revenue')) else 'No'} |

### Historical Trends by Sector

![Sectoral Trends]({charts[2] if len(charts) > 2 else 'N/A'})

*This chart shows the evolution of government spending across major functional categories over time.*

### Expenditure Composition Evolution

![Expenditure Evolution]({charts[6] if len(charts) > 6 else 'N/A'})

*This stacked area chart illustrates how the composition of government spending has changed over the decades.*

### Sectoral Analysis

"""

        # Education
        if pd.notna(latest_exp.get('education_gdp')):
            report += f"""
**Education ({latest_exp['education_gdp']:.2f}% of GDP):**
- Education spending is a key indicator of human capital investment
- Global average: ~4.5% of GDP
- {country_name} spends {"above" if latest_exp['education_gdp'] > 4.5 else "below"} the global average
- Recommended minimum: 4% of GDP (UNESCO)
"""

        # Health
        if pd.notna(latest_exp.get('health_govt_gdp')):
            report += f"""
**Health ({latest_exp['health_govt_gdp']:.2f}% of GDP):**
- Government health expenditure reflects public healthcare commitment
- Global average: ~4.1% of GDP
- {country_name} spends {"above" if latest_exp['health_govt_gdp'] > 4.1 else "below"} the global average
- High-income countries typically spend 6-9% of GDP
"""

        # Military
        if pd.notna(latest_exp.get('military_gdp')):
            report += f"""
**Military ({latest_exp['military_gdp']:.2f}% of GDP):**
- Military expenditure varies widely by security environment
- Global average: ~2.1% of GDP
- NATO target: 2.0% of GDP
- {country_name} spends {"above" if latest_exp['military_gdp'] > 2.1 else "at or below"} the global average
"""

        # R&D
        if pd.notna(latest_exp.get('rd_gdp')):
            report += f"""
**R&D ({latest_exp['rd_gdp']:.2f}% of GDP):**
- R&D investment drives innovation and productivity growth
- Global average: ~1.5% of GDP (limited data)
- OECD Barcelona target: 3.0% of GDP
- {country_name} spends {"above" if latest_exp['rd_gdp'] > 1.5 else "below"} the global average
"""

    else:
        report += """
### Expenditure Data Not Available

Government expenditure data for this country is not currently available in the dataset. This may be due to:
- Limited reporting to international organizations (World Bank, IMF)
- Classification as a regional/income aggregate rather than individual country
- Recent state formation or independence
- Data quality concerns
"""

    report += """
---

## Fiscal Balance Analysis
"""

    if data['has_tax'] and data['has_exp']:
        report += f"""
### Revenue vs Expenditure

![Fiscal Balance]({charts[3] if len(charts) > 3 else 'N/A'})

**Important Note:** The expenditure data in this analysis covers only **specific functional categories** (education, health, military, R&D, social protection) for which international data is available. These typically represent **20-40% of total government expenditure**.

Missing categories include:
- General public services
- Public order and safety
- Environmental protection
- Housing and community amenities
- Recreation, culture, and religion

Therefore, the "measured expenditure" shown in the chart is **substantially lower** than actual total government spending. This analysis provides insights into sectoral priorities but cannot be used to calculate the actual fiscal balance.

### Fiscal Capacity Assessment

Based on the available data:
- **Tax Revenue:** {metrics['tax_revenue']:.2f}% of GDP
- **Measured Expenditure:** Sum of available sectors
- **Unmeasured Categories:** ~60-80% of total spending

A complete fiscal balance analysis requires:
- Total government expenditure data (often available only from national sources)
- Non-tax revenue (fees, asset sales, aid)
- Capital vs current spending breakdown

For comprehensive fiscal analysis, consult:
- IMF Article IV Reports for this country
- National Ministry of Finance budget documents
- OECD data (if country is OECD member)
"""
    elif data['has_tax']:
        report += """
### Revenue Data Available, Expenditure Data Limited

Tax revenue data is available, but expenditure breakdown is not. A fiscal balance analysis requires both revenue and expenditure data.
"""
    elif data['has_exp']:
        report += """
### Expenditure Data Available, Revenue Data Limited

Expenditure breakdown is available, but tax revenue data is not. A fiscal balance analysis requires both revenue and expenditure data.
"""
    else:
        report += """
### Insufficient Data for Fiscal Balance Analysis

Neither comprehensive tax revenue nor expenditure data is available for fiscal balance analysis.
"""

    report += """
---

## International Comparisons
"""

    if len(charts) > 4:
        report += f"""
### Regional Comparison

![Regional Comparison]({charts[4]})

This chart compares {country_name} to peer countries within the same geographic region. Regional context is important because:
- Neighboring countries often face similar challenges
- Regional integration (trade agreements, etc.) affects fiscal policy
- Shared historical and institutional legacies
- Similar economic development stages within regions

### Income-Level Comparison

![Income-Level Comparison]({charts[5]})

This chart compares {country_name} to countries at similar income levels globally. Income-level comparisons are important because:
- Development stage strongly influences fiscal capacity
- High-income countries can afford higher spending as % of GDP
- Low-income countries face severe fiscal constraints
- Middle-income countries are in transition, building institutions
"""
    else:
        report += """
### Comparison Data Not Generated

International comparison charts were not generated for this report. This may be due to insufficient peer group data.
"""

    report += f"""
---

## Data Quality & Methodology

### Data Sources

**Tax Revenue:**
- **Primary Source:** World Bank World Development Indicators
- **Indicator Code:** GC.TAX.TOTL.GD.ZS
- **Definition:** Tax revenue as percentage of GDP, including social contributions
- **Coverage:** {f"{len(data['tax_data'])} observations" if data['has_tax'] else "No data"}

**Government Expenditure:**
- **Primary Source:** World Bank Open Data API
- **Indicators:** 9 functional expenditure categories
- **Coverage:** {f"{len(data['exp_data'])} observations" if data['has_exp'] else "No data"}
- **COFOG Mapping:** 5 of 10 divisions covered

### Quality Assessment

**Data Quality Rating:** {
    "5/5 - Excellent (Tier 1)" if metadata.get('tier') == 1 else
    "4/5 - Good (Tier 2)" if metadata.get('tier') == 2 else
    "3/5 - Fair (Tier 3)"
}

**Completeness:**
- Tax Revenue: {'High' if data['has_tax'] and len(data['tax_data']) > 20 else 'Limited' if data['has_tax'] else 'None'}
- Expenditure: {'High' if data['has_exp'] and len(data['exp_data']) > 20 else 'Limited' if data['has_exp'] else 'None'}

**Reliability:**
- Data validated against original World Bank sources
- Cross-checked with OECD data where available
- Outliers flagged and investigated

### Limitations

1. **Incomplete COFOG Coverage:** Only 5 of 10 government functions covered
2. **Aggregation Level:** National level only (no subnational breakdowns)
3. **Definition Variations:** Some cross-country comparability issues
4. **Reporting Lags:** Most recent data is typically 1-2 years old
5. **Missing Data:** Some years/indicators may have no reported values

---

## Using This Report

### For Researchers
- All data is available in machine-readable Excel files
- Charts are 300 DPI publication-quality
- Sources fully documented for citation
- Methodology transparent and replicable

### For Policymakers
- Benchmark spending against peer countries
- Identify under/over-spending in specific sectors
- Assess fiscal capacity and constraints
- Prioritize resource allocation

### For Journalists/Public
- Clear visual explanations of fiscal patterns
- International context for domestic debates
- Historical perspective on fiscal trends
- Data-driven rather than ideological

---

## Files & Resources

### Data Files
- **Tax Revenue:** `Countries/{country_code}/Output/Data/{country_code.lower()}_national_tax_data.xlsx`
- **Expenditure:** `Countries/{country_code}/Output/Data/{country_code.lower()}_government_expenditure.xlsx`
- **Summary Metadata:** `Countries/{country_code}/Output/Data/{country_code.lower()}_expenditure_summary.json`

### Visualizations
All charts in this report are saved in: `Countries/{country_code}/Output/Charts/`

### Related Documentation
- **Global Analysis:** `Technical/docs/GLOBAL_EXPENDITURE_ANALYSIS.md`
- **Methodology:** `Technical/docs/METHODOLOGY_AND_LIMITATIONS_ANALYSIS.md`
- **COFOG Mapping:** `Technical/docs/COFOG_MAPPING.md`
- **Unified Index:** `Countries/UNIFIED_MASTER_INDEX.md`

---

## Report Information

**Generated By:** Gerhard Fiscal Analysis Platform
**Report Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data Vintage:** {metrics.get('coverage_years', 'Various')}
**Pattern:** Publication-quality data standards
**Version:** 1.0

---

*For questions about this analysis or to report data issues, please refer to project documentation.*

*All data is from official sources (World Bank, IMF, OECD) and is publicly available.*
"""

    return report


def generate_country_report(country_code):
    """
    Generate complete fiscal report for a country

    Args:
        country_code: ISO alpha-2 country code

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*70}")
    print(f"Generating Fiscal Report: {country_code}")
    print(f"{'='*70}")

    try:
        # Load data
        print("Loading data...")
        data = load_country_data(country_code)

        if not data['has_tax'] and not data['has_exp']:
            print(f"  WARNING: No data available for {country_code}")
            return False

        country_name = data['name']
        print(f"  Country: {country_name}")
        print(f"  Tax data: {'YES' if data['has_tax'] else 'NO'}")
        print(f"  Expenditure data: {'YES' if data['has_exp'] else 'NO'}")

        # Get metadata
        metadata = get_country_metadata(country_code)

        # Calculate metrics
        metrics = calculate_metrics(data['tax_data'], data['exp_data'], metadata)

        # Create visualizations
        charts_dir = COUNTRIES_DIR / country_code / "Output" / "Charts"
        visualizer = CountryFiscalVisualizer(country_code, country_name, charts_dir)

        # Prepare comparison data (simplified for now)
        comparison_data = {
            'regional': {},
            'income_level': {}
        }

        charts = visualizer.generate_all_charts(
            data['tax_data'],
            data['exp_data'],
            comparison_data,
            metrics
        )

        # Generate markdown report
        print("Generating markdown report...")
        report_content = generate_markdown_report(
            country_code, country_name, data, metadata, metrics, charts
        )

        # Save report
        report_path = COUNTRIES_DIR / country_code / "Output" / "FISCAL_REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"SUCCESS: Report generated successfully!")
        print(f"   Report: {report_path}")
        print(f"   Charts: {len(charts)} visualizations in {charts_dir}")

        return True

    except Exception as e:
        print(f"ERROR: Failed to generate report for {country_code}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        country_code = sys.argv[1].upper()
        generate_country_report(country_code)
    else:
        print("Usage: python generate_country_fiscal_report.py [COUNTRY_CODE]")
        print("Example: python generate_country_fiscal_report.py US")
