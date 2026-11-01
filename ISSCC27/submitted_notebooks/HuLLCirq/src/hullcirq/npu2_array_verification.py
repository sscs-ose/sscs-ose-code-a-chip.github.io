"""Versioned finite checks for one shared scalar PE definition in a 2x2 array.

The eleven-node expansion below is ONLY an independent verifier-contract
projection. It is never a generated RTL source, adopted node, compiler result,
or physical hierarchy. Actual sources remain the eight saved logical nodes;
the compiler must elaborate four instances of their single PE module.
"""
from __future__ import annotations

import copy
import re

from .domain import DomainError
from .instance_arrays import array_shape, validate_design_arrays
from . import npu2_global_verification as explicit
from . import npu2_datapath_verification as datapath
from .verification import content_hash, object_hash

PROFILE = "npu2-shared-pe-array-2x2-v1"
PLAN_KIND = "npu2-array-global-original-matrix-v1"
TEMPLATE = PLAN_KIND
NODE_KIND = "npu2_array_node_original_job"
NODE_TEMPLATE = "npu2-shared-array-node-original-job-v1"
MONITOR_TEMPLATE = "npu2-shared-array-public-boundary-original-job-v1"
PE_ID = "npu2-pe"
PE_MODULE = "hullcirq_npu2_pe"
TOP_MODULE = "hullcirq_npu2_array_top"
LANES = explicit.LANES
NODE_IDS = tuple(node_id for node_id in explicit.NODE_IDS if node_id not in
                 ("npu2-pe01", "npu2-pe10", "npu2-pe11"))
NODE_IDS = tuple(PE_ID if node_id == "npu2-pe00" else node_id for node_id in NODE_IDS)
MODULE_NAMES = {node_id: PE_MODULE if node_id == PE_ID else explicit.MODULE_NAMES[node_id]
                for node_id in NODE_IDS}
SHARED_PE_BEHAVIOR = ("Shared scalar output-stationary MAC definition. "
                      + datapath.EXPECTED_NODES["npu2-pe00"]["behavior"].split(". ", 1)[1])


def _require(condition, message, code="npu2_array_contract_unsupported"):
    if not condition:
        raise DomainError(code, message, 422)


def is_array_design(design):
    return type(design) is dict and any(type(node) is dict and node.get("id") == PE_ID
                                       and "instance_array" in node for node in design.get("nodes", []))


def _logical_source(design):
    """Freeze logical input, not viewport, display name or physical-only edits."""
    value = copy.deepcopy(design)
    value.pop("physical_design", None)
    value["layout"] = {"nodes": {}, "viewport": {"x": 0, "y": 0, "zoom": 1}}
    value["project"]["name"] = ""
    return value


def collapse_explicit_design(design):
    """Return a NEW design draft; do not carry any results or adoptions.

    This pure conversion accepts only the existing recognized contract and
    preserves its original job, non-PE nodes, edge language and public ports.
    The caller must save into a separate system/project explicitly.
    """
    explicit.recognize_design(design)
    value = copy.deepcopy(design)
    value["settings"]["top_module"] = TOP_MODULE
    value["design_intent"]["architecture"] = "shared_PE_definition_array"
    value["global_integration"]["top_module"] = TOP_MODULE
    value["global_integration"]["one_instance_per_graph_node"] = False
    value["global_integration"]["instance_array_expansion"] = "one_scalar_module_per_declared_array_element"
    pe = copy.deepcopy(next(node for node in value["nodes"] if node["id"] == "npu2-pe00"))
    pe.update(id=PE_ID, name="PE Array", module_name=PE_MODULE, behavior=SHARED_PE_BEHAVIOR,
              instance_array={"rows": 2, "columns": 2})
    pe["constraints"].pop("row"); pe["constraints"].pop("column")
    for port in pe["ports"]:
        port["id"] = port["id"].replace("npu2-pe00-", "npu2-pe-")
    value["nodes"] = [pe if node["id"] == "npu2-pe00" else node for node in value["nodes"]
                      if node["id"] not in ("npu2-pe01", "npu2-pe10", "npu2-pe11")]
    for edge in value["edges"]:
        for side in ("source", "target"):
            endpoint = edge[side]
            match = re.fullmatch(r"npu2-pe([01])([01])", endpoint["node_id"])
            if match:
                endpoint["node_id"] = PE_ID
                endpoint["port_id"] = re.sub(r"^npu2-pe[01][01]-", "npu2-pe-", endpoint["port_id"])
                endpoint["instance_index"] = [int(match[1]), int(match[2])]
    old_positions = value["layout"]["nodes"]
    if "npu2-pe00" in old_positions:
        old_positions[PE_ID] = old_positions["npu2-pe00"]
    for lane in LANES:
        old_positions.pop("npu2-pe" + lane, None)
    return value


