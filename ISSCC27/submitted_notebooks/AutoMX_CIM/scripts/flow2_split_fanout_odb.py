#!/usr/bin/env python3
"""Insert bounded physical buffer trees in a post-CTS OpenDB, before routing.

Run with the pinned container's openroad -python. Clocks are included and
must undergo fresh routing, extracted STA, DRC and LVS afterwards.
Keep this entry point compatible with Python 3.6 embedded in older OpenROAD.
"""

import argparse
import json
from pathlib import Path
import sys


def group_loads(loads, limit):
    if limit < 2:
        raise ValueError("fanout limit must be at least two")
    return [loads[i:i + limit] for i in range(0, len(loads), limit)]


def split_net(loads, original, make_buffer, *, limit=8):
    """Callbacks keep OpenDB mutation separate from the testable tree shape.

    make_buffer(parent_net, loads) moves loads to a new output net and returns
    the new buffer input, already attached to parent_net. Repeated grouping
    bounds the old driver's load as well as every inserted buffer's load.
    """
    if limit < 2:
        raise ValueError("fanout limit must be at least two")
    current = list(loads)
    added = 0
    while len(current) > limit:
        current = [make_buffer(original, group) for group in group_loads(current, limit)]
        added += len(current)
    return added


def wrapper_adc_connectivity(block):
    """Reject the disconnected LEF bus interface before changing the ODB."""
    adc = next((i for i in block.getInsts() if i.getName() == "adc_i"), None)
    if adc is None:
        return {"status": "NOT_APPLICABLE"}
    if adc.getMaster().getName() != "adc_top":
        raise ValueError("adc_i does not contain the real adc_top macro")
    errors = []
    checked = []
    for bus in ("result_out", "config_1_in", "config_2_in"):
        for bit in range(16):
            name = "{}[{}]".format(bus, bit)
            pin = adc.findITerm(name)
            net = pin.getNet() if pin else None
            if net is None:
                errors.append("adc_i/" + name + " is disconnected")
            elif bus.startswith("config_"):
                value = 0x0400 if bus == "config_1_in" else 0x8421
                expected = "HI" if value & (1 << bit) else "LO"
                # Supply-net ties are never routed by PDN or router (_03 LVS).
                if net.getSigType() in ("POWER", "GROUND"):
                    errors.append("adc_i/" + name + " is tied to supply net " + net.getName())
                    continue
                drivers = [t for t in net.getITerms() if t.isOutputSignal()]
                if len(drivers) != 1:
                    errors.append("adc_i/" + name + " has {} drivers".format(len(drivers)))
                    continue
                driver = drivers[0]
                if (driver.getInst().getMaster().getName() != "sky130_fd_sc_hd__conb_1"
                        or driver.getMTerm().getName() != expected):
                    errors.append("adc_i/" + name + " must be driven by conb_1/" + expected)
            checked.append(name)
    if errors:
        raise ValueError("wrapper ADC bus connectivity failed: " + "; ".join(errors))
    return {"status": "PASS_ADC_BUS_CONNECTIVITY", "checked_pins": checked,
            "scope": "48 digital ADC ITerms; config constants from conb_1 HI/LO; analog behavior requires measurement"}


