"""Collect finished real NPU node evidence without modifying its workspace."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".work/projects/npu")
    parser.add_argument("--output", type=Path, default=ROOT / "results/npu_pe_continuous_flow")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Use a new empty output directory; original evidence is never replaced.")
    state = json.loads((args.data_dir / "state.json").read_text(encoding="utf-8"))
    generation = json.loads((args.data_dir / "generation.json").read_text(encoding="utf-8"))
    workflow = json.loads((args.data_dir / "workflow.json").read_text(encoding="utf-8"))
    candidate = next(job for job in reversed(generation["jobs"]) if job["node_id"] == "node-pe")
    if state['revision']['id'] != candidate['revision_id'] or state['snapshots'].get(candidate['revision_id']) != state['design']:
        raise ValueError('The current design differs from the candidate source snapshot. Refusing to mix a new design with old evidence.')
    assert all(run['revision_id'] == candidate['revision_id'] for run in state['runs'])
    assert all(job['revision_id'] == candidate['revision_id'] and job['input_hash'] == candidate['input_hash'] for job in generation['jobs'])
    assert candidate["execution_status"] == "Completed" and candidate["validation_status"] == "Passed" and candidate["review_status"] == "Accepted"
    synthesis = next(run for run in reversed(workflow["runs"]) if run["stage_id"] == "local_synthesis")
    simulation = next(run for run in reversed(workflow["runs"]) if run["stage_id"] == "local_netlist_simulation")
    for run in (synthesis, simulation):
        assert run["candidate_id"] == candidate["id"] and run["revision_id"] == candidate["revision_id"]
        assert run["execution_status"] == "Completed" and run["validation_status"] == "Passed" and run["review_status"] == "Accepted"
        assert run["verification_plan"] == candidate["verification_plan"]
        assert run["rtl_sha256"] == candidate["rtl_sha256"]
    assert simulation["prior_run_id"] == synthesis["id"]
    assert simulation["netlist"] == synthesis["netlist"]
    assert simulation["netlist_sha256"] == synthesis["netlist_sha256"]
    assert all(item.get("actor") == "automation_policy" for item in state["reviews"] + generation["reviews"] + workflow["reviews"])
    assert all(item["execution_status"] not in ("Queued", "Running") for item in generation["jobs"])
    args.output.mkdir(parents=True)
    for name in ("state.json", "generation.json", "workflow.json"):
        shutil.copyfile(args.data_dir / name, args.output / name)
    write_json(args.output / "design.json", state["design"])
    write_json(args.output / "verification_plan.json", candidate["verification_plan"])
    write_json(args.output / "reference_trace.json", candidate["verification_plan"]["reference_trace"])
    write_json(args.output / "vectors.json", candidate["verification_plan"]["contract"]["vectors"])
    (args.output / "candidate.v").write_text(candidate["rtl"], encoding="utf-8", newline="\n")
    (args.output / "netlist.v").write_text(synthesis["netlist"], encoding="utf-8", newline="\n")
    (args.output / "contract_tb.v").write_text(candidate["verification_plan"]["testbench"], encoding="utf-8", newline="\n")
    operations = ROOT / ".work/m2b/gui-operations"
    copied = []
    for folder in sorted(operations.iterdir()):
        action_file = folder / "gui-actions.json"
        if not action_file.exists():
            continue
        record = json.loads(action_file.read_text(encoding="utf-8"))
        destination = args.output / "gui_operations" / folder.name
        destination.mkdir(parents=True)
        shutil.copyfile(action_file, destination / "gui-actions.json")
        copied.append(str((destination / "gui-actions.json").relative_to(args.output)).replace("\\", "/"))
    files = {str(path.relative_to(args.output)).replace("\\", "/"): {"sha256": digest(path), "bytes": path.stat().st_size}
             for path in sorted(args.output.rglob("*")) if path.is_file()}
    manifest = {
        "record_kind": "actual_GUI_originated_local_LLM_and_EDA_evidence",
        "scope": "one_PE_template_in_saved_4x4_INT8_NPU_project",
        "project_id": state["design"]["project"]["id"],
        "source_revision_id": candidate["revision_id"],
        "candidate_id": candidate["id"], "synthesis_run_id": synthesis["id"], "netlist_run_id": simulation["id"],
        "vector_hash": candidate["verification_plan"]["vector_hash"],
        "testbench_sha256": candidate["verification_plan"]["testbench_sha256"],
        "rtl_sha256": candidate["rtl_sha256"], "netlist_sha256": synthesis["netlist_sha256"],
        "model_calls": len(generation["jobs"]),
        "attempts": [{"id": job["id"], "operation": job["operation"], "base_job_id": job["base_job_id"],
                      "prompt_template_version": job["context"]["prompt_template_version"],
                      "validation_status": job["validation_status"],
                      "checks": {key: value.get("validation_status") for key, value in job["checks"].items()},
                      "review_status": job["review_status"]} for job in generation["jobs"]],
        "specification_origin": "development_assistant_proposal_imported_edited_and_saved_through_real_GUI",
        "GUI_operator": "development_assistant_under_explicit_user_instruction",
        "adoption_origin": "automation_policy_user_preapproved_accept_on_pass",
        "manual_human_reviews": 0, "manual_RTL_modifications": [], "imported_existing_RTL": [],
        "program_interface_header": True,
        "development_assistant_correction_instructions_including_ready_expression": True,
        "same_original_vectors_and_frozen_testbench_across_RTL_and_netlist": True,
        "PDK_mapping": False, "timing_or_SDF": False, "full_NPU_verified": False,
        "original_source_directory": str(args.data_dir.resolve()),
        "runtime_record": "../../configs/runtime_m2b.json",
        "gui_operation_records": copied, "files": files}
    write_json(args.output / "manifest.json", manifest)
    print(json.dumps({key: manifest[key] for key in ("candidate_id", "model_calls", "vector_hash", "rtl_sha256", "netlist_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
