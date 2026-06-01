"""Test that core pipeline scripts can be imported without errors."""
import pytest
import importlib
import sys
from pathlib import Path


class TestPipelineImports:
    """Verify core scripts don't have import errors."""

    @pytest.fixture(autouse=True)
    def add_src_to_path(self, src_dir):
        """Add src directory to Python path."""
        sys.path.insert(0, str(src_dir))
        yield
        sys.path.remove(str(src_dir))

    @pytest.mark.parametrize("script", [
        "process_tax_data",
        "analyze_tax_burden",
        "visualize_tax_burden",
        "analyze_countries",
        "validate_data",
        "check_data",
    ])
    def test_core_script_imports(self, script):
        """Core scripts should import without errors."""
        try:
            mod = importlib.import_module(script)
            assert mod is not None
        except ImportError as e:
            pytest.fail(f"Import error in {script}: {e}")
