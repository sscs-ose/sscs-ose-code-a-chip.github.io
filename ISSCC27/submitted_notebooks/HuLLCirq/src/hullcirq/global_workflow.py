"""S09/S10: fixed multi-source synthesis and original-job netlist-only checks.

Generic technology-independent, zero-delay finite evidence. This module never
calls an LLM or modifies the adopted RTL, stimulus, expected values or S08 plan.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack, contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import threading

from .domain import DomainError, IMPLEMENTED_STAGES
from .envelope_cache import memoized_envelope
from .observation import ObservedState, persist_observation, require_durable_write
from .execution_submissions import PROTOCOL_VERSION, run_submission, submission_view, validate_submissions
from .global_generation import (GlobalGenerationManager, build_global_plan,
    compiler_public_hierarchy, expected_instance_counts, expected_output_count,
    expected_pe_records, instrument_public_testbench, parse_runtime_records,
    public_transfer_counts, required_node_ids, require, top_interface,
    validate_global_plan)
from .implementation_specs import _ports_with_ranges, execution_evidence_hash
from .presentation_revision import same_revision_design
from .rtl_checks import _strip_comments
from .store import _io_path, new_id, strict_loads, utc_now, validate_policy_history, validate_policy_review, _replace_with_windows_retry
from .review_actor import REVIEW_ACTORS, manual_review_fields
from .verification import content_hash, object_hash, trusted_command, execute_fixed, _wsl_path
from . import generic_global_verification as generic_global

STAGES = ("global_synthesis", "global_netlist_simulation")
ACTIVE = {"Queued", "Running"}
EARLIER = (*IMPLEMENTED_STAGES, "local_rtl_generation", "local_synthesis",
           "local_netlist_simulation", "node_implementation_specs", "global_rtl_generation")
SCOPE = "generic_technology_independent_nonflatten_zero_delay_no_pdk_no_timing"


def _folder(config, folder, prefix):
    parent = Path(config.get("working_directory") or tempfile.gettempdir()).resolve()
    folder = Path(folder).resolve()
    require(folder.parent == parent and folder.name.startswith(prefix), "global_tool_path_conflict",
            "Whole-system tools require the configured fixed artifact directory.")
    return parent, folder


def source_bundle(rtl, manifest):
    require(type(rtl) is str and type(manifest) is dict and type(manifest.get("design")) is dict
            and type(manifest.get("nodes")) is list, "global_source_conflict",
            "Preserve the complete top and adopted source manifest.")
    node_ids = required_node_ids(manifest["design"])
    require([n["node_id"] for n in manifest["nodes"]] == list(node_ids),
            "global_source_conflict", "Preserve the top and every adopted source node in its required order.")
    files = [{"file": "candidate_top.v", "module_name": top_interface(manifest["design"])["module_name"],
              "sha256": content_hash(rtl)}]
    for node in manifest["nodes"]:
        require(type(node["rtl"]) is str and node["rtl_sha256"] == content_hash(node["rtl"]),
                "global_source_conflict", "Each source RTL must retain its saved hash.")
        files.append({"file": node["node_id"] + ".v", "module_name": node["module_name"], "sha256": node["rtl_sha256"]})
    require(all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", x["module_name"]) for x in files)
            and len({x["module_name"] for x in files}) == len(files),
            "global_module_conflict", "The top and every adopted source require distinct plain public module names.")
    return files


def synthesis_script(manifest):
    top = top_interface(manifest["design"])["module_name"]
    require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", top), "global_module_conflict", "Use a fixed plain top module.")
    require([n["node_id"] for n in manifest["nodes"]] == list(required_node_ids(manifest["design"])),
            "global_source_conflict", "Use every adopted source in its required order.")
    sources = ["candidate_top.v", *(n["node_id"] + ".v" for n in manifest["nodes"])]
    return "\n".join([*("read_verilog " + name for name in sources),
        "synth -top " + top + " -noabc", "check -assert", "write_verilog -noattr netlist.v", ""])


def fixed_global_synthesis_commands(synthesizer, manifest, folder):
    _, folder = _folder(synthesizer, folder, "hullcirq-global-synth-")
    executable = synthesizer.get("executable")
    require(type(executable) is str and executable.replace("\\", "/").split("/")[-1].lower() in ("yosys", "yosys.exe"),
            "invalid_synthesizer", "Whole-system synthesis uses the configured Yosys only.")
    synthesis_script(manifest)
    environment = synthesizer.get("environment", {})
    require(type(environment) is dict and not set(environment) - {"LD_LIBRARY_PATH", "YOSYS_DATDIR"}
            and all(type(v) is str and v.startswith("/") and not any(ord(c) < 32 for c in v) for v in environment.values())
            and (not environment or synthesizer["kind"] == "wsl"),
            "invalid_synthesizer", "Only isolated WSL Yosys library/data paths may be overridden.")
    def command(arguments):
        return (trusted_command(synthesizer, "/usr/bin/env", [*(f"{k}={v}" for k,v in sorted(environment.items())), executable, *arguments], folder)
                if environment else trusted_command(synthesizer, executable, arguments, folder))
    return [command(["-V"]), command(["-Q", "-s", "synthesis.ys"])]


def netlist_public_interfaces(netlist, manifest):
    """Check literal public bit order; lowered signed declarations are recorded."""
    require(type(netlist) is str, "global_netlist_missing", "A complete saved netlist is required.")
    source = _strip_comments(netlist)
    modules = re.findall(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b[\s\S]*?\bendmodule\b", source)
    names = [top_interface(manifest["design"])["module_name"], *(n["module_name"] for n in manifest["nodes"])]
    require(len(set(names)) == len(names) and sorted(modules) == sorted(names)
            and len(re.findall(r"\bmodule\b", source)) == len(names),
            "global_netlist_modules_unsupported", "Nonflatten synthesis must retain exactly every original module definition.")
    interfaces = {top_interface(manifest["design"])["module_name"]: top_interface(manifest["design"])}
    interfaces.update({n["module_name"]: n["public_interface"] for n in manifest["nodes"]})
    observed = []
    for match in re.finditer(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b[\s\S]*?\bendmodule\b", source):
        name, ports = _ports_with_ranges(match[0]); expected = interfaces[name]["ports"]
        by_name = {p["name"]:p for p in ports}
        require(set(by_name) == {p["name"] for p in expected}, "global_netlist_ports_unsupported", "All original public ports must remain present.")
        for p in expected:
            got = by_name[p["name"]]
            require(got["direction"] == p["direction"] and type(got["width"]) is int and got["width"] == p["width"]
                    and got["range"] == (None if p["width"] == 1 else {"msb":p["width"]-1,"lsb":0})
                    and (p["signed"] or not got["signed"]), "global_netlist_ports_unsupported",
                    "Public names, directions, widths and literal bit order must match; signed omission is allowed only for lowered signed RTL.")
        observed.append({"module_name":name,"ports":[{**p,"rtl_declared_signed":next(x["signed"] for x in expected if x["name"]==p["name"])} for p in ports]})
    return observed


def synthesize_global_generic(rtl, manifest, synthesizer, directory=None, cancel_event=None):
    files = source_bundle(rtl, manifest); script = synthesis_script(manifest)
    result = {"validation_status":"Unsupported","executed":False,"exit_code":None,"diagnostics":[],"commands":[],
        "stdout":"","stderr":"","netlist":None,"netlist_sha256":None,"scope":SCOPE,
        "global_rtl_sha256":content_hash(rtl),"source_manifest_sha256":object_hash(manifest),
        "source_bundle":files,"source_bundle_sha256":object_hash(files),"synthesis_script":script,
        "synthesis_script_sha256":content_hash(script),"tool_configuration":copy.deepcopy(synthesizer)}
    if synthesizer is None:
        result["diagnostics"].append({"code":"global_synthesizer_unavailable","severity":"warning","message":"Configure trusted Yosys before whole-system synthesis."})
        return result
    parent = Path(synthesizer.get("working_directory") or tempfile.gettempdir()).resolve(); parent.mkdir(parents=True,exist_ok=True)
    folder = Path(directory).resolve() if directory else Path(tempfile.mkdtemp(prefix="hullcirq-global-synth-",dir=parent))
    _folder(synthesizer,folder,"hullcirq-global-synth-"); folder.mkdir(parents=True,exist_ok=True)
    commands = fixed_global_synthesis_commands(synthesizer,manifest,folder)
    (folder/"candidate_top.v").write_text(rtl,encoding="utf-8")
    for node in manifest["nodes"]: (folder/(node["node_id"]+".v")).write_text(node["rtl"],encoding="utf-8")
    (folder/"synthesis.ys").write_text(script,encoding="utf-8")
    result["artifacts_directory"] = str(folder)
    for index, command in enumerate(commands):
        outcome = execute_fixed(command,folder,cancel_event,10 if index == 0 else 180)
        result["commands"].append(outcome)
        result.update(executed=outcome["executed"],exit_code=outcome["exit_code"],stdout=result["stdout"]+outcome["stdout"],stderr=result["stderr"]+outcome["stderr"])
        if index == 0: result["tool_version"] = outcome["stdout"]+outcome["stderr"]
        if outcome["status"] != "Completed" or outcome["exit_code"] != 0: break
    if len(result["commands"]) == 2 and all(_command_pass(c) for c in result["commands"]) and (folder/"netlist.v").exists():
        netlist = (folder/"netlist.v").read_text(encoding="utf-8")
        result.update(netlist=netlist,netlist_sha256=content_hash(netlist))
        try:
            result["netlist_public_interfaces"] = netlist_public_interfaces(netlist,manifest)
            result["validation_status"] = "Passed"
        except DomainError as error:
            result["validation_status"] = "Unsupported"
            result["diagnostics"].append({"code":error.code,"severity":"error","message":error.message})
    else:
        result["validation_status"] = "Failed" if result["executed"] else "Unsupported"
        result["diagnostics"].append({"code":"global_synthesis_failed","severity":"error","message":"Fixed nonflatten Yosys synthesis did not complete; inspect retained commands and logs."})
    return result


def fixed_global_netlist_commands(compiler, folder, plan=None, *, record_waveform=False):
    parent, folder = _folder(compiler, folder, "hullcirq-global-netlist-")
    executable = compiler.get("executable")
    require(type(executable) is str and executable.replace("\\", "/").split("/")[-1].lower() in ("iverilog", "iverilog.exe"),
            "invalid_compiler", "Netlist verification uses configured Icarus and sibling vvp only.")
    path = lambda p: _wsl_path(p) if compiler["kind"] == "wsl" else str(p)
    base = ["-B", compiler["base_directory"]] if compiler.get("base_directory") else []
    runtime = executable.rsplit("/",1)[0]+"/vvp" if compiler["kind"] == "wsl" else str(Path(executable).with_name("vvp.exe" if executable.lower().endswith(".exe") else "vvp"))
    tb_module = generic_global.testbench_module(plan) if type(plan) is dict and plan.get('kind') == generic_global.KIND else "hullcirq_global_tb"
    def compile(tb,output):
        return trusted_command(compiler,executable,[*base,"-g2005","-s",tb_module,"-o",path(folder/output),path(folder/"netlist.v"),path(folder/tb)],parent)
    return [trusted_command(compiler,executable,[*base,"-V"],parent),compile("original_job_tb.v","hierarchy.vvp"),
            compile("recorded_job_tb.v" if record_waveform else "instrumented_job_tb.v","global.vvp"),trusted_command(compiler,runtime,[*(["-M",compiler["base_directory"]] if compiler.get("base_directory") else []),path(folder/"global.vvp")],folder if record_waveform else parent)]


def _command_pass(command):
    return type(command) is dict and command.get("executed") is True and command.get("status") == "Completed" and type(command.get("exit_code")) is int and command["exit_code"] == 0


def _records(stdout, plan, stderr=''):
    return parse_runtime_records(stdout, plan, stderr)


def compiler_netlist_public_hierarchy(scope_lines,manifest):
    """Safe Verilog selectors for actual Yosys escaped instance scope names.

    Yosys may retain a generate instance as one literal name such as
    ``pe_inst[0].u_pe``. The embedded dot is not a hierarchy separator: escape
    the complete compiler scope component, with the required ending space.
    """
    if generic_global.handles(manifest['design']):
        return generic_global.hierarchy(scope_lines, manifest, netlist=True)
    scopes={}
    for line in scope_lines:
        match=re.fullmatch(r'(S_[A-Za-z0-9_]+)\s+\.scope (\w+),\s*"([^"]+)"(?:\s+"([^"]+)")?(.*);',line)
        require(match is not None,"global_netlist_hierarchy_unsupported","Compiler netlist scope output is unsupported.")
        identifier,kind,name,module,rest=match.groups(); parents=re.findall(r'\bS_[A-Za-z0-9_]+\b',rest)
        require(identifier not in scopes,"global_netlist_hierarchy_unsupported","Duplicate compiler scope identifiers are unsupported.")
        scopes[identifier]={"kind":kind,"name":name,"module":module,"parent":parents[-1] if parents else None}
    def components(identifier,seen=None):
        seen=set() if seen is None else seen
        require(identifier in scopes and identifier not in seen,"global_netlist_hierarchy_unsupported","Compiler netlist scope ancestry is incomplete or cyclic.")
        seen.add(identifier); record=scopes[identifier]; name=record["name"]
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?(?:\.[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?)*',name) is not None,
                "global_netlist_hierarchy_unsupported","Observable synthesized scope names require safe plain components and constant indices.")
        selector=("\\"+name+" ") if "." in name or (record["kind"]=="module" and "[" in name) else name
        return (components(record["parent"],seen) if record["parent"] else [])+[(name,selector)]
    expected_counts=expected_instance_counts(manifest)
    result={}
    for entry in manifest["nodes"]:
        locations=[]
        for identifier,record in scopes.items():
            if record["kind"]=="module" and record["module"]==entry["module_name"]:
                parts=components(identifier)
                require(len(parts)>=3 and [p[0] for p in parts[:2]]==["hullcirq_global_tb","dut"],
                        "global_netlist_hierarchy_unsupported","Adopted synthesized modules must remain inside the original candidate top.")
                locations.append(".".join(p[1] for p in parts[1:]))
        require(len(locations)==expected_counts[entry["node_id"]],"global_netlist_instance_count",
                "Keep exactly every required adopted public module boundary.")
        if entry["node_id"] == "npu2-pe":
            require(set(locations) == {"dut.pe" + lane for lane in ("00", "01", "10", "11")},
                    "global_netlist_array_binding", "Keep the four shared PE instance-to-lane names after synthesis.")
        result[entry["node_id"]]=sorted(locations)
    return result


def check_global_netlist(netlist, manifest, plan, compiler, cancel_event=None):
    validate_global_plan(manifest["design"],plan)
    result = {"validation_status":"Failed","executed":False,"exit_code":None,"diagnostics":[],"commands":[],
        "stdout":"","stderr":"","checks":{},"scope":SCOPE,"netlist_sha256":content_hash(netlist),
        "source_manifest_sha256":object_hash(manifest),"verification_plan_sha256":object_hash(plan),
        "vector_hash":plan["vector_hash"],"testbench_sha256":plan["testbench_sha256"],
        "public_boundary_vector_hash":plan["public_boundary_vector_hash"],"tool_configuration":copy.deepcopy(compiler),
        "compiled_design_sources":[{"file":"netlist.v","sha256":content_hash(netlist)}],"source_rtl_linked":False}
    try: result["netlist_public_interfaces"] = netlist_public_interfaces(netlist,manifest)
    except DomainError as error:
        result.update(validation_status="Unsupported"); result["diagnostics"].append({"code":error.code,"severity":"error","message":error.message}); return result
    if compiler is None:
        result.update(validation_status="Unsupported"); result["diagnostics"].append({"code":"global_compiler_unavailable","severity":"warning","message":"Configure Icarus and vvp before netlist verification."}); return result
    parent = Path(compiler.get("working_directory") or tempfile.gettempdir()).resolve(); parent.mkdir(parents=True,exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="hullcirq-global-netlist-",dir=parent)); result["artifacts_directory"] = str(folder)
    from . import simulation_waveforms_v1 as waveform
    (folder/"netlist.v").write_text(netlist,encoding="utf-8"); (folder/"original_job_tb.v").write_text(plan["testbench"],encoding="utf-8")
    fixed = fixed_global_netlist_commands(compiler,folder,plan,record_waveform=True)
    for index in (0,1):
        outcome=execute_fixed(fixed[index],parent,cancel_event,10 if index==0 else 60); result["commands"].append(outcome)
        result.update(executed=outcome["executed"],exit_code=outcome["exit_code"],stdout=result["stdout"]+outcome["stdout"],stderr=result["stderr"]+outcome["stderr"])
        if index==0: result["tool_version"]=outcome["stdout"]+outcome["stderr"]
        if not _command_pass(outcome):
            result["diagnostics"].append({"code":"global_netlist_compile_failed","severity":"error","message":outcome["stderr"] or "Netlist-only compilation did not complete."}); return waveform.finish(folder,result)
    elaboration=(folder/"hierarchy.vvp").read_text(encoding="utf-8",errors="replace")
    counts={n["node_id"]:len(re.findall(r'\.scope module,\s*"[^"]*"\s*"'+re.escape(n["module_name"])+r'"',elaboration)) for n in manifest["nodes"]}
    required_counts=expected_instance_counts(manifest)
    result["elaborated_instance_counts"]=counts
    result["checks"]["elaboration"]={"validation_status":"Passed" if counts==required_counts else "Failed","instance_counts":counts}
    if result["checks"]["elaboration"]["validation_status"] != "Passed":
        result["diagnostics"].append({"code":"global_netlist_instance_count","severity":"error","message":"The synthesized circuit must elaborate every required adopted source instance."}); return waveform.finish(folder,result)
    scopes=[line for line in elaboration.splitlines() if re.match(r'^S_\S+\s+\.scope ',line)]
    try: hierarchy=compiler_netlist_public_hierarchy(scopes,manifest); instrumented,monitor=instrument_public_testbench(plan,hierarchy)
    except DomainError as error:
        result.update(validation_status="Unsupported"); result["diagnostics"].append({"code":error.code,"severity":"error","message":error.message}); return waveform.finish(folder,result)
    tb_module = generic_global.testbench_module(plan) if plan.get('kind') == generic_global.KIND else 'hullcirq_global_tb'
    instrumented, result['waveform_recording'] = waveform.prepare(folder,plan,instrumented,tb_module)
    (folder/"instrumented_job_tb.v").write_text(instrumented,encoding="utf-8")
    result.update(public_port_hierarchy=hierarchy,hierarchy_scope_lines=scopes,hierarchy_scope_sha256=object_hash(scopes),
        public_monitor_source=monitor,public_monitor_sha256=content_hash(monitor),instrumented_testbench_sha256=content_hash(instrumented),
        instrumentation_origin="ordinary_program_from_unchanged_S08_plan_and_actual_netlist_compiler_public_hierarchy")
    for index in (2,3):
        outcome=execute_fixed(fixed[index],folder if index==3 else parent,cancel_event,60); result["commands"].append(outcome)
        result.update(executed=outcome["executed"],exit_code=outcome["exit_code"],stdout=result["stdout"]+outcome["stdout"],stderr=result["stderr"]+outcome["stderr"])
        if not _command_pass(outcome):
            result["diagnostics"].append({"code":"global_netlist_execution_failed","severity":"error","message":outcome["stderr"] or "Instrumented netlist simulation did not complete."}); return waveform.finish(folder,result)
    passed,outputs,streams,pes=_records(result["commands"][-1]["stdout"],plan,result["commands"][-1].get('stderr', ''))
    result.update(validation_status="Passed" if passed else "Failed",actual_output_transfers=outputs,
        actual_public_stream_transfers=streams,actual_pe_lane_transfers=pes)
    if plan.get('kind') == generic_global.KIND:
        result.update(verification_profile=generic_global.KIND, signal_sample_count=len(outputs),
                      expected_signal_samples=expected_output_count(plan))
    result["checks"].update({name:{"validation_status":result["validation_status"],"executed":True} for name in ("functional","public_boundary")})
    if not passed: result["diagnostics"].append({"code":"global_netlist_behavior_mismatch","severity":"error","message":"The exact netlist did not pass the unchanged original job/public boundary assertions."})
    return waveform.finish(folder,result)


def validate_synthesis_proof(run):
    """Rebuild trusted commands and every retained synthesis input, not a pass flag."""
    proof=run["checks"]; manifest=run["source_manifest"]
    require(proof.get("validation_status")=="Passed" and _command_pass({**proof,"status":"Completed"}),
            "global_synthesis_proof_conflict","Synthesis must retain an executed integer-zero result.")
    files=source_bundle(run["global_rtl"],manifest); script=synthesis_script(manifest)
    require(object_hash(proof.get("tool_configuration"))==object_hash(run["tool_configuration"])
            and proof.get("global_rtl_sha256")==run["global_rtl_sha256"]
            and proof.get("source_manifest_sha256")==run["source_manifest_sha256"]
            and object_hash(proof.get("source_bundle"))==object_hash(files)
            and proof.get("source_bundle_sha256")==object_hash(files)
            and proof.get("synthesis_script")==script and proof.get("synthesis_script_sha256")==content_hash(script)
            and proof.get("netlist")==run["netlist"] and proof.get("netlist_sha256")==run["netlist_sha256"]
            and object_hash(proof.get("netlist_public_interfaces"))==object_hash(netlist_public_interfaces(run["netlist"],manifest)),
            "global_synthesis_proof_conflict","Saved synthesis must preserve the exact sources, script, public boundaries and generated netlist.")
    commands=proof.get("commands")
    expected=fixed_global_synthesis_commands(run["tool_configuration"],manifest,proof["artifacts_directory"])
    require(type(commands) is list and len(commands)==2 and all(_command_pass(c) for c in commands)
            and object_hash([c.get("command") for c in commands])==object_hash(expected),
            "global_synthesis_proof_conflict","Saved synthesis commands must exactly reconstruct the fixed Yosys operation.")


def validate_netlist_proof(run):
    """Rebuild netlist-only commands, original assertions and compiler hierarchy."""
    proof=run["checks"]; manifest=run["source_manifest"]; plan=run["verification_plan"]
    commands=proof.get("commands")
    require(type(commands) is list and len(commands)==4 and all(_command_pass(c) for c in commands),
            "global_netlist_proof_conflict","Four actual successful fixed commands are required.")
    if plan.get('kind') == generic_global.KIND:
        validate_global_plan(manifest['design'], plan)
    recording = proof.get('waveform_recording') is not None
    expected=fixed_global_netlist_commands(run["tool_configuration"],proof["artifacts_directory"],plan,record_waveform=recording)
    hierarchy=compiler_netlist_public_hierarchy(proof["hierarchy_scope_lines"],manifest)
    instrumented,monitor=instrument_public_testbench(plan,hierarchy)
    if recording:
        from . import simulation_waveforms_v1 as waveform
        tb_module = generic_global.testbench_module(plan) if plan.get('kind') == generic_global.KIND else 'hullcirq_global_tb'
        waveform.validate(proof,plan,instrumented,tb_module)
        instrumented = waveform.instrument(plan,instrumented,tb_module)
    passed,outputs,streams,pes=_records(commands[-1]["stdout"],plan,commands[-1].get('stderr', ''))
    if plan.get('kind') == generic_global.KIND:
        require(proof.get('verification_profile') == generic_global.KIND
                and proof.get('signal_sample_count') == len(outputs)
                and proof.get('expected_signal_samples') == expected_output_count(plan),
                'global_netlist_proof_conflict', 'Retain the exact generic cycle profile and signal-sample counts.')
    require(passed and proof.get("validation_status")=="Passed" and proof.get("executed") is True
            and type(proof.get("exit_code")) is int and proof["exit_code"]==0
            and object_hash([c.get("command") for c in commands])==object_hash(expected)
            and object_hash(proof.get("tool_configuration"))==object_hash(run["tool_configuration"])
            and proof.get("netlist_sha256")==run["netlist_sha256"]
            and proof.get("source_manifest_sha256")==run["source_manifest_sha256"]
            and proof.get("verification_plan_sha256")==object_hash(plan)
            and proof.get("vector_hash")==plan["vector_hash"] and proof.get("testbench_sha256")==plan["testbench_sha256"]
            and proof.get("public_boundary_vector_hash")==plan["public_boundary_vector_hash"]
            and proof.get("source_rtl_linked") is False
            and object_hash(proof.get("compiled_design_sources"))==object_hash([{"file":"netlist.v","sha256":run["netlist_sha256"]}])
            and object_hash(proof.get("netlist_public_interfaces"))==object_hash(netlist_public_interfaces(run["netlist"],manifest))
            and object_hash(proof.get("elaborated_instance_counts"))==object_hash(expected_instance_counts(manifest))
            and object_hash(proof.get("public_port_hierarchy"))==object_hash(hierarchy)
            and proof.get("hierarchy_scope_sha256")==object_hash(proof["hierarchy_scope_lines"])
            and proof.get("public_monitor_source")==monitor and proof.get("public_monitor_sha256")==content_hash(monitor)
            and proof.get("instrumented_testbench_sha256")==content_hash(instrumented)
            and all(proof.get("checks",{}).get(k,{}).get("validation_status")=="Passed" for k in ("elaboration","functional","public_boundary"))
            and object_hash(proof.get("actual_output_transfers"))==object_hash(outputs)
            and object_hash(proof.get("actual_public_stream_transfers"))==object_hash(streams)
            and object_hash(proof.get("actual_pe_lane_transfers"))==object_hash(pes)
            and "HULLCIRQ_FAIL" not in proof.get("stdout", ""),
            "global_netlist_proof_conflict","Saved pass must preserve the exact netlist-only execution, original job, values and public-port assertions.")


class GlobalWorkflowManager(ObservedState):
    """Separate durable async S09/S10 history with revocable exact-source adoption."""
    def __init__(self, store, generation, implementation_specs, global_generation, compiler=None, synthesizer=None):
        self.store,self.generation,self.specifications,self.global_generation=store,generation,implementation_specs,global_generation
        self.compiler,self.synthesizer=copy.deepcopy(compiler),copy.deepcopy(synthesizer)
        self.path=store.state_path.parent/"global_workflow.json"; self.lock=threading.RLock()
        self._worker=None; self._cancel=threading.Event(); self._closed=False; self._storage_error=None
        self._state={"global_workflow_store_version":"0.1","runs":[],"reviews":[],"source_key":None,"source_epoch":0,"source_transitions":[]}
        if _io_path(self.path).exists():
            try: self._state=strict_loads(_io_path(self.path).read_text(encoding="utf-8")); self._validate_saved()
            except (DomainError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
                raise DomainError("invalid_global_workflow_store","Whole-system workflow history is inconsistent; original file preserved.",500) from error
        self._committed=copy.deepcopy(self._state)
        changed=False
        for run in self._state["runs"]:
            if run["execution_status"] in ACTIVE:
                run.update(execution_status="Interrupted",validation_status="Not Checked",finished_at=utc_now(),error={"code":"service_restarted","message":"Interrupted tool execution retained; no operation was resent."}); changed=True
        if changed: self._persist()

    def _source_state(self):
        global_manager=self.global_generation
        try:
            _,manifest,error=global_manager.observe_design()
            require(manifest is not None and error is None,"global_sources_not_current","All exact adopted node sources must remain current.")
            with global_manager.lock:
                require(bool(global_manager._state["jobs"]),"global_rtl_not_adopted","Adopt Passed S08 integration before whole-system tools.")
                raw=global_manager._state["jobs"][-1]; job=global_manager._decorate(raw)
                require(job["execution_status"]=="Completed" and job["validation_status"]=="Passed" and job["review_status"]=="Accepted"
                        and job["freshness"]=="Current" and object_hash(job["context"]["source_manifest"])==object_hash(manifest)
                        and GlobalGenerationManager._passed(raw),"global_rtl_not_adopted","Use the latest current Passed and adopted exact-source S08 candidate.")
                reviews=[r for r in global_manager._state["reviews"] if r["job_id"]==job["id"]]
                require(reviews and reviews[-1]["decision"]=="accepted","global_adoption_missing","S08 needs its latest authoritative adoption.")
                identity={"global_job_id":job["id"],"global_context_id":job["context_id"],"revision_id":job["revision_id"],
                    "global_rtl_sha256":job["rtl_sha256"],"global_execution_hash":execution_evidence_hash(raw),
                    "source_manifest_sha256":object_hash(manifest),"global_source_key":global_manager._state["source_key"],
                    "global_acceptance_epoch":job["acceptance_epoch"],"global_source_epoch":global_manager._state["source_epoch"],"global_adoption":reviews[-1]}
                return object_hash(identity),{"identity":copy.deepcopy(identity),"job":copy.deepcopy(raw),"manifest":manifest},None
        except DomainError as error:
            current=self.store.envelope()
            with global_manager.lock:
                key=object_hash({"revision_id":current["revision"]["id"],"design":current["design"],"blocked":error.code,
                    "global_source_epoch":global_manager._state["source_epoch"],"global_source_key":global_manager._state["source_key"],
                    "global_jobs":[[j["id"],j["review_status"],j.get("acceptance_epoch")] for j in global_manager._state["jobs"]],"reviews":global_manager._state["reviews"]})
            return key,None,{"code":error.code,"message":error.message}

    def observe_design(self):
        key,source,error=self._source_state()
        with self.lock:
            if key!=self._state["source_key"]:
                self._state["source_key"]=key; self._state["source_epoch"]+=1
                self._state["source_transitions"].append({"epoch":self._state["source_epoch"],"source_key":key,"created_at":utc_now()})
                persist_observation(self)
        return key,source,error

    def _run(self,identifier):
        run=next((r for r in self._state["runs"] if r["id"]==identifier),None)
        require(run is not None,"global_workflow_run_not_found","Whole-system tool run does not exist.",404)
        return run

    def _latest(self,stage):
        values=[r for r in self._state["runs"] if r["stage_id"]==stage]
        return values[-1] if values else None

    def _decorate(self,run):
        value=copy.deepcopy(run)
        current=run["source_key"]==self._state["source_key"] and run["source_epoch_at_start"]==self._state["source_epoch"]
        if run["stage_id"]==STAGES[1]:
            prior=self._run(run["prior_run_id"]); latest=self._latest(STAGES[0])
            reviews=[r for r in self._state["reviews"] if r["run_id"]==prior["id"]]
            current=current and latest is not None and latest["id"]==prior["id"] and prior["review_status"]=="Accepted" and bool(reviews) and object_hash(reviews[-1])==object_hash(run["synthesis_adoption"])
        value["freshness"]="Current" if current else "Stale"
        if value["review_status"]=="Accepted" and (not current or run.get("acceptance_epoch")!=self._state["source_epoch"]): value["review_status"]="Awaiting Review"
        value["artifacts"]=[{"kind":"global_workflow_run","url":"/api/global-workflow/runs/"+run["id"]}]
        return value

    @memoized_envelope
    def envelope(self):
        _,source,error=self.observe_design()
        with self.lock:
            runs=[self._decorate(r) for r in self._state["runs"]]
            stages=[]
            for stage in STAGES:
                matches=[r for r in runs if r["stage_id"]==stage]; latest=matches[-1] if matches else None
                stages.append({"stage_id":stage,"latest_run_id":latest["id"] if latest else None,
                    "accepted_run_id":latest["id"] if latest and latest["review_status"]=="Accepted" and latest["freshness"]=="Current" else None})
            return {"global_workflow":{"implemented":True,"runs":runs,"reviews":copy.deepcopy(self._state["reviews"]),"stages":stages,
                "ready":source is not None,"blocked_reason":error["message"] if error else None,"storage_error":copy.deepcopy(self._storage_error),
                "execution_submissions":submission_view(self),"submission_protocol_version":PROTOCOL_VERSION}}

    def run(self,identifier):
        self.observe_design()
        with self.lock: return self._decorate(self._run(identifier))

    def is_active(self):
        with self.lock: return any(r["execution_status"] in ACTIVE for r in self._state["runs"])

    @contextmanager
    def _source_locks(self):
        # Match S08's source/review lock order. In particular, do not acquire
        # our result lock before a source-manager or project-store lock.
        with ExitStack() as stack:
            for manager in (self.global_generation,self.specifications,self.global_generation.workflow,self.generation,self.store):
                stack.enter_context(manager.lock)
            yield

    def start(self,stage_id,global_job_id,synthesis_run_id=None,revision_id=None, *, _submission=None):
        with self._source_locks(): return self._start_locked(stage_id,global_job_id,synthesis_run_id,revision_id,_submission=_submission)

    def _start_locked(self,stage_id,global_job_id,synthesis_run_id,revision_id, *, _submission=None):
        require(stage_id in STAGES and type(global_job_id) is str and (synthesis_run_id is None or type(synthesis_run_id) is str)
                and (revision_id is None or type(revision_id) is str),"unsupported_global_workflow_stage","Use S09 synthesis or S10 netlist simulation with exact saved sources.")
        key,source,error=self.observe_design()
        require(source is not None,"global_rtl_not_adopted",error["message"] if error else "Current S08 adoption required.")
        current=self.store.envelope(); job=source["job"]; plan=job["context"]["verification_plan"]
        require(global_job_id==job["id"] and (revision_id is None or revision_id==current["revision"]["id"]),
                "global_workflow_source_conflict","Continue from the latest current adopted S08 and GUI revision.")
        validate_global_plan(source["manifest"]["design"],plan)
        with self.lock:
            require(not self._closed and not self.is_active() and not (self._worker and self._worker.is_alive()),"global_workflow_busy","Only one whole-system tool operation can run at a time.")
            require(not any(r["execution_status"] in ACTIVE for manager,field in
                    ((self.global_generation,"jobs"),(self.generation,"jobs"),(self.global_generation.workflow,"runs")) for r in manager._state[field]),
                    "global_workflow_peer_busy","Wait for active node/global model or node-tool execution before whole-system tools.")
            prior=None; adoption=None
            if stage_id==STAGES[1]:
                prior=self._latest(STAGES[0]); prior=self._decorate(prior) if prior else None
                require(prior is not None and (synthesis_run_id is None or synthesis_run_id==prior["id"])
                        and prior["review_status"]=="Accepted" and prior["freshness"]=="Current" and prior["validation_status"]=="Passed"
                        and prior["global_job_id"]==global_job_id,"global_synthesis_not_adopted","Adopt latest Passed S09 of the exact S08 before netlist verification.")
                validate_synthesis_proof(prior)
                adoption=copy.deepcopy([r for r in self._state["reviews"] if r["run_id"]==prior["id"]][-1])
            else: require(synthesis_run_id is None,"invalid_global_prior","S09 does not take a prior synthesis run.")
            run={"id":new_id("global-workflow"),"stage_id":stage_id,"global_job_id":job["id"],"candidate_id":job["id"],
                "revision_id":job["revision_id"],"global_context_id":job["context_id"],"global_rtl":job["rtl"],"global_rtl_sha256":job["rtl_sha256"],
                "source_identity":source["identity"],"source_key":key,"source_epoch_at_start":self._state["source_epoch"],
                "source_manifest":copy.deepcopy(source["manifest"]),"source_manifest_sha256":object_hash(source["manifest"]),
                "verification_plan":copy.deepcopy(plan),"verification_plan_sha256":object_hash(plan),"vector_hash":plan["vector_hash"],
                "testbench_sha256":plan["testbench_sha256"],"public_boundary_vector_hash":plan["public_boundary_vector_hash"],
                "prior_run_id":prior["id"] if prior else None,"synthesis_run_id":prior["id"] if prior else None,"synthesis_adoption":adoption,
                "netlist":prior["netlist"] if prior else None,"netlist_sha256":prior["netlist_sha256"] if prior else None,
                "execution_status":"Queued","validation_status":"Not Checked","review_status":"Awaiting Review","checks":{},"diagnostics":[],
                "created_at":utc_now(),"finished_at":None,"error":None,"tool_configuration":copy.deepcopy(self.synthesizer if stage_id==STAGES[0] else self.compiler)}
            if _submission is not None:
                run["submission_id"] = _submission.submission_id
                _submission.bind(run["id"])
            self._state["runs"].append(run); self._persist(); self._cancel=threading.Event()
            self._worker=threading.Thread(target=self._execute,args=(run["id"],self._cancel),daemon=True,name="HuLLCirq-whole-system-tools"); self._worker.start()
        return self.envelope()

    def _execute(self,identifier,cancel):
        try:
            with self.lock:
                run=self._run(identifier); run["execution_status"]="Running"; self._persist(); frozen=copy.deepcopy(run)
            if frozen["stage_id"]==STAGES[0]:
                result=synthesize_global_generic(frozen["global_rtl"],frozen["source_manifest"],frozen["tool_configuration"],cancel_event=cancel)
            else: result=check_global_netlist(frozen["netlist"],frozen["source_manifest"],frozen["verification_plan"],frozen["tool_configuration"],cancel)
            with self.lock:
                run=self._run(identifier); run.update(execution_status="Cancelled" if cancel.is_set() else "Completed",
                    validation_status="Not Checked" if cancel.is_set() else result["validation_status"],checks=result,diagnostics=result.get("diagnostics",[]),finished_at=utc_now())
                if frozen["stage_id"]==STAGES[0] and result.get("netlist") is not None: run.update(netlist=result["netlist"],netlist_sha256=result["netlist_sha256"])
                self._persist()
            self.observe_design(); policy=self.store.review_policy()
            if result["validation_status"]=="Passed" and not cancel.is_set() and policy["mode"]=="accept_on_pass" and policy["user_authorized"] is True:
                try: self._review(identifier,"accepted","Adopted under the user's configured Passed policy.",None,"automation_policy",self.store.policy_provenance(policy["id"]))
                except DomainError as error:
                    with self.lock:
                        self._run(identifier)["diagnostics"].append({"code":"automatic_adoption_blocked","severity":"info","message":error.message}); self._persist()
        except Exception as error:
            with self.lock:
                run=self._run(identifier); run.update(execution_status="Cancelled" if cancel.is_set() else "Failed",validation_status="Not Checked",finished_at=utc_now(),
                    error={"code":getattr(error,"code","global_workflow_error"),"message":getattr(error,"message","Tool execution or durable evidence recording failed.")})
                try: self._persist()
                except (OSError,ValueError,TypeError): pass

    def _review(self,identifier,decision,note,target_stage,actor,provenance=None):
        with self._source_locks(): return self._review_locked(identifier,decision,note,target_stage,actor,provenance)

    def _review_locked(self,identifier,decision,note,target_stage,actor,provenance):
        require(decision in ("accepted","changes_requested","return_to_stage") and type(note) is str
                and (decision=="accepted" or note.strip()),"invalid_global_workflow_review","Provide a valid decision and correction/return reason.")
        self.observe_design()
        with self.lock:
            run=self._run(identifier); current=self._decorate(run)
            require(run["execution_status"] not in ACTIVE and self._latest(run["stage_id"])["id"]==identifier,
                    "global_workflow_superseded","Review the latest completed result for this stage.")
            allowed=EARLIER if run["stage_id"]==STAGES[0] else (*EARLIER,STAGES[0])
            require(target_stage in allowed if decision=="return_to_stage" else target_stage is None,
                    "invalid_target_stage","Return only to an implemented earlier stage.")
            if decision=="accepted":
                require(current["freshness"]=="Current","stale_global_workflow","Sources or source adoption changed; run the current stage again.")
                require(run["execution_status"]=="Completed" and run["validation_status"]=="Passed","global_workflow_not_passed","Only exact current executed Passed results may be adopted.")
                (validate_synthesis_proof if run["stage_id"]==STAGES[0] else validate_netlist_proof)(run)
                if actor=="automation_policy":
                    policy=self.store.review_policy()
                    require(policy["mode"]=="accept_on_pass" and policy["user_authorized"] is True and provenance is not None and policy["id"]==provenance.get("policy_id"),
                            "review_policy_changed","Automatic adoption policy changed while tools were running.")
                run.update(review_status="Accepted",acceptance_epoch=self._state["source_epoch"])
            else: run["review_status"]="Changes Requested"
            record={"id":new_id("global-workflow-review"),"run_id":identifier,"decision":decision,"note":note,"target_stage":target_stage,"actor":actor,
                "source_key":run["source_key"],"acceptance_epoch":run.get("acceptance_epoch"),"created_at":utc_now(),"reviewed_revision_id":self.store.envelope()["revision"]["id"]}
            if provenance: record["provenance"]=copy.deepcopy(provenance)
            self._state["reviews"].append(record); self._persist()
        return self.envelope()

    def review(self,identifier,decision,note,target_stage=None, *, operator=None):
        fields = manual_review_fields(operator)
        return self._review(identifier, decision, note, target_stage, fields["actor"], fields["provenance"])

    def cancel(self,identifier):
        with self.lock:
            require(self._run(identifier)["execution_status"] in ACTIVE,"global_workflow_not_active","Only an active tool operation may be cancelled.")
            self._cancel.set()
        return self.envelope()

    def artifact(self,identifier,field):
        with self.lock:
            run=copy.deepcopy(self._run(identifier))
        if field=="verification-plan": return run["verification_plan"]
        if field=="source-manifest": return run["source_manifest"]
        if field=="netlist" and run["netlist"] is not None: return run["netlist"]
        if field=="synthesis-script" and "synthesis_script" in run["checks"]: return run["checks"]["synthesis_script"]
        if field=="public-monitor" and "public_monitor_source" in run["checks"]: return run["checks"]["public_monitor_source"]
        if field=="instrumented-testbench" and "public_port_hierarchy" in run["checks"]: return instrument_public_testbench(run["verification_plan"],run["checks"]["public_port_hierarchy"])[0]
        raise DomainError("global_workflow_artifact_not_found","Only retained fixed whole-system artifacts are downloadable.",404)

    def _validate_saved(self):
        state=self._state
        require(type(state) is dict and state.get("global_workflow_store_version")=="0.1"
                and type(state.get("runs")) is list and type(state.get("reviews")) is list and type(state.get("source_epoch")) is int
                and state["source_epoch"]>=0 and type(state.get("source_transitions")) is list,
                "global_workflow_history_invalid","Invalid whole-system history containers.")
        transitions=state["source_transitions"]
        require([t["epoch"] for t in transitions]==list(range(1,state["source_epoch"]+1))
                and (transitions[-1]["source_key"] if transitions else None)==state["source_key"]
                and all(type(t["epoch"]) is int and type(t["source_key"]) is str for t in transitions),
                "global_workflow_history_invalid","Whole-system source epochs are inconsistent.")
        policies=validate_policy_history(self.store.envelope()); ids=set()
        for run in state["runs"]:
            require(type(run) is dict and all(type(run.get(k)) is str for k in ("id","stage_id","global_job_id","candidate_id","revision_id","global_context_id","global_rtl","global_rtl_sha256","source_key","created_at"))
                    and all(type(run.get(k)) is dict for k in ("source_identity","source_manifest","verification_plan","checks")) and type(run.get("diagnostics")) is list
                    and run["id"] not in ids and run["stage_id"] in STAGES and type(run.get("source_epoch_at_start")) is int
                    and run["execution_status"] in ACTIVE|{"Completed","Failed","Cancelled","Interrupted"}
                    and run["validation_status"] in ("Not Checked","Passed","Failed","Unsupported") and run["review_status"] in ("Awaiting Review","Accepted","Changes Requested")
                    and run.get("record_hash")==object_hash({k:v for k,v in run.items() if k!="record_hash"}),
                    "global_workflow_record_invalid","Whole-system record types, statuses or checksum differ.")
            job=self.global_generation._job(run["global_job_id"]); manifest=job["context"]["source_manifest"]; plan=job["context"]["verification_plan"]
            identity=run["source_identity"]
            require(run["candidate_id"]==job["id"] and run["revision_id"]==job["revision_id"] and run["global_context_id"]==job["context_id"]
                    and run["global_rtl"]==job["rtl"] and run["global_rtl_sha256"]==content_hash(job["rtl"])
                    and object_hash(run["source_manifest"])==object_hash(manifest)==run["source_manifest_sha256"]
                    and object_hash(run["verification_plan"])==object_hash(plan)==run["verification_plan_sha256"]
                    and all(run[k]==plan[k] for k in ("vector_hash","testbench_sha256","public_boundary_vector_hash"))
                    and identity.get("global_job_id")==job["id"] and identity.get("revision_id")==job["revision_id"]
                    and identity.get("global_context_id")==job["context_id"] and identity.get("global_rtl_sha256")==run["global_rtl_sha256"]
                    and identity.get("global_execution_hash")==execution_evidence_hash(job)
                    and identity.get("source_manifest_sha256")==object_hash(manifest) and identity.get("global_source_key")==job["source_key"]
                    and type(identity.get("global_source_epoch")) is int and type(identity.get("global_acceptance_epoch")) is int
                    and identity["global_source_epoch"]==identity["global_acceptance_epoch"]
                    and any(object_hash(identity.get("global_adoption"))==object_hash(r) for r in self.global_generation._state["reviews"])
                    and identity["global_adoption"]["job_id"]==job["id"] and identity["global_adoption"]["decision"]=="accepted"
                    and identity["global_adoption"]["acceptance_epoch"]==identity["global_acceptance_epoch"]
                    and run["source_key"]==object_hash(identity)
                    and any(t["source_key"]==run["source_key"] and t["epoch"]==run["source_epoch_at_start"] for t in transitions),
                    "global_workflow_source_conflict","Retain the exact original adopted S08, node sources, immutable plan and historical source epoch.")
            validate_global_plan(self.store.snapshot(run["revision_id"]),run["verification_plan"])
            if run["netlist"] is not None: require(type(run["netlist"]) is str and run["netlist_sha256"]==content_hash(run["netlist"]),"global_netlist_hash_conflict","Saved netlist bytes differ.")
            else: require(run["netlist_sha256"] is None,"global_netlist_hash_conflict","Absent netlist cannot have a hash.")
            if run["stage_id"]==STAGES[1]:
                prior=next((r for r in state["runs"] if r["id"]==run["prior_run_id"] and r["id"] in ids),None)
                require(prior is not None and prior["stage_id"]==STAGES[0] and run["synthesis_run_id"]==prior["id"]
                        and prior["global_job_id"]==run["global_job_id"] and prior["source_key"]==run["source_key"]
                        and prior["netlist"]==run["netlist"] and prior["netlist_sha256"]==run["netlist_sha256"]
                        and object_hash(prior["verification_plan"])==object_hash(run["verification_plan"])
                        and any(object_hash(run["synthesis_adoption"])==object_hash(r) and r["run_id"]==prior["id"] and r["decision"]=="accepted" for r in state["reviews"]),
                        "global_workflow_prior_conflict","S10 must retain the exact earlier adopted S09 netlist and its original plan.")
            else: require(run["prior_run_id"] is None and run["synthesis_run_id"] is None and run["synthesis_adoption"] is None,"global_workflow_prior_conflict","S09 has no previous synthesis.")
            if run["validation_status"]=="Passed": (validate_synthesis_proof if run["stage_id"]==STAGES[0] else validate_netlist_proof)(run)
            reviews=[r for r in state["reviews"] if r["run_id"]==run["id"]]
            expected="Awaiting Review" if not reviews else "Accepted" if reviews[-1]["decision"]=="accepted" else "Changes Requested"
            require(run["review_status"]==expected and (expected!="Accepted" or run["execution_status"]=="Completed" and run["validation_status"]=="Passed"
                    and type(run.get("acceptance_epoch")) is int and run["acceptance_epoch"]==reviews[-1]["acceptance_epoch"]),
                    "global_workflow_review_conflict","Whole-system adoption differs from recorded decisions.")
            ids.add(run["id"])
        for review in state["reviews"]:
            require(type(review) is dict and review.get("run_id") in ids and review.get("decision") in ("accepted","changes_requested","return_to_stage")
                    and review.get("actor") in REVIEW_ACTORS and type(review.get("note")) is str,
                    "global_workflow_review_conflict","Invalid recorded whole-system decision.")
            run=self._run(review["run_id"]); allowed=EARLIER if run["stage_id"]==STAGES[0] else (*EARLIER,STAGES[0])
            require(review["source_key"]==run["source_key"] and (review.get("target_stage") in allowed if review["decision"]=="return_to_stage" else review.get("target_stage") is None),
                    "global_workflow_review_conflict","Decision sources or return destination differ.")
            self.store.snapshot(review["reviewed_revision_id"]); validate_policy_review(review,policies)
            if review["decision"]=="accepted":
                require(type(review.get("acceptance_epoch")) is int and review["acceptance_epoch"]==run["source_epoch_at_start"]
                        and same_revision_design(self.store, review["reviewed_revision_id"], run["revision_id"]),"global_workflow_review_conflict","Acceptance binds the actual original source epoch and semantic revision.")

        validate_submissions(self._state)

    def _persist(self):
        require_durable_write()
        name=None
        try:
            for run in self._state["runs"]: run["record_hash"]=object_hash({k:v for k,v in run.items() if k!="record_hash"})
            _io_path(self.path.parent).mkdir(parents=True,exist_ok=True)
            descriptor,name=tempfile.mkstemp(prefix=".global-workflow-",suffix=".tmp",dir=_io_path(self.path.parent))
            with os.fdopen(descriptor,"w",encoding="utf-8",newline="\n") as handle:
                handle.write(json.dumps(self._state,ensure_ascii=False,allow_nan=False,indent=2)+"\n"); handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name,self.path); self._committed=copy.deepcopy(self._state); self._storage_error=None
        except (OSError,ValueError,TypeError):
            self._state=copy.deepcopy(self._committed); self._storage_error={"code":"storage_error","message":"Whole-system save failed; last durable state retained."}; raise
        finally:
            if name and _io_path(name).exists(): _io_path(name).unlink()

    def close(self):
        with self.lock:
            self._closed=True
            if self._worker and self._worker.is_alive(): self._cancel.set()
        if self._worker and self._worker.is_alive(): self._worker.join(timeout=3)
