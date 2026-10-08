"""Unit tests for the analysis scripts whose results the notebook quotes.

Each test feeds a script a small, hand-checked input and compares the output with the value worked out
by hand, so that a change in a script cannot silently change a published number.
usage (from the submission folder): python3 -m pytest -q tests
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- vcd_window.py
VCD_WITH_WINDOW = """$timescale 1ps $end
$scope module tb $end
$var wire 1 ! clk $end
$upscope $end
$enddefinitions $end
#0
$dumpvars
0!
$end
$dumpoff
x!
$end
#100
1!
#200
$dumpon
0!
$end
#300
1!
#400
0!
#500
$dumpoff
x!
$end
#600
1!
"""


def test_vcd_window_keeps_only_the_dump_window(tmp_path):
    vw = load("vcd_window")
    src, dst = tmp_path / "in.vcd", tmp_path / "out.vcd"
    src.write_text(VCD_WITH_WINDOW)
    vw.main(str(src), str(dst))
    body = dst.read_text().split("$enddefinitions $end\n", 1)[1].split()
    body = [x for i, x in enumerate(body) if i == 0 or x != body[i - 1]]   # a repeated time stamp is harmless
    # starts at the $dumpon time with its listed values, keeps the changes inside, stops at $dumpoff
    assert body ==["#200", "0!", "#300", "1!", "#400", "0!", "#500"]


# ---------------------------------------------------------------- vcd_macro_accesses.py
def macro_vcd(cycles):
    """cycles: list of (csb, web, addr) registered at each rising clock edge."""
    lines = ["$timescale 1ps $end", "$scope module tb $end", "$scope module u_macro $end",
             "$var wire 1 c clk0 $end", "$var reg 1 s csb0_reg $end", "$var reg 1 w web0_reg $end",
             "$var reg 8 a addr0_reg [7:0] $end", "$upscope $end", "$upscope $end", "$enddefinitions $end",
             "#0", "0c"]
    t = 0
    for csb, web, addr in cycles:
        t += 10
        lines += [f"#{t}", "1c", f"{csb}s", f"{web}w", f"b{addr:b} a"]
        t += 10
        lines += [f"#{t}", "0c"]
    return "\n".join(lines) + "\n"


def test_macro_access_classes(tmp_path):
    ma = load("vcd_macro_accesses")
    cycles = [(0, 0, 5),   # write 5
              (0, 1, 5),   # read of the address just written: same address
              (0, 1, 6),   # read of a new address
              (0, 1, 6),   # same again
              (1, 1, 6),   # deselected
              (0, 1, 7)]   # new address
    f = tmp_path / "w.vcd"
    f.write_text(macro_vcd(cycles))
    out = tmp_path / "acc.json"
    ma.main(str(f), "u_macro", str(out))
    assert json.loads(out.read_text()) == {"cycles": 6, "writes": 1, "reads_new_address": 2,
                                           "reads_same_address": 2, "idle": 1}


# ---------------------------------------------------------------- sram_energy_model.py
def spice_results():
    def run(read, write, idle):
        return {"read_pj": [read] * 3, "read_repeat_pj": [read - 1] * 3, "write_pj": [write] * 3,
                "idle_pj": [idle, idle + 5], "reads_correct": [True] * 3, "read_repeat_correct": [True] * 3}
    return {"method": "test", "clock_ns": 40.0, "supply_v": 1.8,
            "macros": {"sky130_sram_1rw_12x256_wpr8": run(60, 62, 3), "sky130_sram_1rw_12x512_wpr8": run(64, 66, 4)},
            "flat_layout": {"macros": {"sky130_sram_1rw_12x256_wpr8": {
                "read_pj": [45.0], "write_pj": [46.5], "idle_pj": [4.5, 9], "reads_correct": [True]}}}}


def accesses():
    return {"window_cycles": 100, "instances": {
        "a": {"master": "sky130_sram_1rw_12x256_wpr8", "writes": 10, "reads": 90, "useful_accesses": 30},
        "b": {"master": "sky130_sram_1rw_12x384_wpr8", "writes": 0, "reads": 100, "useful_accesses": 0}}}


def test_sram_energy_model_by_hand(tmp_path):
    em = load("sram_energy_model")
    sp, ac, out = tmp_path / "s.json", tmp_path / "a.json", tmp_path / "o.json"
    sp.write_text(json.dumps(spice_results())); ac.write_text(json.dumps(accesses()))
    em.main(str(sp), str(ac), str(out))
    r = json.loads(out.read_text())
    f_acc = (45 + 46.5) / 2 / ((60 + 62) / 2)           # flat over schematic, 12x256 only
    f_idle = 4.5 / 3
    # instance a: 20 new-address reads, 70 repeated reads, 10 writes, all scaled by its own factor
    e_a = (20 * 60 + 70 * 59 + 10 * 62) * f_acc
    # instance b: 12x384 is interpolated halfway between 12x256 and 12x512, scaled by the mean (= only) factor
    e_b = 100 * 61 * f_acc                              # every read repeats the same address
    assert r["sram_energy_per_decaps_uj"] == pytest.approx((e_a + e_b) * 1e-6)
    g_a = (20 * 60 + 10 * 62) * f_acc + 70 * 3 * f_idle
    g_b = 100 * 3.5 * f_idle
    assert r["sram_energy_with_chip_select_gating_uj"] == pytest.approx((g_a + g_b) * 1e-6)


# ---------------------------------------------------------------- sram_energy_deck.py
NETLIST = """* toy
.subckt sky130_sram_1rw_8x16 din0[0] din0[1] din0[2] addr0[0] addr0[1] addr0[2] addr0[3] csb0 web0 clk0
+ dout0[0] dout0[1] dout0[2] vccd1 vssd1
.ends
"""


def test_deck_and_parse_round_trip(tmp_path):
    dk = load("sram_energy_deck")
    net, deck = tmp_path / "toy.sp", tmp_path / "energy.sp"
    net.write_text(NETLIST)
    dk.deck(str(net), "sky130_sram_1rw_8x16", str(deck), "/pdk/sky130.lib.spice")
    text = deck.read_text()
    assert "X0 din0_0_ din0_1_ din0_2_" in text and " vdd 0 sky130_sram_1rw_8x16" in text
    meta = json.loads((tmp_path / "energy.sp.json").read_text())
    n = meta["settle"] + 1 + 2 * meta["writes"] + 1
    # a log in which every cycle drew 10 pC from the supply and every read returned the written word
    log = [f"q{k} = -1.0e-11" for k in range(meta["settle"], n)]
    for i, word in enumerate(meta["data"]):
        log += [f"r{i}b{b} = {1.8 if (word >> b) & 1 else 0.0}" for b in range(meta["data_bits"])]
    (tmp_path / "energy.log").write_text("\n".join(log) + "\nTotal elapsed time (seconds) = 1.0\n")
    dk.parse(str(tmp_path / "energy.log"), "toy", str(tmp_path / "e.json"))
    r = json.loads((tmp_path / "e.json").read_text())
    assert r["read_pj"] == [18.0] * meta["writes"] and all(r["reads_correct"])
