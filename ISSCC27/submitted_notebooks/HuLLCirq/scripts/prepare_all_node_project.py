"""Build the complete six-node specification before any new model execution."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import validate_stage
from hullcirq.verification import build_verification_plan, object_hash
from prepare_npu_nodes_project import build_proposal
from prepare_control_contract import build_control_node


def prepare(design):
    proposal = build_proposal(design)
    control = build_control_node(design)
    proposal["nodes"] = [control if node["id"] == "node-control" else node for node in proposal["nodes"]]
    proposal["edges"] = [edge for edge in proposal["edges"] if edge["id"] != "edge-fifo-control-completion"]
    proposal["edges"].append({"id": "edge-fifo-control-completion",
        "source": {"node_id": "node-fifo", "port_id": "port-fifo-output_transfer"},
        "target": {"node_id": "node-control", "port_id": "port-control-output_transfer"},
        "protocol": "raw", "behavior": "Unsigned one-bit pulse for each actual output_data valid/ready transfer. Count exactly sixteen final output transfers before job_done; scheduler dispatch completion alone is insufficient. Reset cancels the job."})
    proposal["project"]["implementation_scope"] = "Six node contracts and sixteen-PE serial NPU integration target; actual execution status is recorded separately in histories."
    proposal["project"]["global_integration"] = {
        "origin": "development_assistant_specification_saved_through_GUI_under_user_authorization",
        "top_module": "hullcirq_npu", "pe_instance_count": 16,
        "architecture": "serial_row_major_output_stationary_independent_MAC_lanes",
        "external_streams": ["config_data134", "load_data16", "output_data_signed32"],
        "external_status": ["busy", "job_done"],
        "source_artifact": "exact_adopted_source_RTL_plus_S07_public_module_interfaces",
        "wiring_requirements": [
            "Preserve every saved graph edge and exact public port name. Instantiate all five non-PE node modules once and the adopted PE module sixteen times.",
            "Gate external loads to the register buffer while not busy; load source-job addressed bytes before accepting configuration.",
            "Connect control schedule_config and post_config handshakes to scheduler and post respectively. Post configuration is saved config[133:5].",
            "Broadcast rst OR scheduler pe_clear to all sixteen PE resets before first product. Do not use pair_meta.first as a same-cycle input reset.",
            "Select one PE by pair_meta[3:0]. Admit one operand pair only when no previous PE result is pending and that PE is ready. Capture lane and last metadata on the pair transfer.",
            "While result is pending, drain non-final partial sums from only the selected PE; route final sums to post with its backpressure. Clear pending only on the selected PE output transfer.",
            "Route post result_data into FIFO. FIFO output_data is the external final stream. FIFO output_transfer pulse drives control output_transfer exactly.",
            "Control job_done occurs after sixteen actual final external transfers, never merely schedule_done. Reject overlapping configurations. Shared synchronous reset cancels pending state/response/outputs while preserving loaded operand bytes.",
        ],
        "verification_source": "the unchanged canonical design.verification_jobs object; independent signed integer matrix reference; finite source job only",
        "physical_scope": "generic_functional_only_no_PDK_no_delay_no_layout_claim",
    }
    assert object_hash(proposal["verification_jobs"]) == object_hash(design["verification_jobs"])
    old_pe = next(node for node in design["nodes"] if node["id"] == "node-pe")
    assert next(node for node in proposal["nodes"] if node["id"] == "node-pe") == old_pe
    assert object_hash(build_verification_plan(proposal, "node-pe")) == object_hash(build_verification_plan(design, "node-pe")), "The original PE plan must remain exact."
    for stage in ("global_settings", "graph_editor", "specifications"):
        errors = [item for item in validate_stage(proposal, stage) if item["severity"] == "error"]
        assert not errors, (stage, errors)
    for node in proposal["nodes"]:
        build_verification_plan(proposal, node["id"])
    return copy.deepcopy(proposal)


def main():
    baseline = ROOT / ".work/m2e/original_runtime/state.json"
    design = json.loads(baseline.read_text(encoding="utf-8"))["design"]
    proposal = prepare(design)
    target = ROOT / "examples/npu_all_nodes_project.json"
    if target.exists():
        assert object_hash(json.loads(target.read_text(encoding="utf-8"))) == object_hash(proposal), "Do not replace a different saved specification."
    else:
        target.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"proposal": str(target), "nodes": len(proposal["nodes"]), "edges": len(proposal["edges"]), "canonical_job_unchanged": True,
                      "plans": {node["id"]: {key: plan[key] for key in ("kind", "vector_count", "vector_hash", "testbench_sha256")}
                                for node in proposal["nodes"] for plan in [build_verification_plan(proposal, node["id"])]}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