def repair(odb, db, *, limit=4, diode_reserve=1):
    block = db.getChip().getBlock()
    adc_connectivity = wrapper_adc_connectivity(block)
    masters = {False: db.findMaster("sky130_fd_sc_hd__buf_4"),
               True: db.findMaster("sky130_fd_sc_hd__clkbuf_4")}
    if not all(masters.values()):
        raise ValueError("SKY130 HD buf_4 and clkbuf_4 masters are required")
    if any(i.getName().startswith("AUTOMX_FO_") for i in block.getInsts()):
        raise ValueError("input ODB already has this repair; use a new flow tag")

    def loads(net):
        def digital_macro_input(t):
            # The passive core LEF exposes bidirectional analog/digital pins.
            # These named controls are digitally driven; BL* must stay analog.
            return (diode_reserve == 2 and t.getIoType() == "INOUT"
                and t.getInst().getMaster().getName() == "automx_ternary_cim_4x4_core"
                and t.getMTerm().getName().startswith(("WPOS_", "WNEG_", "WLP", "WLN")))
        return ([t for t in net.getITerms() if (t.getIoType() == "INPUT" or digital_macro_input(t))
                 and t.getSigType() not in ("POWER", "GROUND")]
                + [t for t in net.getBTerms() if t.getIoType() == "OUTPUT"])

    def position(pin):
        if hasattr(pin, "getInst"):
            return tuple(pin.getInst().getLocation())
        die = block.getDieArea()
        return ((die.xMin() + die.xMax()) // 2, (die.yMin() + die.yMax()) // 2)

    def is_clock(net, sinks):
        return (net.getSigType() == "CLOCK" or net.getName() == "clk_i" or
                any(t.getMTerm().getName() in ("CLK", "CK") for t in sinks if hasattr(t, "getMTerm")) or
                any("__clkbuf_" in t.getInst().getMaster().getName()
                    for t in net.getITerms() if t.getIoType() == "OUTPUT"))

    serial = 0
    records = []
    for net in sorted(list(block.getNets()), key=lambda n: n.getName()):
        if net.getSigType() in ("POWER", "GROUND") or net.isSpecial():
            continue
        pins = sorted(loads(net), key=position)
        if len(pins) <= limit:
            continue
        drivers = [t for t in net.getITerms() if t.getIoType() == "OUTPUT"] + [
            t for t in net.getBTerms() if t.getIoType() == "INPUT"]
        if len(drivers) != 1:
            raise ValueError(f"net {net.getName()} has {len(drivers)} drivers")
        clock = is_clock(net, pins)
        master = masters[clock]

        def insert(parent, children):
            nonlocal serial
            serial += 1
            name = f"AUTOMX_FO_{serial}"
            inst = odb.dbInst_create(block, master, name)
            child_net = odb.dbNet_create(block, name + "_Y")
            if clock:
                child_net.setSigType("CLOCK")
            a, y = inst.findITerm("A"), inst.findITerm("X")
            if not a or not y:
                raise ValueError("buffer master does not have A/X pins")
            locations = [position(p) for p in children]
            inst.setLocation(sum(x for x, _ in locations) // len(locations),
                             sum(y for _, y in locations) // len(locations))
            inst.setOrient("R0")
            inst.setPlacementStatus("PLACED")
            a.connect(parent)
            y.connect(child_net)
            for pin in children:
                pin.disconnect()
                pin.connect(child_net)
            # Supply/well connections are explicit even before global_connect.
            for port, supply in (("VPWR", "VPWR"), ("VPB", "VPWR"),
                                 ("VGND", "VGND"), ("VNB", "VGND")):
                pin = inst.findITerm(port)
                if pin:
                    supply_net = block.findNet(supply)
                    if not supply_net:
                        raise ValueError(f"supply net missing: {supply}")
                    pin.connect(supply_net)
            return a

        added = split_net(pins, net, insert, limit=limit)
        records.append({"net": net.getName(), "original_loads": len(pins),
                        "clock": clock, "inserted_buffers": added})
    violations = [{"net": n.getName(), "loads": len(loads(n))} for n in block.getNets()
                  if n.getSigType() not in ("POWER", "GROUND") and len(loads(n)) > limit]
    if violations:
        raise ValueError(f"unrepaired topological fanout: {violations[:5]}")
    return {"format": "automx-cim-flow2-fanout-topology-v1",
            "status": "TOPOLOGY_REPAIRED_PENDING_ROUTE_STA_DRC_LVS",
            "sink_limit": limit, "inserted_buffers": serial, "nets": records,
            "antenna_reserve_per_sink": diode_reserve,
            "projected_post_diode_sink_limit": (1 + diode_reserve) * limit,
            "digital_core_controls_included": diode_reserve == 2,
            "remaining_topological_violations": violations,
            "wrapper_adc_connectivity": adc_connectivity,
            "not_signoff": "sink count only; timing/Liberty fanout load, skew and physical checks require the subsequent full flow"}


def runtime_check(odb):
    required = ("dbDatabase", "read_db", "write_db", "dbInst_create", "dbNet_create")
    missing = [name for name in required if not hasattr(odb, name)]
    return {"format": "automx-cim-openroad-python-runtime-v1",
            "status": "PASS" if not missing else "FAIL",
            "python_version": sys.version, "missing_odb_api": missing}


def repair_guarded(odb, db, plan, limit=3):
    # Keep the two already measured pre-fanout guards in place. Generated
    # AUTOMX_FO_* receivers only exist AFTER deterministic tree insertion.
    try:
        from .flow2_antenna_guard_odb import isolate
    except ImportError:  # script entry point inside the pinned OpenROAD
        from flow2_antenna_guard_odb import isolate
    if (any(t.get("stage", "pre_fanout") not in ("pre_fanout", "post_fanout") for t in plan["targets"])
            or len({t["pin"] for t in plan["targets"]}) != len(plan["targets"])):
        raise ValueError("antenna guard plan has invalid stages or repeated endpoints")
    first = isolate(odb, db, plan, stage="pre_fanout")
    result = repair(odb, db, limit=limit, diode_reserve=2)
    last = isolate(odb, db, plan, stage="post_fanout")
    result["antenna_isolation"] = dict(first, targets=first["targets"]+last["targets"],
        stage="PRE_AND_POST_FANOUT")
    # Each guard replaces exactly one sink and creates a one-sink output
    # net. Preserve the splitter bound, including on newly clocked nets.
    block = db.getChip().getBlock()
    violations = []
    for net in block.getNets():
        if net.getSigType() in ("POWER", "GROUND"):
            continue
        count = sum(p.getIoType() == "INPUT" or (
            p.getIoType() == "INOUT" and p.getInst().getMaster().getName() == "automx_ternary_cim_4x4_core"
            and p.getMTerm().getName().startswith(("WPOS_", "WNEG_", "WLP", "WLN")))
            for p in net.getITerms())
        count += sum(p.getIoType() == "OUTPUT" for p in net.getBTerms())
        if count > limit:
            violations.append({"net": net.getName(), "loads": count})
    if violations:
        raise ValueError("post-guard fanout bound failed: "+str(violations[:5]))
    result["post_guard_topological_violations"] = violations
    return result


if __name__ == "__main__":
    import odb
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-odb")
    parser.add_argument("--output-odb")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--guard-plan", type=Path)
    parser.add_argument("--check-runtime", action="store_true",
                        help="validate embedded Python/ODB before starting a full flow")
    args = parser.parse_args()
    if args.check_runtime:
        result = runtime_check(odb)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "PASS" else 1)
    if not all((args.input_odb, args.output_odb, args.report)):
        parser.error("--input-odb, --output-odb and --report are required for repair")
    db = odb.dbDatabase.create()
    odb.read_db(db, args.input_odb)
    if args.guard_plan:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        result = repair_guarded(odb, db, json.loads(args.guard_plan.read_text()), limit=args.limit)
    else:
        result = repair(odb, db, limit=args.limit, diode_reserve=1)
    odb.write_db(db, args.output_odb)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
