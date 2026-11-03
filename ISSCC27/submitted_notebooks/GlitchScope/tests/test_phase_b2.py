from __future__ import annotations
from pathlib import Path
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.load import derive_net_loads
from glitchscope.model import Cell, Network, StimulusEpoch, ps_to_fs
from glitchscope.timed import TransportSimulator

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "tests" / "fixtures" / "synthetic_b2.lib"

def _path_network():
    return Network(
        ["A", "B"], ["Y"],
        [
            Cell("U1", "INV", {"A": "A"}, "n1", 0, 0,
                 library_cell="INVX1", library_output_pin="Y"),
            Cell("U2", "NAND2", {"A": "n1", "B": "B"}, "n2", 0, 0,
                 library_cell="NAND2X1", library_output_pin="Y"),
            Cell("U3", "BUF", {"A": "n2"}, "Y", 0, 0,
                 library_cell="BUFX1", library_output_pin="X"),
        ],
        {"A": 0, "B": 1},
    )

def test_b2_fanout_wire_po_load_derivation():
    lib = parse_liberty_file(LIB)
    n = _path_network()
    q = derive_net_loads(
        n, lib,
        wire_cap_ff_by_net={"n1": 0.5, "n2": 0.25},
        primary_output_load_ff_by_net={"Y": 3.0},
    )
    assert abs(q["n1"].sink_pin_cap_ff - 2.0) < 1e-12
    assert abs(q["n1"].wire_cap_ff - 0.5) < 1e-12
    assert abs(q["n1"].total_ff - 2.5) < 1e-12
    assert abs(q["n2"].sink_pin_cap_ff - 1.0) < 1e-12
    assert abs(q["n2"].wire_cap_ff - 0.25) < 1e-12
    assert abs(q["n2"].total_ff - 1.25) < 1e-12
    assert abs(q["Y"].primary_output_load_ff - 3.0) < 1e-12
    assert abs(q["Y"].total_ff - 3.0) < 1e-12

def test_b2_multiple_fanout_caps_sum():
    lib = parse_liberty_file(LIB)
    n = Network(
        ["A", "B"], ["Y1", "Y2"],
        [
            Cell("U0", "INV", {"A": "A"}, "n", 0, 0,
                 library_cell="INVX1", library_output_pin="Y"),
            Cell("U1", "NAND2", {"A": "n", "B": "B"}, "Y1", 0, 0,
                 library_cell="NAND2X1", library_output_pin="Y"),
            Cell("U2", "BUF", {"A": "n"}, "Y2", 0, 0,
                 library_cell="BUFX1", library_output_pin="X"),
        ],
        {"A": 0, "B": 1},
    )
    q = derive_net_loads(n, lib)
    assert abs(q["n"].total_ff - 3.0) < 1e-12  # NAND A 2 fF + BUF A 1 fF

def test_b2_propagated_slew_matches_stepwise_reference():
    lib = parse_liberty_file(LIB)
    p = LibertyDelayProvider(lib)
    n = _path_network()
    loads = derive_net_loads(
        n, lib,
        wire_cap_ff_by_net={"n1": 0.5, "n2": 0.25},
        primary_output_load_ff_by_net={"Y": 3.0},
    )

    s0 = ps_to_fs(20)
    c1, c2, c3 = n.cells

    q1 = p.delay(
        c1, 0, input_slew_fs=s0, load_ff=loads["n1"].total_ff,
        related_pin="A", pin_values={"A": 1}, input_transition=(0, 1)
    )
    q2 = p.delay(
        c2, 1, input_slew_fs=q1.output_slew_fs,
        load_ff=loads["n2"].total_ff,
        related_pin="A", pin_values={"A": 0, "B": 1},
        input_transition=(1, 0)
    )
    q3 = p.delay(
        c3, 1, input_slew_fs=q2.output_slew_fs,
        load_ff=loads["Y"].total_ff,
        related_pin="A", pin_values={"A": 1}, input_transition=(0, 1)
    )

    sim = TransportSimulator(
        n, p, default_input_slew_fs=s0,
        auto_load_from_liberty=True,
        wire_cap_ff_by_net={"n1": 0.5, "n2": 0.25},
        primary_output_load_ff_by_net={"Y": 3.0},
    )
    t0 = ps_to_fs(100)
    tr, state = sim.run([StimulusEpoch(t0, {"A": 1}, 1)])

    ev = {e.net: e for e in tr if e.net in ("n1", "n2", "Y")}
    assert set(ev) == {"n1", "n2", "Y"}
    assert ev["n1"].time_fs == t0 + q1.delay_fs
    assert ev["n2"].time_fs == t0 + q1.delay_fs + q2.delay_fs
    assert ev["Y"].time_fs == t0 + q1.delay_fs + q2.delay_fs + q3.delay_fs

    assert sim.last_event_slew_fs[ev["n1"].event_id] == q1.output_slew_fs
    assert sim.last_event_slew_fs[ev["n2"].event_id] == q2.output_slew_fs
    assert sim.last_event_slew_fs[ev["Y"].event_id] == q3.output_slew_fs
    assert state["Y"] == 1

    # Prove the new path timing is genuinely using propagated slew.
    q2_fixed = p.delay(
        c2, 1, input_slew_fs=s0, load_ff=loads["n2"].total_ff,
        related_pin="A", pin_values={"A": 0, "B": 1},
        input_transition=(1, 0)
    )
    assert q2.delay_fs != q2_fixed.delay_fs

def test_b2_primary_input_slew_override():
    lib = parse_liberty_file(LIB)
    p = LibertyDelayProvider(lib)
    n = Network(
        ["A"], ["Y"],
        [Cell("U", "INV", {"A": "A"}, "Y", 0, 0,
              library_cell="INVX1", library_output_pin="Y")],
        {"A": 0},
    )
    sim = TransportSimulator(
        n, p, default_input_slew_fs=ps_to_fs(20),
        input_slew_fs_by_net={"A": ps_to_fs(10)},
        load_ff_by_net={"Y": 2.0},
    )
    t0 = ps_to_fs(100)
    tr, _ = sim.run([StimulusEpoch(t0, {"A": 1}, 1)])
    y = [e for e in tr if e.net == "Y"][0]
    q = p.delay(
        n.cells[0], 0, input_slew_fs=ps_to_fs(10), load_ff=2.0,
        related_pin="A", pin_values={"A": 1}, input_transition=(0, 1)
    )
    assert y.time_fs == t0 + q.delay_fs

def test_b2_simultaneous_multi_input_timing_fails_closed():
    lib = parse_liberty_file(LIB)
    p = LibertyDelayProvider(lib)
    n = Network(
        ["A", "B"], ["Y"],
        [Cell("U", "NAND2", {"A": "A", "B": "B"}, "Y", 0, 0,
              library_cell="NAND2X1", library_output_pin="Y")],
        {"A": 0, "B": 0},
    )
    sim = TransportSimulator(
        n, p, default_input_slew_fs=ps_to_fs(20),
        load_ff_by_net={"Y": 2.0},
    )
    try:
        sim.run([StimulusEpoch(ps_to_fs(100), {"A": 1, "B": 1}, 1)])
    except ValueError as e:
        assert "ambiguous simultaneous multi-input" in str(e)
    else:
        raise AssertionError("Expected simultaneous multi-input timing ambiguity to fail closed")
