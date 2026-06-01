#!/usr/bin/env python3
"""
Reference value spot-checks for Gerhard series.
Verifies known published values appear in the data panels.
These are sanity checks — if they fail, something is wrong with the data pipeline.
"""
import pytest
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_panel(filename: str) -> pd.DataFrame:
    for prefix in ["Outputs/Data", "Output/Data"]:
        p = PROJECT_ROOT / prefix / filename
        if p.exists():
            return pd.read_excel(p)
    pytest.skip(f"{filename} not found")


class TestTaxReferenceValues:
    """Key findings from README: US tax-to-GDP 10.9%, top 1% pay 40.4%."""

    def test_us_tax_to_gdp_range(self):
        df = load_panel("master_fiscal_panel.xlsx")
        us = df[(df["country_code"] == "USA") & (df["year"] >= 2015) & (df["year"] <= 2023)]
        assert not us.empty, "No US data in master panel"
        us_tax = us["tax_revenue_pct_gdp"].dropna()
        assert len(us_tax) > 0, "No US tax_revenue_pct_gdp"
        assert 8.0 < us_tax.mean() < 15.0, f"US tax/GDP mean {us_tax.mean():.1f}% outside expected 8-15%"

    def test_global_tax_gdp_mean(self):
        """README: global average 15.3% tax/GDP."""
        df = load_panel("master_fiscal_panel.xlsx")
        recent = df[(df["year"] >= 2018) & (df["year"] <= 2022)]
        mean = recent["tax_revenue_pct_gdp"].dropna().mean()
        assert 10.0 < mean < 25.0, f"Global tax/GDP mean {mean:.1f}% outside expected 10-25%"

    def test_country_count(self):
        """README: 202 countries."""
        df = load_panel("master_fiscal_panel.xlsx")
        n_countries = df["country_code"].nunique()
        assert n_countries >= 180, f"Only {n_countries} countries, expected 180+"


class TestDebtReferenceValues:
    """Debt early warning AUC=0.99, US Treasury $30.6T."""

    def test_debt_panel_has_data(self):
        df = load_panel("debt_panel.xlsx")
        assert len(df) > 1000, f"Debt panel has only {len(df)} rows"

    def test_us_debt_to_gdp_range(self):
        df = load_panel("debt_panel.xlsx")
        us = df[(df["country_code"] == "USA") & (df["year"] >= 2015)]
        us_debt = us["debt_pct_gdp"].dropna()
        if len(us_debt) > 0:
            assert 50.0 < us_debt.mean() < 200.0, f"US debt/GDP {us_debt.mean():.1f}% outside range"


class TestGovernanceReferenceValues:
    """Governance is strongest predictor: +4pp tax/GDP per unit, R2=0.25."""

    def test_governance_panel_has_6_dimensions(self):
        df = load_panel("governance_panel.xlsx")
        expected_cols = ["govt_effectiveness", "regulatory_quality", "rule_of_law",
                         "control_of_corruption", "voice_accountability", "political_stability"]
        found = [c for c in expected_cols if c in df.columns]
        assert len(found) >= 5, f"Only {len(found)}/6 governance dimensions found"

    def test_governance_index_range(self):
        """WGI scores range -2.5 to +2.5."""
        df = load_panel("governance_panel.xlsx")
        for col in ["govt_effectiveness", "rule_of_law"]:
            if col in df.columns:
                vals = df[col].dropna()
                assert vals.min() >= -3.0, f"{col} min {vals.min()} below -3.0"
                assert vals.max() <= 3.0, f"{col} max {vals.max()} above 3.0"


class TestTreasuryReferenceValues:
    """US Treasury: $30.6T outstanding, 4.56yr portfolio duration."""

    def test_mspd_panel_has_data(self):
        df = load_panel("treasury_security_panel.xlsx")
        assert len(df) > 100, f"MSPD panel has only {len(df)} rows"

    def test_yield_curve_range(self):
        df = load_panel("yield_curve_daily.xlsx")
        assert len(df) > 10000, f"Yield curve has only {len(df)} rows"
        # Yields should be between -1% and 20% for modern era
        numeric_cols = df.select_dtypes(include="number").columns
        for col in numeric_cols[:5]:
            vals = df[col].dropna()
            if len(vals) > 0:
                assert vals.min() >= -2.0, f"{col} yield below -2%"
                assert vals.max() <= 25.0, f"{col} yield above 25%"

    def test_auction_panel_has_data(self):
        df = load_panel("treasury_auction_panel.xlsx")
        assert len(df) > 500, f"Auction panel has only {len(df)} rows"


class TestInequalityReferenceValues:
    """WID: top 1% income share data exists."""

    def test_inequality_panel_has_top1(self):
        df = load_panel("inequality_panel.xlsx")
        assert "top1_income_share" in df.columns
        top1 = df["top1_income_share"].dropna()
        assert len(top1) > 100, f"Only {len(top1)} top1 observations"
        assert 0.0 < top1.mean() < 0.5, f"Top 1% mean {top1.mean():.3f} outside 0-50%"


class TestPanelIntegrity:
    """Cross-panel consistency checks."""

    def test_no_negative_gdp(self):
        df = load_panel("master_fiscal_panel.xlsx")
        if "gdp_current_usd" in df.columns:
            gdp = df["gdp_current_usd"].dropna()
            assert (gdp >= 0).all(), "Negative GDP values found"

    def test_year_range_reasonable(self):
        df = load_panel("master_fiscal_panel.xlsx")
        years = df["year"].dropna()
        assert years.min() >= 1900, f"Year min {years.min()} before 1900"
        assert years.max() <= 2030, f"Year max {years.max()} after 2030"

    def test_no_nan_country_codes(self):
        df = load_panel("master_fiscal_panel.xlsx")
        nan_codes = df["country_code"].isna().sum()
        assert nan_codes == 0, f"{nan_codes} rows with NaN country_code"

    def test_expenditure_pct_range(self):
        df = load_panel("expenditure_panel.xlsx")
        exp = df["expenditure_pct_gdp"].dropna()
        assert exp.min() >= 0, "Negative expenditure % found"
        assert exp.quantile(0.999) < 200, f"Expenditure 99.9th pctile {exp.quantile(0.999):.1f}% > 200%"
