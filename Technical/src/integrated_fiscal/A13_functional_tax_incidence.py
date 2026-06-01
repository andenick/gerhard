"""
A13: Functional Tax Incidence — Who Really Pays: Labor vs Capital
=================================================================
Classifies OECD tax revenue by functional incidence (labor/capital/consumption)
and tests whether the tax burden shifted from capital to labor as profit rates fell.

Data: OECD Revenue Stats (41 countries, 95 categories, 1965-2023) + PWT profit rates
Output: Output/Data/integrated_fiscal/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
from pathlib import Path
import sys
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

OECD_DIR = raw_data_dir() / "oecd" / "revenue_stats"
PWT_DIR = raw_data_dir() / "profit_rates"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OECD tax category → functional incidence classification
# T_1000 = Taxes on income, profits, capital gains
# T_1100 = Individual income tax (MIXED: wages + capital income)
# T_1200 = Corporate income tax (CAPITAL)
# T_2000 = Social security contributions (LABOR)
# T_3000 = Taxes on payroll/workforce (LABOR)
# T_4000 = Taxes on property (MIXED)
# T_5000 = Taxes on goods and services (CONSUMPTION)
# T_6000 = Other taxes

INCIDENCE_MAP = {
    # LABOR (clearly borne by workers)
    'T_2000': ('LABOR', 1.0),      # Social security contributions (total)
    'T_2100': ('LABOR', 1.0),      # Employee SSC
    'T_2200': ('LABOR', 1.0),      # Employer SSC (shifted to wages)
    'T_2300': ('LABOR', 0.7),      # Self-employed/non-employed SSC
    'T_3000': ('LABOR', 1.0),      # Payroll taxes

    # CAPITAL (clearly borne by capital owners)
    'T_1200': ('CAPITAL', 1.0),    # Corporate income tax
    'T_1210': ('CAPITAL', 1.0),    # Corporate tax on profits
    'T_1220': ('CAPITAL', 1.0),    # Corporate tax on capital gains
    'T_4200': ('CAPITAL', 1.0),    # Net wealth taxes
    'T_4300': ('CAPITAL', 1.0),    # Estate/inheritance/gift taxes
    'T_4400': ('CAPITAL', 1.0),    # Financial/capital transaction taxes
    'T_4500': ('CAPITAL', 1.0),    # Other non-recurrent property taxes

    # MIXED — personal income tax (split: 75% labor, 25% capital)
    'T_1100': ('MIXED_INCOME', 0.75),  # Individual income tax total
    'T_1110': ('MIXED_INCOME', 0.75),  # On income/profits
    'T_1120': ('MIXED_INCOME', 0.25),  # On capital gains (→ CAPITAL portion)

    # MIXED — property (split: 60% labor/housing, 40% capital/wealth)
    'T_4000': ('MIXED_PROPERTY', 0.6),  # Property taxes total
    'T_4100': ('MIXED_PROPERTY', 0.6),  # Recurrent on immovable property
    'T_4310': ('CAPITAL', 1.0),         # Estate taxes
    'T_4320': ('CAPITAL', 1.0),         # Gift taxes

    # CONSUMPTION (borne by consumers — workers in long run)
    'T_5000': ('CONSUMPTION', 1.0),    # Goods and services total
    'T_5100': ('CONSUMPTION', 1.0),    # On production/sale/transfer
    'T_5110': ('CONSUMPTION', 1.0),    # General (VAT/sales)
    'T_5111': ('CONSUMPTION', 1.0),    # VAT
    'T_5120': ('CONSUMPTION', 1.0),    # Excise/specific
    'T_5130': ('CONSUMPTION', 1.0),    # Customs/import duties
    'T_5200': ('CONSUMPTION', 1.0),    # On use of goods
    'T_5300': ('CONSUMPTION', 1.0),    # Unallocable goods/services

    # Other
    'T_6000': ('OTHER', 1.0),          # Other taxes
}

# Aggregates (don't double-count)
AGGREGATE_CODES = {'T_1000', 'T_4000', 'T_5000', 'T_2000', 'T_AI', 'T_AB', 'T_AD', 'T_TOT'}


def load_oecd_revenue() -> pd.DataFrame:
    """Load parsed OECD revenue panel."""
    fpath = OECD_DIR / "oecd_revenue_panel.parquet"
    if not fpath.exists():
        logger.error(f"OECD panel not found: {fpath}. Run parse_oecd_revenue.py first.")
        return pd.DataFrame()

    df = pd.read_parquet(fpath)
    # Filter to % GDP unit and total general government
    if 'unit' in df.columns:
        # Find % GDP unit code
        units = df['unit'].unique()
        gdp_units = [u for u in units if 'GDP' in str(u).upper() or 'PC_GDP' in str(u)]
        if gdp_units:
            df = df[df['unit'].isin(gdp_units)]
            logger.info(f"Filtered to GDP units ({gdp_units}): {len(df):,} rows")
        else:
            logger.info(f"Available units: {units}")
            # Use all, or try first unit
            if len(units) > 1:
                df = df[df['unit'] == units[0]]

    if 'gov_level' in df.columns:
        # Total general government (S13 or GEN or similar)
        gov_levels = df['gov_level'].unique()
        total_levels = [g for g in gov_levels if any(k in str(g).upper() for k in ['S13', 'GEN', 'TOT', 'NES'])]
        if total_levels:
            df = df[df['gov_level'].isin(total_levels)]
            logger.info(f"Filtered to total govt ({total_levels[:3]}): {len(df):,} rows")

    logger.info(f"OECD revenue: {len(df):,} rows, {df['country_code'].nunique()} countries, "
               f"{df['year'].min()}-{df['year'].max()}")
    return df


def load_pwt_profit() -> pd.DataFrame:
    """Load PWT profit rate panel."""
    fpath = PWT_DIR / "pwt_profit_rate_panel.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_parquet(fpath)
    df = df.rename(columns={'countrycode': 'country_code'})
    return df[['country_code', 'year', 'labsh', 'irr']].dropna(subset=['labsh'])


def compute_functional_incidence(oecd: pd.DataFrame) -> pd.DataFrame:
    """Classify each country-year's tax revenue by functional incidence."""
    if oecd.empty:
        return pd.DataFrame()

    # Only use non-aggregate tax categories
    detail_codes = set(INCIDENCE_MAP.keys()) - AGGREGATE_CODES
    detail = oecd[oecd['tax_category'].isin(detail_codes)].copy()

    if detail.empty:
        # Try with whatever categories we have
        available = set(oecd['tax_category'].unique()) & set(INCIDENCE_MAP.keys())
        detail = oecd[oecd['tax_category'].isin(available)].copy()
        logger.info(f"Using {len(available)} available categories: {sorted(available)[:10]}")

    results = []
    for (country, year), grp in detail.groupby(['country_code', 'year']):
        labor_tax = 0
        capital_tax = 0
        consumption_tax = 0
        mixed_tax = 0
        total_classified = 0

        for _, row in grp.iterrows():
            cat = row['tax_category']
            val = row['value']
            if pd.isna(val) or val == 0:
                continue

            if cat in INCIDENCE_MAP:
                incidence_type, weight = INCIDENCE_MAP[cat]
                if incidence_type == 'LABOR':
                    labor_tax += val * weight
                elif incidence_type == 'CAPITAL':
                    capital_tax += val
                elif incidence_type == 'CONSUMPTION':
                    consumption_tax += val
                elif incidence_type == 'MIXED_INCOME':
                    labor_tax += val * weight  # 75% to labor
                    capital_tax += val * (1 - weight)  # 25% to capital
                elif incidence_type == 'MIXED_PROPERTY':
                    labor_tax += val * weight  # 60% to labor (housing)
                    capital_tax += val * (1 - weight)  # 40% to capital
                else:
                    mixed_tax += val
                total_classified += val

        if total_classified > 0:
            total = labor_tax + capital_tax + consumption_tax + mixed_tax
            results.append({
                'country_code': country,
                'year': year,
                'labor_tax_gdp': labor_tax,
                'capital_tax_gdp': capital_tax,
                'consumption_tax_gdp': consumption_tax,
                'total_classified_gdp': total,
                'labor_tax_share': labor_tax / total if total > 0 else np.nan,
                'capital_tax_share': capital_tax / total if total > 0 else np.nan,
                'consumption_tax_share': consumption_tax / total if total > 0 else np.nan,
                # Shaikh interpretation: consumption ultimately borne by workers
                'shaikh_labor_burden': (labor_tax + consumption_tax) / total if total > 0 else np.nan,
                'shaikh_capital_burden': capital_tax / total if total > 0 else np.nan,
            })

    df = pd.DataFrame(results)
    logger.info(f"Functional incidence: {len(df):,} country-years, {df['country_code'].nunique()} countries")
    return df


