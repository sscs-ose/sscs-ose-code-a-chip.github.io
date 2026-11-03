"""Pinned LibreLane 3.0.16 flow: real same-chip standard-cell fence regions.

Official API sources and exact bundled OpenROAD commit are recorded in the
versioned profile. This is new placement, not a Functional Map visualization.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys

from block_layout_runtime import (VERSION, MAPPED_TIE_MASTER, build_ownership, contains, object_hash,
                                  protect_mapped_ties, require, validate_placement)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def odb_operation():
    """Executed only as a supervised child of the explicit GUI S11 run."""
    import odb
    folder = Path(os.environ["HULLCIRQ_BLOCK_ROOT"])
    mode = os.environ["HULLCIRQ_BLOCK_OPERATION"]
    database = odb.dbDatabase.create()
    odb.read_db(database, os.environ["HULLCIRQ_BLOCK_ODB_IN"])
    block = database.getChip().getBlock()
    inputs, ownership = read(folder / "block-input.json"), read(folder / "block-ownership.json")
    scale = block.getDbUnitsPerMicron()
    require(type(scale) is int and scale > 0, "block_region_database", "OpenDB needs positive integer database units.")
    instances = {inst.getName(): inst for inst in block.getInsts()}
    capacities = []
    if mode == "apply":
        require(not list(block.getRegions()), "block_region_database", "Do not overwrite existing OpenDB placement regions.")
        protected_ties = protect_mapped_ties(ownership, instances)
        core = block.getCoreArea()
        actual_core = [core.xMin() / scale, core.yMin() / scale, core.xMax() / scale, core.yMax() / scale]
        for region in ownership["regions"]:
            rectangle = region["rect_um"]
            require(contains(actual_core, rectangle), "block_region_database", "Row-snapped actual core does not contain a requested region.")
            coords = [round(v * scale) for v in rectangle]
            require(all(abs(v * scale - i) < 0.000001 for v, i in zip(rectangle, coords)), "block_region_database", "Region coordinates must fall on the OpenDB integer grid.")
            area = 0
            for cell in region["cells"]:
                inst = instances.get(cell["name"])
                require(inst is not None and inst.getMaster().getName() == cell["master"], "block_region_hierarchy", "OpenDB must contain each exact hierarchy-derived mapped cell and master.")
                master = inst.getMaster()
                area += master.getWidth() * master.getHeight()
            # Count actual row intersections, not the geometric rectangle alone.
            row_area = 0
            for row in block.getRows():
                bbox = row.getBBox()
                row_area += max(0, min(coords[2], bbox.xMax()) - max(coords[0], bbox.xMin())) * max(0, min(coords[3], bbox.yMax()) - max(coords[1], bbox.yMin()))
            require(row_area > 0 and area <= 0.7 * row_area, "block_region_capacity", "Mapped cells exceed the fixed 70 percent actual-row region capacity.")
            physical_region = odb.dbRegion_create(block, "hullcirq_" + region["id"])
            require(physical_region is not None, "block_region_database", "Failed to create a unique placement region.")
            physical_region.setRegionType("EXCLUSIVE")
            odb.dbBox_create(physical_region, *coords)
            group = odb.dbGroup_create(physical_region, "hullcirq_" + region["id"])
            require(group is not None, "block_region_database", "Failed to create the physical placement group.")
            for cell in region["cells"]:
                group.addInst(instances[cell["name"]])
            capacities.append({"id": region["id"], "cell_area_um2": area / (scale * scale), "row_area_um2": row_area / (scale * scale), "maximum_utilization": 0.7})
        write(folder / "block-region-capacity.json", {"version": VERSION, "ownership_sha256": object_hash(ownership),
              "protected_mapped_ties": protected_ties, "regions": capacities})
    elif mode == "verify":
        cells = []
        for region in ownership["regions"]:
            for source_cell in region["cells"]:
                inst = instances.get(source_cell["name"])
                require(inst is not None, "block_region_cell_missing", "A region-owned mapped cell was removed; preserve this failure instead of inventing ownership.")
                bbox, group = inst.getBBox(), inst.getGroup()
                location = inst.getLocation()
                cells.append({"name": inst.getName(), "master": inst.getMaster().getName(), "region_id": region["id"],
                              "placed": bool(inst.isPlaced()),
                              **({"mapped_tie_protected": bool(inst.isDoNotTouch())}
                                 if source_cell["master"] == MAPPED_TIE_MASTER else {}),
                              "group_member": group is not None and group.getName() == "hullcirq_" + region["id"] and group.getRegion() is not None,
                              "bbox_um": [bbox.xMin() / scale, bbox.yMin() / scale, bbox.xMax() / scale, bbox.yMax() / scale],
                              "origin_dbu": list(location), "orient": str(inst.getOrient())})
        proof = {"version": VERSION, "ownership_sha256": object_hash(ownership), "plan_sha256": inputs["plan_sha256"],
                 "database_units_per_micron": scale, "cells": cells, "validation_status": "Passed",
                 "scope": ownership["scope"], "unclaimed_final_cells": sorted(set(instances) - {c["name"] for c in cells})}
        validate_placement(ownership, proof)
        write(folder / "block-placement-proof.json", proof)
    else:
        raise ValueError("Unknown fixed block-region operation")
    odb.write_db(database, os.environ["HULLCIRQ_BLOCK_ODB_OUT"])
    odb.write_def(block, os.environ["HULLCIRQ_BLOCK_DEF_OUT"])


def register_flow():
    from librelane.common import Path as ConfigPath
    from librelane.config import Variable
    from librelane.flows import Flow
    from librelane.flows.classic import Classic
    from librelane.state import DesignFormat
    from librelane.steps import Step, Yosys

    variable = Variable("HULLCIRQ_BLOCK_INPUT", ConfigPath, "Frozen source-bound same-chip placement plan")

    class MappedBlockHierarchy(Yosys.Synthesis):
        config_vars = Yosys.Synthesis.config_vars + [variable]

        def run(self, state_in, **kwargs):
            require(self.config["SYNTH_HIERARCHY_MODE"] == "keep" and self.config["SYNTH_WRITE_NOATTR"] is False,
                    "block_region_profile", "Block mapping requires the pinned preserved-hierarchy profile.")
            updates, metrics = super().run(state_in, **kwargs)
            folder = Path(self.config["HULLCIRQ_BLOCK_INPUT"]).parent
            mapped_json = Path(str(updates[DesignFormat.NETLIST]) + ".json")
            synthesis, inputs = read(mapped_json), read(folder / "block-input.json")
            ownership = build_ownership(synthesis, inputs)
            shutil.copyfile(mapped_json, folder / "block-synthesis.json")
            write(folder / "block-ownership.json", ownership)
            return updates, metrics

    class ApplyBlockRegions(Step):
        id = "HuLLCirq.ApplyBlockRegionsV1"
        name = "Apply Source-Bound Block Placement Fences"
        inputs = [DesignFormat.ODB]
        outputs = [DesignFormat.ODB, DesignFormat.DEF]
        config_vars = [variable]
        operation = "apply"

        def run(self, state_in, **kwargs):
            folder = Path(self.config["HULLCIRQ_BLOCK_INPUT"]).parent
            out_odb = Path(self.step_dir) / "block-regions.odb"
            out_def = Path(self.step_dir) / "block-regions.def"
            env = dict(os.environ)
            env.update(HULLCIRQ_BLOCK_ROOT=str(folder), HULLCIRQ_BLOCK_OPERATION=self.operation,
                       HULLCIRQ_BLOCK_ODB_IN=str(state_in[DesignFormat.ODB]),
                       HULLCIRQ_BLOCK_ODB_OUT=str(out_odb), HULLCIRQ_BLOCK_DEF_OUT=str(out_def))
            self.run_subprocess(["openroad", "-exit", "-python", str(folder / "block_region_flow_v1.py")], env=env, **kwargs)
            require(out_odb.is_file() and out_def.is_file(), "block_region_database", "The fixed region step must create actual ODB and DEF outputs.")
            return {DesignFormat.ODB: ConfigPath(str(out_odb)), DesignFormat.DEF: ConfigPath(str(out_def))}, {}

    class VerifyBlockRegions(ApplyBlockRegions):
        id = "HuLLCirq.VerifyBlockRegionsV1"
        name = "Verify Final Source-Bound Region Containment"
        operation = "verify"

    @Flow.factory.register("HuLLCirqBlockRegionsV1")
    class BlockRegionFlow(Classic):
        Substitutions = {"Yosys.Synthesis": MappedBlockHierarchy,
                         "+OpenROAD.Floorplan": ApplyBlockRegions,
                         "+OpenROAD.FillInsertion": VerifyBlockRegions}


if __name__ == "__main__":
    if os.environ.get("HULLCIRQ_BLOCK_OPERATION") in ("apply", "verify"):
        odb_operation()
    else:
        register_flow()
        from librelane.__main__ import cli
        cli()
