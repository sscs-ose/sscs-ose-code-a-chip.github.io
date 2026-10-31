"""Isolate measured small-gate antenna endpoints with local physical buffers.

Python 3.6 for pinned OpenROAD. Preserve logic polarity and explicit PG/body
connections. The complete subsequent DRC/LVS/ARC/STA decides acceptance.
"""
import json
from pathlib import Path


def isolate(odb, db, plan, stage="pre_fanout"):
    if stage not in ("pre_fanout", "post_fanout"):
        raise ValueError("invalid antenna guard stage")
    block = db.getChip().getBlock()
    insts = {i.getName(): i for i in block.getInsts()}
    if stage == "pre_fanout" and any(name.startswith("AUTOMX_AG_") for name in insts):
        raise ValueError("antenna isolation already present; use an original CTS database")
    units = db.getTech().getDbUnitsPerMicron()
    records = []
    for index, target in enumerate(plan["targets"]):
        if target.get("stage", "pre_fanout") != stage:
            continue
        name = "AUTOMX_AG_"+str(index)
        if name in insts or block.findNet(name+"_Y"):
            raise ValueError("antenna isolation already present: "+name)
        master_name = target.get("guard_cell", "sky130_fd_sc_hd__buf_16")
        if master_name not in ("sky130_fd_sc_hd__buf_16", "sky130_fd_sc_hd__clkbuf_16"):
            raise ValueError("guard must be an approved noninverting native buffer")
        master = db.findMaster(master_name)
        if not master:
            raise ValueError("native SKY130 guard missing: "+master_name)
        instance, port = target["pin"].split("/")
        inst = insts.get(instance)
        if inst is None or inst.getMaster().getName() != target["cell"]:
            raise ValueError("measured antenna endpoint changed: "+target["pin"])
        pin = inst.findITerm(port)
        if pin is None or pin.getIoType() != "INPUT" or pin.getNet() is None:
            raise ValueError("antenna endpoint must be one connected logic input")
        parent = pin.getNet()
        guard = odb.dbInst_create(block, master, name)
        child = odb.dbNet_create(block, name+"_Y")
        child.setSigType(parent.getSigType())
        x, y = inst.getLocation()
        # Small physical output leg; detailed placement must legalize it.
        x = max(block.getDieArea().xMin(), x-master.getWidth()-3*units)
        guard.setLocation(x, y)
        guard.setOrient("R0")
        guard.setPlacementStatus("PLACED")
        guard.findITerm("A").connect(parent)
        guard.findITerm("X").connect(child)
        pin.disconnect()
        pin.connect(child)
        for port, rail in (("VPWR", "VPWR"), ("VPB", "VPWR"), ("VGND", "VGND"), ("VNB", "VGND")):
            term = guard.findITerm(port)
            supply = block.findNet(rail)
            if not term or not supply:
                raise ValueError("guard power/body connection missing")
            term.connect(supply)
        records.append({"pin": target["pin"], "guard": name, "stage": stage,
            "parent_net": parent.getName(), "child_net": child.getName(),
            "master": master.getName(), "initial_location_dbu": [x, y]})
    return {"targets": records, "status": "INSERTED_PENDING_LEGALIZATION_DRC_LVS_ARC_STA",
        "source": plan["source"], "stage": stage,
        "not_signoff": "physical input-area isolation and short output legs require routed checks"}
