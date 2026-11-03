"""Library independence: a small non-SKY130 Liberty library with GF180/ASAP7-style syntax."""
import tempfile
from pathlib import Path

TABLE = '''values ("0.01, 0.02", "0.02, 0.03");'''
LIB = '''library (mini_lib) {
  time_unit : 1ns ;
  voltage_unit : 1V ;
  capacitive_load_unit(1, pf);
  nom_voltage : 1.2 ;
  lu_table_template (t2) { variable_1 : input_net_transition; variable_2 : total_output_net_capacitance;
    index_1 ("0.01, 0.1"); index_2 ("0.001, 0.01"); }
  cell (MY_NOR2) {
    pin (A1) { direction : input ; capacitance : 0.002 ; }
    pin (A2) { direction : input ; capacitance : 0.002 ; }
    pin (ZN) { direction : output ; function : "(A1+A2)'" ;
      timing () { related_pin : "A1" ; timing_sense : negative_unate ;
        cell_rise (t2) { %T } cell_fall (t2) { %T } rise_transition (t2) { %T } fall_transition (t2) { %T } }
      timing () { related_pin : "A2" ; timing_sense : negative_unate ;
        cell_rise (t2) { %T } cell_fall (t2) { %T } rise_transition (t2) { %T } fall_transition (t2) { %T } }
      internal_power () { related_pin : "A1" ; rise_power (t2) { %T } fall_power (t2) { %T } }
      internal_power () { related_pin : "A2" ; rise_power (t2) { %T } fall_power (t2) { %T } } } }
  cell (MY_AND2) {
    pin (A) { direction : input ; capacitance : 0.002 ; }
    pin (B) { direction : input ; capacitance : 0.002 ; }
    pin (Z) { direction : output ; function : "A B" ;
      timing () { related_pin : "A" ; timing_sense : positive_unate ;
        cell_rise (t2) { %T } cell_fall (t2) { %T } rise_transition (t2) { %T } fall_transition (t2) { %T } }
      timing () { related_pin : "B" ; timing_sense : positive_unate ;
        cell_rise (t2) { %T } cell_fall (t2) { %T } rise_transition (t2) { %T } fall_transition (t2) { %T } } } }
  cell (MY_DFFN) {
    ff (IQ, IQN) { clocked_on : "CK" ; next_state : "D" ; }
    pin (D) { direction : input ; capacitance : 0.002 ; }
    pin (CK) { direction : input ; capacitance : 0.002 ; clock : true ; }
    pin (QN) { direction : output ; function : "IQN" ;
      timing () { related_pin : "CK" ; timing_type : rising_edge ;
        cell_rise (t2) { %T } cell_fall (t2) { %T } rise_transition (t2) { %T } fall_transition (t2) { %T } } } }
  cell (MY_DFFR) {
    ff (IQ, IQN) { clocked_on : "CK" ; next_state : "D" ; clear : "!RN" ; }
    pin (D) { direction : input ; capacitance : 0.002 ; }
    pin (RN) { direction : input ; capacitance : 0.002 ; }
    pin (CK) { direction : input ; capacitance : 0.002 ; clock : true ; }
    pin (Q) { direction : output ; function : "IQ" ;
      timing () { related_pin : "CK" ; timing_type : rising_edge ;
        cell_rise (t2) { %T } cell_fall (t2) { %T } rise_transition (t2) { %T } fall_transition (t2) { %T } } } }
  cell (MY_TIEH) { pin (Z) { direction : output ; function : "1" ; } }
  cell (MY_FILL) { area : 1 ; }
}
'''.replace("%T", TABLE)

NET = '''
module top(clk, a, b, rn, y);
  input clk, a, b, rn; output y;
  wire qn, q, n1, hi, d1;
  MY_DFFN f0 (.D(a), .CK(clk), .QN(qn));
  MY_DFFR f1 (.D(d1), .RN(rn), .CK(clk), .Q(q));
  MY_TIEH t0 (.Z(hi));
  MY_NOR2 g0 (.A1(qn), .A2(b), .ZN(n1));
  MY_AND2 g1 (.A(n1), .B(hi), .Z(d1));
  MY_AND2 g2 (.A(q), .B(hi), .Z(y));
  MY_FILL fill_1 ();
endmodule
'''


def test_non_sky130_library_end_to_end():
    from glitchscope.liberty import parse_liberty_file
    from glitchscope.liberty_power import liberty_units
    from glitchscope.verilog import read_design
    from glitchscope.pdk import pick_cells
    from glitchscope.seq import read_clk_to_q, build_cycles, random_waves
    with tempfile.TemporaryDirectory() as d:
        lp = Path(d) / "mini.lib"; lp.write_text(LIB)
        vp = Path(d) / "top.v"; vp.write_text(NET)
        lib = parse_liberty_file(lp)
        u = liberty_units(lp)
        assert lib.name == "mini_lib" and abs(lib.nom_voltage - 1.2) < 1e-12 and u["vdd"] == 1.2
        assert u["time_ps"] == 1000.0 and u["cap_ff"] == 1000.0
        pc = pick_cells(lib, wanted=("nor2", "and2", "dff"))
        assert pc["nor2"].name == "MY_NOR2" and pc["and2"].name == "MY_AND2" and pc["dff"].name == "MY_DFFN"
        des = read_design(vp, lib)
        assert sorted(c.name for c in des.network.cells) == ["g0", "g1", "g2"]
        f0 = next(f for f in des.flops if f.name == "f0")
        f1 = next(f for f in des.flops if f.name == "f1")
        assert f0.q is None and f0.qn == "qn" and f0.clk_pin == "CK"
        assert f1.clear == "!RN" and f1.ctrl == {"RN": "rn"}
        assert des.network.initial_inputs["qn"] == 1 and des.network.initial_inputs["hi"] == 1
        # clock-edge behaviour: QN-only flop and async clear (rn = 0 forces q = 0)
        c2q = read_clk_to_q(lp, {f.libcell for f in des.flops})
        assert set(c2q["MY_DFFN"]) == {"QN"} and set(c2q["MY_DFFR"]) == {"Q"}
        waves = {"clk": [(0, 0), (1_000_000, 1), (1_500_000, 0), (2_000_000, 1), (2_500_000, 0), (3_000_000, 1)],
                 "a": [(0, 1)], "b": [(0, 0)], "rn": [(0, 1), (2_100_000, 0)]}
        init, cycles, _ = build_cycles(des, waves, lib, c2q, {}, clock="clk", input_delay_ps=100)
        st = dict(init)
        seen = []
        for cyc in cycles:
            for _, u_ in cyc:
                st.update(u_)
            seen.append((st["qn"], st["q"]))
        assert seen[0][0] == 0                  # a = 1 captured -> QN = 0
        assert seen[-1][1] == 0                 # clear active at the last edge -> Q = 0
