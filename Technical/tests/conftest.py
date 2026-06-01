"""Shared test fixtures for Gerhard test suite."""
import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Return the Gerhard project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def output_data_dir(project_root):
    """Return the Output/Data directory."""
    return project_root / "Output" / "Data"


@pytest.fixture
def output_pdfs_dir(project_root):
    """Return the Output/PDFs directory."""
    return project_root / "Output" / "PDFs"


@pytest.fixture
def countries_dir(project_root):
    """Return the Countries directory."""
    return project_root / "Countries"


@pytest.fixture
def src_dir(project_root):
    """Return the Technical/src directory."""
    return project_root / "Technical" / "src"


@pytest.fixture
def raw_data_dir(project_root):
    """Return the Technical/data/raw directory."""
    return project_root / "Technical" / "data" / "raw"
