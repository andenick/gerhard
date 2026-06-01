"""Chart service — themed Plotly figure builders returned as JSON.

Column names verified against the real cached panels (2026-05-31):
  master S006: tax_revenue_pct_gdp, debt_pct_gdp, fiscal_balance_pct_gdp,
               education_pct_gdp, health_pct_gdp, military_pct_gdp
  us_top_income_shares: 'Top 10%','Top 1%','Top 0.1%'  (Year->year)
  us_tax_1913_2024: top_1_percent_share, top_10_percent_share, top_50_percent_share
  us_government_expenditure: *_Expenditure_GDP  (Year->year)
  treasury_comprehensive_ts: Market/Fed/Foreign_Average_Duration, Total_Outstanding_Billions
  qe_duration_timeline: Duration_Extracted_Billions, Fed_Holdings_Percentage
"""
from __future__ import annotations

import json
from typing import Callable

import pandas as pd
import plotly.graph_objects as go

from app.services import data_service as D

PALETTE = ["#1f4e79", "#c0504d", "#4f8a4f", "#e0a526", "#7b5ea7",
           "#3a8fb7", "#b5651d", "#5a5a5a", "#8c1d40", "#2e6e6e"]


def _theme(fig: go.Figure, title: str, ytitle: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(family="Georgia, serif", size=20, color="#1a1a1a")),
        template="plotly_white", colorway=PALETTE,
        font=dict(family="Segoe UI, Helvetica, Arial, sans-serif", size=13, color="#2a2a2a"),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        margin=dict(l=64, r=24, t=64, b=48), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis=dict(title=ytitle, gridcolor="#e6e6e6", zeroline=False),
        xaxis=dict(gridcolor="#e6e6e6", zeroline=False))
    return fig


def _span(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    if df.empty or "year" not in df.columns:
        return df
    y0, y1 = params.get("y0"), params.get("y1")
    if y0 is not None:
        df = df[df["year"] >= int(y0)]
    if y1 is not None:
        df = df[df["year"] <= int(y1)]
    return df


def _result(fig: go.Figure, caption: str, dlkey: str, citations=None) -> dict:
    return {"figure": json.loads(fig.to_json()), "caption": caption,
            "download": {"csv": f"/api/download/{dlkey}.csv", "xlsx": f"/api/download/{dlkey}.xlsx"} if dlkey else {},
            "citations": citations or []}


def us_top_income_shares(params: dict) -> dict:
    df = _span(D.load_dataset("us_top_income_shares"), params)
    fig = go.Figure()
    for col in ["Top 10%", "Top 1%", "Top 0.1%"]:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df["year"], y=df[col], name=col, mode="lines"))
    _theme(fig, "U.S. Top Income Shares (DINA)", "Share of pre-tax national income (%)")
    return _result(fig, "Top income shares — Piketty–Saez–Zucman Distributional National Accounts.",
                   "us_top_income_shares", ["piketty_saez_zucman_2018"])


def us_tax_composition(params: dict) -> dict:
    df = _span(D.load_dataset("us_tax_1913_2024"), params)
    fig = go.Figure()
    for col, nm in [("top_1_percent_share", "Top 1%"), ("top_10_percent_share", "Top 10%"),
                    ("top_50_percent_share", "Top 50%")]:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df["year"], y=df[col], mode="lines", name=nm))
    _theme(fig, "U.S. Income Tax Share by Group, 1913–2024", "Share of federal income tax (%)")
    return _result(fig, "Historical U.S. income-tax shares by income group.",
                   "us_tax_1913_2024", ["irs_soi", "cbo"])


def us_spending_by_function(params: dict) -> dict:
    df = _span(D.load_dataset("us_government_expenditure"), params)
    fig = go.Figure()
    for c, nm in [("Education_Expenditure_GDP", "Education"), ("Health_Expenditure_GDP", "Health"),
                  ("Military_Expenditure_GDP", "Defense"), ("RD_Expenditure_GDP", "R&D")]:
        if c in df.columns:
            fig.add_trace(go.Scatter(x=df["year"], y=df[c], mode="lines", stackgroup="one", name=nm))
    _theme(fig, "U.S. Federal Spending by Function (% GDP)", "% of GDP")
    return _result(fig, "Government expenditure by function (World Bank indicators).",
                   "us_government_expenditure", ["worldbank_wdi"])