def expand_for_contracts(design):
    """Validate actual array input and build a labelled verifier-only witness."""
    _require(type(design) is dict and type(design.get("nodes")) is list,
             "A complete saved shared-array design is required.")
    _require(tuple(node.get("id") for node in design["nodes"] if type(node) is dict) == NODE_IDS,
             "The shared 2x2 profile requires eight logical nodes in their declared order.")
    validate_design_arrays(design)
    by_id = {node["id"]: node for node in design["nodes"]}
    _require(all(node["module_name"] == MODULE_NAMES[node["id"]] for node in design["nodes"]),
             "The shared-array profile requires its saved public module identities.")
    pe = by_id[PE_ID]
    _require(array_shape(pe) == (2, 2) and all("instance_array" not in node for node in design["nodes"] if node["id"] != PE_ID),
             "This finite NPU profile verifies only a single 2x2 PE array; larger structural arrays are not verified.")
    expected = copy.deepcopy(datapath.EXPECTED_NODES["npu2-pe00"])
    expected["behavior"] = SHARED_PE_BEHAVIOR
    expected["constraints"].pop("row"); expected["constraints"].pop("column")
    for port in expected["ports"]:
        port["id"] = port["id"].replace("npu2-pe00-", "npu2-pe-")
    _require(pe.get("parent_id") is None and pe.get("verification") is None
             and all(object_hash(pe.get(key)) == object_hash(item) for key, item in expected.items()),
             "Use the saved shared scalar MAC behavior, public ports and constraints without alteration.")
    _require(design.get("settings", {}).get("top_module") == TOP_MODULE
             and design.get("design_intent", {}).get("architecture") == "shared_PE_definition_array"
             and design.get("global_integration", {}).get("top_module") == TOP_MODULE
             and design["global_integration"].get("one_instance_per_graph_node") is False
             and design["global_integration"].get("instance_array_expansion") == "one_scalar_module_per_declared_array_element",
             "Use the versioned shared-array top and explicit instance-expansion contract.")
    value = _logical_source(design)
    value["settings"]["top_module"] = "hullcirq_npu2_top"
    value["design_intent"]["architecture"] = "four_explicit_parallel_output_stationary_MACs"
    value["global_integration"]["top_module"] = "hullcirq_npu2_top"
    value["global_integration"]["one_instance_per_graph_node"] = True
    value["global_integration"].pop("instance_array_expansion")
    expanded = []
    witness = []
    for node in value["nodes"]:
        if node["id"] != PE_ID:
            expanded.append(node)
            witness.append({"logical_node_id": node["id"], "instance_index": None, "contract_node_id": node["id"]})
            continue
        for lane in LANES:
            item = copy.deepcopy(node)
            item.update(id="npu2-pe" + lane, name="PE " + lane,
                        module_name=explicit.MODULE_NAMES["npu2-pe" + lane])
            item.pop("instance_array")
            item.update(copy.deepcopy(datapath.EXPECTED_NODES[item["id"]]))
            expanded.append(item)
            witness.append({"logical_node_id": PE_ID, "instance_index": [int(x) for x in lane],
                            "contract_node_id": item["id"]})
    value["nodes"] = expanded
    for edge in value["edges"]:
        for side in ("source", "target"):
            endpoint = edge[side]
            if endpoint["node_id"] == PE_ID:
                index = endpoint.pop("instance_index")
                lane = "".join(str(x) for x in index)
                endpoint["node_id"] = "npu2-pe" + lane
                endpoint["port_id"] = endpoint["port_id"].replace("npu2-pe-", "npu2-pe" + lane + "-")
    explicit.recognize_design(value)
    return value, {"kind": "verifier_only_expansion_witness_not_RTL_or_compiler_hierarchy",
                   "version": 1, "mapping": witness,
                   "scope": "independent_original_job_contract_and_reference_reuse_only"}


