"""Test US enhanced state-level analysis outputs."""
import pytest
from pathlib import Path


class TestUSEnhancedAnalysis:
    """Verify US enhanced analysis outputs exist and are valid."""

    def test_enhanced_analysis_dir_exists(self, project_root):
        """Enhanced Analysis directory should exist."""
        enhanced = project_root / "Countries" / "US" / "Output" / "Enhanced_Analysis"
        assert enhanced.exists(), "Countries/US/Output/Enhanced_Analysis/ missing"

    def test_enhanced_analysis_has_excel_files(self, project_root):
        """Should have at least 4 Excel files."""
        enhanced = project_root / "Countries" / "US" / "Output" / "Enhanced_Analysis"
        if not enhanced.exists():
            pytest.skip("Enhanced Analysis not yet generated")
        xlsx = list(enhanced.glob("*.xlsx"))
        assert len(xlsx) >= 4, f"Expected 4+ Excel files, found {len(xlsx)}: {[f.name for f in xlsx]}"

    def test_state_estimates_has_data(self, project_root):
        """State tax estimates should have 50+ rows (states)."""
        import pandas as pd
        f = project_root / "Countries" / "US" / "Output" / "Enhanced_Analysis" / "us_state_tax_estimates.xlsx"
        if not f.exists():
            pytest.skip("State estimates not yet generated")
        df = pd.read_excel(f)
        assert len(df) >= 50, f"Expected 50+ rows (states), got {len(df)}"

    def test_state_estimates_has_data_source_column(self, project_root):
        """State tax estimates should have a data_source column."""
        import pandas as pd
        f = project_root / "Countries" / "US" / "Output" / "Enhanced_Analysis" / "us_state_tax_estimates.xlsx"
        if not f.exists():
            pytest.skip("State estimates not yet generated")
        df = pd.read_excel(f)
        assert 'data_source' in df.columns, f"Missing data_source column; columns: {list(df.columns)}"

    def test_oecd_comparison_exists(self, project_root):
        """US vs OECD comparison should exist."""
        f = project_root / "Countries" / "US" / "Output" / "Enhanced_Analysis" / "us_vs_oecd_tax_comparison.xlsx"
        if not f.exists():
            pytest.skip("OECD comparison not yet generated")
        import pandas as pd
        df = pd.read_excel(f)
        assert len(df) >= 3, f"Expected 3+ comparison metrics, got {len(df)}"
