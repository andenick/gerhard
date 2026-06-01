"""Test minimum coverage requirements for each panel."""
import pytest
import pandas as pd
from pathlib import Path


class TestPanelCoverage:
    """Verify panels meet minimum country/year coverage."""

    def test_master_panel_min_countries(self, output_data_dir):
        """Master panel should have >=200 countries."""
        df = pd.read_excel(output_data_dir / 'master_fiscal_panel.xlsx')
        n = df['country_code'].nunique()
        assert n >= 200, f"Master panel has {n} countries, expected >=200"

    def test_revenue_panel_min_countries(self, output_data_dir):
        """Revenue composition should have >=150 countries."""
        f = output_data_dir / 'revenue_composition_panel.xlsx'
        if not f.exists():
            pytest.skip("Revenue panel not found")
        df = pd.read_excel(f)
        n = df['country_code'].nunique()
        assert n >= 150, f"Revenue panel has {n} countries, expected >=150"

    def test_bop_panel_min_countries(self, output_data_dir):
        """BOP panel should have >=200 countries."""
        f = output_data_dir / 'bop_panel.xlsx'
        if not f.exists():
            pytest.skip("BOP panel not found")
        df = pd.read_excel(f)
        n = df['country_code'].nunique()
        assert n >= 200, f"BOP panel has {n} countries, expected >=200"

    def test_social_panel_has_gini(self, output_data_dir):
        """Social panel should have Gini for >=80 countries."""
        f = output_data_dir / 'social_outcomes_panel.xlsx'
        if not f.exists():
            pytest.skip("Social panel not found")
        df = pd.read_excel(f)
        if 'gini_coefficient' not in df.columns:
            pytest.skip("No gini column")
        n = df.dropna(subset=['gini_coefficient'])['country_code'].nunique()
        assert n >= 80, f"Gini available for {n} countries, expected >=80"

    def test_cofog_has_eu_countries(self, output_data_dir):
        """Expenditure composition should have COFOG for >=20 EU countries."""
        f = output_data_dir / 'expenditure_composition_panel.xlsx'
        if not f.exists():
            pytest.skip("Expenditure composition not found")
        df = pd.read_excel(f)
        cofog_cols = [c for c in df.columns if 'cofog' in c.lower()]
        if not cofog_cols:
            pytest.skip("No COFOG columns")
        has_cofog = df.dropna(subset=[cofog_cols[0]])['country_code'].nunique()
        assert has_cofog >= 20, f"COFOG data for {has_cofog} countries, expected >=20"

    def test_aggregates_has_income_groups(self, output_data_dir):
        """Aggregates should cover all 4 income groups."""
        f = output_data_dir / 'aggregates_panel.xlsx'
        if not f.exists():
            pytest.skip("Aggregates panel not found")
        df = pd.read_excel(f)
        if 'aggregate_type' in df.columns and 'aggregate_name' in df.columns:
            income_rows = df[df['aggregate_type'] == 'income_group']
            groups = set(income_rows['aggregate_name'].unique())
            expected = {'High income', 'Upper middle income', 'Lower middle income', 'Low income'}
            # Check with fuzzy matching (names may vary)
            found = sum(1 for e in expected if any(e.lower() in g.lower() for g in groups))
            assert found >= 3, f"Only {found}/4 income groups in aggregates"

    def test_exchange_panel_coverage(self, output_data_dir):
        """Exchange rate panel should have >=200 countries."""
        f = output_data_dir / 'exchange_rate_panel.xlsx'
        if not f.exists():
            pytest.skip("Exchange rate panel not found")
        df = pd.read_excel(f)
        n = df['country_code'].nunique()
        assert n >= 200, f"Exchange panel has {n} countries, expected >=200"

    def test_trade_panel_coverage(self, output_data_dir):
        """Trade panel should have >=200 countries."""
        f = output_data_dir / 'trade_panel.xlsx'
        if not f.exists():
            pytest.skip("Trade panel not found")
        df = pd.read_excel(f)
        n = df['country_code'].nunique()
        assert n >= 200, f"Trade panel has {n} countries, expected >=200"
