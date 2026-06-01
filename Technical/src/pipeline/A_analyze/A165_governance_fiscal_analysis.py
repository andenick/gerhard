#!/usr/bin/env python3
"""
A165: Governance-Fiscal Analysis
Cross-domain analysis linking governance quality (WGI) with fiscal outcomes:
tax capacity, tax effort, corruption-revenue gap, rule-of-law-debt, and
institutional quality clusters.
Stage: A | ID: A165
Project: Gerhard

MANIFEST depends_on: ["P110"]
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe

logger = setup_logging(__name__)

MANIFEST = {
    "id": "A165",
    "name": "Governance-Fiscal Analysis",
    "stage": "A",
    "description": (
        "Governance-fiscal nexus: tax capacity, tax effort, corruption-revenue gap, "
        "rule-of-law-debt risk, institutional clusters"
    ),
    "depends_on": ["P110"],
    "inputs": [
        {"path": "Output/Data/governance_panel.xlsx", "required": True},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True},
        {"path": "Output/Data/tax_effort_index.xlsx", "required": False},
        {"path": "Output/Data/debt_composition_panel.xlsx", "required": False},
        {"path": "Output/Data/fiscal_efficiency.xlsx", "required": False},
        {"path": "Output/Data/fiscal_regime_taxonomy.xlsx", "required": False},
    ],
    "outputs": [{"path": "Output/Data/governance_fiscal_analysis.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}


def _ols_summary(x, y, x_label, y_label):
    """Run OLS regression and return summary dict."""
    mask = np.isfinite(x) & np.isfinite(y)
    x_clean, y_clean = x[mask], y[mask]
    if len(x_clean) < 15:
        return None
    slope, intercept, r_val, p_val, se = stats.linregress(x_clean, y_clean)
    return {
        "x_var": x_label,
        "y_var": y_label,
        "slope": round(slope, 4),
        "intercept": round(intercept, 3),
        "r_squared": round(r_val ** 2, 4),
        "p_value": round(p_val, 6),
        "n": len(x_clean),
        "significant": p_val < 0.05,
    }


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out = output_data_dir()

    gov = read_excel_safe(out / "governance_panel.xlsx")
    master = read_excel_safe(out / "master_fiscal_panel.xlsx")
    tax_effort = read_excel_safe(out / "tax_effort_index.xlsx")
    debt_comp = read_excel_safe(out / "debt_composition_panel.xlsx")
    fiscal_eff = read_excel_safe(out / "fiscal_efficiency.xlsx")
    regimes = read_excel_safe(out / "fiscal_regime_taxonomy.xlsx")

    if gov.empty or master.empty:
        logger.error("Cannot load governance_panel or master_fiscal_panel; aborting.")
        return

    logger.info(
        f"Governance panel: {len(gov)} rows, {gov['country_code'].nunique()} countries"
    )

    # ── Merge governance with master fiscal (latest year per country) ──
    master_cols = [
        "country_code", "year", "tax_revenue_pct_gdp", "expenditure_pct_gdp",
        "debt_pct_gdp", "income_group", "country_name", "region",
        "gdp_per_capita_ppp",
    ]
    master_sub = master[[c for c in master_cols if c in master.columns]].drop_duplicates(
        subset=["country_code", "year"]
    )

    # Latest governance per country
    gov_latest = gov.sort_values("year").groupby("country_code").last().reset_index()
    master_latest = master_sub.sort_values("year").groupby("country_code").last().reset_index()

    merged = gov_latest.merge(master_latest, on="country_code", how="inner",
                              suffixes=("", "_fiscal"))
    # Resolve duplicates
    for col in ["country_name", "year"]:
        col_fiscal = f"{col}_fiscal"
        if col_fiscal in merged.columns:
            merged[col] = merged[col].fillna(merged[col_fiscal])
            merged.drop(columns=[col_fiscal], inplace=True)

    logger.info(
        f"Merged gov-fiscal: {len(merged)} countries"
    )

    results_rows = []

    # ════════════════════════════════════════════════════════════════
    # (a) Governance and tax capacity
    # ════════════════════════════════════════════════════════════════
    reg_a = _ols_summary(
        merged["governance_composite"].values,
        merged["tax_revenue_pct_gdp"].values,
        "governance_composite", "tax_revenue_pct_gdp"
    )
    if reg_a:
        interp = (
            "Better governance associated with higher tax collection"
            if reg_a["slope"] > 0 and reg_a["significant"]
            else "Weak or insignificant governance-tax relationship"
        )
        logger.info(
            f"(a) Governance -> Tax capacity: slope={reg_a['slope']}, "
            f"R2={reg_a['r_squared']}, p={reg_a['p_value']}, n={reg_a['n']} -> {interp}"
        )
        results_rows.append({
            "analysis": "a_governance_tax_capacity",
            "country_code": "REGRESSION",
            **reg_a,
            "interpretation": interp,
        })

        # Add per-country scatter data
        for _, row in merged.dropna(
            subset=["governance_composite", "tax_revenue_pct_gdp"]
        ).iterrows():
            results_rows.append({
                "analysis": "a_governance_tax_capacity",
                "country_code": row["country_code"],
                "country_name": row.get("country_name", ""),
                "governance_composite": round(row["governance_composite"], 3),
                "tax_revenue_pct_gdp": round(row["tax_revenue_pct_gdp"], 2),
                "income_group": row.get("income_group", ""),
            })

    # ════════════════════════════════════════════════════════════════
    # (b) Governance and tax effort
    # ════════════════════════════════════════════════════════════════
    if not tax_effort.empty:
        gov_effort = merged.merge(
            tax_effort[["country_code", "tax_effort", "revenue_gap", "predicted_tax"]],
            on="country_code", how="inner",
        )
        reg_b = _ols_summary(
            gov_effort["governance_composite"].values,
            gov_effort["tax_effort"].values,
            "governance_composite", "tax_effort"
        )
        if reg_b:
            interp = (
                "Better governance -> higher tax effort (collecting closer to potential)"
                if reg_b["slope"] > 0 and reg_b["significant"]
                else "Governance does NOT strongly explain tax effort residual"
            )
            logger.info(
                f"(b) Governance -> Tax effort: slope={reg_b['slope']}, "
                f"R2={reg_b['r_squared']}, p={reg_b['p_value']} -> {interp}"
            )
            results_rows.append({
                "analysis": "b_governance_tax_effort",
                "country_code": "REGRESSION",
                **reg_b,
                "interpretation": interp,
            })

            for _, row in gov_effort.dropna(
                subset=["governance_composite", "tax_effort"]
            ).iterrows():
                results_rows.append({
                    "analysis": "b_governance_tax_effort",
                    "country_code": row["country_code"],
                    "country_name": row.get("country_name", ""),
                    "governance_composite": round(row["governance_composite"], 3),
                    "tax_effort": round(row["tax_effort"], 3),
                    "revenue_gap": round(row["revenue_gap"], 2),
                })
    else:
        logger.warning("(b) tax_effort_index.xlsx not available; skipping")

    # ════════════════════════════════════════════════════════════════
    # (c) Corruption and revenue gap
    # ════════════════════════════════════════════════════════════════
    if not tax_effort.empty and "control_of_corruption" in merged.columns:
        corr_gap = merged.merge(
            tax_effort[["country_code", "revenue_gap"]],
            on="country_code", how="inner",
        )
        # revenue_gap = predicted - actual; positive = undertaxing
        reg_c = _ols_summary(
            corr_gap["control_of_corruption"].values,
            corr_gap["revenue_gap"].values,
            "control_of_corruption", "revenue_gap_pct_gdp"
        )
        if reg_c:
            interp = (
                "Higher corruption -> larger revenue gap (more undertaxing)"
                if reg_c["slope"] < 0 and reg_c["significant"]
                else "Corruption-revenue gap link is weak or insignificant"
            )
            logger.info(
                f"(c) Corruption -> Revenue gap: slope={reg_c['slope']}, "
                f"R2={reg_c['r_squared']}, p={reg_c['p_value']} -> {interp}"
            )
            results_rows.append({
                "analysis": "c_corruption_revenue_gap",
                "country_code": "REGRESSION",
                **reg_c,
                "interpretation": interp,
            })

            for _, row in corr_gap.dropna(
                subset=["control_of_corruption", "revenue_gap"]
            ).iterrows():
                results_rows.append({
                    "analysis": "c_corruption_revenue_gap",
                    "country_code": row["country_code"],
                    "country_name": row.get("country_name", ""),
                    "control_of_corruption": round(row["control_of_corruption"], 3),
                    "revenue_gap": round(row["revenue_gap"], 2),
                })

    # ════════════════════════════════════════════════════════════════
    # (d) Rule of law and debt sustainability
    # ════════════════════════════════════════════════════════════════
    if not debt_comp.empty and "debt_risk_score" in debt_comp.columns:
        debt_latest = (
            debt_comp.sort_values("year")
            .groupby("country_code")[["debt_risk_score"]]
            .last()
            .reset_index()
        )
        rol_debt = merged.merge(debt_latest, on="country_code", how="inner")

        reg_d = _ols_summary(
            rol_debt["rule_of_law"].values,
            rol_debt["debt_risk_score"].values,
            "rule_of_law", "debt_risk_score"
        )
        if reg_d:
            interp = (
                "Better rule of law -> lower debt risk"
                if reg_d["slope"] < 0 and reg_d["significant"]
                else "Rule of law - debt risk relationship is weak"
            )
            logger.info(
                f"(d) Rule of law -> Debt risk: slope={reg_d['slope']}, "
                f"R2={reg_d['r_squared']}, p={reg_d['p_value']} -> {interp}"
            )
            results_rows.append({
                "analysis": "d_ruleoflaw_debt",
                "country_code": "REGRESSION",
                **reg_d,
                "interpretation": interp,
            })
    else:
        logger.warning("(d) debt_composition_panel or debt_risk_score not available; skipping")

    # ════════════════════════════════════════════════════════════════
    # (e) Institutional quality clusters x fiscal regime
    # ════════════════════════════════════════════════════════════════
    if not regimes.empty and "fiscal_regime" in regimes.columns:
        regime_gov = merged.merge(
            regimes[["country_code", "fiscal_regime", "cluster_name"]],
            on="country_code", how="inner",
        )
        if len(regime_gov) >= 10:
            cluster_stats = (
                regime_gov.groupby("fiscal_regime")
                .agg(
                    mean_governance=("governance_composite", "mean"),
                    median_governance=("governance_composite", "median"),
                    std_governance=("governance_composite", "std"),
                    mean_govt_effectiveness=("govt_effectiveness", "mean"),
                    mean_control_corruption=("control_of_corruption", "mean"),
                    n_countries=("country_code", "nunique"),
                )
                .round(3)
                .reset_index()
                .sort_values("mean_governance", ascending=False)
            )
            logger.info(
                f"(e) Governance by fiscal regime:\n{cluster_stats.to_string(index=False)}"
            )

            # ANOVA test: does governance differ across regimes?
            groups = [
                g["governance_composite"].dropna().values
                for _, g in regime_gov.groupby("fiscal_regime")
                if len(g) >= 3
            ]
            if len(groups) >= 2:
                f_stat, anova_p = stats.f_oneway(*groups)
                logger.info(f"(e) ANOVA F={f_stat:.2f}, p={anova_p:.4f}")
            else:
                f_stat, anova_p = np.nan, np.nan

            for _, row in cluster_stats.iterrows():
                results_rows.append({
                    "analysis": "e_regime_governance",
                    "country_code": "",
                    "country_name": row["fiscal_regime"],
                    "mean_governance": row["mean_governance"],
                    "median_governance": row["median_governance"],
                    "std_governance": row["std_governance"],
                    "mean_govt_effectiveness": row["mean_govt_effectiveness"],
                    "mean_control_corruption": row["mean_control_corruption"],
                    "n_countries": row["n_countries"],
                    "anova_f": round(f_stat, 2) if pd.notna(f_stat) else np.nan,
                    "anova_p": round(anova_p, 4) if pd.notna(anova_p) else np.nan,
                })

    # ════════════════════════════════════════════════════════════════
    # (f) Summary by governance quintile
    # ════════════════════════════════════════════════════════════════
    quint_data = merged.dropna(subset=["governance_composite"]).copy()
    if len(quint_data) >= 25:
        quint_data["gov_quintile"] = pd.qcut(
            quint_data["governance_composite"], 5,
            labels=["Q1 (worst)", "Q2", "Q3", "Q4", "Q5 (best)"]
        )

        # Merge tax effort if available
        if not tax_effort.empty:
            quint_data = quint_data.merge(
                tax_effort[["country_code", "tax_effort"]],
                on="country_code", how="left",
            )

        agg_cols = {}
        for col, label in [
            ("tax_revenue_pct_gdp", "mean_tax_pct_gdp"),
            ("expenditure_pct_gdp", "mean_exp_pct_gdp"),
            ("debt_pct_gdp", "mean_debt_pct_gdp"),
            ("gdp_per_capita_ppp", "mean_gdp_pc_ppp"),
            ("tax_effort", "mean_tax_effort"),
            ("governance_composite", "mean_governance"),
        ]:
            if col in quint_data.columns:
                agg_cols[col] = ("mean", label)

        if agg_cols:
            quintile_summary = (
                quint_data.groupby("gov_quintile", observed=True)
                .agg(**{label: (col, "mean") for col, (_, label) in agg_cols.items()})
                .round(3)
                .reset_index()
            )
            # Add country count
            quintile_summary["n_countries"] = (
                quint_data.groupby("gov_quintile", observed=True)["country_code"]
                .nunique()
                .values
            )
            logger.info(
                f"(f) Summary by governance quintile:\n{quintile_summary.to_string(index=False)}"
            )

            for _, row in quintile_summary.iterrows():
                row_dict = {
                    "analysis": "f_quintile_summary",
                    "country_code": "",
                    "country_name": str(row["gov_quintile"]),
                    "n_countries": row["n_countries"],
                }
                for col, (_, label) in agg_cols.items():
                    if label in row.index:
                        row_dict[label] = row[label]
                results_rows.append(row_dict)
    else:
        logger.warning(f"(f) Insufficient data for quintile analysis: {len(quint_data)}")

    # ── Build output ──
    if not results_rows:
        logger.error("No analysis produced results; aborting output.")
        return

    result_df = pd.DataFrame(results_rows)

    # Sort: summary/regressions first, then detail
    sort_order = {
        "f_quintile_summary": 0,
        "e_regime_governance": 1,
        "a_governance_tax_capacity": 2,
        "b_governance_tax_effort": 3,
        "c_corruption_revenue_gap": 4,
        "d_ruleoflaw_debt": 5,
    }
    result_df["_sort"] = result_df["analysis"].map(sort_order).fillna(99)
    result_df = result_df.sort_values(
        ["_sort", "analysis", "country_code"]
    ).drop(columns=["_sort"])

    out_path = out / "governance_fiscal_analysis.xlsx"
    write_single_sheet_excel(result_df, out_path, sheet_name="Governance Fiscal Analysis")

    logger.info(
        f"[{MANIFEST['id']}] Complete: {len(result_df)} rows, "
        f"{result_df['analysis'].nunique()} analysis sections saved to {out_path.name}"
    )


if __name__ == "__main__":
    run()
