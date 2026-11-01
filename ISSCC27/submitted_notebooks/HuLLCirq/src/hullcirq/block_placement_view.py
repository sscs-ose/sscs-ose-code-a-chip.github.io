"""Read-only source-bound placement geometry, not a new placement or role map."""
from __future__ import annotations

import copy
import hashlib
import re

from .block_recipe import recipe_for, runtime_for
from .domain import DomainError
from .physical_tools import configuration_projection
from .store import strict_loads
from .verification import object_hash

VERSION = "block-placement-view-v1"
SCOPE = "Original region-owned mapped cells only; original top-level glue and inserted clock, physical/filler and interconnect support are excluded."


def require(condition, code, message, status=409):
    if not condition:
        raise DomainError(code, message, status)


def block_placement_projection(run, validate_saved):
    """Validate each selected saved execution before exposing its exact bboxes.

    ``validate_saved`` is the manager's existing full physical-proof validator,
    not an execution callback. No current-source observation, persistence,
    acceptance or recipe modification is performed by this function.
    """
    configuration = run.get("runtime_configuration")
    recipe = recipe_for(configuration)
    require(run.get("execution_status") == "Completed" and run.get("validation_status") == "Passed"
            and recipe is not None and run.get("evidence_kind") in ("trusted_fixed_tool_execution", "trusted_saved_tool_revalidation")
            and run.get("checks", {}).get("software_qa_fixture") is not True,
            "block_placement_view_unavailable", "Block Placement requires a completed Passed saved block-region execution with its original proof. Mixed, failed and unexecuted layouts have no supported block geometry view.")
    result = run["checks"]
    entries = result.get("artifacts", [])
    require(type(entries) is list and len({entry.get("id") for entry in entries if type(entry) is dict}) == len(entries),
            "block_placement_view_integrity", "Retain one exact artifact manifest for the selected block execution.")
    by_id = {entry["id"]: entry for entry in entries}
    needed = {"block-input", "block-plan", "block-synthesis", "block-ownership", "block-capacity", "block-placement-proof",
              "block-flow", "block-runtime", "def", "config"}
    require(needed <= set(by_id), "block_placement_view_unavailable", "The selected block execution is missing its retained placement proof or source artifacts.")
    require(validate_saved(run) is None, "block_placement_view_integrity", "The complete saved physical proof must validate before exposing block geometry.")

    # Use only the fixed manifest IDs. Recheck the exact bytes consumed for the
    # projection even after the full validator, so a later file change cannot
    # become geometry merely because an earlier validation completed.
    from .physical_workflow import _artifact_path
    raw_cache = {}
    def raw(identifier):
        if identifier not in raw_cache:
            entry = by_id[identifier]
            path = _artifact_path(result, entry)
            data = path.read_bytes()
            require(type(entry.get("bytes")) is int and len(data) == entry["bytes"]
                    and hashlib.sha256(data).hexdigest() == entry.get("sha256"),
                    "block_placement_view_integrity", "The selected source-bound placement artifact changed: " + identifier)
            raw_cache[identifier] = data
        return raw_cache[identifier]
    def load(identifier):
        return strict_loads(raw(identifier).decode("utf-8"))

    require(hashlib.sha256(raw("block-runtime")).hexdigest() == recipe.runtime_sha256
            and hashlib.sha256(raw("block-flow")).hexdigest() == recipe.flow_sha256,
            "block_placement_view_integrity", "The saved block runtime and launcher must match the selected immutable recipe.")
    runtime = runtime_for(configuration)
    inputs = runtime.source_input(configuration, run["source_manifest"], run["settings"]["top_module"])
    require(object_hash(load("block-input")) == object_hash(inputs)
            and object_hash(load("block-plan")) == configuration["block_plan_sha256"]
            and object_hash(load("config")) == object_hash(configuration_projection(run["settings"], configuration, run["source_manifest"])),
            "block_placement_view_integrity", "The view must retain the exact saved source, placement plan and configuration.")
    ownership = runtime.build_ownership(load("block-synthesis"), inputs)
    require(object_hash(load("block-ownership")) == object_hash(ownership),
            "block_placement_view_integrity", "Rebuild block ownership only from the exact retained mapped synthesis hierarchy.")
    capacity, proof = load("block-capacity"), load("block-placement-proof")
    runtime.validate_capacity(ownership, capacity)
    runtime.validate_placement(ownership, proof)
    final_def = raw("def").decode("utf-8")
    runtime.validate_def_binding(final_def, ownership, proof)
    body = re.search(r"\bCOMPONENTS\s+([0-9]+)\s*;(.*?)\bEND\s+COMPONENTS\b", final_def, re.S)
    require(body is not None, "block_placement_view_integrity", "Retain the complete final DEF component section.")
    names = re.findall(r"(?:^|;)\s*-\s+(\S+)\s+\S+", body[2])
    require(len(names) == len(set(names)) == int(body[1]),
            "block_placement_view_integrity", "Final DEF component names and count must be complete and unique.")
    # V1 had no explicit encoded field. Its own immutable validator establishes
    # that source/proof spelling; never apply the latest recipe to old evidence.
    owned_odb = {cell.get("odb_name", cell["name"]) for cell in proof["cells"]}
    excluded = set(names) - owned_odb
    require(owned_odb <= set(names) and len(owned_odb) == len(proof["cells"])
            and type(proof.get("unclaimed_final_cells")) is list
            and len(proof["unclaimed_final_cells"]) == len(set(proof["unclaimed_final_cells"]))
            and set(proof["unclaimed_final_cells"]) == excluded,
            "block_placement_view_integrity", "The view must account exactly for owned and unclaimed final instances without inventing support ownership.")
    cells = [{"name": cell["name"], "source_name": cell.get("source_name", cell["name"]),
              "odb_name": cell.get("odb_name", cell["name"]), "master": cell["master"],
              "region_id": cell["region_id"], "bbox_um": copy.deepcopy(cell["bbox_um"])} for cell in proof["cells"]]
    return {"version": VERSION, "validation_status": "Passed", "run_id": run["id"], "physical_run_id": run["id"],
            "record_hash": run.get("record_hash"), "revision_id": run["revision_id"],
            "physical_design_revision_id": run.get("physical_design_revision_id", run["revision_id"]),
            "profile_version": recipe.profile_version, "scope": SCOPE,
            "source": {"global_job_id": run["global_job_id"], "synthesis_run_id": run["synthesis_run_id"],
                       "netlist_run_id": run["netlist_run_id"], "source_manifest_sha256": run["source_manifest_sha256"],
                       "plan_sha256": configuration["block_plan_sha256"],
                       "proof_sha256": by_id["block-placement-proof"]["sha256"],
                       "ownership_sha256": by_id["block-ownership"]["sha256"],
                       "ownership_content_sha256": object_hash(ownership), "final_def_sha256": by_id["def"]["sha256"]},
            "core_um": copy.deepcopy(inputs["plan"]["core_um"]),
            "regions": [{key: copy.deepcopy(region[key]) for key in ("id", "targets", "rect_um")} for region in ownership["regions"]],
            "cells": cells,
            "counts": {"original_owned_cells": len(cells), "regions": len(ownership["regions"]),
                       "unclaimed_final_cells": len(excluded), "final_DEF_components": len(names),
                       "original_mapped_ties": len(capacity.get("protected_mapped_ties", []))},
            "limits": [SCOPE, "This is a validated saved placement view, not another placement run, a full routed mask renderer or a Functional Map inference.",
                       "Historical evidence remains bound to its selected run and original inputs; viewing it does not adopt it or establish currentness.",
                       "S11 routing checks are not signoff DRC, LVS, post-layout verification or foundry qualification."]}