def analyze_incidence_trends(incidence: pd.DataFrame) -> pd.DataFrame:
    """Compute trends in tax incidence over time."""
    if incidence.empty:
        return pd.DataFrame()

    results = []
    for country, grp in incidence.groupby('country_code'):
        grp = grp.sort_values('year')
        if len(grp) < 10:
            continue

        row = {'country_code': country, 'n_years': len(grp)}

        # Early vs late comparison
        mid_year = grp['year'].median()
        early = grp[grp['year'] <= mid_year]
        late = grp[grp['year'] > mid_year]

        for col in ['labor_tax_share', 'capital_tax_share', 'consumption_tax_share',
                   'shaikh_labor_burden', 'shaikh_capital_burden']:
            if col in grp.columns:
                row[f'{col}_early'] = early[col].mean()
                row[f'{col}_late'] = late[col].mean()
                row[f'{col}_change'] = late[col].mean() - early[col].mean()

                # Trend (slope per year)
                valid = grp[['year', col]].dropna()
                if len(valid) >= 10:
                    slope = np.polyfit(valid['year'], valid[col], 1)[0]
                    row[f'{col}_trend_per_year'] = slope

        results.append(row)

    return pd.DataFrame(results)


def cross_with_profit_rate(incidence: pd.DataFrame, pwt: pd.DataFrame) -> pd.DataFrame:
    """Test: does declining profit rate correlate with tax burden shift?"""
    if incidence.empty or pwt.empty:
        return pd.DataFrame()

    merged = incidence.merge(pwt, on=['country_code', 'year'], how='inner')
    if merged.empty:
        logger.warning("No overlap between incidence and PWT data")
        return pd.DataFrame()

    logger.info(f"Merged incidence+PWT: {len(merged)} rows, {merged['country_code'].nunique()} countries")

    results = []
    for country, grp in merged.groupby('country_code'):
        grp = grp.sort_values('year').dropna(subset=['irr', 'capital_tax_share'])
        if len(grp) < 10:
            continue

        row = {'country_code': country, 'n_years': len(grp)}

        # Levels correlation
        row['corr_irr_capital_share'] = grp['irr'].corr(grp['capital_tax_share'])
        row['corr_irr_labor_share'] = grp['irr'].corr(grp['labor_tax_share'])
        row['corr_labsh_labor_tax'] = grp['labsh'].corr(grp['labor_tax_share'])

        # Changes correlation
        changes = grp[['irr', 'capital_tax_share', 'labor_tax_share', 'labsh']].diff().dropna()
        if len(changes) > 8:
            row['corr_dirr_dcapital_share'] = changes['irr'].corr(changes['capital_tax_share'])
            row['corr_dirr_dlabor_share'] = changes['irr'].corr(changes['labor_tax_share'])

        # Key test: when labor share falls, does labor TAX share rise?
        if 'labsh' in grp.columns and 'labor_tax_share' in grp.columns:
            valid = grp[['labsh', 'labor_tax_share']].dropna()
            if len(valid) > 10:
                slope, _, r, p, _ = stats.linregress(valid['labsh'], valid['labor_tax_share'])
                row['h3_slope'] = slope  # H3: negative slope = burden shifts to labor as wages fall
                row['h3_r2'] = r ** 2
                row['h3_p'] = p
                row['h3_confirmed'] = slope < 0 and p < 0.05

        results.append(row)

    return pd.DataFrame(results)


