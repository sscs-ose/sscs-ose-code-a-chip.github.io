"""TRUSTEDGE_T3_MARGIN: two half-cycle SRAM paths that pass with the TT macro view but not with the macro's SPICE delay at
ss (about 3.3 ns more than the view for a 12 x 256 macro).

  - Public-key export (trustedge_top.v): C3_PK_RD_REQ, _WAIT and _CAP present the export address in all three states,
    so the ekpke macro's data for the address is stable from the falling edge in WAIT; CAP digested it on a half-cycle
    path (+1.4 ns with the TT view). With the define on, a register takes the macro output at every rising edge and CAP
    uses it (the value taken at the end of WAIT). No cycle is added.
  - Key-generation self-check (mlkem512_matrix_mac_selftest.sv): core_ok compared the digest that includes the last
    pair, a function of the error RAM's output in that cycle (+1.6 ns). With the define on, the last pair's digest is
    compared one cycle later, in S_DK_ADDR, from the digest register (which holds it then); core_ok is cleared there on a
    mismatch. Only the KAT self-check (check_expected) uses the digest; no cycle is added.
SPDX-License-Identifier: Apache-2.0
"""


def _rep(s: str, a: str, b: str) -> str:
    assert s.count(a) == 1, (s.count(a), a[:80])
    return s.replace(a, b)


def edit_margin_top(s: str) -> str:
    old = """    wire [7:0] c3_pk_export_byte = (c3_absolute_byte < 10'd768) ?
        ((c3_pk_export_lane == 2'd0) ? mlkem512_runtime_ekpke_pair_data[7:0] :
         (c3_pk_export_lane == 2'd1) ? mlkem512_runtime_ekpke_pair_data[15:8] :
                                       mlkem512_runtime_ekpke_pair_data[23:16]) :
        mlkem512_runtime_rho_data;
"""
    return _rep(s, old, """`ifdef TRUSTEDGE_T3_MARGIN
    reg  [23:0] c3_ek_r;                     // the ekpke macro's output, one edge after it is presented
    always @(posedge clk) c3_ek_r <= mlkem512_runtime_ekpke_pair_data;
    wire [7:0] c3_pk_export_byte = (c3_absolute_byte < 10'd768) ?
        ((c3_pk_export_lane == 2'd0) ? c3_ek_r[7:0] :
         (c3_pk_export_lane == 2'd1) ? c3_ek_r[15:8] : c3_ek_r[23:16]) :
        mlkem512_runtime_rho_data;
`else
""" + old + "`endif\n")


def edit_margin_matrix(s: str) -> str:
    s = _rep(s, "            core_ok <= 1'b0;\n            serial_pair_index <= 8'd0;\n",
             "            core_ok <= 1'b0;\n`ifdef TRUSTEDGE_T3_MARGIN\n            t3_dig_chk <= 1'b0;\n`endif\n"
             "            serial_pair_index <= 8'd0;\n")
    s = _rep(s, "(digest_after_pair == EXPECTED_DIGEST)));\n",
             "`ifdef TRUSTEDGE_T3_MARGIN\n"
             "                                             1'b1));     // the digest is checked in S_DK_ADDR\n"
             "                                t3_dig_chk <= check_expected;\n"
             "`else\n"
             "                                             (digest_after_pair == EXPECTED_DIGEST)));\n"
             "`endif\n")
    s = _rep(s, "                S_DK_ADDR: state <= S_DK_WAIT;\n",
             "`ifdef TRUSTEDGE_T3_MARGIN\n"
             "                S_DK_ADDR: begin\n"
             "                    state <= S_DK_WAIT;\n"
             "                    if (t3_dig_chk && (digest != EXPECTED_DIGEST)) core_ok <= 1'b0;\n"
             "                    t3_dig_chk <= 1'b0;\n"
             "                end\n"
             "`else\n"
             "                S_DK_ADDR: state <= S_DK_WAIT;\n"
             "`endif\n")
    # the flag is declared at module level, next to the pair wires
    return _rep(s, "    wire [23:0] secret_pair_bytes;\n",
                "    wire [23:0] secret_pair_bytes;\n"
                "`ifdef TRUSTEDGE_T3_MARGIN\n    reg t3_dig_chk;                          // compare the last pair's digest in S_DK_ADDR\n`endif\n")
