import json
from pathlib import Path

from entry_tools import digest, verify_files
from layout_evidence import snapshot_hashes

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reproduction" / "pvt45"
SMOKE = SOURCE / "pvt45_reproduce" / "evidence" / "smoke-v1"


def test_clean_reproduction_source_closure_is_intact_without_private_history():
    hashes = snapshot_hashes((SOURCE / "source-manifest.sha256").read_text())
    assert len(hashes) == 31
    verify_files(SOURCE, hashes)
    assert (SOURCE / "pvt45_reproduce" / "reproduce.py").is_file()
    assert not (SOURCE / "layout_pvt45_windows" / "io_retry_v3" / "evidence" / "final").exists()
    assert not list(SOURCE.rglob("*.zip"))


def test_new_smoke_is_exactly_four_validation_runs_not_a_second_full_grid():
    assert digest(SMOKE / "evidence-sha256.txt") == "9ceaf4c6792828beeadaaf708d82a8b78acda139aec2c31a5e4c251768cf6bef"
    hashes = snapshot_hashes((SMOKE / "evidence-sha256.txt").read_text())
    assert len(hashes) == 58
    verify_files(SMOKE, hashes)
    assert digest(SMOKE / "independent-smoke-audit.json") == "e1823d00edd27781b3adb20210fc2f1d154c9aa1be515ca82b0ca1ef0ee2e139"
    audit = json.loads((SMOKE / "independent-smoke-audit.json").read_text())
    assert audit["actual_new_transients"] == audit["charged_attempts"] == 4
    assert audit["numerical_pairs_qualified"] == audit["numerical_pairs"] == 2
    assert audit["same_point_reference_comparisons_pass"] == 4
    assert audit["full_new_rerun_performed"] is False
    assert audit["original_study720_722ledger_not_changed"] is True
    assert audit["all_owned_processes_stopped"] is True
    assert audit["privacy_private_absolute_path_findings"] == []
