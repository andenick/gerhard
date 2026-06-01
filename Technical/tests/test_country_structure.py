"""Test country directory infrastructure completeness."""
import pytest
from pathlib import Path


class TestCountryStructure:
    """Verify all 202 country directories have expected structure."""

    def test_country_count(self, countries_dir):
        """Should have at least 200 country directories."""
        country_dirs = [
            d for d in countries_dir.iterdir()
            if d.is_dir() and len(d.name) == 2 and d.name.isupper()
        ]
        assert len(country_dirs) >= 200, (
            f"Expected 200+ country directories, found {len(country_dirs)}"
        )

    def test_countries_have_output_data(self, countries_dir):
        """Each country should have Output/Data/ directory."""
        country_dirs = [
            d for d in countries_dir.iterdir()
            if d.is_dir() and len(d.name) == 2 and d.name.isupper()
        ]

        missing = [
            d.name for d in country_dirs
            if not (d / "Output" / "Data").exists()
        ]

        assert len(missing) <= 5, (
            f"{len(missing)} countries missing Output/Data/: {missing[:10]}"
        )

    def test_countries_have_profiles(self, countries_dir):
        """Each country should have a profile markdown file."""
        country_dirs = [
            d for d in countries_dir.iterdir()
            if d.is_dir() and len(d.name) == 2 and d.name.isupper()
        ]

        missing = [
            d.name for d in country_dirs
            if not (d / f"{d.name}_PROFILE.md").exists()
        ]

        assert len(missing) <= 5, (
            f"{len(missing)} countries missing profile: {missing[:10]}"
        )

    def test_countries_have_sources(self, countries_dir):
        """Each country should have a sources markdown file."""
        country_dirs = [
            d for d in countries_dir.iterdir()
            if d.is_dir() and len(d.name) == 2 and d.name.isupper()
        ]

        missing = [
            d.name for d in country_dirs
            if not (d / f"{d.name}_SOURCES.md").exists()
        ]

        assert len(missing) <= 5, (
            f"{len(missing)} countries missing sources: {missing[:10]}"
        )

    def test_master_index_exists(self, countries_dir):
        """Countries/MASTER_INDEX.md should exist."""
        assert (countries_dir / "MASTER_INDEX.md").exists()
