"""Post-layout netlist features: physical-only cells, CTS buffers, tie cells, SPEF caps."""
import tempfile
from pathlib import Path

NETLIST = """
module top(clk, a, b, y);
  input clk; input a; input b; output y;
  wire clk_0, clk_1, q0, q1, d1, hi, n1;
  sky130_fd_sc_hd__clkbuf_4 cts_0 (.A(clk), .X(clk_0));
  sky130_fd_sc_hd__clkbuf_1 cts_1 (.A(clk_0), .X(clk_1));
  sky130_fd_sc_hd__dfxtp_1 f0 (.CLK(clk_1), .D(a), .Q(q0));
  sky130_fd_sc_hd__dfxtp_1 f1 (.CLK(clk_0), .D(d1), .Q(q1));
  sky130_fd_sc_hd__conb_1 tie (.HI(hi), .LO());
  sky130_fd_sc_hd__and3_1 g0 (.A(q0), .B(b), .C(hi), .X(n1));
  sky130_fd_sc_hd__xor2_1 g1 (.A(n1), .B(q1), .X(d1));
  sky130_fd_sc_hd__buf_1 g2 (.A(q1), .X(y));
  sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_1 ();
  sky130_fd_sc_hd__decap_4 FILLER_1 ();
  sky130_fd_sc_hd__diode_2 ANT_1 (.DIODE(b));
endmodule
"""

SPEF = """*SPEF "IEEE 1481-1998"
*DESIGN "top"
*T_UNIT 1 NS
*C_UNIT 1 PF
*R_UNIT 1 OHM
*L_UNIT 1 HENRY
*NAME_MAP
*1 n1
*2 d1
*PORTS
*D_NET *1 0.0021
*CONN
*END
*D_NET *2 0.0005
*END
*D_NET y 0.004
*END
"""


def test_postlayout_netlist_and_spef():
    from glitchscope.test_support import lib_path_or_none
    from glitchscope.spef import read_spef_caps
    with tempfile.TemporaryDirectory() as d:
        sp = Path(d) / "t.spef"; sp.write_text(SPEF)
        caps = read_spef_caps(sp)
        assert abs(caps["n1"] - 2.1) < 1e-9 and abs(caps["d1"] - 0.5) < 1e-9 and abs(caps["y"] - 4.0) < 1e-9
        lib = lib_path_or_none()
        if not lib:
            return
        from glitchscope.liberty import parse_liberty_file
        from glitchscope.verilog import read_design
        from glitchscope.functional import evaluate_stable
        v = Path(d) / "t.v"; v.write_text(NETLIST)
        des = read_design(v, parse_liberty_file(lib))
        names = sorted(c.name for c in des.network.cells)
        assert names == ["g0", "g1", "g2"], names          # CTS, tie, physical cells removed
        assert len(des.flops) == 2 and des.clocks == ["clk"] and des.real_inputs == ["a", "b"]
        assert des.network.initial_inputs["hi"] == 1        # tie-high constant
        st = evaluate_stable(des.network, {**des.network.initial_inputs, "a": 0, "b": 1, "q0": 1, "q1": 0})
        assert st["n1"] == 1 and st["d1"] == 1
