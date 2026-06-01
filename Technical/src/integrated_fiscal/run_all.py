"""
Run All Integrated Fiscal Analysis Modules
===========================================
Executes A01-A10 in sequence, collecting results and timing.

Usage:
    python -m integrated_fiscal.run_all              # Run all
    python -m integrated_fiscal.run_all A01 A05 A08  # Run specific modules
    python -m integrated_fiscal.run_all --list       # List available modules
"""

import sys
import time
import importlib
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging

logger = setup_logging("run_all")

MODULES = {
    'A01': ('A01_expenditure_composition', 'Expenditure Composition Analysis'),
    'A02': ('A02_military_fiscal_tradeoff', 'Military Spending and Fiscal Tradeoffs'),
    'A03': ('A03_fiscal_sustainability', 'Fiscal Sustainability and Debt Dynamics'),
    'A04': ('A04_tax_structure_evolution', 'Tax Structure Evolution'),
    'A05': ('A05_cofog_functional_analysis', 'COFOG Functional Analysis (Eurostat)'),
    'A06': ('A06_wid_fiscal_distribution', 'WID Fiscal Distribution'),
    'A07': ('A07_us_deep_fiscal', 'US Deep Fiscal (PSZ/DINA)'),
    'A08': ('A08_cross_country_convergence', 'Cross-Country Convergence'),
    'A09': ('A09_fiscal_cyclicality', 'Fiscal Cyclicality'),
    'A10': ('A10_debt_dynamics_decomposition', 'Debt Dynamics Decomposition'),
    'A11': ('A11_profit_fiscal_nexus', 'Profit Rate ↔ Fiscal Dynamics Nexus'),
    'A12': ('A12_master_panel', 'Unified Master Fiscal Panel'),
}


def run_module(module_id: str) -> dict:
    """Import and run a single analysis module."""
    if module_id not in MODULES:
        logger.error(f"Unknown module: {module_id}")
        return {'status': 'error', 'message': f'Unknown module {module_id}'}

    module_name, description = MODULES[module_id]
    logger.info(f"\n{'='*80}")
    logger.info(f"RUNNING {module_id}: {description}")
    logger.info(f"{'='*80}")

    start = time.time()
    try:
        mod = importlib.import_module(f"integrated_fiscal.{module_name}")
        result = mod.run()
        elapsed = time.time() - start
        logger.info(f"{module_id} completed in {elapsed:.1f}s")
        return {'status': 'success', 'elapsed': elapsed, 'result': result}
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"{module_id} FAILED after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'elapsed': elapsed, 'message': str(e)}


def main():
    parser = argparse.ArgumentParser(description="Run integrated fiscal analysis modules")
    parser.add_argument('modules', nargs='*', help="Module IDs to run (e.g., A01 A05)")
    parser.add_argument('--list', action='store_true', help="List available modules")
    args = parser.parse_args()

    if args.list:
        print("\nAvailable modules:")
        print("-" * 60)
        for mid, (_, desc) in MODULES.items():
            print(f"  {mid}: {desc}")
        print()
        return

    modules_to_run = args.modules if args.modules else list(MODULES.keys())

    logger.info(f"Gerhard Integrated Fiscal Analysis Suite")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info(f"Modules to run: {modules_to_run}")
    logger.info(f"{'='*80}")

    total_start = time.time()
    results = {}

    for module_id in modules_to_run:
        result = run_module(module_id)
        results[module_id] = result

    total_elapsed = time.time() - total_start

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")

    successes = sum(1 for r in results.values() if r['status'] == 'success')
    failures = sum(1 for r in results.values() if r['status'] == 'error')

    logger.info(f"Results: {successes} succeeded, {failures} failed")
    for mid, result in results.items():
        status = "OK" if result['status'] == 'success' else "FAIL"
        elapsed = result.get('elapsed', 0)
        msg = result.get('message', '')
        logger.info(f"  {mid}: {status} ({elapsed:.1f}s) {msg}")

    logger.info(f"\nOutput directory: Output/Data/integrated_fiscal/")
    logger.info(f"Finished: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
