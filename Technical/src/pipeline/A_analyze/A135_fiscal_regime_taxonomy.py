#!/usr/bin/env python3
"""
A135: Fiscal Regime Taxonomy
Classify countries into fiscal regime types using tax structure, expenditure,
resource dependence, and development indicators.
Stage: A | ID: A135
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A135",
    "name": "Fiscal Regime Taxonomy",
    "stage": "A",
    "description": "Classify countries into fiscal regime types based on tax, expenditure, and structural features",
    "depends_on": ["A88", "P65", "P70"],
    "inputs": [
        {"path": "Output/Data/fiscal_clusters.xlsx", "required": True},
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/expenditure_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/trade_panel.xlsx", "required": True},
        {"path": "Output/Data/national_accounts_panel.xlsx", "required": True},
        {"path": "Output/Data/social_outcomes_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/fiscal_regime_taxonomy.xlsx"},
        {"path": "Output/Data/regime_summary_statistics.xlsx"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}


def classify_regime(row):
    """Decision-tree classification of fiscal regime type."""
    tax = row.get('tax_pct_gdp', 0) or 0
    social = row.get('cofog_social_protection', 0) or 0
    fuel = row.get('fuel_exports_pct', 0) or 0
    agri = row.get('agriculture_pct_gdp', 0) or 0
    debt = row.get('debt_pct_gdp', 0) or 0
    manuf = row.get('manufactures_exports_pct', 0) or 0

    if tax > 30 and social > 15:
        return 'Nordic Welfare'
    elif tax > 25 and social > 8:
        return 'Continental European'
    elif 15 <= tax <= 25 and manuf > 40:
        return 'Anglo-Saxon Liberal'
    elif tax > 18 and agri < 10 and fuel < 15:
        return 'Developmental'
    elif tax < 10 and fuel > 25:
        return 'Petro-State'
    elif tax < 15 and agri > 15:
        return 'Agrarian Developing'
    elif tax > 10 and debt > 80:
        return 'Debt-Constrained'
    else:
        return 'Mixed/Transitional'


def get_latest_value(df, cc, col):
    """Get most recent non-null value for a country."""
    sub = df[df['country_code'] == cc].dropna(subset=[col]).sort_values('year', ascending=False)
    if sub.empty:
        return np.nan
    return sub.iloc[0][col]


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    # Load data
    clusters = read_excel_safe(out / "fiscal_clusters.xlsx")
    rev_comp = read_excel_safe(out / "revenue_composition_panel.xlsx")
    exp_comp = read_excel_safe(out / "expenditure_composition_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    trade = read_excel_safe(out / "trade_panel.xlsx")
    natl = read_excel_safe(out / "national_accounts_panel.xlsx")
    social = read_excel_safe(out / "social_outcomes_panel.xlsx")

    if clusters.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    # Get unique countries from clusters
    countries = clusters[['country_code', 'country_name', 'cluster_id', 'cluster_name',
                          'region', 'income_group']].copy()
    logger.info(f"Building taxonomy for {len(countries)} countries")

    # Build classification features for each country (latest available year)
    records = []
    for _, crow in countries.iterrows():
        cc = crow['country_code']
        rec = {
            'country_code': cc,
            'country_name': crow['country_name'],
            'cluster_id': crow.get('cluster_id'),
            'cluster_name': crow.get('cluster_name'),
            'region': crow.get('region'),
            'income_group': crow.get('income_group'),
        }

        # From master
        rec['tax_pct_gdp'] = get_latest_value(master, cc, 'tax_revenue_pct_gdp')
        rec['expenditure_pct_gdp'] = get_latest_value(master, cc, 'expenditure_pct_gdp')
        rec['debt_pct_gdp'] = get_latest_value(master, cc, 'debt_pct_gdp')
        rec['gdp_per_capita_ppp'] = get_latest_value(master, cc, 'gdp_per_capita_ppp')

        # From revenue composition
        rec['income_tax_pct_revenue'] = get_latest_value(rev_comp, cc, 'income_tax_pct_revenue')
        rec['goods_services_tax_pct_revenue'] = get_latest_value(rev_comp, cc, 'goods_services_tax_pct_revenue')
        rec['trade_tax_pct_revenue'] = get_latest_value(rev_comp, cc, 'trade_tax_pct_revenue')

        # From expenditure composition
        rec['cofog_social_protection'] = get_latest_value(exp_comp, cc, 'cofog_social_protection')

        # From trade
        rec['fuel_exports_pct'] = get_latest_value(trade, cc, 'fuel_exports_pct')
        rec['manufactures_exports_pct'] = get_latest_value(trade, cc, 'manufactures_exports_pct')

        # From national accounts
        rec['agriculture_pct_gdp'] = get_latest_value(natl, cc, 'agriculture_pct_gdp')

        # From social outcomes
        if not social.empty:
            rec['gini'] = get_latest_value(social, cc, 'gini_coefficient')

        records.append(rec)

    taxonomy = pd.DataFrame(records)

    # Apply classification
    taxonomy['fiscal_regime'] = taxonomy.apply(classify_regime, axis=1)

    # Log regime distribution
    regime_counts = taxonomy['fiscal_regime'].value_counts()
    logger.info(f"Regime distribution:\n{regime_counts.to_string()}")

    # Save taxonomy
    write_single_sheet_excel(taxonomy, out / "fiscal_regime_taxonomy.xlsx", sheet_name="Regime Taxonomy")

    # Build summary statistics per regime
    summary_cols = ['tax_pct_gdp', 'expenditure_pct_gdp', 'debt_pct_gdp',
                    'gdp_per_capita_ppp', 'agriculture_pct_gdp', 'fuel_exports_pct']
    if 'gini' in taxonomy.columns:
        summary_cols.append('gini')

    summaries = []
    for regime, grp in taxonomy.groupby('fiscal_regime'):
        rec = {'fiscal_regime': regime, 'n_countries': len(grp)}
        for col in summary_cols:
            vals = grp[col].dropna()
            rec[f'{col}_mean'] = round(vals.mean(), 2) if len(vals) > 0 else np.nan
            rec[f'{col}_median'] = round(vals.median(), 2) if len(vals) > 0 else np.nan
            rec[f'{col}_std'] = round(vals.std(), 2) if len(vals) > 1 else np.nan
        summaries.append(rec)

    summary_df = pd.DataFrame(summaries).sort_values('n_countries', ascending=False)
    write_single_sheet_excel(summary_df, out / "regime_summary_statistics.xlsx",
                             sheet_name="Regime Summary")

    logger.info(f"[{MANIFEST['id']}] Complete: {len(taxonomy)} countries classified into "
                f"{taxonomy['fiscal_regime'].nunique()} regimes")


if __name__ == "__main__":
    run()
