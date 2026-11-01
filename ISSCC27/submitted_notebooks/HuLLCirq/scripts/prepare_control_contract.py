"""Build an explicit control-node proposal without editing any live project."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.domain import DomainError
from hullcirq.scheduler_verification import pack_configuration


def build_control_node(design):
    nodes = [node for node in design.get("nodes", []) if node.get("id") == "node-control"]
    jobs = design.get("verification_jobs")
    if len(nodes) != 1 or type(jobs) is not list or len(jobs) != 1:
        raise DomainError("invalid_control_source", "The proposal requires one control node and the one original canonical matrix job.")
    pack_configuration(jobs[0])
    node = copy.deepcopy(nodes[0])
    node["behavior"] = (
        "One original matrix job at a time. Config134: K[4:0]1..16,ReLU[5],signed32 column biases[6+32*i+:32]. "
        "States IDLE,SEND_CONFIG,RUN,DONE. IDLE config_data_ready=!rst && incoming K in1..16, independent of valid. "
        "Config handshake latches all134 bits, clears independent schedule_sent/post_sent flags and output count, then SEND_CONFIG. "
        "SEND_CONFIG schedule_config_valid=!schedule_sent and post_config_valid=!post_sent, gated !rst. "
        "schedule_config=saved_config134; post_config={saved_config[133:6],saved_config[5]}129. "
        "Hold each valid/data until its own ready handshake; then drop only that valid. Enter RUN after both handshakes, including simultaneous handshakes. "
        "Do not count output_transfer on the SEND_CONFIG-to-RUN edge. RUN counts actual final FIFO output transfer pulses;16th enters DONE. "
        "DONE job_done1cycle then IDLE. busy=!rst && state!=IDLE, including DONE; job_done=!rst && state==DONE. "
        "Reject config while busy. Ignore output_transfer outside RUN. Sync high rst overrides, clears saved config/state/flags/count, "
        "and gates ready/valid/busy/job_done low. Raw output_transfer must be actual final FIFO output valid&&ready in global integration; "
        "scheduler dispatch done is not job completion. No arbitrary timeout or fake completion pulse."
    )
    node["test_expectations"] = (
        "Same unchanged original GUI matrix job for RTL and netlist. Fixed independent exercise uses invalidK0/17 by changing only K bits, "
        "independent staggered configuration stalls in both completion orders, busy config offers held until reset, "
        "non-RUN output pulses ignored, reset after5final transfers, restart and16final transfers, one done pulse. "
        "Finite control-boundary evidence only; S08 must prove actual FIFO/output integration and numerical results."
    )
    node["constraints"] = {"latency_cycles": 1, "protocol": "valid_ready", "jobs_in_flight": 1, "final_outputs_per_job": 16}
    node["ports"] = [port for port in node["ports"] if port["name"] not in ("output_transfer", "busy", "job_done")]
    for name, direction, kind, meaning in (
        ("output_transfer", "input", "pulse", "Actual final FIFO output_valid && output_ready; count only in RUN."),
        ("busy", "output", "level", "High in SEND_CONFIG, RUN and DONE; low in IDLE and during reset."),
        ("job_done", "output", "pulse", "One cycle after the 16th final output transfer; not scheduler dispatch completion."),
    ):
        node["ports"].append({"id": "port-control-" + name, "name": name, "direction": direction, "width": 1,
                              "signed": False, "protocol": "raw", "clock": "clk", "reset": "rst",
                              "sideband": {"kind": kind, "associated_port_id": None, "meaning": meaning}})
    node["verification"] = {"kind": "npu_control_stream", "version": 1, "source_job": copy.deepcopy(jobs[0]),
                            "exercise": {"kind": "original_job_projection_v1"}}
    return node


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="A saved design.json or state.json; never modified.")
    parser.add_argument("output", type=Path, help="A new node-only proposal file; must not exist.")
    arguments = parser.parse_args()
    source = json.loads(arguments.source.read_text(encoding="utf-8"))
    node = build_control_node(source.get("design", source))
    with arguments.output.open("x", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(node, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"node_id": node["id"], "proposal": str(arguments.output), "live_project_modified": False, "rtl_generated": False}))


if __name__ == "__main__":
    main()
