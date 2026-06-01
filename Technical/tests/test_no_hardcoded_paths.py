"""Test that no scripts contain hardcoded absolute paths."""
import pytest
from pathlib import Path
import re


class TestNoHardcodedPaths:
    """Verify scripts use relative paths, not hardcoded absolutes."""

    def test_no_hardcoded_absolute_paths(self, src_dir):
        """No production script should contain a hardcoded absolute root path."""
        pattern = re.compile(r'["\']D:/', re.IGNORECASE)

        violations = []
        for py_file in src_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8", errors="replace")
            matches = pattern.findall(content)
            if matches:
                violations.append(f"{py_file.name}: {len(matches)} hardcoded path(s)")

        assert not violations, (
            f"Hardcoded paths found:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_utils_exist(self, src_dir):
        """Utils package should exist."""
        utils_dir = src_dir / "utils"
        assert utils_dir.exists(), "utils/ package missing"
        assert (utils_dir / "__init__.py").exists(), "utils/__init__.py missing"
        assert (utils_dir / "config.py").exists(), "utils/config.py missing"

    def test_config_exists(self, project_root):
        """Central config file should exist."""
        config = project_root / "Technical" / "configs" / "config.yaml"
        assert config.exists(), "Technical/configs/config.yaml missing"
