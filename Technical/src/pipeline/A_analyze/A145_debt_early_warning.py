#!/usr/bin/env python3
"""
A145: Debt Early Warning System
Build logistic regression + Random Forest models to predict debt crises,
score current risk for all countries.
Stage: A | ID: A145
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A145",
    "name": "Debt Early Warning",
    "stage": "A",
    "description": "Build ML models to predict debt crises and score current risk",
    "depends_on": ["P90", "P60"],
    "inputs": [
        {"path": "Output/Data/debt_composition_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/bop_panel.xlsx", "required": False},
        {"path": "Output/Data/exchange_rate_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/Data/debt_early_warning_model.xlsx"},
        {"path": "Output/Data/debt_early_warning_diagnostics.xlsx"},
    ],
    "timeout": 300,
    "parallel_safe": True,
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    debt = read_excel_safe(out / "debt_composition_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    bop = read_excel_safe(out / "bop_panel.xlsx")
    exr = read_excel_safe(out / "exchange_rate_panel.xlsx")

    if debt.empty or master.empty:
        logger.error("Cannot load required panels; aborting.")
        return

    # Merge panels
    merged = debt.merge(master[['country_code', 'year', 'tax_revenue_pct_gdp',
                                 'expenditure_pct_gdp', 'debt_pct_gdp',
                                 'gdp_per_capita_ppp', 'fiscal_balance_pct_gdp',
                                 'region', 'income_group']],
                        on=['country_code', 'year'], how='left')

    if not bop.empty:
        merged = merged.merge(bop[['country_code', 'year', 'current_account_pct_gdp']],
                              on=['country_code', 'year'], how='left')

    if not exr.empty:
        merged = merged.merge(exr[['country_code', 'year', 'inflation_pct', 'real_depreciation']],
                              on=['country_code', 'year'], how='left')

    merged = merged.sort_values(['country_code', 'year'])

    # Compute GDP growth from master
    gdp_growth = master.sort_values(['country_code', 'year']).copy()
    gdp_growth['gdp_growth'] = gdp_growth.groupby('country_code')['gdp_per_capita_ppp'].pct_change() * 100
    merged = merged.merge(gdp_growth[['country_code', 'year', 'gdp_growth']],
                          on=['country_code', 'year'], how='left')

    # Define crisis indicator
    # Crisis = debt_pct_gni increase > 10pp in one year OR debt_service > 25% exports
    merged['debt_change_1yr'] = merged.groupby('country_code')['external_debt_pct_gni'].diff()
    merged['crisis'] = (
        (merged['debt_change_1yr'] > 10) |
        (merged['debt_service_pct_exports'] > 25)
    ).astype(int)

    # Compute 3-year debt change
    merged['debt_3yr_change'] = merged.groupby('country_code')['external_debt_pct_gni'].diff(3)

    # Feature columns
    feature_cols = ['external_debt_pct_gni', 'debt_3yr_change', 'short_term_pct_total',
                    'fiscal_balance_pct_gdp', 'gdp_growth', 'debt_service_pct_exports']
    if 'current_account_pct_gdp' in merged.columns:
        feature_cols.append('current_account_pct_gdp')
    if 'inflation_pct' in merged.columns:
        feature_cols.append('inflation_pct')

    # Drop rows missing all features or crisis label
    model_df = merged.dropna(subset=['crisis']).copy()
    model_df = model_df.dropna(subset=feature_cols, how='all')

    # Fill remaining NaN with column median
    for col in feature_cols:
        if col in model_df.columns:
            model_df[col] = model_df[col].fillna(model_df[col].median())

    # Remove any remaining NaN rows
    model_df = model_df.dropna(subset=feature_cols)

    logger.info(f"Model dataset: {len(model_df)} rows, crisis rate: "
                f"{model_df['crisis'].mean():.3f}")

    if len(model_df) < 100 or model_df['crisis'].sum() < 10:
        logger.warning("Insufficient data for ML modeling; producing descriptive output only")
        # Still produce risk scoring from debt_risk_score
        latest = debt.sort_values('year').groupby('country_code').last().reset_index()
        latest = latest.merge(master[['country_code', 'country_name', 'region', 'income_group']].drop_duplicates('country_code'),
                              on='country_code', how='left')
        if 'debt_risk_score' in latest.columns:
            latest['risk_rank'] = latest['debt_risk_score'].rank(ascending=False, method='min')
            latest = latest.sort_values('debt_risk_score', ascending=False)
        write_single_sheet_excel(
            latest[['country_code', 'country_name', 'year', 'external_debt_pct_gni',
                     'debt_service_pct_exports', 'debt_risk_score'] +
                    (['risk_rank'] if 'debt_risk_score' in latest.columns else [])],
            out / "debt_early_warning_model.xlsx", sheet_name="Risk Scores"
        )
        write_single_sheet_excel(
            pd.DataFrame({'note': ['Insufficient crisis events for ML modeling']}),
            out / "debt_early_warning_diagnostics.xlsx", sheet_name="Diagnostics"
        )
        logger.info(f"[{MANIFEST['id']}] Complete (descriptive only)")
        return

    # Temporal split
    train = model_df[model_df['year'] < 2015].copy()
    test = model_df[model_df['year'] >= 2015].copy()

    if len(train) < 50 or train['crisis'].sum() < 5:
        logger.warning("Insufficient training data; using 70/30 random split")
        from sklearn.model_selection import train_test_split
        train, test = train_test_split(model_df, test_size=0.3, random_state=42,
                                       stratify=model_df['crisis'])

    X_train = train[feature_cols].values
    y_train = train['crisis'].values
    X_test = test[feature_cols].values
    y_test = test['crisis'].values

    logger.info(f"Train: {len(train)} ({y_train.sum()} crises), "
                f"Test: {len(test)} ({y_test.sum()} crises)")

    # Models
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import roc_auc_score, classification_report
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
        rf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)

        lr.fit(X_train_s, y_train)
        rf.fit(X_train, y_train)

        lr_probs = lr.predict_proba(X_test_s)[:, 1]
        rf_probs = rf.predict_proba(X_test)[:, 1]

        lr_auc = roc_auc_score(y_test, lr_probs) if y_test.sum() > 0 and (y_test == 0).sum() > 0 else np.nan
        rf_auc = roc_auc_score(y_test, rf_probs) if y_test.sum() > 0 and (y_test == 0).sum() > 0 else np.nan

    logger.info(f"Logistic Regression AUC: {lr_auc:.3f}")
    logger.info(f"Random Forest AUC: {rf_auc:.3f}")

    # Feature importances
    fi = pd.DataFrame({
        'feature': feature_cols,
        'lr_coefficient': lr.coef_[0],
        'rf_importance': rf.feature_importances_,
    }).sort_values('rf_importance', ascending=False)
    logger.info(f"Top features:\n{fi.to_string(index=False)}")

    # Score latest year for all countries
    latest_year = model_df['year'].max()
    latest_data = model_df[model_df['year'] == latest_year].copy()
    if latest_data.empty:
        latest_data = model_df.sort_values('year').groupby('country_code').last().reset_index()

    X_latest = latest_data[feature_cols].values
    X_latest_s = scaler.transform(X_latest)

    latest_data['lr_crisis_prob'] = lr.predict_proba(X_latest_s)[:, 1]
    latest_data['rf_crisis_prob'] = rf.predict_proba(X_latest)[:, 1]
    latest_data['ensemble_prob'] = (latest_data['lr_crisis_prob'] + latest_data['rf_crisis_prob']) / 2
    latest_data['risk_rank'] = latest_data['ensemble_prob'].rank(ascending=False, method='min').astype(int)

    output_cols = ['country_code', 'country_name', 'year', 'region', 'income_group',
                   'external_debt_pct_gni', 'debt_service_pct_exports', 'short_term_pct_total',
                   'fiscal_balance_pct_gdp', 'gdp_growth',
                   'lr_crisis_prob', 'rf_crisis_prob', 'ensemble_prob', 'risk_rank']
    output_cols = [c for c in output_cols if c in latest_data.columns]
    risk_output = latest_data[output_cols].sort_values('risk_rank')

    write_single_sheet_excel(risk_output, out / "debt_early_warning_model.xlsx",
                             sheet_name="Risk Scores")

    # Diagnostics
    diag_rows = [
        {'metric': 'lr_auc', 'value': round(lr_auc, 4)},
        {'metric': 'rf_auc', 'value': round(rf_auc, 4)},
        {'metric': 'train_n', 'value': len(train)},
        {'metric': 'test_n', 'value': len(test)},
        {'metric': 'train_crisis_rate', 'value': round(y_train.mean(), 4)},
        {'metric': 'test_crisis_rate', 'value': round(y_test.mean(), 4)},
        {'metric': 'n_features', 'value': len(feature_cols)},
    ]
    for _, row in fi.iterrows():
        diag_rows.append({
            'metric': f"fi_{row['feature']}",
            'value': round(row['rf_importance'], 4),
        })

    diag_df = pd.DataFrame(diag_rows)
    write_single_sheet_excel(diag_df, out / "debt_early_warning_diagnostics.xlsx",
                             sheet_name="Diagnostics")

    # Log top-risk countries
    top10 = risk_output.head(10)
    logger.info(f"Top 10 highest-risk countries:\n"
                f"{top10[['country_code', 'country_name', 'ensemble_prob', 'risk_rank']].to_string(index=False)}")

    logger.info(f"[{MANIFEST['id']}] Complete: {len(risk_output)} countries scored, "
                f"LR AUC={lr_auc:.3f}, RF AUC={rf_auc:.3f}")


if __name__ == "__main__":
    run()
