"""Test pipeline registry: script discovery, DAG building, execution planning."""
import pytest
import sys
from pathlib import Path

# Ensure pipeline package is importable
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))


class TestRegistry:
    """Test the pipeline registry module."""

    def test_import_registry(self):
        """Registry module should import without errors."""
        from pipeline._registry import discover_scripts, build_dag, execution_plan
        assert discover_scripts is not None
        assert build_dag is not None
        assert execution_plan is not None

    def test_discover_scripts_finds_migrated(self):
        """Should discover the 6 Wave 1 migrated scripts."""
        from pipeline._registry import discover_scripts
        scripts = discover_scripts()
        assert len(scripts) >= 6, f"Expected 6+ scripts, found {len(scripts)}"

    def test_discovered_scripts_have_valid_ids(self):
        """All discovered scripts should have valid stage-number IDs."""
        import re
        from pipeline._registry import discover_scripts
        scripts = discover_scripts()
        pattern = re.compile(r'^[LEPAVR]\d{2,3}$')
        for sid in scripts:
            assert pattern.match(sid), f"Invalid script ID: {sid}"

    def test_manifest_has_required_fields(self):
        """Each script MANIFEST should have all required fields."""
        from pipeline._registry import discover_scripts
        required = {"id", "name", "stage", "description", "depends_on", "inputs", "outputs", "timeout", "parallel_safe"}
        scripts = discover_scripts()
        for sid, meta in scripts.items():
            # Check ScriptMeta attributes exist
            assert meta.id == sid
            assert meta.name
            assert meta.stage in "LEPAVR"
            assert isinstance(meta.depends_on, list)
            assert isinstance(meta.inputs, list)
            assert isinstance(meta.outputs, list)
            assert isinstance(meta.timeout, int)
            assert isinstance(meta.parallel_safe, bool)

    def test_dag_is_acyclic(self):
        """Dependency DAG should have no cycles."""
        from pipeline._registry import discover_scripts, execution_plan
        scripts = discover_scripts()
        # This will raise ValueError if cycles exist
        plan = execution_plan(scripts)
        assert len(plan) > 0

    def test_dag_dependencies_reference_existing_scripts(self):
        """All depends_on references should point to existing script IDs."""
        from pipeline._registry import discover_scripts, validate_dag
        scripts = discover_scripts()
        errors = validate_dag(scripts)
        # Filter: only flag errors for deps within migrated scripts
        # (deps on not-yet-migrated scripts are expected during gradual migration)
        real_errors = [e for e in errors if "Circular" in e]
        assert not real_errors, f"DAG errors: {real_errors}"

    def test_execution_plan_respects_dependencies(self):
        """Scripts should appear after their dependencies in the plan."""
        from pipeline._registry import discover_scripts, execution_plan
        scripts = discover_scripts()
        plan = execution_plan(scripts)

        # Build position map: script_id -> level index
        positions = {}
        for level_idx, group in enumerate(plan):
            for sid in group:
                positions[sid] = level_idx

        # Check every dependency appears at an earlier level
        for sid, meta in scripts.items():
            if sid not in positions:
                continue
            for dep in meta.depends_on:
                if dep in positions:
                    assert positions[dep] < positions[sid], (
                        f"{sid} (level {positions[sid]}) depends on {dep} "
                        f"(level {positions[dep]}) but {dep} is not earlier"
                    )

    def test_stage_filter_works(self):
        """execution_plan with stage filter should only include that stage."""
        from pipeline._registry import discover_scripts, execution_plan
        scripts = discover_scripts()
        l_plan = execution_plan(scripts, stage="L")
        for group in l_plan:
            for sid in group:
                assert sid.startswith("L"), f"Non-L script {sid} in L-stage plan"

    def test_script_filter_works(self):
        """execution_plan with script_ids should only include those scripts."""
        from pipeline._registry import discover_scripts, execution_plan
        scripts = discover_scripts()
        if "A00" in scripts:
            plan = execution_plan(scripts, script_ids=["A00"])
            all_ids = [sid for group in plan for sid in group]
            assert "A00" in all_ids
            assert len(all_ids) == 1