def us_spending_treemap(params: dict) -> dict:
    df = D.load_dataset("us_government_expenditure")
    if df.empty:
        return _result(go.Figure(), "No data.", "us_government_expenditure")
    row = df.dropna(how="all").iloc[-1]
    labels, vals = [], []
    for c, nm in [("Education_Expenditure_GDP", "Education"), ("Health_Expenditure_GDP", "Health"),
                  ("Military_Expenditure_GDP", "Defense"), ("RD_Expenditure_GDP", "R&D")]:
        if c in df.columns and not pd.isna(row.get(c)):
            labels.append(nm); vals.append(float(row[c]))
    fig = go.Figure(go.Treemap(labels=labels, parents=[""] * len(labels), values=vals,
                               marker=dict(colors=PALETTE), textinfo="label+value+percent root"))
    yr = int(row["year"]) if "year" in df.columns and not pd.isna(row.get("year")) else ""
    _theme(fig, f"U.S. Spending Composition {yr} (% GDP)")
    return _result(fig, "Latest-year spending composition by function.",
                   "us_government_expenditure", ["worldbank_wdi"])


def _us_master(params: dict):
    df = D.load_dataset("S006")
    if df.empty or "country_code" not in df.columns:
        return None
    return _span(df[df["country_code"] == "US"], params)


def us_debt_to_gdp(params: dict) -> dict:
    df = _us_master(params)
    fig = go.Figure()
    if df is not None and "debt_pct_gdp" in df.columns:
        d = df.dropna(subset=["debt_pct_gdp"])
        fig.add_trace(go.Scatter(x=d["year"], y=d["debt_pct_gdp"], mode="lines",
                                 fill="tozeroy", name="Debt (% GDP)"))
    _theme(fig, "U.S. Government Debt (% of GDP)", "% of GDP")
    return _result(fig, "Central government debt as a share of GDP (master fiscal panel).",
                   "S006", ["worldbank_wdi"])


def us_fiscal_balance(params: dict) -> dict:
    df = _us_master(params)
    fig = go.Figure()
    if df is not None and "fiscal_balance_pct_gdp" in df.columns:
        d = df.dropna(subset=["fiscal_balance_pct_gdp"])
        colors = ["#4f8a4f" if v >= 0 else "#c0504d" for v in d["fiscal_balance_pct_gdp"]]
        fig.add_trace(go.Bar(x=d["year"], y=d["fiscal_balance_pct_gdp"], marker_color=colors,
                             name="Fiscal balance (% GDP)"))
    _theme(fig, "U.S. Fiscal Balance (% of GDP)", "% of GDP (surplus + / deficit −)")
    return _result(fig, "Overall fiscal balance: surplus (green) vs deficit (red).",
                   "S006", ["worldbank_wdi", "treasury_mts"])


def us_tax_revenue(params: dict) -> dict:
    df = _us_master(params)
    fig = go.Figure()
    if df is not None and "tax_revenue_pct_gdp" in df.columns:
        d = df.dropna(subset=["tax_revenue_pct_gdp"])
        fig.add_trace(go.Scatter(x=d["year"], y=d["tax_revenue_pct_gdp"], mode="lines",
                                 name="Tax revenue (% GDP)"))
    _theme(fig, "U.S. Federal Tax Revenue (% of GDP)", "% of GDP")
    return _result(fig, "Central government tax revenue as a share of GDP.", "S006", ["worldbank_wdi"])


