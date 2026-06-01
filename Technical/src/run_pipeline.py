"""
Pipeline Runner for Gerhard
Orchestrates the analytical framework: L→P→E→A→V→R
Supports both legacy (hardcoded steps) and DAG-driven (registry) modes.
Project: Gerhard

Usage:
    python run_pipeline.py                        # Auto-detect mode
    python run_pipeline.py --legacy               # Force legacy mode
    python run_pipeline.py --stage L P E          # Run specific stages
    python run_pipeline.py --script A00 A05       # Run specific scripts
    python run_pipeline.py --skip L               # Skip stages
    python run_pipeline.py --skip-download        # Shorthand for --skip L
    python run_pipeline.py --dry-run              # Show plan only
    python run_pipeline.py --check                # Run E00 only
    python run_pipeline.py --continue-on-error    # Don't stop on failure
"""

import sys
import time
import argparse
import subprocess
import importlib
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = PROJECT_ROOT / "Technical" / "src"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [pipeline] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("pipeline")

# Legacy pipeline steps (backward compat)
LEGACY_STEPS = [
    {"name": "download", "script": "download_tax_data.py", "description": "Download international tax data", "skippable": True, "timeout": 300},
    {"name": "fetch_us", "script": "fetch_us_tax_data.py", "description": "Fetch US tax distribution data", "skippable": True, "timeout": 120},
    {"name": "process", "script": "process_tax_data.py", "description": "Standardize and process raw tax data", "skippable": False, "timeout": 300},
    {"name": "analyze", "script": "analyze_tax_burden.py", "description": "Analyze tax burden distribution", "skippable": False, "timeout": 120},
    {"name": "visualize", "script": "visualize_tax_burden.py", "description": "Generate tax burden visualizations", "skippable": False, "timeout": 120},
    {"name": "reports", "script": "generate_latex_reports.py", "description": "Generate LaTeX reports", "skippable": True, "timeout": 300},
    {"name": "countries_analyze", "script": "analyze_countries.py", "description": "Analyze data for all countries", "skippable": True, "timeout": 600},
]

STAGE_NAMES = {
    "L": "Load",
    "P": "Process",
    "E": "Explore",
    "A": "Analyze",
    "V": "Visualize",
    "R": "Report",
}