def recognize_design(design):
    _, witness = expand_for_contracts(design)
    return {"profile": PROFILE, "node_ids": list(NODE_IDS), "module_names": copy.deepcopy(MODULE_NAMES),
            "instance_counts": {node_id: 4 if node_id == PE_ID else 1 for node_id in NODE_IDS},
            "contract_projection": witness}


def top_interface(design):
    value, _ = expand_for_contracts(design)
    result = explicit._top_interface(value)
    result["module_name"] = TOP_MODULE
    return result


def original_job(design):
    expand_for_contracts(design)
    return copy.deepcopy(design["verification_jobs"][0])


def _node_plan_from_source(source, node_id):
    from .context import build_node_context
    from .verification import build_verification_plan
    expanded, witness = expand_for_contracts(source)
    _require(node_id in NODE_IDS, "Select an existing shared-array logical node.")
    ids = ["npu2-pe" + lane for lane in LANES] if node_id == PE_ID else [node_id]
    bases = [build_verification_plan(expanded, item) for item in ids]
    result = copy.deepcopy(bases[0])
    if node_id == PE_ID:
        vectors = [copy.deepcopy(vector) for base in bases for vector in base["expanded_vectors"]]
        # Each lane recipe starts with synchronous reset. One physical scalar
        # DUT is checked successively against all four ORIGINAL job lanes.
        trace = datapath.reference_trace("npu2_pe_original_job", vectors)
        vector_hash = object_hash(vectors)
        result.update(expanded_vectors=vectors, vector_hash=vector_hash, reference_trace=trace,
                      reference_trace_hash=object_hash(trace), vector_count=len(vectors),
                      testbench=datapath.testbench("npu2_pe_original_job", PE_MODULE, trace, vector_hash))
        result["testbench_sha256"] = content_hash(result["testbench"])
        result["coverage"] = {"source_job_k": source["verification_jobs"][0]["k"],
                              "original_job_lanes_checked": list(LANES),
                              "scalar_DUT_instances": 1, "full_array_concurrency_checked": False,
                              "lane_recipes": [copy.deepcopy(base["coverage"]) for base in bases]}
    context = build_node_context(source, "verification-source", node_id)
    actual_node = next(node for node in source["nodes"] if node["id"] == node_id)
    actual_contract = {"kind": NODE_KIND, "version": 1, "source_node": copy.deepcopy(actual_node),
                       "source_edges": [copy.deepcopy(edge) for edge in source["edges"]
                                        if any(edge[side]["node_id"] == node_id for side in ("source", "target"))],
                       "source_job": copy.deepcopy(source["verification_jobs"][0]),
                       "settings": copy.deepcopy(source["settings"]),
                       "global_integration": copy.deepcopy(source["global_integration"]),
                       "design_intent": copy.deepcopy(source["design_intent"])}
    result.update(kind=NODE_KIND, source_node_id=node_id, module_name=MODULE_NAMES[node_id],
                  node_input_hash=context["node_input_hash"], testbench_template_version=NODE_TEMPLATE,
                  contract=actual_contract, contract_hash=object_hash(actual_contract),
                  source_design=copy.deepcopy(source), contract_projection=witness,
                  projected_plan_kind=bases[0]["kind"], projected_plans=bases,
                  stimulus_origin="same_saved_array_design_original_job_with_explicit_verifier_only_contract_projection",
                  reference_origin="ordinary_program_independent_original_job_references_not_generated_RTL",
                  testbench_origin="versioned_shared_array_original_job_adapter")
    result["limits"] += ["Projection entries are verifier contracts, never adopted explicit-node RTL or observed hierarchy.",
                         "Scalar PE local checks replay all four original lanes sequentially; array concurrency is checked only by S08/S10."]
    return result


def build_node_plan(design, node_id, template_version=None):
    _require(template_version in (None, NODE_TEMPLATE), "Unsupported shared-array node template.", "unsupported_verification_template")
    return _node_plan_from_source(_logical_source(design), node_id)


def validate_node_plan(plan):
    try:
        valid = type(plan) is dict and plan.get("kind") == NODE_KIND and object_hash(plan) == object_hash(
            _node_plan_from_source(plan["source_design"], plan["source_node_id"]))
    except (KeyError, TypeError, ValueError, AttributeError, DomainError):
        valid = False
    _require(valid, "Frozen shared-array source, job, vectors and testbench must rebuild exactly.", "invalid_verification_plan")


