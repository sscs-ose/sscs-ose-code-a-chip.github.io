"""S07: derive a finite, evidence-backed public node contract from S04–S06.

This is an ordinary-program consistency check of saved executed evidence. It
neither invokes a model nor invents new stimuli, universal behavior or timing.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import tempfile
import threading

from .context import node_fingerprint, physical_interface
from .domain import DomainError, IMPLEMENTED_STAGES, revision_hashes
from .envelope_cache import memoized_envelope, read_scope
from .observation import ObservedState, persist_observation, require_durable_write
from .rtl_checks import _parse_interface, _strip_comments
from .store import _io_path, new_id, strict_loads, utc_now, validate_policy_history, validate_policy_review, _replace_with_windows_retry
from .review_actor import REVIEW_ACTORS, manual_review_fields
from .verification import (build_verification_plan, content_hash, object_hash,
                           validate_plan, verification_template_version)

STAGE = "node_implementation_specs"
EARLIER_STAGES = (*IMPLEMENTED_STAGES, "local_rtl_generation", "local_synthesis", "local_netlist_simulation")
_MUTABLE = {"review_status", "acceptance_epoch", "reviewed_revision_id", "freshness", "artifacts", "record_hash"}


def execution_evidence_hash(record):
    """Keep execution proof stable when a later review withdraws adoption."""
    return object_hash({key: value for key, value in record.items() if key not in _MUTABLE})


def _require(condition, code, message):
    if not condition:
        raise DomainError(code, message, 409)


def _executed_pass(check):
    return (type(check) is dict and check.get("validation_status") == "Passed"
            and check.get("executed") is True and type(check.get("exit_code")) is int and check["exit_code"] == 0)


def _ports_with_ranges(source):
    """The same limited fixed Verilog interface, retaining literal bit order."""
    source = _strip_comments(source)
    name, ports, diagnostics = _parse_interface(source)
    _require(not diagnostics, "unsupported_public_interface", "Public ports require one fixed, plain Verilog module and literal ranges.")
    header = re.search(r"\bmodule\s+" + re.escape(name) + r"\s*\(([^()]*)\)\s*;", source)
    if re.search(r"\b(input|output|inout)\b", header[1]):
        groups = [header[1].split(",")]
    else:
        body = source[header.end():]
        body = re.sub(r"\bfunction\b[\s\S]*?\bendfunction\b|\btask\b[\s\S]*?\bendtask\b", "", body)
        groups = [(match[1] + " " + match[2]).split(",") for match in re.finditer(r"\b(input|output|inout)\s+([^;]+);", body)]
    ranges = {}
    pattern = re.compile(r"^(input|output|inout)\s+(?:(?:wire|reg)\s+)?(?:signed\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([A-Za-z_][A-Za-z0-9_$]*)$")
    for group in groups:
        inherited = None
        for part in group:
            part = re.sub(r"\s+", " ", part.strip())
            match = pattern.fullmatch(part)
            if match:
                _, msb, lsb, port_name = match.groups()
                inherited = None if msb is None else {"msb": int(msb), "lsb": int(lsb)}
            else:
                port_name = part
            ranges[port_name] = copy.deepcopy(inherited)
    _require(set(ranges) == {port["name"] for port in ports}, "unsupported_public_interface", "Cannot recover all public port bit ranges.")
    return name, [{**port, "range": ranges[port["name"]]} for port in ports]


def _check_simulation(check, plan, artifact_hash):
    marker = f"HULLCIRQ_PASS vectors={plan['vector_count']} vector_hash={plan['vector_hash']}"
    _require(_executed_pass(check), "unverified_simulation", "Finite simulation must have executed, passed, and exited with integer zero.")
    expected = {"rtl_sha256": artifact_hash, "vector_hash": plan["vector_hash"],
                "testbench_sha256": plan["testbench_sha256"], "reference_trace_hash": plan["reference_trace_hash"],
                "vector_count": plan["vector_count"], "coverage": plan["coverage"]}
    _require(all(check.get(key) == value for key, value in expected.items()), "simulation_provenance_conflict", "Simulation proof must reference this exact artifact and original frozen plan.")
    output = check.get("stdout", "")
    commands = check.get("commands", [])
    _require(type(output) is str and output.splitlines().count(marker) == 1 and "HULLCIRQ_FAIL" not in output
             and type(commands) is list and len(commands) >= 3
             and all(command.get("executed") is True and command.get("status") == "Completed" and type(command.get("exit_code")) is int and command["exit_code"] == 0 for command in commands)
             and commands[-1].get("stdout", "").splitlines().count(marker) == 1 and "HULLCIRQ_FAIL" not in commands[-1].get("stdout", ""),
             "simulation_marker_missing", "The saved executed compile/simulation log must contain the matching pass marker and no failure marker.")
    if plan.get("kind") == "generic_cycle_vectors":
        from .generic_verification import parse_cycle_runtime
        _require(parse_cycle_runtime(commands[-1].get("stdout", ""), plan, commands[-1].get("stderr", ""))["validation_status"] == "Passed",
                 "simulation_cycle_samples_missing", "Every saved generic output expectation must have one known matching actual sample.")


def _npu2_control_asserted_trace(plan):
    """Describe the frozen v1 testbench's recipe, including bounded waits.

    The independent recipe is not a captured DUT cycle trace. In IDLE the
    harness checks ready is known, rather than requiring eager ready=1.
    """
    trace = []
    def values(source, idle=False):
        checked = {key: source[key] for key in ("config_data_ready", "schedule_config_valid", "post_config_valid", "busy", "job_done")}
        if idle and checked["config_data_ready"] == 1:
            del checked["config_data_ready"]
        for key in ("schedule_config", "post_config"):
            if source[key + "_valid"]:
                checked[key] = source[key]
        return checked
    for item in plan["reference_trace"]:
        vector = item["stimulus"]
        waits = bool(item["config_transfer"])
        before_idle = waits or item["phase_before"] == "IDLE"
        after_idle = not waits and item["phase_after"] == "IDLE"
        predicates = [{"phase": phase, "signal": "config_data_ready", "operator": "known_bit", "allowed": [0, 1]}
                      for phase, source, idle in (("before", item["before"], before_idle), ("after", item["after"], after_idle))
                      if idle and source["config_data_ready"] == 1]
        row = {"recipe_step": item["step"], "stimulus": copy.deepcopy(vector),
               "reference_transfers": {key: item[key] for key in ("config_transfer", "schedule_transfer", "post_transfer", "counted_output_transfer")},
               "asserted_before": values(item["before"], before_idle), "asserted_after": values(item["after"], after_idle),
               "after_condition": "after_actual_configuration_acceptance" if waits else "after_recipe_clock_edge",
               "predicate_assertions": predicates, "temporal_assertions": [], "conditional_assertions": []}
        if waits:
            row["conditional_assertions"].append({"phase": "after_unaccepted_configuration_attempt", "asserted": values(item["before"], True),
                "predicate_assertions": [{"signal": "config_data_ready", "operator": "known_bit", "allowed": [0, 1]}],
                "condition": "configuration_offer_not_yet_accepted", "maximum_attempts": 64})
        if vector["reset_pulse_before_edge"]:
            gated = dict(item["before"])
            gated.update({key: 0 for key in ("config_data_ready", "schedule_config_valid", "post_config_valid", "busy", "job_done")})
            row["temporal_assertions"] = [{"phase": phase, "asserted": values(source)} for phase, source in
                (("before_nonclocked_reset", item["before"]), ("during_nonclocked_reset", gated), ("after_nonclocked_reset", item["before"]))]
        trace.append(row)
    return trace


def _npu2_buffer_asserted_trace(plan):
    """Mirror v1's actual-handshake checks without inventing ready values."""
    trace = []
    def response(source):
        checked = {"operands_valid": source["operands_valid"]}
        if source["operands_valid"]:
            checked["operands"] = source["operands"]
        return checked
    for item in plan["reference_trace"]:
        vector = item["stimulus"]
        wait_kind = "load" if item["load_transfer"] else "read" if item["read_transfer"] else None
        predicates = []
        if not vector["reset"]:
            for name in ("load_data", "read_index"):
                if vector[name + "_valid"]:
                    predicates.append({"phase": "before", "signal": name + "_ready", "operator": "known_bit", "allowed": [0, 1]})
                    if item["before"]["operands_valid"]:
                        predicates.append({"phase": "before", "signal": name + "_ready", "operator": "equals", "expected": 0,
                                           "reason": "no_input_acceptance_while_response_pending"})
            if vector["load_data_valid"] and vector["read_index_valid"]:
                predicates.append({"phase": "before", "signal": "read_index_ready", "operator": "equals", "expected": 0, "reason": "load_priority"})
            for name, kind in (("load_data", "load"), ("read_index", "read")):
                if vector[name + "_valid"] and wait_kind != kind:
                    predicates.append({"phase": "before", "signal": name + "_ready", "operator": "equals", "expected": 0,
                                       "reason": "no_unexpected_input_transfer"})
        row = {"recipe_step": item["cycle"], "stimulus": copy.deepcopy(vector),
               "reference_transfers": {key: item[key] for key in ("load_transfer", "read_transfer", "response_transfer")},
               "asserted_before": response(item["before"]) if not vector["reset"] else None,
               "asserted_after": response(item["after"]),
               "after_condition": "after_actual_" + wait_kind + "_acceptance" if wait_kind else "after_recipe_clock_edge",
               "predicate_assertions": predicates, "conditional_assertions": []}
        if wait_kind:
            row["conditional_assertions"].append({"phase": "after_unaccepted_input_attempt", "asserted": response(item["before"]),
                "condition": "original_input_offer_not_yet_accepted", "maximum_attempts": 64})
        trace.append(row)
    return trace


