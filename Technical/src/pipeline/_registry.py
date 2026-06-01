"""
Pipeline Registry
Discovers numbered pipeline scripts, builds dependency DAG, plans execution.
Project: Gerhard
"""
import ast
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple


PIPELINE_DIR = Path(__file__).resolve().parent
STAGE_ORDER = ["L", "P", "E", "A", "V", "R"]
STAGE_DIRS = {
    "L": "L_load",
    "P": "P_process",
    "E": "E_explore",
    "A": "A_analyze",
    "V": "V_visualize",
    "R": "R_report",
}
SCRIPT_PATTERN = re.compile(r'^([LEPAVR])(\d{2,3})_(.+)\.py$')


class ScriptMeta:
    """Metadata for a pipeline script."""

    def __init__(self, script_id: str, name: str, stage: str, description: str,
                 depends_on: List[str], inputs: List[dict], outputs: List[dict],
                 timeout: int, parallel_safe: bool, path: Path):
        self.id = script_id
        self.name = name
        self.stage = stage
        self.description = description
        self.depends_on = depends_on
        self.inputs = inputs
        self.outputs = outputs
        self.timeout = timeout
        self.parallel_safe = parallel_safe
        self.path = path

    def __repr__(self):
        return f"ScriptMeta({self.id}: {self.name})"