def node_asserted_trace(plan):
    validate_node_plan(plan)
    base = plan["projected_plans"][0]
    kind = base["kind"]
    if plan["source_node_id"] == PE_ID:
        return datapath.datapath_asserted_trace({"kind": kind, "reference_trace": plan["reference_trace"]})
    if kind in ("npu2_collector_original_job", "npu2_post_original_job"):
        return datapath.datapath_asserted_trace(base)
    if kind in ("npu2_scheduler_original_job", "npu2_dispatcher_original_job"):
        from .npu2_schedule_verification import schedule_asserted_trace
        return schedule_asserted_trace(base)
    if kind == "fifo_original_job":
        from .fifo_spec_verification import fifo_asserted_trace
        return fifo_asserted_trace(base)
    from .implementation_specs import _npu2_control_asserted_trace, _npu2_buffer_asserted_trace
    return (_npu2_control_asserted_trace if kind == "npu2_control_original_job" else _npu2_buffer_asserted_trace)(base)


def build_plan(design):
    value, witness = expand_for_contracts(design)
    result = explicit.build_plan(value)
    result.update(kind=PLAN_KIND, profile=PROFILE, contract_projection=witness)
    result["recipe"]["kind"] = PLAN_KIND
    result["vector_hash"] = object_hash(result["recipe"])
    result["testbench"] = explicit._global_tb(TOP_MODULE, result["recipe"], result["vector_hash"])
    result["testbench_sha256"] = content_hash(result["testbench"])
    result["limits"].append("Eight actual logical sources include one shared scalar PE definition elaborated exactly four times; projection IDs name verification lanes, not adopted nodes.")
    return result


def validate_plan(design, plan):
    _require(object_hash(plan) == object_hash(build_plan(design)),
             "Shared-array whole-system plan must rebuild exactly from saved graph and original job.", "npu2_array_global_plan_conflict")


def _require_plan(plan):
    _require(type(plan) is dict and plan.get("kind") == PLAN_KIND and type(plan.get("version")) is int
             and plan["version"] == 1 and plan.get("profile") == PROFILE and plan.get("output_count") == 4,
             "Use the versioned shared-array original-job plan.", "npu2_array_global_plan_unsupported")


def _explicit_plan_view(plan):
    _require_plan(plan)
    value = copy.deepcopy(plan)
    value.update(kind=explicit.PLAN_KIND, profile=explicit.PROFILE)
    return value


def expected_instance_counts(manifest):
    _require(type(manifest) is dict and type(manifest.get("nodes")) is list,
             "A complete shared-array adopted manifest is required.")
    recognize_design(manifest.get("design"))
    _require([entry.get("node_id") for entry in manifest["nodes"]] == list(NODE_IDS)
             and all(entry.get("module_name") == MODULE_NAMES[entry["node_id"]] for entry in manifest["nodes"]),
             "The shared-array source manifest must retain exactly its eight actual source nodes.")
    return {node_id: 4 if node_id == PE_ID else 1 for node_id in NODE_IDS}


def compiler_public_hierarchy(scope_lines, manifest):
    """Find actual compiler scopes, requiring declared pe00/01/10/11 names."""
    expected = expected_instance_counts(manifest)
    _require(type(scope_lines) is list and all(type(line) is str for line in scope_lines), "Retain actual compiler scope text.")
    scopes = {}
    for line in scope_lines:
        match = re.fullmatch(r'(S_[A-Za-z0-9_]+)\s+\.scope (\w+),\s*"([^"]+)"(?:\s+"([^"]+)")?(.*);', line)
        _require(match is not None, "Unsupported compiler scope syntax.")
        identifier, kind, name, module, rest = match.groups()
        _require(identifier not in scopes, "Compiler scope IDs must be unique.")
        parents = re.findall(r'\bS_[A-Za-z0-9_]+\b', rest)
        scopes[identifier] = {"kind": kind, "name": name, "module": module, "parent": parents[-1] if parents else None}
    def path(identifier, seen=None):
        seen = set() if seen is None else seen
        _require(identifier in scopes and identifier not in seen, "Compiler scope ancestry must be complete and acyclic.")
        seen.add(identifier); item = scopes[identifier]
        _require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?', item["name"]) is not None,
                 "Observable compiler paths require safe names.")
        return (path(item["parent"], seen) + "." if item["parent"] else "") + item["name"]
    result = {}
    for entry in manifest["nodes"]:
        locations = []
        for identifier, item in scopes.items():
            if item["kind"] == "module" and item["module"] == entry["module_name"]:
                absolute = path(identifier)
                _require(absolute.startswith("hullcirq_global_tb.dut."), "Adopted modules must elaborate below the candidate top.")
                locations.append(absolute.removeprefix("hullcirq_global_tb."))
        _require(len(locations) == expected[entry["node_id"]], "Elaborate every declared source with its exact instance count.")
        if entry["node_id"] == PE_ID:
            _require(set(locations) == {"dut.pe" + lane for lane in LANES},
                     "The four shared PE scopes must be the direct declared pe00, pe01, pe10 and pe11 instances.")
            locations = ["dut.pe" + lane for lane in LANES]
        result[entry["node_id"]] = locations
    return result


