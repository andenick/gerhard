"""Test panel data integrity: structure, consistency, and cross-panel validation."""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path


class TestPanelStructure:
    """Validate that all panels have correct structure."""

    PANEL_FILES = [
        'master_fiscal_panel.xlsx',
        'revenue_composition_panel.xlsx',
        'expenditure_composition_panel.xlsx',
        'bop_panel.xlsx',
        'exchange_rate_panel.xlsx',
        'trade_panel.xlsx',
        'debt_composition_panel.xlsx',
        'social_outcomes_panel.xlsx',
        'national_accounts_panel.xlsx',
        'clean_tax_panel.xlsx',
        'balanced_panel.xlsx',
        'enriched_tax_panel.xlsx',
    ]

    @pytest.fixture
    def panels(self, output_data_dir):
        """Load all panels that exist."""
        result = {}
        for fname in self.PANEL_FILES:
            path = output_data_dir / fname
            if path.exists():
                result[fname] = pd.read_excel(path)
        return result

    def test_all_panels_have_country_code(self, panels):
        """Every panel must have a country_code column."""
        missing = [name for name, df in panels.items() if 'country_code' not in df.columns]
        assert not missing, f"Panels missing country_code: {missing}"

    def test_all_panels_have_year(self, panels):
        """Every panel must have a year column."""
        missing = [name for name, df in panels.items() if 'year' not in df.columns]
        assert not missing, f"Panels missing year: {missing}"

    def test_country_codes_are_3_chars(self, panels):
        """All country codes should be 3 characters (ISO 3166-1 alpha-3)."""
        violations = []
        for name, df in panels.items():
            if 'country_code' in df.columns:
                bad = df[df['country_code'].astype(str).str.len() != 3]
                if len(bad) > 0:
                    violations.append(f"{name}: {len(bad)} non-3-char codes")
        assert not violations, f"ISO3 violations:\n" + "\n".join(violations)

    def test_no_duplicate_country_year(self, panels):
        """No panel should have duplicate (country_code, year) pairs."""
        violations = []
        for name, df in panels.items():
            if 'country_code' in df.columns and 'year' in df.columns:
                dupes = df.duplicated(subset=['country_code', 'year']).sum()
                if dupes > 0:
                    violations.append(f"{name}: {dupes} duplicates")
        assert not violations, f"Duplicate rows:\n" + "\n".join(violations)

    def test_years_plausible(self, panels):
        """All years should be between 1960 and 2035."""
        violations = []
        for name, df in panels.items():
            if 'year' in df.columns:
                yr = df['year'].dropna()
                if yr.min() < 1960 or yr.max() > 2035:
                    violations.append(f"{name}: year range [{yr.min()}, {yr.max()}]")
        assert not violations, f"Implausible years:\n" + "\n".join(violations)


class TestCrossPanelConsistency:
    """Validate consistency between related panels."""

    def test_revenue_countries_overlap_master(self, output_data_dir):
        """Revenue panel countries should mostly overlap with master panel."""
        master = pd.read_excel(output_data_dir / 'master_fiscal_panel.xlsx')
        revenue = output_data_dir / 'revenue_composition_panel.xlsx'
        if not revenue.exists():
            pytest.skip("Revenue panel not found")
        rev = pd.read_excel(revenue)
        master_cc = set(master['country_code'].unique())
        rev_cc = set(rev['country_code'].unique())
        overlap = len(master_cc & rev_cc) / len(rev_cc) * 100 if rev_cc else 0
        assert overlap > 70, f"Revenue/master overlap only {overlap:.0f}%"

    def test_fiscal_balance_consistent(self, output_data_dir):
        """fiscal_balance should approximately equal tax - expenditure."""
        master = pd.read_excel(output_data_dir / 'master_fiscal_panel.xlsx')
        subset = master.dropna(subset=['tax_revenue_pct_gdp', 'expenditure_pct_gdp', 'fiscal_balance_pct_gdp'])
        if len(subset) < 10:
            pytest.skip("Too few rows with all three fields")
        computed = subset['tax_revenue_pct_gdp'] - subset['expenditure_pct_gdp']
        diff = (computed - subset['fiscal_balance_pct_gdp']).abs()
        mean_diff = diff.mean()
        assert mean_diff < 5, f"Mean fiscal balance discrepancy: {mean_diff:.1f}pp"

    def test_tax_revenue_range_clean(self, output_data_dir):
        """Clean tax panel should have no values > 100% (Sudan removed)."""
        clean = output_data_dir / 'clean_tax_panel.xlsx'
        if not clean.exists():
            pytest.skip("Clean panel not found")
        df = pd.read_excel(clean)
        max_val = df['tax_revenue_pct_gdp'].max()
        assert max_val <= 100, f"Tax > 100% found in clean panel: {max_val:.1f}%"

    def test_expenditure_shares_approximate_sum(self, output_data_dir):
        """Expenditure composition shares should roughly sum to ~100%."""
        exp = output_data_dir / 'expenditure_composition_panel.xlsx'
        if not exp.exists():
            pytest.skip("Expenditure composition not found")
        df = pd.read_excel(exp)
        share_cols = [c for c in df.columns if '_pct_expense' in c]
        if not share_cols:
            pytest.skip("No share columns found")
        sums = df[share_cols].sum(axis=1).dropna()
        if len(sums) == 0:
            pytest.skip("No complete rows")
        median_sum = sums.median()
        assert 80 < median_sum < 120, f"Median share sum: {median_sum:.0f}% (expected ~100%)"

    def test_debt_composition_sums(self, output_data_dir):
        """long_term + short_term should approximately equal total external debt."""
        debt = output_data_dir / 'debt_composition_panel.xlsx'
        if not debt.exists():
            pytest.skip("Debt composition not found")
        df = pd.read_excel(debt)
        if 'long_term_debt_usd' in df.columns and 'short_term_debt_usd' in df.columns and 'external_debt_total_usd' in df.columns:
            subset = df.dropna(subset=['long_term_debt_usd', 'short_term_debt_usd', 'external_debt_total_usd'])
            if len(subset) < 10:
                pytest.skip("Too few complete rows")
            computed = subset['long_term_debt_usd'] + subset['short_term_debt_usd']
            ratio = (computed / subset['external_debt_total_usd']).median()
            assert 0.5 < ratio < 1.5, f"LT+ST / Total median ratio: {ratio:.2f} (expected ~1.0)"


class TestDataQualityPanels:
    """Test data quality across panels."""

    def test_no_all_nan_columns(self, output_data_dir):
        """No panel should have entirely NaN columns."""
        violations = []
        for f in output_data_dir.glob('*_panel.xlsx'):
            df = pd.read_excel(f)
            all_nan = [c for c in df.columns if df[c].isna().all()]
            if all_nan:
                violations.append(f"{f.name}: {all_nan}")
        assert not violations, f"All-NaN columns:\n" + "\n".join(str(v) for v in violations)