def _assertion_site_count(trace):
    return sum(len(item["asserted_before"] or {}) + len(item["asserted_after"]) + len(item.get("predicate_assertions", []))
               + sum(len(action["asserted"]) + len(action.get("predicate_assertions", []))
                     for action in item.get("temporal_assertions", []) + item.get("conditional_assertions", [])) for item in trace)


def build_node_implementation_spec(design, candidate, synthesis, simulation):
    """Deterministic payload only. The manager separately checks adoption.

    Rebuilding from the original GUI snapshot and executed proof also validates
    historical payloads after a later review changes effective adoption.
    """
    node_id = candidate["node_id"]
    node = next((node for node in design["nodes"] if node["id"] == node_id), None)
    _require(node is not None, "node_not_found", "The original source node no longer exists in its saved snapshot.")
    synthesis_scoped = synthesis.get("workflow_scope_version") == "stage-boundary-v2"
    simulation_scoped = simulation.get("workflow_scope_version") == "stage-boundary-v2"
    _require(not synthesis_scoped or simulation_scoped, "workflow_scope_conflict",
             "An interface-only S04/S05 chain requires S06-owned behavioral evidence.")
    plan = simulation.get("verification_plan") if simulation_scoped else candidate.get("verification_plan")
    validate_plan(plan)
    rebuilt = build_verification_plan(design, node_id, verification_template_version(plan))
    _require(plan == rebuilt, "verification_input_conflict", "Rebuild the identical plan from the original GUI specification; substituted stimulus is not allowed.")
    source_hash = node_fingerprint(design, node_id)
    design_hash = revision_hashes(design)["semantic_hash"]
    rtl_hash = content_hash(candidate["rtl"])
    _require(candidate.get("execution_status") == "Completed" and (simulation_scoped or candidate.get("validation_status") == "Passed")
             and candidate.get("input_hash") == source_hash and candidate.get("rtl_sha256") == rtl_hash,
             "candidate_evidence_conflict", "The saved candidate must be a complete Passed result of this source node.")
    interface = physical_interface(design, node)
    syntax = candidate.get("checks", {}).get("syntax", {})
    _require(candidate.get("checks", {}).get("interface", {}).get("validation_status") == "Passed"
             and (simulation_scoped or _executed_pass(syntax)),
             "candidate_not_verified", "Original candidate interface checks are required; legacy chains also retain their executed syntax proof.")
    if not simulation_scoped:
        behavior = candidate["checks"].get("behavioral", candidate["checks"].get("functional_verification", {}))
        _check_simulation(behavior, plan, rtl_hash)
    for run, stage_id in ((synthesis, "local_synthesis"), (simulation, "local_netlist_simulation")):
        _require(run.get("record_hash") == object_hash({key: value for key, value in run.items() if key not in ("record_hash", "freshness", "artifacts")}),
                 "workflow_checksum_conflict", "Original workflow execution record checksum is inconsistent.")
        _require(run.get("stage_id") == stage_id and run.get("execution_status") == "Completed" and run.get("validation_status") == "Passed"
                 and run.get("candidate_id") == candidate["id"] and run.get("node_id") == node_id
                 and run.get("revision_id") == candidate["revision_id"] and run.get("input_hash") == source_hash
                 and run.get("design_hash") == design_hash and run.get("rtl_sha256") == rtl_hash,
                 "workflow_provenance_conflict", "Synthesis and simulation must inherit this exact source, candidate and frozen plan.")
        if stage_id == "local_synthesis" and synthesis_scoped:
            _require(run.get("module_name") == interface["module_name"]
                     and all(run.get(key) is None for key in ("verification_plan", "vector_hash", "testbench_sha256")),
                     "workflow_provenance_conflict", "S05 must retain the original public module without claiming an S06 verification plan.")
        else:
            _require(run.get("verification_plan") == plan and run.get("vector_hash") == plan["vector_hash"]
                     and run.get("testbench_sha256") == plan["testbench_sha256"]
                     and (not simulation_scoped or stage_id != "local_netlist_simulation" or run.get("module_name") == interface["module_name"]),
                     "workflow_provenance_conflict", "S06 must retain its exact original-input plan; legacy S05 retains its original plan.")
        _require(_executed_pass(run.get("checks")), "workflow_not_verified", "Both original tool operations must have executed and Passed.")
    netlist = synthesis.get("netlist")
    _require(type(netlist) is str and content_hash(netlist) == synthesis.get("netlist_sha256")
             and simulation.get("prior_run_id") == synthesis["id"] and simulation.get("netlist") == netlist
             and simulation.get("netlist_sha256") == synthesis["netlist_sha256"],
             "netlist_source_conflict", "S06 must simulate the exact adopted S05 netlist, without replacement.")
    _require(synthesis["checks"].get("rtl_sha256") == rtl_hash and synthesis["checks"].get("netlist_sha256") == synthesis["netlist_sha256"]
             and synthesis["checks"].get("netlist") == netlist
             and synthesis["checks"].get("scope") == "generic_technology_independent_no_pdk_no_delay",
             "synthesis_evidence_conflict", "This version derives specifications only from the recorded generic synthesis scope.")
    _check_simulation(simulation["checks"], plan, synthesis["netlist_sha256"])
    rtl_name, rtl_ports = _ports_with_ranges(candidate["rtl"])
    net_name, net_ports = _ports_with_ranges(netlist)
    _require(rtl_name == net_name == interface["module_name"], "public_module_conflict", "The original RTL and synthesized public module names must match.")
    rtl_map, net_map = ({port["name"]: port for port in ports} for ports in (rtl_ports, net_ports))
    _require(set(rtl_map) == set(net_map) == {port["name"] for port in interface["ports"]}, "public_ports_conflict", "Only the exact requested module boundary ports may be exported.")
    public_ports = []
    logical_ports = {port["id"]: port for port in node["ports"]}
    for expected in interface["ports"]:
        source, lowered = rtl_map[expected["name"]], net_map[expected["name"]]
        required_range = None if expected["width"] == 1 else {"msb": expected["width"] - 1, "lsb": 0}
        _require(all(source[key] == expected[key] for key in ("direction", "width", "signed"))
                 and source["range"] == required_range
                 and all(lowered[key] == source[key] for key in ("direction", "width", "range")),
                 "public_port_mapping_conflict", "Port names, directions, widths and literal bit order must match the original interface; netlist signed metadata may be lowered.")
        public_ports.append({"name": expected["name"], "direction": expected["direction"], "width": expected["width"],
                             "semantic_signed": expected["signed"], "source_rtl_signed": source["signed"],
                             "netlist_declared_signed": lowered["signed"], "rtl_range": source["range"], "netlist_range": lowered["range"],
                             "role": expected["role"], **({"logical_port_id": expected["logical_port_id"], "protocol": logical_ports[expected["logical_port_id"]]["protocol"]} if "logical_port_id" in expected else {})})
    trace = []
    template = verification_template_version(plan)
    scheduler = plan["kind"] == "npu_scheduler_stream"
    generic_cycles = plan["kind"] == "generic_cycle_vectors"
    additional_node = plan["kind"] in ("npu_buffer_stream", "npu_post_stream", "npu_fifo_stream", "npu_control_stream")
    array_fifo = (plan["kind"] == "npu2_array_node_original_job"
                  and plan.get("projected_plan_kind") == "fifo_original_job")
    fifo_spec = plan["kind"] == "fifo_original_job" or array_fifo
    npu2_recipe = not array_fifo and plan["kind"] in (
        "npu2_array_node_original_job",
        "npu2_control_original_job", "npu2_buffer_original_job", "npu2_scheduler_original_job",
        "npu2_dispatcher_original_job", "npu2_pe_original_job", "npu2_collector_original_job", "npu2_post_original_job",
    )
    if generic_cycles:
        from .generic_verification import cycle_asserted_trace
        trace = cycle_asserted_trace(plan)
    elif plan["kind"] == "npu2_array_node_original_job":
        from .npu2_array_verification import node_asserted_trace
        trace = node_asserted_trace(plan)
    elif plan["kind"] == "npu2_control_original_job":
        trace = _npu2_control_asserted_trace(plan)
    elif plan["kind"] == "npu2_buffer_original_job":
        trace = _npu2_buffer_asserted_trace(plan)
    elif plan["kind"] in ("npu2_scheduler_original_job", "npu2_dispatcher_original_job"):
        from .npu2_schedule_verification import schedule_asserted_trace
        trace = schedule_asserted_trace(plan)
    elif plan["kind"] in ("npu2_pe_original_job", "npu2_collector_original_job", "npu2_post_original_job"):
        from .npu2_datapath_verification import datapath_asserted_trace
        trace = datapath_asserted_trace(plan)
    elif fifo_spec:
        from .fifo_spec_verification import fifo_asserted_trace
        trace = fifo_asserted_trace(plan)
    elif scheduler:
        from .scheduler_verification import scheduler_asserted_trace
        trace = scheduler_asserted_trace(plan)
    elif additional_node:
        if plan["kind"] == "npu_control_stream":
            from .control_verification import control_asserted_trace
            trace = control_asserted_trace(plan)
        else:
            from .npu_nodes_verification import nodes_asserted_trace
            trace = nodes_asserted_trace(plan)
    elif plan["kind"] == "int8_mac_stream":
        for item in plan["reference_trace"]:
            before_checked = item["cycle"] != 0 or template == "legacy-bootstrap-v1"
            trace.append({"cycle": item["cycle"], "stimulus": copy.deepcopy(item["stimulus"]),
                          "input_transfer": item["input_transfer"], "output_transfer": item["output_transfer"],
                          "asserted_before": copy.deepcopy(item["before"]) if before_checked else None,
                          "asserted_after": {key: item["after"][key] for key in ("input_ready", "output_valid", "output_data")}})
    else:
        raise DomainError("unsupported_implementation_trace", "S07 has no assertion-trace extractor for this frozen verification plan kind.", 409)
    node_limits = ("Connected-system behavior, other matrix jobs and physical implementation remain unverified by this finite 2x2 node recipe."
                   if npu2_recipe else ("Real buffer/control/PE/FIFO integration, all K values beyond the source job, bias/ReLU execution and system completion remain unverified."
                   if scheduler else ("Connected-system behavior, other matrix jobs and physical implementation remain unverified by this finite FIFO proof." if fifo_spec else ("Connected full-NPU integration, 16-PE replication, K values beyond the saved job and physical implementation remain unverified by this finite node proof." if additional_node else "Global job-boundary reset, 16-PE replication, the other NPU blocks, K=1/16, bias/ReLU and FIFO integration remain unverified."))))
    if generic_cycles:
        node_limits = "Only the complete saved node cycle vectors were checked; connected-system behavior, other vectors, timing and physical implementation are not established."
    plan_limits = list(plan["limits"])
    if npu2_recipe:
        # These original RTL-plan sentences predate its adopted S05/S06
        # execution. Keep the frozen plan untouched while describing this
        # S07 document's actual evidence scope without a contradictory claim.
        prior_scope = {"No cross-node integration, synthesis, netlist, timing, layout, DRC, LVS or post-layout check is claimed.",
                       "No cross-node integration, full-NPU behavior, synthesis, timing, layout, DRC, LVS or post-layout check is claimed."}
        plan_limits = [limit for limit in plan_limits if limit not in prior_scope]
        plan_limits.append("Recorded S05/S06 evidence covers only this generic synthesized netlist and the saved finite recipe; cross-node/full-NPU behavior, PDK timing, layout, DRC, LVS and post-layout checks remain unverified.")
    limits = plan_limits + [
        "Assertions checked the saved independent reference trace; no raw waveform or independently captured actual trace is claimed.",
        "Requested latency and target clock period are requirements, not measured physical timing or PPA.",
        "Generic synthesis and zero-delay finite simulation do not establish formal equivalence or all possible inputs.",
        node_limits,
        "Only exact public boundary port names are stable for integration. Synthesized internal wire names are not a global API.",
        "Netlist declaration signedness may differ after lowering; integrate the adopted source RTL with its explicit signed contract.",
    ]
    return {"schema_version": "0.1", "origin": "ordinary_program_from_adopted_frozen_evidence",
            "original_requirements": {"node": copy.deepcopy(node), "connected_edges": copy.deepcopy([edge for edge in design["edges"] if node_id in (edge["source"]["node_id"], edge["target"]["node_id"])]),
                                      "settings": copy.deepcopy(design["settings"]), "verification_provenance": copy.deepcopy(node.get("verification_provenance")),
                                      "verification_jobs": copy.deepcopy(design.get("verification_jobs", [])),
                                      **({"verification_plan_limits": copy.deepcopy(plan["limits"])} if npu2_recipe or generic_cycles else {}),
                                      "classification": "requested_requirements_not_universal_verified_facts"},
            "public_interface": {"module_name": interface["module_name"], "ports": public_ports,
                                 "global_integration_artifact": "adopted_source_rtl", "internal_nets_exposed": False,
                                 "clock": interface["clock"], "reset": interface["reset"],
                                 "requested_reset_active": interface["reset_active"], "requested_reset_kind": interface["reset_kind"],
                                 "streams": [{"logical_port_id": port["id"], "direction": port["direction"], "protocol": port["protocol"],
                                              "data": port["name"], "valid": port["name"] + "_valid", "ready": port["name"] + "_ready"} for port in node["ports"] if port["protocol"] == "valid_ready"],
                                 **({"raw_signals": [{"logical_port_id": port["id"], "name": port["name"], "direction": port["direction"],
                                                     "width": port["width"], "sideband": copy.deepcopy(port.get("sideband"))}
                                                    for port in node["ports"] if port["protocol"] == "raw"]} if scheduler or additional_node or fifo_spec or npu2_recipe or generic_cycles else {}),
                                 "notes": ["Connect these exact public module boundary names; no arbitrary internal nets are exported.",
                                           "Source RTL signedness defines the global language contract; netlist bit-vector declarations are recorded separately."]},
            "observed_facts": {"scope": "finite_original_vectors_only", "classification": "assertions_checked_reference_trace",
                               "vector_count": plan["vector_count"], "coverage": copy.deepcopy(plan["coverage"]),
                               "signal_checks": plan["signal_checks"] if scheduler or additional_node or fifo_spec or npu2_recipe or generic_cycles else ["input_ready", "output_valid", "output_data"],
                               "checked_assertion_count": _assertion_site_count(trace),
                               **({"vector_unit": "recipe_step", "stimulus_timing": plan["stimulus_timing"],
                                   "assertion_count_scope": "static_recipe_assertion_sites_not_measured_runtime_samples",
                                   "trace_timing": "earliest_acceptance_reference_recipe_not_observed_dut_cycles",
                                   "harness_maximum_attempts_per_offer": 64} if npu2_recipe else {}),
                               **({"vector_unit": "cycle", "stimulus_timing": copy.deepcopy(plan["stimulus_timing"]),
                                   "assertion_count_scope": "all_saved_output_assertion_sites",
                                   "trace_timing": "fixed_saved_cycle_samples_not_a_waveform"} if generic_cycles else {}),
                               "trace": trace, "evidence_run_id": simulation["id"],
                               "initialization_origin": plan.get("initialization_origin", "saved_original_testbench_template"),
                               "simulation_scope": simulation["checks"].get("scope"),
                               "timing_claim": "zero_delay_functional_assertions_only"},
            "unverified_limits": limits,
            "lineage": {"source_revision_id": candidate["revision_id"], "node_id": node_id, "node_input_hash": source_hash,
                        "design_semantic_hash": design_hash, "candidate_id": candidate["id"], "synthesis_run_id": synthesis["id"], "netlist_run_id": simulation["id"],
                        "rtl_sha256": rtl_hash, "netlist_sha256": synthesis["netlist_sha256"],
                        "verification_plan_sha256": object_hash(plan), "vector_hash": plan["vector_hash"],
                        "reference_trace_hash": plan["reference_trace_hash"], "testbench_sha256": plan["testbench_sha256"],
                        "candidate_execution_hash": execution_evidence_hash(candidate), "synthesis_execution_hash": execution_evidence_hash(synthesis),
                        "simulation_execution_hash": execution_evidence_hash(simulation)},
            "checks": {"validation_status": "Passed", "executed": True, "scope": "deterministic_saved_evidence_consistency_check",
                       "items": [{"code": code, "status": "Passed", "message": message} for code, message in (
                           ("original_frozen_plan", "Original GUI snapshot rebuilt the exact existing vectors, reference and testbench."),
                           ("executed_source_proof", "S05 synthesis and S06 original-input netlist simulation executed and passed; S04 checks the public interface."
                            if simulation_scoped else "Original RTL and netlist tools executed and passed the same assertions."),
                           ("continuous_lineage", "Candidate, generic synthesis and netlist simulation share exact source and artifact hashes."),
                           ("public_boundary_mapping", "Only exact boundary names, directions, widths and bit order are exported; lowered signed metadata is explicit."),
                           ("finite_scope_separation", "Requested behavior, finite checked reference facts and unverified limits are separate."))]}}


