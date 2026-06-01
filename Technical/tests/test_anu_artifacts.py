#!/usr/bin/env python3
"""
Anu Framework artifact validation tests for Gerhard.
Tests D3-D12 artifact existence, format compliance, and data integrity.
"""
import json
import csv
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TECHNICAL = PROJECT_ROOT / "Technical"
REGISTRY_PATH = TECHNICAL / "series_registry.json"
CHOPPED_DIR = TECHNICAL / "ANU_REPLICATOR" / "data" / "final-data" / "chopped"
EXTENBOOK_DIR = TECHNICAL / "ANU_REPLICATOR" / "data" / "final-data" / "extenbooks"
RESEARCH_DIR = TECHNICAL / "research"
DPR_DIR = TECHNICAL / "docs" / "series"
ABSORBED_DIR = TECHNICAL / "absorbed"


@pytest.fixture(scope="module")
def registry():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def tier1_series(registry):
    return {
        sid: entry for sid, entry in registry["series"].items()
        if entry.get("tier") != 2 and entry.get("status") not in ("intermediate",)
    }


class TestRegistryIntegrity:
    def test_registry_exists(self):
        assert REGISTRY_PATH.exists()

    def test_registry_has_series(self, registry):
        assert len(registry["series"]) >= 28

    def test_all_series_have_required_fields(self, registry):
        required = {"id", "name", "description", "content_type", "source", "units", "module"}
        for sid, entry in registry["series"].items():
            missing = required - set(entry.keys())
            assert not missing, f"{sid} missing fields: {missing}"

    def test_series_ids_sequential(self, registry):
        ids = sorted(registry["series"].keys())
        for sid in ids:
            assert sid.startswith("S"), f"{sid} doesn't start with S"
            num = int(sid[1:])
            assert 1 <= num <= 999, f"{sid} number out of range"

    def test_no_synthetic_data_flags(self, registry):
        for sid, entry in registry["series"].items():
            assert entry.get("construction") != "synthetic", f"{sid} marked synthetic"
            assert "placeholder" not in entry.get("description", "").lower(), f"{sid} mentions placeholder"


class TestResearchJSONs:
    def test_research_dir_exists(self):
        assert RESEARCH_DIR.exists()

    def test_all_series_have_research(self, tier1_series):
        for sid in tier1_series:
            path = RESEARCH_DIR / f"{sid}_research.json"
            assert path.exists(), f"Missing research JSON for {sid}"

    def test_research_json_valid(self, tier1_series):
        for sid in tier1_series:
            path = RESEARCH_DIR / f"{sid}_research.json"
            if not path.exists():
                continue
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("series_id") == sid
            assert data.get("methodology_summary"), f"{sid} missing methodology_summary"
            assert data.get("citations"), f"{sid} missing citations"


class TestDPRs:
    def test_dpr_dir_exists(self):
        assert DPR_DIR.exists()

    def test_all_series_have_dpr(self, registry):
        for sid in registry["series"]:
            path = DPR_DIR / f"{sid}_DPR.md"
            assert path.exists(), f"Missing DPR for {sid}"

    def test_dpr_has_required_sections(self, registry):
        for sid in registry["series"]:
            path = DPR_DIR / f"{sid}_DPR.md"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            assert "Quick Reference" in content, f"{sid} DPR missing Quick Reference"
            assert "Data Source" in content, f"{sid} DPR missing Data Source"
            assert "Validation Record" in content, f"{sid} DPR missing Validation Record"


class TestDecompositions:
    def test_composite_series_have_decomposition(self, registry):
        for sid, entry in registry["series"].items():
            if entry.get("construction") == "composite":
                path = DPR_DIR / f"{sid}_DECOMPOSITION.md"
                assert path.exists(), f"Composite {sid} missing decomposition"

    def test_decomposition_has_mermaid(self, registry):
        for sid, entry in registry["series"].items():
            if entry.get("construction") != "composite":
                continue
            path = DPR_DIR / f"{sid}_DECOMPOSITION.md"
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            assert "mermaid" in content.lower(), f"{sid} decomposition missing Mermaid diagram"