def _extract_manifest(filepath: Path) -> Optional[dict]:
    """Extract MANIFEST dict from a Python file using AST (no execution)."""
    try:
        source = filepath.read_text(encoding='utf-8')
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'MANIFEST':
                        # Safely evaluate the manifest dict
                        return ast.literal_eval(node.value)
    except (SyntaxError, ValueError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse MANIFEST from {filepath.name}: {e}")
    return None


def discover_scripts() -> Dict[str, ScriptMeta]:
    """Scan pipeline directories and discover all numbered scripts."""
    scripts = {}

    for stage, dirname in STAGE_DIRS.items():
        stage_dir = PIPELINE_DIR / dirname
        if not stage_dir.exists():
            continue

        for pyfile in sorted(stage_dir.glob("*.py")):
            match = SCRIPT_PATTERN.match(pyfile.name)
            if not match:
                continue

            manifest = _extract_manifest(pyfile)
            if manifest is None:
                print(f"Warning: No MANIFEST found in {pyfile.name}, skipping")
                continue

            script_id = manifest.get("id", f"{match.group(1)}{match.group(2)}")
            meta = ScriptMeta(
                script_id=script_id,
                name=manifest.get("name", match.group(3)),
                stage=manifest.get("stage", stage),
                description=manifest.get("description", ""),
                depends_on=manifest.get("depends_on", []),
                inputs=manifest.get("inputs", []),
                outputs=manifest.get("outputs", []),
                timeout=manifest.get("timeout", 120),
                parallel_safe=manifest.get("parallel_safe", True),
                path=pyfile,
            )
            scripts[script_id] = meta

    return scripts


def build_dag(scripts: Dict[str, ScriptMeta] = None) -> Dict[str, List[str]]:
    """Build dependency graph from script manifests.

    Returns dict mapping script_id -> list of script_ids it depends on.
    """
    if scripts is None:
        scripts = discover_scripts()

    dag = {}
    for sid, meta in scripts.items():
        dag[sid] = meta.depends_on

    return dag


def _topological_sort(dag: Dict[str, List[str]]) -> List[List[str]]:
    """Topological sort returning execution levels (groups of parallelizable scripts).

    Returns a list of lists. Each inner list contains script IDs that can
    execute in parallel (no dependencies between them within the group).
    """
    # Compute in-degrees
    all_nodes = set(dag.keys())
    in_degree = {node: 0 for node in all_nodes}

    for node, deps in dag.items():
        for dep in deps:
            if dep in all_nodes:  # Only count deps that exist in the DAG
                in_degree[node] = in_degree.get(node, 0)  # ensure node exists

    # Recount properly
    in_degree = {node: 0 for node in all_nodes}
    for node, deps in dag.items():
        for dep in deps:
            if dep in all_nodes:
                in_degree[node] += 1

    levels = []
    remaining = dict(dag)

    while remaining:
        # Find all nodes with no remaining dependencies
        ready = [
            node for node, deps in remaining.items()
            if all(d not in remaining for d in deps)
        ]

        if not ready:
            # Circular dependency detected
            raise ValueError(
                f"Circular dependency detected among: {list(remaining.keys())}"
            )

        # Sort within level for deterministic ordering
        ready.sort()
        levels.append(ready)

        # Remove completed nodes
        for node in ready:
            del remaining[node]

    return levels


def execution_plan(
    scripts: Dict[str, ScriptMeta] = None,
    stage: Optional[str] = None,
    script_ids: Optional[List[str]] = None,
    id_range: Optional[Tuple[int, int]] = None,
) -> List[List[str]]:
    """Compute execution plan as ordered groups of parallelizable scripts.

    Args:
        scripts: Script registry (auto-discovered if None)
        stage: Filter to a specific stage letter (e.g., 'A')
        script_ids: Filter to specific script IDs
        id_range: Filter to ID range within a stage (e.g., (0, 40) for 00-40)

    Returns:
        List of lists of script IDs, in execution order. Each inner list
        can be executed in parallel.
    """
    if scripts is None:
        scripts = discover_scripts()

    # Apply filters
    filtered = dict(scripts)

    if stage:
        filtered = {k: v for k, v in filtered.items() if v.stage == stage}

    if script_ids:
        filtered = {k: v for k, v in filtered.items() if k in script_ids}

    if id_range and stage:
        lo, hi = id_range
        filtered = {
            k: v for k, v in filtered.items()
            if v.stage == stage and lo <= int(k[1:]) <= hi
        }

    if not filtered:
        return []

    # Build sub-DAG for filtered scripts
    dag = {}
    for sid, meta in filtered.items():
        # Only include deps that are in our filtered set
        deps = [d for d in meta.depends_on if d in filtered]
        dag[sid] = deps

    return _topological_sort(dag)


def validate_inputs(script_id: str, project_root: Path, scripts: Dict[str, ScriptMeta] = None) -> List[str]:
    """Check if required input files exist for a script.

    Returns list of missing required input file paths.
    """
    if scripts is None:
        scripts = discover_scripts()

    meta = scripts.get(script_id)
    if meta is None:
        return [f"Unknown script: {script_id}"]

    missing = []
    for inp in meta.inputs:
        if inp.get("required", False):
            filepath = project_root / inp["path"]
            if not filepath.exists():
                missing.append(inp["path"])

    return missing


def validate_dag(scripts: Dict[str, ScriptMeta] = None) -> List[str]:
    """Validate the dependency DAG for issues.

    Returns list of error messages (empty if valid).
    """
    if scripts is None:
        scripts = discover_scripts()

    errors = []
    all_ids = set(scripts.keys())

    for sid, meta in scripts.items():
        for dep in meta.depends_on:
            if dep not in all_ids:
                errors.append(f"{sid} depends on unknown script: {dep}")

    # Check for cycles
    try:
        dag = build_dag(scripts)
        _topological_sort(dag)
    except ValueError as e:
        errors.append(str(e))

    return errors


def print_execution_plan(plan: List[List[str]], scripts: Dict[str, ScriptMeta] = None):
    """Pretty-print an execution plan."""
    if scripts is None:
        scripts = discover_scripts()

    print(f"\nExecution Plan ({sum(len(g) for g in plan)} scripts in {len(plan)} levels)")
    print("=" * 70)

    for i, group in enumerate(plan):
        parallel_tag = " (parallel)" if len(group) > 1 else ""
        print(f"\nLevel {i}{parallel_tag}:")
        for sid in group:
            meta = scripts.get(sid)
            name = meta.name if meta else "?"
            deps = meta.depends_on if meta else []
            dep_str = f" [after: {', '.join(deps)}]" if deps else ""
            print(f"  {sid:6s} {name}{dep_str}")


# CLI entry point
if __name__ == "__main__":
    import sys

    scripts = discover_scripts()
    print(f"Discovered {len(scripts)} pipeline scripts:")

    for stage in STAGE_ORDER:
        stage_scripts = {k: v for k, v in scripts.items() if v.stage == stage}
        if stage_scripts:
            print(f"\n  {stage} ({STAGE_DIRS[stage]}):")
            for sid in sorted(stage_scripts):
                meta = stage_scripts[sid]
                print(f"    {sid}: {meta.name}")

    # Validate
    errors = validate_dag(scripts)
    if errors:
        print(f"\nDAG Errors:")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"\nDAG valid (no errors)")

    # Show execution plan
    if scripts:
        plan = execution_plan(scripts)
        print_execution_plan(plan, scripts)