def treasury_duration_evolution(params: dict) -> dict:
    df = D.load_dataset("treasury_comprehensive_ts")
    fig = go.Figure()
    xcol = "date" if "date" in df.columns else ("year" if "year" in df.columns else (df.columns[0] if not df.empty else None))
    for c, nm in [("Market_Average_Duration", "Market"), ("Fed_Average_Duration", "Fed"),
                  ("Foreign_Average_Duration", "Foreign")]:
        if not df.empty and c in df.columns:
            fig.add_trace(go.Scatter(x=df[xcol], y=df[c], mode="lines+markers", name=nm))
    _theme(fig, "Treasury Portfolio Duration by Holder", "Average duration (years)")
    return _result(fig, "Average duration of marketable Treasury debt by holder class.",
                   "treasury_comprehensive_ts", ["treasury_mspd"])


def qe_duration_extraction(params: dict) -> dict:
    df = D.load_dataset("qe_duration_timeline")
    fig = go.Figure()
    xcol = "date" if "date" in df.columns else (df.columns[0] if not df.empty else None)
    if not df.empty and "Duration_Extracted_Billions" in df.columns:
        fig.add_trace(go.Scatter(x=df[xcol], y=df["Duration_Extracted_Billions"], mode="lines",
                                 fill="tozeroy", name="Duration extracted ($B)"))
    if not df.empty and "Fed_Holdings_Percentage" in df.columns:
        fig.add_trace(go.Scatter(x=df[xcol], y=df["Fed_Holdings_Percentage"], yaxis="y2",
                                 mode="lines", name="Fed holdings (%)"))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", title="Fed holdings (%)"))
    _theme(fig, "QE & Duration Extraction from the Treasury Market", "Duration extracted ($B)")
    return _result(fig, "Federal Reserve removal of duration risk via large-scale asset purchases.",
                   "qe_duration_timeline", ["treasury_mspd", "fed_soma"])


def yield_curve_history(params: dict) -> dict:
    """Yield curve heatmap across maturities over time, from S027 daily."""
    df = D.load_dataset("S027")
    mats = [("DGS3MO", 0.25), ("DGS6MO", 0.5), ("DGS1", 1), ("DGS2", 2), ("DGS5", 5),
            ("DGS7", 7), ("DGS10", 10), ("DGS20", 20), ("DGS30", 30)]
    have = [(c, m) for c, m in mats if c in df.columns]
    if df.empty or "date" not in df.columns or not have:
        return _result(go.Figure(), "Yield curve data unavailable.", "S027")
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"]).set_index("date")
    d = d[[c for c, _ in have]].resample("MS").mean().dropna(how="all")
    z = d.T.values
    fig = go.Figure(go.Heatmap(z=z, x=d.index, y=[m for _, m in have],
                               colorscale="RdYlBu_r", colorbar=dict(title="Yield %")))
    _theme(fig, "U.S. Treasury Yield Curve Over Time", "Maturity (years)")
    return _result(fig, "Constant-maturity Treasury yields by maturity, monthly average.",
                   "S027", ["fred", "treasury_mspd"])


def generic_series(params: dict) -> dict:
    sid, var = params.get("series"), params.get("variable")
    countries = params.get("countries") or []
    df = D.load_dataset(sid)
    entry = D.dataset_entry(sid) or {}
    if df.empty or not var or var not in df.columns:
        return _result(go.Figure(), "No data for this selection.", sid)
    xcol = "year" if "year" in df.columns else ("date" if "date" in df.columns else None)
    fig = go.Figure()
    if "country_code" in df.columns and countries and xcol:
        for c in countries[:8]:
            sub = df[df["country_code"] == c]
            fig.add_trace(go.Scatter(x=sub[xcol], y=sub[var], mode="lines", name=c))
    elif xcol:
        fig.add_trace(go.Scatter(x=df[xcol], y=df[var], mode="lines", name=var))
    _theme(fig, f"{entry.get('name', sid)} — {var.replace('_', ' ').title()}", entry.get("units", ""))
    return _result(fig, f"Source: {entry.get('source', 'N/A')}", sid)


