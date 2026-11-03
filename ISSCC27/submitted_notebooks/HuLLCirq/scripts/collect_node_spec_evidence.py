"""Preserve S07 results from the same real GUI-originated, adopted PE flow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from node_spec_evidence import ROOT, inspect_preserved_spec, select_current_spec, sha, verify_source, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".work/projects/npu")
    parser.add_argument("--source-evidence", type=Path, default=ROOT / "results/npu_pe_continuous_flow")
    parser.add_argument("--gui-operation", type=Path, required=True, help="Completed real S07 GUI operation directory.")
    parser.add_argument("--output", type=Path, default=ROOT / "results/npu_pe_implementation_spec")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Use a new empty output directory; preserved evidence is never replaced.")
    source = verify_source(args.source_evidence)
    for name in ("state.json", "generation.json", "workflow.json"):
        if (args.data_dir / name).read_bytes() != (args.source_evidence / name).read_bytes():
            parser.error("S07 source differs from the preserved continuous flow: " + name)
    history = args.data_dir / "implementation_specs.json"
    envelope = inspect_preserved_spec(args.source_evidence, history)
    spec = select_current_spec(envelope, "node-pe")
    if (envelope["design"]["project"]["id"] != source["project_id"]
            or envelope["revision"]["id"] != source["source_revision_id"]
            or spec["candidate_id"] != source["candidate_id"]
            or spec["source_run_id"] != source["netlist_run_id"]):
        parser.error("S07 is not a continuation of the preserved PE candidate and original GUI source.")
    from node_spec_evidence import load
    action = load(args.gui_operation / "gui-actions.json")
    if (action.get("record_kind") != "actual_project_GUI_operations"
            or action.get("phase") != "implementation-specs"
            or action.get("actor") != "development_assistant_gui_automation"
            or action.get("page_errors") != []):
        parser.error("Require a completed real GUI operation with truthful operator attribution.")
    recorded = load(args.gui_operation / "actual-spec-record.json")
    if recorded != spec:
        parser.error("The GUI result no longer equals the current preserved specification.")
    args.output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(history, args.output / "implementation_specs.json")
    write_json(args.output / "adopted_spec_record.json", spec)
    write_json(args.output / "node_implementation_spec.json", spec["specification"])
    shutil.copyfile(args.gui_operation / "gui-actions.json", args.output / "gui-actions.json")
    screenshot = args.gui_operation / "actual-pe-implementation-specs.png"
    if screenshot.is_file():
        shutil.copyfile(screenshot, args.output / screenshot.name)
    files = {path.name: {"sha256": sha(path), "bytes": path.stat().st_size}
             for path in sorted(args.output.iterdir()) if path.is_file()}
    manifest = {
        "record_kind": "actual_GUI_S07_continuation_of_preserved_PE_flow",
        "scope": "finite_evidence_backed_one_PE_implementation_specification",
        "spec_id": spec["id"], "node_id": spec["node_id"],
        "source_revision_id": source["source_revision_id"],
        "candidate_id": source["candidate_id"], "source_run_id": source["netlist_run_id"],
        "specification_sha256": spec["specification_sha256"],
        "lineage": spec["specification"]["lineage"],
        "original_vector_count": spec["specification"]["observed_facts"]["vector_count"],
        "checked_assertion_count": spec["specification"]["observed_facts"]["checked_assertion_count"],
        "public_port_count": len(spec["specification"]["public_interface"]["ports"]),
        "source_evidence_manifest_sha256": sha(args.source_evidence / "manifest.json"),
        "source_evidence_hint": "../npu_pe_continuous_flow",
        "source_files_sha256": {name: sha(args.source_evidence / name)
                                for name in ("state.json", "generation.json", "workflow.json")},
        "new_model_calls": 0, "new_EDA_runs": 0, "replacement_vectors": False,
        "operator": "development_assistant_under_explicit_user_instruction",
        "adoption_origin": "automation_policy_user_preapproved_accept_on_pass",
        "manual_human_reviews": 0, "new_RTL_modifications": [],
        "full_NPU_verified": False, "PDK_mapping": False, "timing_or_SDF": False,
        "files": files,
    }
    write_json(args.output / "manifest.json", manifest)
    print(json.dumps({"spec_id": spec["id"], "validation_status": spec["validation_status"],
                      "review_status": spec["review_status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
