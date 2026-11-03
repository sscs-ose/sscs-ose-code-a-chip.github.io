from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path

from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.load import derive_net_loads
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def find_cell(lib, exact, token):
    if exact in lib.cells:
        return exact
    xs = sorted(n for n in lib.cells if token in n.lower())
    if not xs:
        raise AssertionError("Missing real SKY130 cell matching " + token)
    return xs[0]

def sole_arc(cell, related_pin):
    xs = [
        a for a in cell.timing_arcs
        if a.related_pin == related_pin and not a.when
    ]
    if len(xs) != 1:
        raise AssertionError(
            f"Expected one unconditional arc for {cell.name} pin={related_pin}; "
            f"got {len(xs)}"
        )
    return xs[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    lib = parse_liberty_file(a.lib)
    p = LibertyDelayProvider(lib)

    inv = find_cell(lib, "sky130_fd_sc_hd__inv_1", "__inv_")
    nand = find_cell(lib, "sky130_fd_sc_hd__nand2_1", "__nand2_")
    buf = find_cell(lib, "sky130_fd_sc_hd__buf_1", "__buf_")

    n = Network(
        ["A", "B"], ["Y"],
        [
            Cell("U_INV", "INV", {"A": "A"}, "n1", 0, 0,
                 library_cell=inv, library_output_pin="Y"),
            Cell("U_NAND", "NAND2", {"A": "n1", "B": "B"}, "n2", 0, 0,
                 library_cell=nand, library_output_pin="Y"),
            Cell("U_BUF", "BUF", {"A": "n2"}, "Y", 0, 0,
                 library_cell=buf, library_output_pin="X"),
        ],
        {"A": 0, "B": 1},
    )

    # Independent load authority from the actual sink pins.
    cap_nand_a = lib.cells[nand].pins["A"].capacitance_ff
    cap_buf_a = lib.cells[buf].pins["A"].capacitance_ff
    if cap_nand_a is None or cap_buf_a is None:
        raise AssertionError("Missing real input-pin capacitance")

    # Choose PO load from the real BUF table interior, so the last stage is
    # guaranteed to exercise a valid characterized load range.
    buf_arc = sole_arc(lib.cells[buf], "A")
    po_axis = buf_arc.cell_rise.index_2
    if len(po_axis) < 2:
        raise AssertionError("BUF load axis requires >=2 points")
    po_load_ff = ((po_axis[0] + po_axis[1]) / 2.0) * lib.capacitance_unit_ff

    ref_loads = {
        "n1": float(cap_nand_a),
        "n2": float(cap_buf_a),
        "Y": float(po_load_ff),
    }

    derived = derive_net_loads(
        n, lib, primary_output_load_ff_by_net={"Y": po_load_ff}
    )
    for net, exp in ref_loads.items():
        got = derived[net].total_ff
        if abs(got - exp) > 1e-12:
            raise AssertionError(
                f"Automatic load mismatch net={net} expected={exp} got={got}"
            )

    s0 = ps_to_fs(20)
    c1, c2, c3 = n.cells

    q1 = p.delay(
        c1, 0, input_slew_fs=s0, load_ff=ref_loads["n1"],
        related_pin="A", pin_values={"A": 1}, input_transition=(0, 1)
    )
    q2 = p.delay(
        c2, 1, input_slew_fs=q1.output_slew_fs, load_ff=ref_loads["n2"],
        related_pin="A", pin_values={"A": 0, "B": 1},
        input_transition=(1, 0)
    )
    q3 = p.delay(
        c3, 1, input_slew_fs=q2.output_slew_fs, load_ff=ref_loads["Y"],
        related_pin="A", pin_values={"A": 1}, input_transition=(0, 1)
    )

    t0 = ps_to_fs(100)
    sim = TransportSimulator(
        n, p,
        default_input_slew_fs=s0,
        auto_load_from_liberty=True,
        primary_output_load_ff_by_net={"Y": po_load_ff},
    )
    tr, state = sim.run([StimulusEpoch(t0, {"A": 1}, 1)])

    by_net = {}
    for e in tr:
        if e.net in ("n1", "n2", "Y"):
            if e.net in by_net:
                raise AssertionError("Unexpected multiple path events on " + e.net)
            by_net[e.net] = e
    if set(by_net) != {"n1", "n2", "Y"}:
        raise AssertionError("Missing real path events: " + str(sorted(by_net)))

    expected_times = {
        "n1": t0 + q1.delay_fs,
        "n2": t0 + q1.delay_fs + q2.delay_fs,
        "Y": t0 + q1.delay_fs + q2.delay_fs + q3.delay_fs,
    }
    expected_slews = {
        "n1": q1.output_slew_fs,
        "n2": q2.output_slew_fs,
        "Y": q3.output_slew_fs,
    }

    for net in ("n1", "n2", "Y"):
        e = by_net[net]
        if e.time_fs != expected_times[net]:
            raise AssertionError(
                f"Path event-time mismatch net={net} "
                f"expected={expected_times[net]} got={e.time_fs}"
            )
        got_slew = sim.last_event_slew_fs[e.event_id]
        if got_slew != expected_slews[net]:
            raise AssertionError(
                f"Path slew mismatch net={net} "
                f"expected={expected_slews[net]} got={got_slew}"
            )
        if abs(sim.last_net_load_ff[net] - ref_loads[net]) > 1e-12:
            raise AssertionError(
                f"Simulator load mismatch net={net} "
                f"expected={ref_loads[net]} got={sim.last_net_load_ff[net]}"
            )

    if state["Y"] != 1:
        raise AssertionError("Unexpected final output state")

    # Show that stage-2 timing really depends on propagated slew rather than
    # silently reusing the primary-input slew at every stage.
    q2_fixed = p.delay(
        c2, 1, input_slew_fs=s0, load_ff=ref_loads["n2"],
        related_pin="A", pin_values={"A": 0, "B": 1},
        input_transition=(1, 0)
    )
    if q2_fixed.delay_fs == q2.delay_fs and s0 != q1.output_slew_fs:
        raise AssertionError(
            "Real path did not expose a slew-dependent stage-2 delay"
        )

    rows = [
        ["1", "U_INV", inv, "A", "0->1", s0, ref_loads["n1"],
         q1.delay_fs, q1.output_slew_fs, expected_times["n1"]],
        ["2", "U_NAND", nand, "A", "1->0", q1.output_slew_fs,
         ref_loads["n2"], q2.delay_fs, q2.output_slew_fs,
         expected_times["n2"]],
        ["3", "U_BUF", buf, "A", "0->1", q2.output_slew_fs,
         ref_loads["Y"], q3.delay_fs, q3.output_slew_fs,
         expected_times["Y"]],
    ]
    with (out / "real_sky130_b2_path.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "stage", "instance", "library_cell", "related_pin",
            "input_transition", "input_slew_fs", "load_ff",
            "delay_fs", "output_slew_fs", "event_time_fs"
        ])
        w.writerows(rows)

    with (out / "real_sky130_b2_loads.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "net", "sink_pin_cap_ff", "wire_cap_ff",
            "primary_output_load_ff", "total_ff"
        ])
        for net in ("n1", "n2", "Y"):
            q = derived[net]
            w.writerow([
                net, q.sink_pin_cap_ff, q.wire_cap_ff,
                q.primary_output_load_ff, q.total_ff
            ])

    summary = {
        "status": "PASS",
        "source_sha256": sha256_file(a.lib),
        "cells": {"inv": inv, "nand2": nand, "buf": buf},
        "primary_input_slew_fs": s0,
        "loads_ff": ref_loads,
        "stage_delay_fs": [q1.delay_fs, q2.delay_fs, q3.delay_fs],
        "stage_output_slew_fs": [
            q1.output_slew_fs, q2.output_slew_fs, q3.output_slew_fs
        ],
        "stage_event_time_fs": [
            expected_times["n1"], expected_times["n2"], expected_times["Y"]
        ],
        "final_state_Y": state["Y"],
        "automatic_fanout_load": True,
        "propagated_slew": True,
        "wire_capability_exercised_in_synthetic_regression": True,
        "simultaneous_multi_input_policy": "fail_closed",
    }
    (out / "real_sky130_b2_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )

    print("B2_REAL_LOAD_N1_FF=%.12g" % ref_loads["n1"])
    print("B2_REAL_LOAD_N2_FF=%.12g" % ref_loads["n2"])
    print("B2_REAL_LOAD_Y_FF=%.12g" % ref_loads["Y"])
    print("B2_REAL_STAGE_DELAYS_FS=%d,%d,%d" %
          (q1.delay_fs, q2.delay_fs, q3.delay_fs))
    print("B2_REAL_STAGE_SLEWS_FS=%d,%d,%d" %
          (q1.output_slew_fs, q2.output_slew_fs, q3.output_slew_fs))
    print("B2_REAL_FINAL_EVENT_FS=%d" % expected_times["Y"])
    print("B2_REAL_SKY130_LOAD_REFERENCE_PASS")
    print("B2_REAL_SKY130_SLEW_CHAIN_PASS")
    print("B2_REAL_SKY130_PATH_REFERENCE_PASS")

if __name__ == "__main__":
    main()