class ImplementationSpecManager(ObservedState):
    """Append-only specification/review history in its own atomic JSON file."""
    def __init__(self, store, generation, workflow):
        self.store, self.generation, self.workflow = store, generation, workflow
        self.path = store.state_path.parent / "implementation_specs.json"
        self.lock = threading.RLock()
        self._storage_error = None
        self._state = {"implementation_spec_store_version": "0.1", "specs": [], "reviews": [], "node_inputs": {}, "node_epochs": {}, "current_design_hash": None}
        if _io_path(self.path).exists():
            try:
                self._state = strict_loads(_io_path(self.path).read_text(encoding="utf-8"))
                self._validate_saved()
            except (DomainError, OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                raise DomainError("invalid_implementation_spec_store", "Node implementation specification history is inconsistent; original file preserved.") from error
        self._committed = copy.deepcopy(self._state)
        self.observe_design()

    def _source(self, source_run_id):
        # Derive and checksum raw durable records. API decoration can replace
        # effective review_status after an input epoch changed; that decoration
        # is not part of the original saved execution record checksum.
        with self.workflow.lock:
            simulation = copy.deepcopy(self.workflow._run(source_run_id))
            synthesis = copy.deepcopy(self.workflow._run(simulation["prior_run_id"]))
        with self.generation.lock:
            candidate = copy.deepcopy(self.generation._stored_job(simulation["candidate_id"]))
        design = self.store.snapshot(candidate["revision_id"])
        return design, candidate, synthesis, simulation

    def _source_reviews(self, candidate, synthesis, simulation):
        generation = self.generation.envelope()["generation"]
        workflow = self.workflow.envelope()
        result = []
        for kind, identifier, reviews, key in (("candidate", candidate["id"], generation["reviews"], "job_id"),
                                               ("synthesis", synthesis["id"], workflow["workflow_reviews"], "run_id"),
                                               ("netlist_simulation", simulation["id"], workflow["workflow_reviews"], "run_id")):
            matches = [review for review in reviews if review[key] == identifier]
            _require(matches and matches[-1]["decision"] == "accepted", "source_not_adopted", "All current source results must have an authoritative adopted review.")
            result.append({"kind": kind, "review": copy.deepcopy(matches[-1])})
        return result

    def _eligible(self, node_id, source_run_id=None):
        current = self.store.envelope()
        _require(any(node["id"] == node_id for node in current["design"]["nodes"]), "node_not_found", "Select an existing current node.")
        _require(all(stage["review_status"] == "Accepted" and stage["freshness"] == "Current" for stage in current["workflow"] if stage["id"] in IMPLEMENTED_STAGES),
                 "review_prerequisite", "Current saved input checks must be adopted first.")
        tools = self.workflow.envelope()
        state = next(item for item in tools["workflow_nodes"] if item["node_id"] == node_id and item["stage_id"] == "local_netlist_simulation")
        _require(state["accepted_run_id"] is not None and (source_run_id is None or source_run_id == state["accepted_run_id"]),
                 "netlist_not_adopted", "Use the current latest Passed and adopted netlist simulation for this node.")
        data = self._source(state["accepted_run_id"])
        design, candidate, synthesis, simulation = data
        _require(revision_hashes(design)["semantic_hash"] == current["revision"]["semantic_hash"],
                 "design_source_conflict", "The specification must derive from the same complete semantic GUI design, without mixed revisions.")
        nodes = self.generation.envelope()["generation"]["nodes"]
        generation_node = next(item for item in nodes if item["node_id"] == node_id)
        synthesis_node = next(item for item in tools["workflow_nodes"] if item["node_id"] == node_id and item["stage_id"] == "local_synthesis")
        _require(generation_node["accepted_job_id"] == generation_node["latest_job_id"] == candidate["id"] and synthesis_node["accepted_run_id"] == synthesis["id"]
                 and all(item.get("freshness") == "Current" and item.get("review_status") == "Accepted" for item in
                         (self.generation.job(candidate["id"]), self.workflow.run(synthesis["id"]), self.workflow.run(simulation["id"]))),
                 "source_not_adopted", "Candidate and exact latest synthesis/netlist adoption must remain current.")
        return data

    @staticmethod
    def _derive(data):
        try:
            payload = build_node_implementation_spec(*data)
            return payload, "Passed", copy.deepcopy(payload["checks"]), None
        except DomainError as error:
            status = "Unsupported" if error.code in ("unsupported_public_interface", "unsupported_implementation_trace") else "Failed"
            diagnostic = {"code": error.code, "severity": "error", "message": error.message}
            checks = {"validation_status": status, "executed": True, "scope": "deterministic_saved_evidence_consistency_check",
                      "items": [{"code": error.code, "status": status, "message": error.message}]}
            return None, status, checks, diagnostic

    def _validate_saved(self):
        state = self._state
        _require(type(state) is dict and state.get("implementation_spec_store_version") == "0.1"
                 and all(type(state.get(key)) is list for key in ("specs", "reviews"))
                 and all(type(state.get(key)) is dict for key in ("node_inputs", "node_epochs"))
                 and all(type(epoch) is int and epoch >= 0 for epoch in state["node_epochs"].values()),
                 "invalid_spec_containers", "Invalid saved implementation specification containers.")
        policies = validate_policy_history(self.store.envelope())
        # Authoritative historical review records are persisted provenance;
        # constructing current GUI envelopes cannot add evidence to them.
        if hasattr(self.generation, "_stored_job"):
            with self.generation.lock:
                generation_reviews = copy.deepcopy(self.generation._state["reviews"])
        else:
            generation_reviews = self.generation.envelope()["generation"]["reviews"]
        if hasattr(self.workflow, "_run"):
            with self.workflow.lock:
                workflow_reviews = copy.deepcopy(self.workflow._state["reviews"])
        else:
            workflow_reviews = self.workflow.envelope()["workflow_reviews"]
        sources = generation_reviews + workflow_reviews
        ids = set()
        for spec in state["specs"]:
            _require(type(spec) is dict and type(spec.get("id")) is str and spec["id"] not in ids
                     and spec.get("stage_id") == STAGE and spec.get("execution_status") == "Completed"
                     and spec.get("validation_status") in ("Passed", "Failed", "Unsupported") and spec.get("review_status") in ("Awaiting Review", "Accepted", "Changes Requested"),
                     "invalid_spec_record", "Invalid saved implementation specification record.")
            ids.add(spec["id"])
            _require(spec.get("record_hash") == object_hash({key: value for key, value in spec.items() if key != "record_hash"}), "spec_checksum_conflict", "Specification record checksum mismatch.")
            data = self._source(spec["source_run_id"])
            design, candidate, synthesis, simulation = data
            rebuilt, status, checks, error = self._derive(data)
            _require(spec["specification"] == rebuilt and spec.get("specification_sha256") == (object_hash(rebuilt) if rebuilt else None)
                     and spec["validation_status"] == status and spec["checks"] == checks and spec.get("error") == error
                     and spec.get("diagnostics") == ([error] if error else [])
                     and spec["revision_id"] == candidate["revision_id"] and spec["node_id"] == candidate["node_id"]
                     and spec["candidate_id"] == candidate["id"] and spec["design_hash"] == revision_hashes(design)["semantic_hash"]
                     and spec["input_hash"] == candidate["input_hash"],
                     "spec_source_conflict", "Saved specification does not rebuild from its original executed evidence.")
            requested_snapshot = self.store.snapshot(spec["requested_revision_id"])
            _require(revision_hashes(requested_snapshot)["semantic_hash"] == spec["design_hash"], "spec_source_conflict", "Requested specification revision must have the same original semantic design.")
            source_adoptions = spec.get("source_adoptions")
            identities = {"candidate": ("job_id", candidate["id"]), "synthesis": ("run_id", synthesis["id"]), "netlist_simulation": ("run_id", simulation["id"])}
            _require(type(source_adoptions) is list and len(source_adoptions) == 3
                     and {item.get("kind") for item in source_adoptions} == set(identities)
                     and all(item["review"] in sources and item["review"]["decision"] == "accepted"
                             and item["review"].get(identities[item["kind"]][0]) == identities[item["kind"]][1]
                             and revision_hashes(self.store.snapshot(item["review"]["reviewed_revision_id"]))["semantic_hash"] == spec["design_hash"]
                             for item in source_adoptions),
                     "spec_adoption_conflict", "Missing authoritative historical source adoption records.")
            reviews = [item for item in state["reviews"] if item.get("spec_id") == spec["id"]]
            expected_status = "Awaiting Review" if not reviews else "Accepted" if reviews[-1]["decision"] == "accepted" else "Changes Requested"
            _require(spec["review_status"] == expected_status and (expected_status != "Accepted" or status == "Passed" and spec.get("acceptance_epoch") == reviews[-1].get("acceptance_epoch")),
                     "spec_review_conflict", "Saved specification adoption does not match the latest review.")
        for review in state["reviews"]:
            _require(type(review) is dict and review.get("spec_id") in ids and review.get("decision") in ("accepted", "changes_requested", "return_to_stage")
                     and review.get("actor") in REVIEW_ACTORS and type(review.get("note")) is str,
                     "invalid_spec_review", "Invalid saved specification review.")
            validate_policy_review(review, policies)
            spec = next(item for item in state["specs"] if item["id"] == review["spec_id"])
            reviewed_snapshot = self.store.snapshot(review["reviewed_revision_id"])
            _require(review.get("node_id") == spec["node_id"] and review.get("source_run_id") == spec["source_run_id"], "spec_review_conflict", "Review must identify its exact source node and netlist result.")
            if review["decision"] == "accepted":
                _require(spec["validation_status"] == "Passed" and revision_hashes(reviewed_snapshot)["semantic_hash"] == spec["design_hash"]
                         and type(review.get("acceptance_epoch")) is int and 0 <= review["acceptance_epoch"] <= state["node_epochs"].get(spec["node_id"], -1),
                         "spec_review_conflict", "Acceptance must bind a Passed specification to the original semantic inputs and a valid adoption epoch.")
            _require(review["decision"] == "accepted" or bool(review["note"].strip()), "invalid_spec_review", "Correction and return reviews require feedback.")
            _require(review.get("target_stage") in EARLIER_STAGES if review["decision"] == "return_to_stage" else review.get("target_stage") is None,
                     "invalid_spec_review", "Review target must be an implemented earlier stage only.")

    def _persist(self):
        require_durable_write()
        name = None
        try:
            for spec in self._state["specs"]:
                spec["record_hash"] = object_hash({key: value for key, value in spec.items() if key != "record_hash"})
            descriptor, name = tempfile.mkstemp(prefix=".implementation-specs-", suffix=".tmp", dir=_io_path(self.path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(self._state, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
                handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, self.path)
            self._committed, self._storage_error = copy.deepcopy(self._state), None
        except (OSError, ValueError, TypeError):
            self._state = copy.deepcopy(self._committed)
            self._storage_error = {"code": "storage_error", "message": "Implementation specification could not be saved; last durable state retained."}
            raise
        finally:
            if name and _io_path(name).exists():
                _io_path(name).unlink()

    def observe_design(self):
        current = self.store.envelope()
        inputs = {node["id"]: node_fingerprint(current["design"], node["id"]) for node in current["design"]["nodes"]}
        design_hash = current["revision"]["semantic_hash"]
        with self.lock:
            if inputs == self._state["node_inputs"] and design_hash == self._state["current_design_hash"]:
                return
            for node_id in set(inputs) | set(self._state["node_inputs"]):
                if design_hash != self._state["current_design_hash"] or inputs.get(node_id) != self._state["node_inputs"].get(node_id):
                    self._state["node_epochs"][node_id] = self._state["node_epochs"].get(node_id, 0) + 1
            self._state.update(node_inputs=inputs, current_design_hash=design_hash)
            if _io_path(self.path).exists():
                persist_observation(self)

    def _spec(self, spec_id):
        result = next((spec for spec in self._state["specs"] if spec["id"] == spec_id), None)
        if result is None:
            raise DomainError("implementation_spec_not_found", "Node implementation specification does not exist.", 404)
        return result

    def _decorate(self, spec):
        result = copy.deepcopy(spec)
        current = self._state["current_design_hash"] == spec["design_hash"] and self._state["node_inputs"].get(spec["node_id"]) == spec["input_hash"]
        reason = None
        if current:
            try:
                _, candidate, synthesis, simulation = self._eligible(spec["node_id"], spec["source_run_id"])
                _require(spec["source_adoptions"] == self._source_reviews(candidate, synthesis, simulation),
                         "source_adoption_changed", "The source adoption decisions changed; derive a new specification from current adopted evidence.")
            except DomainError as error:
                current, reason = False, error.message
        result["freshness"] = "Current" if current else "Stale"
        result["source_current"] = current
        result["blocked_reason"] = reason if reason else None if current else "The current semantic design differs from the original saved source."
        if result["review_status"] == "Accepted" and (not current or spec.get("acceptance_epoch") != self._state["node_epochs"].get(spec["node_id"])):
            result["review_status"] = "Awaiting Review"
        result["artifacts"] = [{"kind": "implementation_spec", "url": f"/api/implementation-specs/{spec['id']}"},
                               {"kind": "design_input_snapshot", "url": f"/api/snapshots/{spec['revision_id']}"},
                               {"kind": "source_netlist_simulation", "url": f"/api/workflow/runs/{spec['source_run_id']}"}]
        return result

    @memoized_envelope
    def envelope(self):
        self.observe_design()
        with self.lock:
            specs = [self._decorate(spec) for spec in self._state["specs"]]
            nodes = []
            for node_id in self._state["node_inputs"]:
                relevant = [spec for spec in specs if spec["node_id"] == node_id]
                latest = relevant[-1] if relevant else None
                try:
                    data = self._eligible(node_id)
                    source_run_id, ready, reason = data[-1]["id"], True, None
                except DomainError as error:
                    source_run_id, ready, reason = None, False, error.message
                nodes.append({"node_id": node_id, "latest_spec_id": latest["id"] if latest else None,
                              "accepted_spec_id": latest["id"] if latest and latest["freshness"] == "Current" and latest["review_status"] == "Accepted" else None,
                              "source_run_id": source_run_id, "ready": ready, "blocked_reason": reason})
            return {"implementation_specs": specs, "implementation_spec_nodes": nodes,
                    "implementation_spec_reviews": copy.deepcopy(self._state["reviews"]), "implementation_specs_storage_error": copy.deepcopy(self._storage_error)}

    def spec(self, spec_id):
        self.observe_design()
        with self.lock:
            return self._decorate(self._spec(spec_id))

    def _result_envelope(self):
        # Only the final read view is shared. Eligibility, derivation, adoption
        # and durable persistence must finish before entering this scope.
        with read_scope():
            return self.envelope()

    def start(self, node_id, revision_id, source_run_id=None):
        if any(type(value) is not str for value in (node_id, revision_id)) or source_run_id is not None and type(source_run_id) is not str:
            raise DomainError("invalid_request", "Provide current node_id, revision_id and optional source_run_id as text.")
        self.observe_design()
        # Match the existing source managers' lock order. Holding all source
        # locks makes extraction/adoption atomic with source review and save.
        with self.lock, self.workflow.lock, self.generation.lock, self.store.lock:
            self.observe_design()
            _require(revision_id == self.store.envelope()["revision"]["id"], "revision_conflict", "Build from the current saved GUI revision.")
            data = self._eligible(node_id, source_run_id)
            payload, status, checks, error = self._derive(data)
            design, candidate, synthesis, simulation = data
            _require(len(self._state["specs"]) < 1000, "history_limit", "Archive reviewed specification evidence before adding more than 1000 records.")
            now = utc_now()
            spec = {"id": new_id("implementation-spec"), "stage_id": STAGE, "node_id": node_id,
                    "revision_id": candidate["revision_id"], "requested_revision_id": revision_id,
                    "input_hash": candidate["input_hash"], "design_hash": revision_hashes(design)["semantic_hash"],
                    "source_run_id": simulation["id"], "candidate_id": candidate["id"], "execution_status": "Completed",
                    "validation_status": status, "review_status": "Awaiting Review", "created_at": now, "finished_at": now,
                    "checks": checks, "diagnostics": [copy.deepcopy(error)] if error else [], "error": error, "specification": payload,
                    "specification_sha256": object_hash(payload) if payload else None, "source_adoptions": self._source_reviews(candidate, synthesis, simulation)}
            self._state["specs"].append(spec)
            policy = self.store.review_policy()
            if status == "Passed" and policy["mode"] == "accept_on_pass" and policy["user_authorized"] is True:
                self._record_review(spec, "accepted", "Accepted after deterministic validation of the same adopted original finite evidence under the user's saved policy.", None,
                                    "automation_policy", self.store.policy_provenance())
            self._persist()
        return self._result_envelope()

    def _record_review(self, spec, decision, note, target_stage, actor, provenance=None):
        spec["review_status"] = "Accepted" if decision == "accepted" else "Changes Requested"
        if decision == "accepted":
            spec["acceptance_epoch"] = self._state["node_epochs"][spec["node_id"]]
        review = {"id": new_id("implementation-spec-review"), "spec_id": spec["id"], "node_id": spec["node_id"],
                  "source_run_id": spec["source_run_id"], "decision": decision, "note": note, "actor": actor, "target_stage": target_stage,
                  "created_at": utc_now(), "acceptance_epoch": spec.get("acceptance_epoch"),
                  "reviewed_revision_id": self.store.envelope()["revision"]["id"]}
        if provenance:
            review["provenance"] = copy.deepcopy(provenance)
        self._state["reviews"].append(review)

    def review(self, spec_id, decision, note, target_stage=None, *, operator=None):
        fields = manual_review_fields(operator)
        if type(spec_id) is not str or decision not in ("accepted", "changes_requested", "return_to_stage") or type(note) is not str or decision != "accepted" and not note.strip():
            raise DomainError("invalid_spec_review", "Provide a valid specification decision and correction/return feedback.")
        if (decision == "return_to_stage" and target_stage not in EARLIER_STAGES) or decision != "return_to_stage" and target_stage is not None:
            raise DomainError("invalid_target_stage", "Choose an implemented earlier stage only when returning.")
        self.observe_design()
        with self.lock, self.workflow.lock, self.generation.lock, self.store.lock:
            self.observe_design()
            spec = self._spec(spec_id)
            relevant = [item for item in self._state["specs"] if item["node_id"] == spec["node_id"]]
            _require(relevant[-1]["id"] == spec_id, "implementation_spec_superseded", "Review the latest specification for this node.")
            if decision == "accepted":
                _require(spec["validation_status"] == "Passed", "implementation_spec_not_passed", "Only a Passed deterministic specification can be accepted.")
                _require(self._decorate(spec)["freshness"] == "Current", "implementation_spec_stale", "Only a current specification with current source adoption can be accepted.")
                rebuilt = build_node_implementation_spec(*self._eligible(spec["node_id"], spec["source_run_id"]))
                _require(spec["specification"] == rebuilt, "spec_source_conflict", "The payload no longer matches original executed evidence.")
            # Feedback and navigation remain available for stale historical
            # evidence; they do not alter the original source or tool results.
            self._record_review(spec, decision, note, target_stage, fields["actor"], fields["provenance"])
            self._persist()
        return self._result_envelope()
