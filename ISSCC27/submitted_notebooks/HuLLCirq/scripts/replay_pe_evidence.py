"""Replay saved PE RTL and synthesis with its original GUI-originated plan."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.context import physical_interface
from hullcirq.rtl_checks import check_rtl
from hullcirq.verification import build_verification_plan, verify_behavior, verification_template_version
from hullcirq.workflow import synthesize_generic


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=ROOT / "results/npu_pe_continuous_flow")
    parser.add_argument("--compiler-config", type=Path, required=True)
    parser.add_argument("--synthesizer-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Use a new empty output directory to preserve previous runs.")
    manifest = load(args.evidence / "manifest.json")
    for relative, record in manifest["files"].items():
        path = (args.evidence / relative).resolve()
        if not path.is_relative_to(args.evidence.resolve()) or sha(path) != record["sha256"]:
            parser.error("Evidence content/hash mismatch: " + relative)
    design = load(args.evidence / "design.json")
    plan = load(args.evidence / "verification_plan.json")
    state = load(args.evidence / 'state.json')
    generation = load(args.evidence / 'generation.json')
    workflow = load(args.evidence / 'workflow.json')
    candidates = [job for job in generation['jobs'] if job['id'] == manifest['candidate_id']]
    if len(candidates) != 1:
        parser.error('Candidate identity does not match the preserved generation history.')
    candidate = candidates[0]
    source_revision = manifest['source_revision_id']
    if (state['revision']['id'] != source_revision or state['snapshots'].get(source_revision) != design
            or state['design'] != design or candidate['revision_id'] != source_revision
            or candidate['verification_plan'] != plan or candidate['node_id'] != plan['source_node_id']
            or candidate['review_status'] != 'Accepted' or candidate['validation_status'] != 'Passed'):
        parser.error('Design snapshot, adopted candidate and original verification plan are inconsistent.')
    for key, stage in [('synthesis_run_id','local_synthesis'), ('netlist_run_id','local_netlist_simulation')]:
        matched = [run for run in workflow['runs'] if run['id'] == manifest[key]]
        if (len(matched) != 1 or matched[0]['stage_id'] != stage or matched[0]['candidate_id'] != candidate['id']
                or matched[0]['revision_id'] != source_revision or matched[0]['verification_plan'] != plan
                or matched[0]['review_status'] != 'Accepted' or matched[0]['validation_status'] != 'Passed'
                or matched[0]['netlist_sha256'] != manifest['netlist_sha256']):
            parser.error('Netlist evidence does not originate from the adopted candidate and original plan.')
    rebuilt = build_verification_plan(design, plan["source_node_id"], template_version=verification_template_version(plan))
    if rebuilt != plan:
        parser.error("Frozen plan no longer matches its original GUI specification.")
    rtl = (args.evidence / "candidate.v").read_text(encoding="utf-8")
    if rtl != candidate['rtl']:
        parser.error('Saved candidate RTL differs from its original generation record.')
    assert hashlib.sha256(rtl.encode()).hexdigest() == manifest["rtl_sha256"]
    compiler = load(args.compiler_config)
    synthesizer = load(args.synthesizer_config)
    args.output.mkdir(parents=True, exist_ok=True)
    node = next(node for node in design["nodes"] if node["id"] == plan["source_node_id"])
    candidate_checks = check_rtl(rtl, physical_interface(design, node), node['module_name'], compiler)
    behavior = verify_behavior(rtl, plan, compiler, args.output / "rtl")
    synthesis = synthesize_generic(rtl, node["module_name"], synthesizer, args.output / "synthesis")
    netlist = verify_behavior(synthesis["netlist"], plan, compiler, args.output / "netlist") if synthesis.get("netlist") else None
    report = {
        "record_kind": "actual_saved_artifact_replay", "LLM_calls": 0, "replacement_vectors": False,
        "source_evidence_manifest_sha256": sha(args.evidence / "manifest.json"),
        "source_revision_id": manifest["source_revision_id"], "candidate_id": manifest["candidate_id"],
        "vector_hash": plan["vector_hash"], "testbench_sha256": plan["testbench_sha256"],
        "candidate_checks": candidate_checks, "RTL_behavior": behavior, "generic_synthesis": synthesis,
        "netlist_behavior": netlist,
        "replayed_netlist_byte_identical": synthesis.get("netlist_sha256") == manifest["netlist_sha256"],
        "manual_RTL_modifications": [], "PDK_mapping": False, "SDF": False}
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    passed = candidate_checks["validation_status"] == "Passed" and all(item and item["validation_status"] == "Passed" for item in (behavior, synthesis, netlist))
    print(json.dumps({"validation_status": "Passed" if passed else "Failed",
                      "vector_hash": plan["vector_hash"], "testbench_sha256": plan["testbench_sha256"],
                      "replayed_netlist_byte_identical": report["replayed_netlist_byte_identical"],
                      "report": str(args.output / "report.json")}))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
