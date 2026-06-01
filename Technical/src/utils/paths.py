"""Path resolution utilities for Gerhard."""
from pathlib import Path
from .config import project_root, get_path


def ensure_dir(path: Path) -> Path:
    """Create directory if it doesn't exist, return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_data_dir() -> Path:
    """Return the Output/Data directory, creating if needed."""
    return ensure_dir(get_path("output_data"))


def output_pdfs_dir() -> Path:
    """Return the Output/PDFs directory, creating if needed."""
    return ensure_dir(get_path("output_pdfs"))


def raw_data_dir() -> Path:
    """Return the Technical/data/raw directory."""
    return get_path("raw_data")


def processed_data_dir() -> Path:
    """Return the Technical/data/processed directory."""
    return ensure_dir(get_path("processed_data"))


def countries_dir() -> Path:
    """Return the Countries directory."""
    return get_path("countries")


def technical_data_dir() -> Path:
    """Return the Technical/data directory."""
    return get_path("technical_data")
