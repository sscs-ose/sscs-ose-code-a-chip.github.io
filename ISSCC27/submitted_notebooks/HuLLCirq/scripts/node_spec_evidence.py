"""Read-only evidence helpers for the S07 continuation of the real PE project."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq.server import make_server, project_envelope
from hullcirq.store import ProjectStore, strict_loads


def load(path):
    return strict_loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def verify_files(directory, files):
    directory = Path(directory).resolve()
    if not isinstance(files, dict) or not files:
        raise ValueError("The evidence manifest must identify preserved files.")
    for relative, record in files.items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory) or not path.is_file() or sha(path) != record["sha256"]:
            raise ValueError("Evidence content/hash mismatch: " + relative)


def verify_source(directory):
    manifest = load(Path(directory) / "manifest.json")
    verify_files(directory, manifest["files"])
    if manifest.get("record_kind") != "actual_GUI_originated_local_LLM_and_EDA_evidence":
        raise ValueError("S07 demonstration needs the preserved real GUI-originated PE flow.")
    return manifest


def inspect_preserved_spec(source_directory, spec_history):
    """Strictly load copied histories; never operate on the original project."""
    scratch = ROOT / ".work/m2c/evidence-checks"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="spec-check-", dir=scratch) as name:
        directory = Path(name)
        for filename in ("state.json", "generation.json", "workflow.json"):
            shutil.copyfile(Path(source_directory) / filename, directory / filename)
        shutil.copyfile(spec_history, directory / "implementation_specs.json")
        store = ProjectStore(directory)
        server = make_server("127.0.0.1", 0, store, ROOT)
        try:
            return project_envelope(server)
        finally:
            server.workflow.close()
            server.generation.close()
            server.server_close()


def select_current_spec(envelope, node_id, spec_id=None):
    records = [item for item in envelope["implementation_specs"] if item["node_id"] == node_id]
    if not records or spec_id and records[-1]["id"] != spec_id:
        raise ValueError("Use the latest preserved specification for the selected node.")
    spec = records[-1]
    if (spec["execution_status"] != "Completed" or spec["validation_status"] != "Passed"
            or spec["review_status"] != "Accepted" or spec["freshness"] != "Current"):
        raise ValueError("The specification needs current, Passed adoption and current source evidence.")
    return spec