def compute_era_comparison(incidence: pd.DataFrame) -> pd.DataFrame:
    """Compare tax incidence across fiscal eras."""
    if incidence.empty:
        return pd.DataFrame()

    eras = {
        'pre_neoliberal': (1965, 1979),
        'early_neoliberal': (1980, 1995),
        'late_neoliberal': (1996, 2007),
        'post_gfc': (2008, 2023),
    }

    results = []
    for era_name, (start, end) in eras.items():
        era_data = incidence[(incidence['year'] >= start) & (incidence['year'] <= end)]
        if era_data.empty:
            continue

        row = {'era': era_name, 'start': start, 'end': end, 'n_obs': len(era_data)}
        for col in ['labor_tax_share', 'capital_tax_share', 'consumption_tax_share',
                   'shaikh_labor_burden', 'shaikh_capital_burden',
                   'labor_tax_gdp', 'capital_tax_gdp']:
            if col in era_data.columns:
                row[f'{col}_mean'] = era_data[col].mean()
                row[f'{col}_median'] = era_data[col].median()

        results.append(row)

    return pd.DataFrame(results)


def run() -> dict:
    """Execute functional tax incidence analysis."""
    logger.info("=" * 80)
    logger.info("A13: FUNCTIONAL TAX INCIDENCE — WHO REALLY PAYS")
    logger.info("=" * 80)

    oecd = load_oecd_revenue()
    if oecd.empty:
        logger.error("No OECD data. Run parse_oecd_revenue.py first.")
        return {}

    # Compute functional incidence
    incidence = compute_functional_incidence(oecd)
    if incidence.empty:
        logger.error("Could not compute incidence")
        return {}

    write_single_sheet_excel(incidence, OUTPUT_DIR / "A13_functional_incidence_panel.xlsx", "Incidence")
    logger.info(f"Wrote incidence panel: {len(incidence)} rows")

    # Trends
    trends = analyze_incidence_trends(incidence)
    if not trends.empty:
        write_single_sheet_excel(trends, OUTPUT_DIR / "A13_incidence_trends.xlsx", "Trends")
        # Key finding: average shift
        if 'capital_tax_share_change' in trends.columns:
            avg_cap_change = trends['capital_tax_share_change'].mean()
            avg_labor_change = trends['labor_tax_share_change'].mean()
            logger.info(f"Average capital tax share change: {avg_cap_change:+.3f}")
            logger.info(f"Average labor tax share change: {avg_labor_change:+.3f}")

    # Cross with profit rate
    pwt = load_pwt_profit()
    profit_cross = cross_with_profit_rate(incidence, pwt)
    if not profit_cross.empty:
        write_single_sheet_excel(profit_cross, OUTPUT_DIR / "A13_incidence_vs_profit.xlsx", "ProfitCross")
        if 'h3_confirmed' in profit_cross.columns:
            n_confirmed = profit_cross['h3_confirmed'].sum()
            logger.info(f"H3 (labor share↓ → labor tax share↑): confirmed in "
                       f"{n_confirmed}/{len(profit_cross)} countries")

    # Era comparison
    era = compute_era_comparison(incidence)
    if not era.empty:
        write_single_sheet_excel(era, OUTPUT_DIR / "A13_era_comparison.xlsx", "Eras")
        logger.info("Era comparison:")
        for _, row in era.iterrows():
            logger.info(f"  {row['era']:20s}: labor={row.get('labor_tax_share_mean',0):.1%} "
                       f"capital={row.get('capital_tax_share_mean',0):.1%} "
                       f"consumption={row.get('consumption_tax_share_mean',0):.1%}")

    logger.info("A13 COMPLETE")
    return {'incidence_rows': len(incidence), 'countries': incidence['country_code'].nunique()}


if __name__ == "__main__":
    run()
