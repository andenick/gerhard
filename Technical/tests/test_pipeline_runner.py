"""Test the pipeline runner CLI."""
import pytest
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).resolve().parent.parent / "src" / "run_pipeline.py"


class TestPipelineRunner:
    """Test pipeline runner CLI modes."""

    def test_runner_exists(self):
        """run_pipeline.py should exist."""
        assert RUNNER.exists()

    def test_dry_run_succeeds(self):
        """--dry-run should complete without errors."""
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--dry-run"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"Dry run failed: {result.stderr}"

    def test_legacy_dry_run(self):
        """--legacy --dry-run should show legacy steps."""
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--legacy", "--dry-run"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        combined = (result.stdout + result.stderr).lower()
        assert "legacy" in combined or "process" in combined

    def test_check_mode(self):
        """--check should run data completeness check."""
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--check"],
            capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0
        assert "DATA" in result.stdout.upper() or "source" in result.stdout.lower()

    def test_stage_filter_dry_run(self):
        """--stage L --dry-run should show only L-stage scripts."""
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--stage", "L", "--dry-run"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        assert "L00" in result.stdout or "L40" in result.stdout
