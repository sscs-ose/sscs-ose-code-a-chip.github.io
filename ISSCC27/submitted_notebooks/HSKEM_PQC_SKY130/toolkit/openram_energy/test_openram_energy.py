"""Unit tests of openram_energy.py on synthetic macro netlists and logs.  SPDX-License-Identifier: Apache-2.0"""
import json
import os
import re

import openram_energy as oe

ONE_PORT = """.SUBCKT m1 din0[0] din0[1] din0[2] addr0[0] addr0[1] addr0[2]
+ csb0 web0 clk0 spare_wen0 dout0[0] dout0[1] dout0[2] vccd1 vssd1
.ENDS m1
"""
TWO_PORT = """.SUBCKT m2 din0[0] din0[1] din0[2] din0[3] addr0[0] addr0[1] addr0[2] addr1[0] addr1[1] addr1[2]
+ csb0 csb1 web0 clk0 clk1 wmask0[0] dout0[0] dout0[1] dout0[2] dout0[3] dout1[0] dout1[1] dout1[2] dout1[3] vccd1 vssd1
.ENDS m2
"""


def build(tmp_path, text, name):
    net = tmp_path / f"{name}.sp"; net.write_text(text)
    out = tmp_path / "e.sp"
    oe.deck(str(net), name, str(out), "/pdk/sky130.lib.spice")
    return out.read_text(), json.load(open(str(out) + ".json"))


def test_one_port_with_spare_column(tmp_path):
    deck, meta = build(tmp_path, ONE_PORT, "m1")
    assert meta["data_bits"] == 2                      # the spare column is not checked
    assert "X0 din0_0_ din0_1_ din0_2_" in deck and deck.split("X0 ")[1].split("\n")[0].endswith("vdd 0 m1")
    assert "Vspare_wen0 spare_wen0 0 0" in deck
    reads = re.findall(r"^\.meas tran r\d+b\d+", deck, re.M)
    assert len(reads) == oe.N_W * 2
    assert len(re.findall(r"^\.meas tran q\d+ INTEG", deck, re.M)) == 1 + 2 * oe.N_W + 1


def test_two_port_macro_second_port_idle(tmp_path):
    deck, meta = build(tmp_path, TWO_PORT, "m2")
    assert meta["data_bits"] == 4
    for line in ("Vcsb1 csb1 0 1.8", "Vclk1 clk1 0 0", "Vaddr1_0_ addr1_0_ 0 0", "Vwmask0_0_ wmask0_0_ 0 1.8",
                 "Cdout1_3_ dout1_3_ 0 10f"):
        assert line in deck
    assert len(re.findall(r"^\.meas tran r\d+b\d+", deck, re.M)) == oe.N_W * 4


def test_parse_energies_and_read_check(tmp_path):
    _, meta = build(tmp_path, ONE_PORT, "m1")
    w0, nw = meta["settle"] + 1, meta["writes"]
    lines = [f"q{k} = {-(k + 1) * 1e-12 / oe.VDD:.6e}" for k in range(meta["settle"], w0 + 2 * nw + 1)]
    for i, word in enumerate(meta["data"]):
        lines += [f"r{i}b{b} = {oe.VDD if (word >> b) & 1 else 0.0}" for b in range(meta["data_bits"])]
    log = tmp_path / "e.log"; log.write_text("\n".join(lines) + "\nTotal elapsed time (seconds) = 12.5\n")
    res_path = tmp_path / "r.json"
    oe.parse(str(log), "m1", str(res_path))
    r = json.load(open(res_path))
    assert r["reads_correct"] == [True] * nw and r["elapsed_s"] == 12.5
    assert r["idle_pj"][0] == round(meta["settle"] + 1, 3) and r["write_pj"][0] == round(w0 + 1, 3)


def test_parse_reports_an_unfinished_transient(tmp_path):
    build(tmp_path, ONE_PORT, "m1")
    log = tmp_path / "e.log"; log.write_text("Warning: m=xx on .subckt line will override multiplier\n")
    try:
        oe.parse(str(log), "m1", str(tmp_path / "r.json"))
    except SystemExit as e:
        assert "did not finish" in str(e)
    else:
        raise AssertionError("an empty log must not pass")


def test_delay_mode_measures_the_crossing_after_the_falling_edge(tmp_path, monkeypatch):
    monkeypatch.setattr(oe, "DELAY", True)
    monkeypatch.setattr(oe, "CORNER", "ss")
    monkeypatch.setattr(oe, "VDD", 1.6)
    monkeypatch.setattr(oe, "TEMP", 100.0)
    deck, meta = build(tmp_path, ONE_PORT, "m1")
    assert '.lib "/pdk/sky130.lib.spice" ss' in deck and ".temp 100" in deck and "Vvdd vdd 0 PWL(0 0 2n 1.6)" in deck
    assert len(re.findall(r"^\.meas tran t\d+b\d+ WHEN", deck, re.M)) == oe.N_W * 2
    assert meta["delay"] and meta["corner"] == "ss" and meta["vdd"] == 1.6
    w0, nw = meta["settle"] + 1, meta["writes"]
    lines = [f"q{k} = {-(k + 1) * 1e-12 / oe.VDD:.6e}" for k in range(meta["settle"], w0 + 2 * nw + 1)]
    for i, word in enumerate(meta["data"]):
        lines += [f"r{i}b{b} = {oe.VDD if (word >> b) & 1 else 0.0}" for b in range(meta["data_bits"])]
        tf = (w0 + nw + i + 1) * oe.T + 0.05
        lines += [f"t{i}b0 = {(tf + 3.2) * 1e-9:.6e}", f"t{i}b1 = {(tf + oe.T) * 1e-9:.6e}"]   # the second belongs to another cycle
    (tmp_path / "e.log").write_text("\n".join(lines) + "\n")
    oe.parse(str(tmp_path / "e.log"), "m1", str(tmp_path / "r.json"))
    r = json.load(open(tmp_path / "r.json"))
    assert r["clk_to_dout_ns"] == {"n": nw, "max": 3.2, "median": 3.2} and r["corner"] == "ss" and r["temp_c"] == 100.0


def _special_pdk(tmp_path, lib_mentions):
    tech = tmp_path / "sky130A" / "libs.tech" / "ngspice"; tech.mkdir(parents=True)
    ref = tmp_path / "sky130A" / "libs.ref" / "sky130_fd_pr" / "spice"; ref.mkdir(parents=True)
    (ref / "sky130_fd_pr__special_nfet_latch.pm3.spice").write_text("* model\n")
    (tech / "sky130.lib.spice").write_text(".lib tt\n.include all.spice\n.endl tt\n")
    (tech / "all.spice").write_text('.include "../../libs.ref/sky130_fd_pr/spice/sky130_fd_pr__special_nfet_latch.pm3.spice"\n'
                                    if lib_mentions else "* nothing special\n")
    net = tmp_path / "m1.sp"
    net.write_text(ONE_PORT.replace(".ENDS m1", "X0 a b c d sky130_fd_pr__special_nfet_latch W=0.21 L=0.15 m=1\n.ENDS m1"))
    out = tmp_path / "e.sp"
    oe.deck(str(net), "m1", str(out), str(tech / "sky130.lib.spice"))
    return out.read_text()


def test_special_models_are_included_only_when_the_tech_library_lacks_them(tmp_path):
    assert "special_nfet_latch.pm3.spice" not in _special_pdk(tmp_path / "a", True)   # a second include breaks ngspice
    assert "special_nfet_latch.pm3.spice" in _special_pdk(tmp_path / "b", False)