class TestChoppedCSVs:
    def test_chopped_dir_exists(self):
        assert CHOPPED_DIR.exists()

    def test_tier1_have_chopped(self, tier1_series):
        for sid, entry in tier1_series.items():
            if entry.get("status") == "pending_generation":
                continue
            path = CHOPPED_DIR / f"{sid}_chopped.csv"
            assert path.exists(), f"Missing chopped CSV for {sid}"

    def test_chopped_format_valid(self, tier1_series):
        for sid, entry in tier1_series.items():
            path = CHOPPED_DIR / f"{sid}_chopped.csv"
            if not path.exists():
                continue
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) >= 3, f"{sid} chopped has <3 rows"
            row2 = lines[1].strip().split(",")
            dash_cols = [c for c in row2 if "-" in c and c.startswith(sid)]
            assert dash_cols, f"{sid} chopped Row 2 has no dash-notation IDs"

    def test_chopped_no_empty_files(self, tier1_series):
        for sid in tier1_series:
            path = CHOPPED_DIR / f"{sid}_chopped.csv"
            if not path.exists():
                continue
            assert path.stat().st_size > 100, f"{sid} chopped CSV suspiciously small"


class TestExtenbooks:
    def test_extenbook_dir_exists(self):
        assert EXTENBOOK_DIR.exists()

    def test_tier1_have_extenbook(self, tier1_series):
        for sid, entry in tier1_series.items():
            if entry.get("status") == "pending_generation":
                continue
            path = EXTENBOOK_DIR / f"{sid}_extenbook.xlsx"
            assert path.exists(), f"Missing extenbook for {sid}"

    def test_extenbook_has_4_sheets(self, tier1_series):
        import openpyxl
        expected_sheets = {"Data", "Provenance", "Research", "Construction"}
        for sid, entry in tier1_series.items():
            path = EXTENBOOK_DIR / f"{sid}_extenbook.xlsx"
            if not path.exists():
                continue
            wb = openpyxl.load_workbook(path, read_only=True)
            sheets = set(wb.sheetnames)
            wb.close()
            assert expected_sheets.issubset(sheets), f"{sid} missing sheets: {expected_sheets - sheets}"


class TestAbsorption:
    def test_absorbed_dir_exists(self):
        assert ABSORBED_DIR.exists()

    def test_module_absorbed_csvs_exist(self):
        modules = ["tax_revenue", "expenditure", "public_debt", "global_comparative", "us_treasury"]
        for module in modules:
            path = ABSORBED_DIR / f"{module}_absorbed.csv"
            assert path.exists(), f"Missing absorbed CSV for {module}"

    def test_combined_absorbed_exists(self):
        assert (ABSORBED_DIR / "gerhard_absorbed_all.csv").exists()

    def test_absorption_report_exists(self):
        assert (ABSORBED_DIR / "gerhard_absorbed_REPORT.md").exists()


class TestReplicator:
    def test_replicate_py_exists(self):
        assert (TECHNICAL / "ANU_REPLICATOR" / "replicate.py").exists()

    def test_replicator_readme_exists(self):
        assert (TECHNICAL / "ANU_REPLICATOR" / "REPLICATOR_README.md").exists()

    def test_subsource_metadata_exists(self):
        path = TECHNICAL / "ANU_REPLICATOR" / "data" / "final-data" / "SUBSOURCE_METADATA.json"
        assert path.exists()
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        assert len(meta) > 300, f"SUBSOURCE_METADATA has only {len(meta)} entries"


class TestPipelineState:
    def test_pipeline_state_exists(self):
        assert (TECHNICAL / "PIPELINE_STATE.json").exists()

    def test_ledger_exists(self):
        assert (TECHNICAL / "ANU_LEDGER.json").exists()

    def test_ledger_coverage(self):
        with open(TECHNICAL / "ANU_LEDGER.json", encoding="utf-8") as f:
            ledger = json.load(f)
        assert ledger.get("artifact_coverage"), "Ledger missing artifact_coverage"
        assert ledger["artifact_coverage"]["series_registry"]["exists"]
        assert ledger["artifact_coverage"]["dprs"]["exists"]
        assert ledger["artifact_coverage"]["chopped_csvs"]["exists"]


class TestDataAuthenticity:
    def test_no_random_in_pipeline_scripts(self):
        pipeline_dir = TECHNICAL / "src" / "pipeline"
        for py_file in pipeline_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            assert "np.random.rand" not in content or "seed" in content, \
                f"{py_file.name} uses np.random without seed"

    def test_no_synthetic_status_in_registry(self, registry):
        for sid, entry in registry["series"].items():
            status = entry.get("status", "")
            assert "synthetic" not in status.lower(), f"{sid} has synthetic status"
