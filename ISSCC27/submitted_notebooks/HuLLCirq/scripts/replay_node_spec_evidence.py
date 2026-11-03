"""Rebuild preserved S07 facts from the same adopted PE source; no model/EDA calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from node_spec_evidence import (ROOT, inspect_preserved_spec, load, select_current_spec,
                                sha, verify_files, verify_source, write_json)
from hullcirq.implementation_specs import build_node_implementation_spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=ROOT / "results/npu_pe_implementation_spec")
    parser.add_argument("--source-evidence", type=Path, default=ROOT / "results/npu_pe_continuous_flow")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Use a new empty output directory to preserve earlier reports.")
    manifest = load(args.evidence / "manifest.json")
    if manifest.get("record_kind") != "actual_GUI_S07_continuation_of_preserved_PE_flow":
        parser.error("This replay needs the preserved S07 continuation record.")
    verify_files(args.evidence, manifest["files"])
    source = verify_source(args.source_evidence)
    if sha(args.source_evidence / "manifest.json") != manifest["source_evidence_manifest_sha256"]:
        parser.error("The original GUI/RTL/EDA evidence manifest differs from the adopted S07 source.")
    for name, expected in manifest["source_files_sha256"].items():
        if name not in ("state.json", "generation.json", "workflow.json") or sha(args.source_evidence / name) != expected:
            parser.error("Source history differs: " + name)
    envelope = inspect_preserved_spec(args.source_evidence, args.evidence / "implementation_specs.json")
    spec = select_current_spec(envelope, manifest["node_id"], manifest["spec_id"])
    if spec != load(args.evidence / "adopted_spec_record.json"):
        parser.error("The saved result differs from the strict history-derived record.")
    if (manifest["specification_sha256"] != spec["specification_sha256"]
            or manifest["lineage"] != spec["specification"]["lineage"]
            or manifest["original_vector_count"] != spec["specification"]["observed_facts"]["vector_count"]
            or manifest["checked_assertion_count"] != spec["specification"]["observed_facts"]["checked_assertion_count"]
            or manifest["public_port_count"] != len(spec["specification"]["public_interface"]["ports"])):
        parser.error("S07 manifest facts differ from the adopted specification.")
    if (envelope["revision"]["id"] != source["source_revision_id"]
            or manifest["source_revision_id"] != source["source_revision_id"]
            or manifest["candidate_id"] != source["candidate_id"]
            or manifest["source_run_id"] != source["netlist_run_id"]
            or spec["candidate_id"] != source["candidate_id"]
            or spec["source_run_id"] != source["netlist_run_id"]):
        parser.error("The specification has mixed source revisions, candidates or tool runs.")
    candidate = next(job for job in envelope["generation"]["jobs"] if job["id"] == spec["candidate_id"])
    simulation = next(run for run in envelope["workflow_runs"] if run["id"] == spec["source_run_id"])
    synthesis = next(run for run in envelope["workflow_runs"] if run["id"] == simulation["prior_run_id"])
    rebuilt = build_node_implementation_spec(envelope["design"], candidate, synthesis, simulation)
    saved = load(args.evidence / "node_implementation_spec.json")
    if rebuilt != saved or saved != spec["specification"]:
        parser.error("Rebuilt specification differs from the adopted document.")
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "rebuilt_node_implementation_spec.json", rebuilt)
    report = {
        "record_kind": "actual_saved_S07_specification_reconstruction",
        "validation_status": "Passed", "new_model_calls": 0, "new_EDA_runs": 0,
        "replacement_vectors": False, "repeated_circuit_simulation": False,
        "source_manifest_sha256": sha(args.source_evidence / "manifest.json"),
        "S07_manifest_sha256": sha(args.evidence / "manifest.json"),
        "spec_id": spec["id"], "source_revision_id": manifest["source_revision_id"],
        "lineage": rebuilt["lineage"], "public_port_count": len(rebuilt["public_interface"]["ports"]),
        "original_vector_count": rebuilt["observed_facts"]["vector_count"],
        "document_identical": True, "checks": rebuilt["checks"],
        "limits": rebuilt["unverified_limits"],
    }
    write_json(args.output / "report.json", report)
    print(json.dumps({"validation_status": "Passed", "document_identical": True,
                      "public_port_count": report["public_port_count"], "original_vector_count": report["original_vector_count"],
                      "report": str(args.output / "report.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
