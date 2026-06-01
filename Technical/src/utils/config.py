"""Central configuration management for Gerhard."""
import yaml
from pathlib import Path
from functools import lru_cache


def project_root() -> Path:
    """Return the project root directory (Gerhard/)."""
    # src/utils/config.py -> src/utils -> src -> Technical -> Gerhard
    return Path(__file__).resolve().parent.parent.parent.parent


@lru_cache(maxsize=1)
def get_config() -> dict:
    """Load and return the project configuration."""
    config_path = project_root() / "Technical" / "configs" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}. "
            f"Expected project root at {project_root()}"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_path(key: str) -> Path:
    """Get a configured path, resolved relative to project root.

    Args:
        key: Path key from config.yaml (e.g., 'output_data', 'raw_data')

    Returns:
        Absolute Path object
    """
    config = get_config()
    relative = config["paths"].get(key)
    if relative is None:
        raise KeyError(f"Path key '{key}' not found in config.yaml")
    return project_root() / relative
