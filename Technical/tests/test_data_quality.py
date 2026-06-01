"""Test data quality for Gerhard output files."""
import pytest
import pandas as pd
from pathlib import Path


class TestDataQuality:
    """Verify data quality in output Excel files."""

    def test_us_percentile_data_exists(self, output_data_dir):
        """US tax distribution by percentile should exist and have data."""
        f = output_data_dir / "us_tax_distribution_by_income_percentile.xlsx"
        assert f.exists(), "US percentile data file missing"

        df = pd.read_excel(f)
        assert len(df) >= 4, f"Expected 4+ rows, got {len(df)}"
        assert "income_percentile" in df.columns
        assert "share_of_total_taxes_percent" in df.columns

    def test_us_top1_tax_share_plausible(self, output_data_dir):
        """US top 1% tax share should be in plausible range (30-50%)."""
        f = output_data_dir / "us_tax_distribution_by_income_percentile.xlsx"
        if not f.exists():
            pytest.skip("US percentile data not available")

        df = pd.read_excel(f)
        top1 = df[df["income_percentile"] == "Top 1%"]
        assert len(top1) == 1, "Expected exactly one Top 1% row"

        share = top1["share_of_total_taxes_percent"].values[0]
        assert 30 <= share <= 50, (
            f"Top 1% tax share {share}% outside plausible range [30%, 50%]"
        )

    def test_global_rankings_coverage(self, output_data_dir):
        """Global tax rankings should cover 150+ countries."""
        f = output_data_dir / "global_tax_rankings.xlsx"
        if not f.exists():
            pytest.skip("Global rankings not available")

        df = pd.read_excel(f)
        assert len(df) >= 150, f"Expected 150+ countries, got {len(df)}"

    def test_no_impossible_tax_rates(self, output_data_dir):
        """Vast majority of tax rates should be between 0 and 100."""
        f = output_data_dir / "world_bank_tax_revenue.xlsx"
        if not f.exists():
            pytest.skip("World Bank data not available")

        df = pd.read_excel(f)
        if "tax_revenue_pct_gdp" in df.columns:
            valid = df["tax_revenue_pct_gdp"].dropna()
            assert valid.min() >= -5, f"Extreme negative tax rate: {valid.min()}"
            # Allow small number of outliers (World Bank data has some anomalies)
            outliers = valid[valid > 100]
            pct_outliers = len(outliers) / len(valid) * 100
            assert pct_outliers < 1, (
                f"{len(outliers)} values > 100% ({pct_outliers:.1f}% of data). "
                f"Max: {valid.max():.1f}%"
            )

    def test_world_bank_has_expected_columns(self, output_data_dir):
        """World Bank data should have standard columns."""
        f = output_data_dir / "world_bank_tax_revenue.xlsx"
        if not f.exists():
            pytest.skip("World Bank data not available")

        df = pd.read_excel(f)
        expected = {"country_code", "year", "tax_revenue_pct_gdp"}
        actual = set(df.columns)
        missing = expected - actual
        assert not missing, f"Missing columns: {missing}"
