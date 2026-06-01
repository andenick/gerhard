#!/usr/bin/env python3
"""
A140: Policy Impact via Difference-in-Differences
Estimate causal effects of fiscal structural breaks using DiD with region/income controls.
Stage: A | ID: A140
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
    "id": "A140",
    "name": "Policy Impact DiD",
    "stage": "A",
    "description": "Estimate causal effects of fiscal structural breaks using difference-in-differences",
    "depends_on": ["A80"],
    "inputs": [
        {"path": "Output/Data/structural_breaks.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/Data/policy_impact_did_results.xlsx"},
        {"path": "Output/Data/policy_impact_summary.xlsx"},
    ],
    "timeout": 180,
    "parallel_safe": True,
}


def estimate_did(treatment_cc, break_year, control_ccs, panel, outcome_col):
    """Estimate difference-in-differences for a single event."""
    pre = panel[(panel['year'] >= break_year - 5) & (panel['year'] < break_year)]
    post = panel[(panel['year'] >= break_year) & (panel['year'] < break_year + 5)]

    treat_pre = pre[pre['country_code'] == treatment_cc][outcome_col].mean()
    treat_post = post[post['country_code'] == treatment_cc][outcome_col].mean()
    ctrl_pre = pre[pre['country_code'].isin(control_ccs)][outcome_col].mean()
    ctrl_post = post[post['country_code'].isin(control_ccs)][outcome_col].mean()

    # Check for sufficient data
    if any(np.isnan(v) for v in [treat_pre, treat_post, ctrl_pre, ctrl_post]):
        return np.nan, {}

    did = (treat_post - treat_pre) - (ctrl_post - ctrl_pre)

    details = {
        'treat_pre': round(treat_pre, 4),
        'treat_post': round(treat_post, 4),
        'ctrl_pre': round(ctrl_pre, 4),
        'ctrl_post': round(ctrl_post, 4),
        'treat_change': round(treat_post - treat_pre, 4),
        'ctrl_change': round(ctrl_post - ctrl_pre, 4),
        'n_controls': len(control_ccs),
    }
    return round(did, 4), details


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    breaks = read_excel_safe(out / "structural_breaks.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")

    if breaks.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    # Compute GDP growth
    master = master.sort_values(['country_code', 'year'])
    master['gdp_growth'] = master.groupby('country_code')['gdp_constant_2015_usd'].pct_change() * 100

    # Filter significant breaks
    sig_breaks = breaks[
        (breaks['change_magnitude'].abs() > 2) &
        (breaks['p_value'] < 0.05)
    ].copy()
    logger.info(f"Significant breaks: {len(sig_breaks)} of {len(breaks)} total")

    if sig_breaks.empty:
        logger.warning("No significant breaks found; relaxing threshold")
        sig_breaks = breaks[breaks['p_value'] < 0.10].copy()

    # Build set of break events by country for exclusion
    break_events = {}
    for _, row in breaks.iterrows():
        cc = row['country_code']
        by = row['break_year']
        if cc not in break_events:
            break_events[cc] = []
        break_events[cc].append(by)

    # Outcomes to test
    outcomes = ['tax_revenue_pct_gdp', 'gdp_growth']

    # Run DiD for each break x outcome
    results = []
    for _, brk in sig_breaks.iterrows():
        treat_cc = brk['country_code']
        break_year = int(brk['break_year'])

        # Get treatment country's region and income group
        treat_info = master[master['country_code'] == treat_cc].iloc[0] if len(master[master['country_code'] == treat_cc]) > 0 else None
        if treat_info is None:
            continue
        treat_region = treat_info.get('region', '')
        treat_ig = treat_info.get('income_group', '')

        # Find control countries: same region + income group, no break within +-3 years
        same_group = master[
            (master['region'] == treat_region) &
            (master['income_group'] == treat_ig) &
            (master['country_code'] != treat_cc)
        ]['country_code'].unique()

        control_ccs = []
        for cc in same_group:
            cc_breaks = break_events.get(cc, [])
            has_nearby_break = any(abs(by - break_year) <= 3 for by in cc_breaks)
            if not has_nearby_break:
                control_ccs.append(cc)

        if len(control_ccs) < 2:
            # Fall back to same region only
            same_region = master[
                (master['region'] == treat_region) &
                (master['country_code'] != treat_cc)
            ]['country_code'].unique()
            control_ccs = [cc for cc in same_region
                           if not any(abs(by - break_year) <= 3 for by in break_events.get(cc, []))]

        if len(control_ccs) < 2:
            continue

        for outcome in outcomes:
            did, details = estimate_did(treat_cc, break_year, control_ccs, master, outcome)
            if np.isnan(did):
                continue

            results.append({
                'country_code': treat_cc,
                'country_name': brk.get('country_name', ''),
                'break_year': break_year,
                'outcome': outcome,
                'did_estimate': did,
                'change_magnitude': round(brk['change_magnitude'], 2),
                'p_value': round(brk['p_value'], 4),
                'region': treat_region,
                'income_group': treat_ig,
                **details,
            })

    results_df = pd.DataFrame(results)
    if results_df.empty:
        logger.warning("No DiD estimates produced.")
        results_df = pd.DataFrame(columns=['country_code', 'break_year', 'outcome', 'did_estimate'])

    logger.info(f"DiD estimates: {len(results_df)} event-outcome pairs")

    write_single_sheet_excel(results_df, out / "policy_impact_did_results.xlsx",
                             sheet_name="DiD Results")

    # Summary by outcome
    summary_rows = []
    if not results_df.empty:
        for outcome, grp in results_df.groupby('outcome'):
            valid = grp['did_estimate'].dropna()
            pos = (valid > 0).sum()
            neg = (valid < 0).sum()
            summary_rows.append({
                'outcome': outcome,
                'n_events': len(valid),
                'mean_did': round(valid.mean(), 3),
                'median_did': round(valid.median(), 3),
                'std_did': round(valid.std(), 3),
                'pct_positive': round(100 * pos / len(valid), 1) if len(valid) > 0 else np.nan,
                'pct_negative': round(100 * neg / len(valid), 1) if len(valid) > 0 else np.nan,
                'min_did': round(valid.min(), 3),
                'max_did': round(valid.max(), 3),
            })
            logger.info(f"  {outcome}: mean DiD = {valid.mean():.3f}, "
                        f"median = {valid.median():.3f}, n = {len(valid)}")

    summary_df = pd.DataFrame(summary_rows)
    write_single_sheet_excel(summary_df, out / "policy_impact_summary.xlsx",
                             sheet_name="DiD Summary")

    logger.info(f"[{MANIFEST['id']}] Complete: {len(results_df)} DiD estimates across "
                f"{results_df['country_code'].nunique() if not results_df.empty else 0} countries")


if __name__ == "__main__":
    run()