def monitor_hierarchy_projection(hierarchy):
    _require(type(hierarchy) is dict and list(hierarchy) == list(NODE_IDS)
             and all(type(hierarchy[node_id]) is list and len(hierarchy[node_id]) == (4 if node_id == PE_ID else 1)
                     and all(type(path) is str for path in hierarchy[node_id]) for node_id in NODE_IDS),
             "Use the actual eight-source compiler-derived public hierarchy.")
    _require(len(set(path for paths in hierarchy.values() for path in paths)) == 11,
             "Every actual graph instance must have a distinct compiler-derived path.")
    _require(hierarchy[PE_ID] == ["dut.pe" + lane for lane in LANES],
             "Bind each scalar PE to its declared direct row/column instance in row-major order.")
    result = {}
    for node_id in explicit.NODE_IDS:
        if node_id.startswith("npu2-pe"):
            result[node_id] = [hierarchy[PE_ID][LANES.index(node_id[-2:])]]
        else:
            result[node_id] = hierarchy[node_id]
    return result


def instrument_public_testbench(plan, hierarchy):
    tb, monitor = explicit.instrument_public_testbench(_explicit_plan_view(plan), monitor_hierarchy_projection(hierarchy))
    for lane in LANES:
        before, after = "HULLCIRQ_PE node=npu2-pe" + lane, "HULLCIRQ_PE node=npu2-pe"
        tb, monitor = tb.replace(before, after), monitor.replace(before, after)
    return tb, monitor


def expected_output_count(plan=None):
    if plan is not None:
        _require_plan(plan)
    return 4


def public_transfer_counts(plan):
    return explicit.public_transfer_counts(_explicit_plan_view(plan))


def expected_pe_records(plan):
    _require_plan(plan)
    return [{"node_id": PE_ID, "instance_index": [int(x) for x in lane], "lane": lane,
             "inputs": plan["recipe"]["source_job"]["k"], "outputs": 1} for lane in LANES]


def runtime_records_pass(stdout, plan):
    _require_plan(plan)
    _require(type(stdout) is str, "Retained simulator stdout must be text.")
    # Reuse the exact finite assertion/transfer parser with a labelled adapter;
    # never rewrite actual logs or actual shared-module source identities.
    translated = stdout
    for lane in LANES:
        translated = translated.replace("HULLCIRQ_PE node=npu2-pe lane=" + lane,
                                        "HULLCIRQ_PE node=npu2-pe" + lane + " lane=" + lane)
    passed, outputs, streams, _ = explicit.runtime_records_pass(translated, _explicit_plan_view(plan))
    records = [{"node_id": PE_ID, "instance_index": [int(x) for x in lane], "lane": lane,
                "inputs": int(inputs), "outputs": int(count)}
               for lane, inputs, count in re.findall(r'^HULLCIRQ_PE node=npu2-pe lane=(00|01|10|11) inputs=(\d+) outputs=(\d+)$', stdout, re.M)]
    return passed and object_hash(records) == object_hash(expected_pe_records(plan)), outputs, streams, records


def proof_expectations(manifest, plan):
    return {"output_marker": f"HULLCIRQ_GLOBAL_PASS outputs=4 vector_hash={plan['vector_hash']}",
            "public_marker": f"HULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}",
            "output_count": 4, "instance_counts": expected_instance_counts(manifest),
            "public_stream_transfers": [{"stream": name, "transfers": count} for name, count in public_transfer_counts(plan).items()],
            "pe_records": expected_pe_records(plan)}
