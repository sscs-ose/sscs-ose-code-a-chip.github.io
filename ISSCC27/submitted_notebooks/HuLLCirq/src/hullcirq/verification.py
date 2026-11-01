"""Deterministic PE stimulus/reference/TB from the original structured input.

The supported contract is deliberately finite and narrow. This is functional
cycle simulation, never synthesis, timing, PDK, or full-NPU verification.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time

from .context import build_node_context
from .domain import DomainError


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def object_hash(value) -> str:
    return content_hash(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False))


def _problem(code, message, severity="error"):
    return {"code": code, "message": message, "severity": severity}


def _signed8(value):
    value &= 255
    return value - 256 if value & 128 else value


def reference_trace(vectors: list[dict]) -> list[dict]:
    """Independent integer state machine; never reads generated RTL."""
    accumulator = data = valid = 0
    result = []
    for index, vector in enumerate(vectors):
        ready = int(not valid or vector["output_ready"])
        before = {"input_ready": ready, "output_valid": valid, "output_data": data}
        a, b = _signed8(vector["input_data"]), _signed8(vector["input_data"] >> 8)
        transfer = int(not vector["reset"] and vector["input_valid"] and ready)
        consumed = int(not vector["reset"] and valid and vector["output_ready"])
        if vector["reset"]:
            accumulator = data = valid = 0
        elif transfer:
            accumulator = (accumulator + a * b) & 0xFFFFFFFF
            data, valid = accumulator, 1
        elif consumed:
            valid = 0
        after = {"input_ready": int(not valid or vector["output_ready"]),
                 "output_valid": valid, "output_data": data, "accumulator": accumulator}
        result.append({"cycle": index, "stimulus": copy.deepcopy(vector), "a": a, "b": b,
                       "input_transfer": transfer, "output_transfer": consumed, "before": before, "after": after})
    return result


def _testbench(module_name, input_port, output_port, trace, vector_hash, template_version="original-vectors-v2"):
    lines = ["`timescale 1ns/1ps", "module hullcirq_contract_tb;", "reg clk; reg rst;",
             "reg [15:0] stimulus_data; reg stimulus_valid; reg sink_ready;",
             "wire stimulus_ready; wire signed [31:0] observed_data; wire observed_valid;",
             f"{module_name} dut (.clk(clk), .rst(rst), .{input_port}(stimulus_data),",
             f"  .{input_port}_valid(stimulus_valid), .{input_port}_ready(stimulus_ready),",
             f"  .{output_port}(observed_data), .{output_port}_valid(observed_valid), .{output_port}_ready(sink_ready));",
             "initial begin", "clk=0; rst=1; stimulus_data=0; stimulus_valid=0; sink_ready=0;"]
    if template_version == "legacy-bootstrap-v1":
        lines += ["// Initialize the synchronous state before checking the first vector.", "#5; clk=1; #5; clk=0;"]
    for item in trace:
        vector, before, after = item["stimulus"], item["before"], item["after"]
        index = item["cycle"]
        lines += [f"// Original design vector {index}",
                  f"clk=0; rst=1'b{vector['reset']}; stimulus_data=16'h{vector['input_data']:04x};",
                  f"stimulus_valid=1'b{vector['input_valid']}; sink_ready=1'b{vector['output_ready']}; #4;"]
        for phase, values in (("before", before), ("after", after)):
            if phase == "before" and index == 0 and template_version != "legacy-bootstrap-v1":
                # The original first reset vector establishes state. Do not
                # insert an extra stage-specific initialization vector.
                continue
            if phase == "after":
                lines.append("#1; clk=1; #1;")
            for observed, key, literal in (("stimulus_ready", "input_ready", "1'b"),
                                           ("observed_valid", "output_valid", "1'b"),
                                           ("observed_data", "output_data", "32'h")):
                expected = literal + (f"{values[key]:08x}" if key == "output_data" else str(values[key]))
                lines.append(f'if ({observed} !== {expected}) begin $display("HULLCIRQ_FAIL cycle={index} phase={phase} signal={key} expected=%h actual=%h", {expected}, {observed}); $finish; end')
        lines.append("#4; clk=0;")
    lines += [f'$display("HULLCIRQ_PASS vectors={len(trace)} vector_hash={vector_hash}");', "$finish;", "end", "endmodule", ""]
    return "\n".join(lines)


def verification_template_version(plan: dict) -> str:
    """Read-only compatibility for early frozen plans, never edit evidence."""
    if type(plan) is not dict:
        raise DomainError("invalid_verification_plan", "Saved verification plan must be an object.")
    if plan.get("kind") == "generic_cycle_vectors":
        from .generic_verification import TEMPLATE
        if plan.get("testbench_template_version") != TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported generic cycle-vector testbench template.")
        return TEMPLATE
    if plan.get("kind") == "npu2_array_node_original_job":
        from .npu2_array_verification import NODE_TEMPLATE
        if plan.get("testbench_template_version") != NODE_TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported shared-array node testbench template.")
        return NODE_TEMPLATE
    if plan.get("kind") in ("npu2_scheduler_original_job", "npu2_dispatcher_original_job"):
        from .npu2_schedule_verification import template_for_kind
        template = template_for_kind(plan["kind"])
        if plan.get("testbench_template_version") != template:
            raise DomainError("unsupported_verification_template", "Unsupported 2x2 scheduling testbench template.")
        return template
    if plan.get("kind") in ("npu2_pe_original_job", "npu2_collector_original_job", "npu2_post_original_job"):
        from .npu2_datapath_verification import TEMPLATE
        if plan.get("testbench_template_version") != TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported 2x2 datapath testbench template.")
        return TEMPLATE
    if plan.get("kind") == "fifo_original_job":
        from .fifo_spec_verification import TEMPLATE
        if plan.get("testbench_template_version") != TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported FIFO saved-specification template.")
        return TEMPLATE
    if plan.get("kind") == "npu2_control_original_job":
        from .npu2_control_verification import TEMPLATE
        if plan.get("testbench_template_version") != TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported 2x2 control testbench template.")
        return TEMPLATE
    if plan.get("kind") == "npu2_buffer_original_job":
        from .npu2_buffer_verification import TEMPLATE
        if plan.get("testbench_template_version") != TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported 2x2 buffer testbench template.")
        return TEMPLATE
    if plan.get("kind") == "npu_scheduler_stream":
        from .scheduler_verification import TEMPLATE
        if plan.get("testbench_template_version") != TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported scheduler testbench template.")
        return TEMPLATE
    if plan.get("kind") in ("npu_buffer_stream", "npu_post_stream", "npu_fifo_stream"):
        from .npu_nodes_verification import TEMPLATE
        if plan.get("testbench_template_version") != TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported NPU node testbench template.")
        return TEMPLATE
    if plan.get("kind") == "npu_control_stream":
        from .control_verification import TEMPLATE
        if plan.get("testbench_template_version") != TEMPLATE:
            raise DomainError("unsupported_verification_template", "Unsupported control testbench template.")
        return TEMPLATE
    version = plan.get("testbench_template_version")
    if version is None:
        version = "legacy-bootstrap-v1" if "// Initialize the synchronous state before checking the first vector." in plan.get("testbench", "") else "original-vectors-v1"
    if version not in ("legacy-bootstrap-v1", "original-vectors-v1", "original-vectors-v2"):
        raise DomainError("unsupported_verification_template", "The saved verification template is unsupported; evidence was preserved.")
    return version


def build_verification_plan(design: dict, node_id: str, template_version=None) -> dict:
    requested = next((node.get("verification") for node in design.get("nodes", []) if node.get("id") == node_id), None)
    if type(requested) is dict and requested.get("kind") == "generic_cycle_vectors":
        from .generic_verification import build_node_plan
        return build_node_plan(design, node_id, template_version)
    if any(node.get("id") == "npu2-pe" for node in design.get("nodes", [])):
        from .npu2_array_verification import build_node_plan
        return build_node_plan(design, node_id, template_version)
    requested = next((node.get("verification") for node in design.get("nodes", []) if node.get("id") == node_id), None)
    if requested is None:
        from .fifo_spec_verification import build_fifo_plan, recognizes_fifo_spec
        node = next((node for node in design.get("nodes", []) if node.get("id") == node_id), None)
        if recognizes_fifo_spec(node):
            return build_fifo_plan(design, node_id, template_version)
    if requested is None and node_id == "npu2-control":
        from .npu2_control_verification import build_control_plan
        return build_control_plan(design, node_id, template_version)
    if requested is None and node_id == "npu2-buffer":
        from .npu2_buffer_verification import build_buffer_plan
        return build_buffer_plan(design, node_id, template_version)
    if requested is None and node_id in ("npu2-scheduler", "npu2-dispatcher"):
        from .npu2_schedule_verification import build_scheduler_plan, build_dispatcher_plan
        builder = build_scheduler_plan if node_id == "npu2-scheduler" else build_dispatcher_plan
        return builder(design, node_id, template_version)
    if requested is None and node_id in ("npu2-pe00", "npu2-pe01", "npu2-pe10", "npu2-pe11", "npu2-collector", "npu2-post"):
        from .npu2_datapath_verification import build_datapath_plan
        return build_datapath_plan(design, node_id, template_version)
    if type(requested) is dict and requested.get("kind") == "npu_scheduler_stream":
        from .scheduler_verification import build_scheduler_plan
        return build_scheduler_plan(design, node_id, template_version)
    if type(requested) is dict and requested.get("kind") in ("npu_buffer_stream", "npu_post_stream", "npu_fifo_stream"):
        from .npu_nodes_verification import build_nodes_plan
        return build_nodes_plan(design, node_id, template_version)
    if type(requested) is dict and requested.get("kind") == "npu_control_stream":
        from .control_verification import build_control_plan
        return build_control_plan(design, node_id, template_version)
    template_version = template_version or "original-vectors-v2"
    if template_version not in ("legacy-bootstrap-v1", "original-vectors-v1", "original-vectors-v2"):
        raise DomainError("unsupported_verification_template", "Unsupported behavioral testbench template.")
    nodes = [node for node in design.get("nodes", []) if node.get("id") == node_id]
    if len(nodes) != 1:
        raise DomainError("invalid_verification_node", "Verification needs one existing design node.")
    contract = nodes[0].get("verification")
    if contract is None:
        raise DomainError("verification_contract_missing", "The original design has no structured behavioral verification contract.")
    required = {"kind", "version", "input_port", "output_port", "accumulator_width", "initial_accumulator", "vectors"}
    if type(contract) is not dict or set(contract) != required:
        raise DomainError("invalid_verification_contract", "The verification contract has missing or unsupported fields.")
    if contract["kind"] != "int8_mac_stream" or type(contract["version"]) is not int or contract["version"] != 1:
        raise DomainError("unsupported_verification_contract", "Only int8_mac_stream version 1 is supported.")
    if type(contract["accumulator_width"]) is not int or contract["accumulator_width"] != 32 or type(contract["initial_accumulator"]) is not int or contract["initial_accumulator"] != 0:
        raise DomainError("unsupported_verification_contract", "This contract requires a 32-bit accumulator reset to zero.")
    vectors = contract["vectors"]
    if type(vectors) is not list or not 2 <= len(vectors) <= 256:
        raise DomainError("invalid_verification_vectors", "Supply 2 to 256 cycle vectors in the original node specification.")
    normalized = []
    for vector in vectors:
        if type(vector) is not dict or set(vector) != {"reset", "input_valid", "output_ready", "input_data"}:
            raise DomainError("invalid_verification_vectors", "Each vector requires reset, input_valid, output_ready, and packed input_data.")
        if any(type(vector[key]) not in (bool, int) or vector[key] not in (0, 1) for key in ("reset", "input_valid", "output_ready")) or type(vector["input_data"]) is not int or not 0 <= vector["input_data"] <= 65535:
            raise DomainError("invalid_verification_vectors", "Control values must be Boolean and packed data an unsigned 16-bit integer.")
        normalized.append({key: int(value) for key, value in vector.items()})
    if not normalized[0]["reset"]:
        raise DomainError("invalid_verification_vectors", "The first original vector must assert synchronous reset.")
    context = build_node_context(design, "verification-source", node_id)
    interface = context["interface"]
    ports = {port["name"]: port for port in interface["ports"]}
    input_port, output_port = contract["input_port"], contract["output_port"]
    if type(input_port) is not str or type(output_port) is not str:
        raise DomainError("invalid_verification_contract", "Contract port names must be text.")
    expected = {"clk": ("input", 1, False), "rst": ("input", 1, False),
                input_port: ("input", 16, False), input_port + "_valid": ("input", 1, False), input_port + "_ready": ("output", 1, False),
                output_port: ("output", 32, True), output_port + "_valid": ("output", 1, False), output_port + "_ready": ("input", 1, False)}
    if set(expected) != set(ports) or any((ports[name]["direction"], ports[name]["width"], ports[name]["signed"]) != value for name, value in expected.items()):
        raise DomainError("invalid_verification_interface", "PE verification requires exactly the declared packed input, signed accumulator output, clock/reset, and valid/ready ports.")
    frozen_contract = copy.deepcopy(contract)
    frozen_contract["vectors"] = normalized
    vector_hash = object_hash(normalized)
    trace = reference_trace(normalized)
    if not any(item["input_transfer"] for item in trace):
        raise DomainError("invalid_verification_vectors", "Original vectors must exercise at least one input transfer.")
    tb = _testbench(interface["module_name"], input_port, output_port, trace, vector_hash, template_version)
    result = {"kind": "int8_mac_stream", "version": 1, "source_node_id": node_id, "module_name": interface["module_name"],
            "node_input_hash": context["node_input_hash"], "input_port": input_port, "output_port": output_port,
            "contract": frozen_contract, "contract_hash": object_hash(frozen_contract), "vector_hash": vector_hash,
            "reference_trace": trace, "reference_trace_hash": object_hash(trace), "testbench": tb, "testbench_sha256": content_hash(tb),
            "vector_count": len(trace), "stimulus_origin": "original_design_node.verification.vectors",
            "reference_origin": "ordinary_program_integer_state_machine_from_structured_contract",
            "testbench_origin": "ordinary_program_from_original_vectors_and_independent_reference",
            "coverage": {"input_transfers": sum(item["input_transfer"] for item in trace),
                         "output_transfers": sum(item["output_transfer"] for item in trace),
                         "reset_cycles": sum(vector["reset"] for vector in normalized),
                         "stall_cycles": sum(item["before"]["output_valid"] and not item["stimulus"]["output_ready"] and not item["stimulus"]["reset"] for item in trace),
                         "simultaneous_transfers": sum(item["input_transfer"] and item["output_transfer"] for item in trace)},
            "limits": ["Finite original cycle vectors only; not exhaustive formal verification.",
                       "No propagation delay, PDK cell timing, or full-NPU behavior is checked.",
                       "Overflow coverage is not claimed unless the original vectors actually reach it."]}
    if template_version == "original-vectors-v2":
        result["testbench_template_version"] = template_version
        result["initialization_origin"] = "first_original_design_vector_asserting_synchronous_reset"
        result["limits"].append("Power-up state before the first original synchronous reset edge is not observed or assumed.")
    return result


def validate_plan(plan: dict) -> None:
    if type(plan) is dict and plan.get("kind") == "generic_cycle_vectors":
        from .generic_verification import validate_cycle_plan
        validate_cycle_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") == "npu2_array_node_original_job":
        from .npu2_array_verification import validate_node_plan
        validate_node_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") in ("npu2_scheduler_original_job", "npu2_dispatcher_original_job"):
        from .npu2_schedule_verification import validate_schedule_plan
        validate_schedule_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") in ("npu2_pe_original_job", "npu2_collector_original_job", "npu2_post_original_job"):
        from .npu2_datapath_verification import validate_datapath_plan
        validate_datapath_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") == "fifo_original_job":
        from .fifo_spec_verification import validate_fifo_plan
        validate_fifo_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") == "npu2_control_original_job":
        from .npu2_control_verification import validate_control_plan
        validate_control_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") == "npu2_buffer_original_job":
        from .npu2_buffer_verification import validate_buffer_plan
        validate_buffer_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") in ("npu_buffer_stream", "npu_post_stream", "npu_fifo_stream"):
        from .npu_nodes_verification import validate_nodes_plan
        validate_nodes_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") == "npu_control_stream":
        from .control_verification import validate_control_plan
        validate_control_plan(plan)
        return
    if type(plan) is dict and plan.get("kind") == "npu_scheduler_stream":
        from .scheduler_verification import validate_scheduler_plan
        validate_scheduler_plan(plan)
        return
    if type(plan) is not dict or plan.get("kind") != "int8_mac_stream" or plan.get("version") != 1:
        raise DomainError("invalid_verification_plan", "A frozen supported verification plan is required.")
    try:
        valid = (object_hash(plan["contract"]) == plan["contract_hash"] and object_hash(plan["contract"]["vectors"]) == plan["vector_hash"] and
                 reference_trace(plan["contract"]["vectors"]) == plan["reference_trace"] and object_hash(plan["reference_trace"]) == plan["reference_trace_hash"] and
                 content_hash(plan["testbench"]) == plan["testbench_sha256"] and
                 _testbench(plan["module_name"], plan["input_port"], plan["output_port"], plan["reference_trace"], plan["vector_hash"], verification_template_version(plan)) == plan["testbench"])
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise DomainError("invalid_verification_plan", "Frozen stimulus, reference, and testbench evidence is inconsistent.")


def _wsl_path(path: Path) -> str:
    value = str(path.resolve())
    if len(value) < 3 or value[1] != ":":
        raise DomainError("unsupported_compiler", "WSL verification needs a local Windows drive path.")
    return "/mnt/" + value[0].lower() + "/" + value[3:].replace("\\", "/")


def trusted_command(config: dict, executable: str, arguments: list[str], cwd: Path) -> list[str]:
    if type(config) is not dict or config.get("kind") not in ("wsl", "native") or type(executable) is not str or any(ord(c) < 32 for c in executable):
        raise DomainError("invalid_tool", "A trusted fixed tool configuration is required.")
    if config["kind"] == "native":
        if not Path(executable).is_absolute():
            raise DomainError("invalid_tool", "Native tool paths must be absolute.")
        return [executable, *arguments]
    distribution = config.get("distribution")
    import re
    if type(distribution) is not str or not re.fullmatch(r"[A-Za-z0-9_.-]+", distribution) or not executable.startswith("/"):
        raise DomainError("invalid_tool", "WSL tool configuration requires a distribution and absolute executable.")
    wsl = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32" / "wsl.exe"
    return [str(wsl), "-d", distribution, "--cd", _wsl_path(cwd), "--exec", executable, *arguments]


def execute_fixed(command: list[str], cwd: Path, cancel_event=None, timeout=30) -> dict:
    """No shell; bounded fixed operation with cancellation and captured logs."""
    if cancel_event is not None and cancel_event.is_set():
        return {"executed": False, "exit_code": None, "status": "Cancelled", "stdout": "", "stderr": "", "command": command}
    started = time.monotonic()
    try:
        process = subprocess.Popen(command, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding="utf-8", errors="replace", shell=False)
    except OSError as error:
        return {"executed": False, "exit_code": None, "status": "Unsupported", "stdout": "", "stderr": str(error), "command": command}
    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.1)
            return {"executed": True, "exit_code": process.returncode, "status": "Completed", "stdout": stdout, "stderr": stderr,
                    "command": command, "elapsed_seconds": time.monotonic() - started}
        except subprocess.TimeoutExpired:
            cancelled = cancel_event is not None and cancel_event.is_set()
            if cancelled or time.monotonic() - started >= timeout:
                process.kill()
                stdout, stderr = process.communicate()
                return {"executed": True, "exit_code": process.returncode, "status": "Cancelled" if cancelled else "Timeout",
                        "stdout": stdout, "stderr": stderr, "command": command, "elapsed_seconds": time.monotonic() - started}


def verify_behavior(rtl: str, plan: dict, compiler: dict | None, working_directory=None, cancel_event=None, *, record_waveform=False) -> dict:
    validate_plan(plan)
    result = {"validation_status": "Unsupported", "executed": False, "exit_code": None, "diagnostics": [], "commands": [],
              "stdout": "", "stderr": "", "scope": "finite_cycle_functional_simulation_no_delay",
              "vector_hash": plan["vector_hash"], "testbench_sha256": plan["testbench_sha256"], "rtl_sha256": content_hash(rtl),
              "reference_trace_hash": plan["reference_trace_hash"], "vector_count": plan["vector_count"], "coverage": plan["coverage"],
              "stimulus_origin": plan["stimulus_origin"], "reference_origin": plan["reference_origin"], "limits": plan["limits"]}
    result["testbench_template_version"] = verification_template_version(plan)
    result["initialization_origin"] = plan.get("initialization_origin", "bootstrap_reset_from_contract_then_original_vectors" if result["testbench_template_version"] == "legacy-bootstrap-v1" else "first_original_reset_vector")
    if compiler is None:
        result["diagnostics"].append(_problem("behavior_compiler_unavailable", "Configure trusted Icarus and vvp before behavioral acceptance.", "warning"))
        return result
    executable = compiler.get("executable")
    if type(executable) is not str or executable.replace("\\", "/").split("/")[-1].lower() not in ("iverilog", "iverilog.exe"):
        raise DomainError("invalid_compiler", "Behavior verification only invokes trusted Icarus and its sibling vvp.")
    parent = Path(working_directory or compiler.get("working_directory") or tempfile.gettempdir()).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="hullcirq-functional-", dir=parent))
    candidate, tb, output = directory / "candidate.v", directory / "contract_tb.v", directory / "simulation.vvp"
    candidate.write_text(rtl, encoding="utf-8")
    tb_module = plan["testbench_module"] if plan.get("kind") == "generic_cycle_vectors" else "hullcirq_contract_tb"
    if record_waveform:
        from . import simulation_waveforms_v1 as waveform
        _, result['waveform_recording'] = waveform.prepare(directory, plan, plan['testbench'], tb_module)
        tb = directory/'recorded_job_tb.v'
    else:
        tb.write_text(plan["testbench"], encoding="utf-8")
    paths = [_wsl_path(path) if compiler["kind"] == "wsl" else str(path) for path in (candidate, tb, output)]
    base = ["-B", compiler["base_directory"]] if compiler.get("base_directory") else []
    version = execute_fixed(trusted_command(compiler, executable, [*base, "-V"], parent), parent, cancel_event, timeout=10)
    result["tool_version"] = (version["stdout"] + version["stderr"]).strip()
    result["commands"].append(version)
    result["artifacts_directory"] = str(directory)
    compile_command = trusted_command(compiler, executable, [*base, "-g2005", "-s", tb_module, "-o", paths[2], paths[0], paths[1]], parent)
    compiled = execute_fixed(compile_command, parent, cancel_event)
    result["commands"].append(compiled)
    result["executed"], result["exit_code"] = compiled["executed"], compiled["exit_code"]
    result["stdout"], result["stderr"] = compiled["stdout"], compiled["stderr"]
    if compiled["status"] != "Completed" or compiled["exit_code"] != 0:
        result["validation_status"] = "Unsupported" if not compiled["executed"] else "Failed"
        result["diagnostics"].append(_problem("behavior_compile_failed", "Behavioral simulation could not compile; inspect the fixed tool output."))
        return waveform.finish(directory, result) if record_waveform else result
    runtime = executable.rsplit("/", 1)[0] + "/vvp" if compiler["kind"] == "wsl" else str(Path(executable).with_name("vvp.exe" if executable.lower().endswith(".exe") else "vvp"))
    runtime_arguments = ["-M", compiler["base_directory"]] if compiler.get("base_directory") else []
    runtime_cwd = directory if record_waveform else parent
    command = trusted_command(compiler, runtime, [*runtime_arguments, paths[2]], runtime_cwd)
    simulated = execute_fixed(command, runtime_cwd, cancel_event)
    result["commands"].append(simulated)
    result["stdout"] += simulated["stdout"]
    result["stderr"] += simulated["stderr"]
    result["executed"], result["exit_code"] = simulated["executed"], simulated["exit_code"]
    marker = f"HULLCIRQ_PASS vectors={plan['vector_count']} vector_hash={plan['vector_hash']}"
    passed = simulated["status"] == "Completed" and simulated["exit_code"] == 0 and simulated["stdout"].splitlines().count(marker) == 1 and "HULLCIRQ_FAIL" not in simulated["stdout"]
    if plan.get("kind") == "generic_cycle_vectors":
        from .generic_verification import parse_cycle_runtime
        cycle_result = parse_cycle_runtime(simulated["stdout"], plan, simulated["stderr"])
        result["cycle_runtime"] = cycle_result
        passed = passed and cycle_result["validation_status"] == "Passed"
        result["diagnostics"].extend(cycle_result["diagnostics"])
    result["validation_status"] = "Passed" if passed else "Unsupported" if not simulated["executed"] else "Failed"
    if not passed:
        result["diagnostics"].append(_problem("behavior_mismatch", "The candidate did not match the original contract trace; inspect the first cycle failure."))
    result["artifacts_directory"] = str(directory)
    result["simulation_timing"] = "Zero propagation delay; no PDK or SDF."
    return waveform.finish(directory, result) if record_waveform else result