def run_legacy_step(step, dry_run=False):
    """Run a single legacy pipeline step."""
    script_path = SRC_DIR / step["script"]
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Step: {step['name']} -- {step['description']}")
    if dry_run:
        return True

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(SRC_DIR),
            capture_output=True, text=True,
            timeout=step["timeout"]
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            logger.info(f"  Completed in {elapsed:.1f}s")
            for line in (result.stdout or "").strip().split("\n")[-3:]:
                if line.strip():
                    logger.info(f"  > {line.strip()}")
            return True
        else:
            logger.error(f"  FAILED (exit {result.returncode}) after {elapsed:.1f}s")
            for line in (result.stderr or result.stdout or "").strip().split("\n")[-5:]:
                if line.strip():
                    logger.error(f"  > {line.strip()}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"  TIMEOUT after {step['timeout']}s")
        return False
    except Exception as e:
        logger.error(f"  ERROR: {e}")
        return False


def run_pipeline_script(script_meta, dry_run=False):
    """Run a single pipeline framework script."""
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}[{script_meta.id}] {script_meta.name}")
    if dry_run:
        return True

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_meta.path)],
            cwd=str(script_meta.path.parent),
            capture_output=True, text=True,
            timeout=script_meta.timeout
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            logger.info(f"  [{script_meta.id}] Completed in {elapsed:.1f}s")
            for line in (result.stdout or "").strip().split("\n")[-2:]:
                if line.strip():
                    logger.info(f"  > {line.strip()}")
            return True
        else:
            logger.error(f"  [{script_meta.id}] FAILED (exit {result.returncode}) after {elapsed:.1f}s")
            for line in (result.stderr or result.stdout or "").strip().split("\n")[-5:]:
                if line.strip():
                    logger.error(f"  > {line.strip()}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"  [{script_meta.id}] TIMEOUT after {script_meta.timeout}s")
        return False
    except Exception as e:
        logger.error(f"  [{script_meta.id}] ERROR: {e}")
        return False


def run_dag_mode(args):
    """Run pipeline using DAG-driven execution from the registry."""
    sys.path.insert(0, str(SRC_DIR))
    from pipeline._registry import discover_scripts, execution_plan, print_execution_plan, validate_inputs

    scripts = discover_scripts()
    if not scripts:
        logger.warning("No pipeline scripts found. Use --legacy or migrate scripts first.")
        return False

    # Build execution plan with filters
    plan_kwargs = {"scripts": scripts}

    skip_stages = set()
    if args.skip:
        skip_stages = set(args.skip)
    if args.skip_download:
        skip_stages.add("L")

    if args.script:
        # Single/multiple script execution
        plan = execution_plan(scripts, script_ids=args.script)
    elif args.stage:
        # Multi-stage execution
        all_levels = []
        for s in args.stage:
            if s in skip_stages:
                continue
            stage_plan = execution_plan(scripts, stage=s)
            all_levels.extend(stage_plan)
        plan = all_levels if all_levels else []
    else:
        # Full pipeline — all stages in order, skipping as requested
        plan = execution_plan(scripts)
        if skip_stages:
            plan = [
                [sid for sid in group if scripts[sid].stage not in skip_stages]
                for group in plan
            ]
            plan = [g for g in plan if g]  # remove empty groups

    if args.dry_run:
        print_execution_plan(plan, scripts)
        return True

    logger.info("=" * 60)
    logger.info("GERHARD PIPELINE (DAG mode)")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Scripts: {sum(len(g) for g in plan)} in {len(plan)} levels")
    if skip_stages:
        logger.info(f"Skipping stages: {', '.join(skip_stages)}")
    logger.info("=" * 60)

    results = {}
    start_total = time.time()

    for level_idx, group in enumerate(plan):
        stage_letters = set(scripts[sid].stage for sid in group if sid in scripts)
        stage_label = "/".join(STAGE_NAMES.get(s, s) for s in sorted(stage_letters))
        logger.info(f"\n--- Level {level_idx} ({stage_label}) ---")

        for sid in group:
            meta = scripts.get(sid)
            if not meta:
                logger.warning(f"  Unknown script: {sid}")
                results[sid] = False
                continue

            # Validate inputs
            missing = validate_inputs(sid, PROJECT_ROOT, scripts)
            if missing:
                logger.warning(f"  [{sid}] Missing inputs: {', '.join(missing)}")

            success = run_pipeline_script(meta, dry_run=args.dry_run)
            results[sid] = success

            if not success and not args.continue_on_error:
                logger.error(f"Pipeline stopped at {sid}. Use --continue-on-error to proceed.")
                break
        else:
            continue
        break

    elapsed_total = time.time() - start_total

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)
    for sid, success in results.items():
        symbol = "+" if success else "x"
        name = scripts[sid].name if sid in scripts else "?"
        logger.info(f"  [{symbol}] {sid}: {name}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    logger.info(f"\n  {passed}/{total} scripts completed in {elapsed_total:.1f}s")

    return passed == total


def run_legacy_mode(args):
    """Run pipeline using legacy hardcoded steps."""
    logger.info("=" * 60)
    logger.info("GERHARD PIPELINE (legacy mode)")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info("=" * 60)

    steps = list(LEGACY_STEPS)
    if args.skip_download:
        steps = [s for s in steps if s["name"] not in ("download", "fetch_us")]
        logger.info("Skipping download steps")

    results = {}
    start_total = time.time()

    for step in steps:
        success = run_legacy_step(step, dry_run=args.dry_run)
        results[step["name"]] = success
        if not success and not args.continue_on_error and not args.dry_run:
            logger.error(f"Pipeline stopped at '{step['name']}'.")
            break

    elapsed_total = time.time() - start_total

    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)
    for name, success in results.items():
        symbol = "+" if success else "x"
        logger.info(f"  [{symbol}] {name}")

    passed = sum(1 for v in results.values() if v)
    logger.info(f"\n  {passed}/{len(results)} steps in {elapsed_total:.1f}s")
    return passed == len(results)


def main():
    parser = argparse.ArgumentParser(description="Gerhard Pipeline Runner")
    parser.add_argument("--legacy", action="store_true", help="Force legacy mode")
    parser.add_argument("--stage", nargs="+", help="Run specific stages (L P E A V R)")
    parser.add_argument("--script", nargs="+", help="Run specific scripts by ID (A00 P00)")
    parser.add_argument("--skip", nargs="+", help="Skip specific stages")
    parser.add_argument("--skip-download", action="store_true", help="Skip L stage")
    parser.add_argument("--dry-run", action="store_true", help="Show plan only")
    parser.add_argument("--check", action="store_true", help="Run data check only")
    parser.add_argument("--continue-on-error", action="store_true", help="Don't stop on failure")
    args = parser.parse_args()

    if args.check:
        # Try E00 first, fall back to old check_data
        e00 = SRC_DIR / "pipeline" / "E_explore" / "E00_check_data_completeness.py"
        check = SRC_DIR / "check_data.py"
        target = e00 if e00.exists() else check
        subprocess.run([sys.executable, str(target)], cwd=str(SRC_DIR))
        return

    # Decide mode
    if args.legacy:
        success = run_legacy_mode(args)
    elif args.stage or args.script:
        # Explicit DAG mode
        success = run_dag_mode(args)
    else:
        # Auto-detect: use DAG if pipeline scripts exist, else legacy
        sys.path.insert(0, str(SRC_DIR))
        try:
            from pipeline._registry import discover_scripts
            scripts = discover_scripts()
            if scripts:
                success = run_dag_mode(args)
            else:
                success = run_legacy_mode(args)
        except ImportError:
            success = run_legacy_mode(args)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