CHART_REGISTRY: dict[str, Callable[[dict], dict]] = {
    "us_top_income_shares": us_top_income_shares,
    "us_tax_composition": us_tax_composition,
    "us_spending_by_function": us_spending_by_function,
    "us_spending_treemap": us_spending_treemap,
    "us_debt_to_gdp": us_debt_to_gdp,
    "us_fiscal_balance": us_fiscal_balance,
    "us_tax_revenue": us_tax_revenue,
    "treasury_duration_evolution": treasury_duration_evolution,
    "qe_duration_extraction": qe_duration_extraction,
    "yield_curve_history": yield_curve_history,
    "generic": generic_series,
}


def build_chart(key: str, params: dict) -> dict:
    builder = CHART_REGISTRY.get(key)
    if builder is None:
        return {"figure": {}, "caption": f"Unknown chart '{key}'", "download": {}, "citations": []}
    try:
        return builder(params)
    except Exception as e:  # noqa: BLE001
        return {"figure": {}, "caption": f"Chart error: {e}", "download": {}, "citations": []}


# === bespoke charts (state choropleth + regulation timeline) ===
def us_state_tax_choropleth(params: dict) -> dict:
    df = D.load_dataset("us_state_tax_estimates")
    if df.empty or "state_code" not in df.columns or "estimated_tax_burden_pct_gdp" not in df.columns:
        return _result(go.Figure(), "State tax data unavailable.", "us_state_tax_estimates")
    d = df.copy()
    if "year" in d.columns and d["year"].notna().any():
        d = d[d["year"] == d["year"].max()]
    d = d.groupby(["state_code"], as_index=False).agg(
        burden=("estimated_tax_burden_pct_gdp", "mean"),
        name=("state_name", "first"))
    fig = go.Figure(go.Choropleth(
        locations=d["state_code"], z=d["burden"], locationmode="USA-states",
        colorscale="Blues", colorbar=dict(title="% of GDP"),
        text=d["name"], hovertemplate="%{text}: %{z:.1f}%<extra></extra>"))
    fig.update_layout(geo=dict(scope="usa", bgcolor="#ffffff", lakecolor="#ffffff"))
    _theme(fig, "Estimated State & Local Tax Burden by State (% of GDP)", "")
    return _result(fig, "Estimated state-and-local tax burden, latest available year.",
                   "us_state_tax_estimates", ["irs_soi"])


_IMPACT_RANK = {"major": 3, "medium": 2, "minor": 1, "low": 1}


def regulation_timeline(params: dict) -> dict:
    df = D.load_dataset("regulatory_timeline")
    if df.empty or "date" not in df.columns:
        return _result(go.Figure(), "Regulatory timeline unavailable.", "regulatory_timeline")
    d = df.copy()
    d["_d"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["_d"]).sort_values("_d")
    impact = d["impact"].astype(str).str.lower() if "impact" in d.columns else pd.Series(["medium"] * len(d), index=d.index)
    d["_rank"] = impact.map(_IMPACT_RANK).fillna(2)
    cats = d["category"].astype(str) if "category" in d.columns else pd.Series(["event"] * len(d), index=d.index)
    label = d["event"].astype(str) if "event" in d.columns else d.index.astype(str)
    desc = d["description"].astype(str) if "description" in d.columns else label
    fig = go.Figure()
    for c in sorted(cats.dropna().unique()):
        m = cats == c
        fig.add_trace(go.Scatter(
            x=d.loc[m, "_d"], y=d.loc[m, "_rank"], mode="markers+text",
            name=c, marker=dict(size=14, line=dict(width=1, color="#333")),
            text=label[m], textposition="top center",
            customdata=desc[m],
            hovertemplate="<b>%{text}</b><br>%{x|%b %Y}<br>%{customdata}<extra>" + c + "</extra>"))
    fig.update_yaxes(tickvals=[1, 2, 3], ticktext=["Minor", "Medium", "Major"], range=[0.5, 3.6])
    _theme(fig, "Treasury Market — Regulation & Intervention Timeline", "Impact")
    return _result(fig, "Major regulatory and intervention events in the Treasury market.",
                   "regulatory_timeline", ["treasury_mspd", "fed_soma"])


CHART_REGISTRY["us_state_tax_choropleth"] = us_state_tax_choropleth
CHART_REGISTRY["regulation_timeline"] = regulation_timeline
