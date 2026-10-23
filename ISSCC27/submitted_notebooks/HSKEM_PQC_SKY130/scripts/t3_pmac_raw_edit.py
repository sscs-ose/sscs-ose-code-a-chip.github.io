"""TRUSTEDGE_T3_PMAC_RAW: slow-corner timing of stage A of the pipelined products (encryption and decapsulation).

Stage A multiplies two SRAM outputs (key or secret pairs times noise or NTT pairs). A macro presents its read data half a
cycle after the clock edge, so the four 12 x 12 multipliers sat on half-cycle paths (up to -5.0 ns at ss, before the
macro's SPICE delay). With the define on, the RAM outputs are registered first (stage Z) and stage A multiplies registers.
Encryption: one stage (its finished pairs go to the NTT while the operands come from other RAMs). Decapsulation: two
stages, because its second polynomial reads and writes the NTT store through one port on alternate cycles, and an odd
number of added stages would move the writes onto the read cycles. The valid, column and pair tags move with the data and
the loops end on the last pair leaving stage R, so the results are unchanged and each product takes one (two) more cycles.
SPDX-License-Identifier: Apache-2.0
"""


def _rep(s: str, a: str, b: str, n: int = 1) -> str:
    assert s.count(a) == n, (s.count(a), a[:80])
    return s.replace(a, b)


def edit_pmac_raw_encrypt(s: str) -> str:
    s = _rep(s, "    wire        pmac_wr = (state == S_MUL2) && mr_v;               // a finished pair goes to the NTT\n",
             "    wire        pmac_wr = (state == S_MUL2) && mr_v;               // a finished pair goes to the NTT\n"
             "`ifdef TRUSTEDGE_T3_PMAC_RAW\n"
             "    // stage Z registers the RAM outputs (key pair and noise pair) of the step addressed two cycles before\n"
             "    reg         mz_v, mz_c;  reg [6:0] mz_p;  reg [11:0] mz_a0, mz_a1, mz_ne, mz_no;\n"
             "`endif\n")
    s = _rep(s, """    wire [23:0] rt_p00 = key_operand_a0 * noise_even_q;
    wire [23:0] rt_p11 = key_operand_a1 * noise_odd_q;
    wire [23:0] rt_p01 = key_operand_a0 * noise_odd_q;
    wire [23:0] rt_p10 = key_operand_a1 * noise_even_q;
""", """`ifdef TRUSTEDGE_T3_PMAC_RAW
    wire [23:0] rt_p00 = mz_a0 * mz_ne;
    wire [23:0] rt_p11 = mz_a1 * mz_no;
    wire [23:0] rt_p01 = mz_a0 * mz_no;
    wire [23:0] rt_p10 = mz_a1 * mz_ne;
`else
    wire [23:0] rt_p00 = key_operand_a0 * noise_even_q;
    wire [23:0] rt_p11 = key_operand_a1 * noise_odd_q;
    wire [23:0] rt_p01 = key_operand_a0 * noise_odd_q;
    wire [23:0] rt_p10 = key_operand_a1 * noise_even_q;
`endif
""")
    # gamma belongs to the pair entering stage A
    g = "    wire [6:0]  pm_gidx = 7'd64 + {1'b0, mi_p[6:1]};\n"
    k = s.count(g)
    assert k >= 1, k
    s = s.replace(g, "`ifdef TRUSTEDGE_T3_PMAC_RAW\n    wire [6:0]  pm_gidx = 7'd64 + {1'b0, mz_p[6:1]};\n`else\n" + g + "`endif\n")
    g2 = "    wire [11:0] pm_gamma = mi_p[0] ? (12'd3329 - pm_gfull[11:0]) : pm_gfull[11:0];\n"
    assert s.count(g2) == k, (s.count(g2), k)
    s = s.replace(g2, "`ifdef TRUSTEDGE_T3_PMAC_RAW\n    wire [11:0] pm_gamma = mz_p[0] ? (12'd3329 - pm_gfull[11:0]) : pm_gfull[11:0];\n"
                      "`else\n" + g2 + "`endif\n")
    s = _rep(s, "            mi_v <= 1'b0; ma_v <= 1'b0; mb_v <= 1'b0; mr_v <= 1'b0;\n",
             "            mi_v <= 1'b0; ma_v <= 1'b0; mb_v <= 1'b0; mr_v <= 1'b0;\n"
             "`ifdef TRUSTEDGE_T3_PMAC_RAW\n"
             "            mz_v <= 1'b0; mz_c <= 1'b0; mz_p <= 7'd0; mz_a0 <= 12'd0; mz_a1 <= 12'd0; mz_ne <= 12'd0; mz_no <= 12'd0;\n"
             "`endif\n")
    s = _rep(s, "            ma_v <= mi_v; ma_c <= mi_c; ma_p <= mi_p;\n",
             "`ifdef TRUSTEDGE_T3_PMAC_RAW\n"
             "            mz_v <= mi_v; mz_c <= mi_c; mz_p <= mi_p;\n"
             "            mz_a0 <= key_operand_a0; mz_a1 <= key_operand_a1; mz_ne <= noise_even_q; mz_no <= noise_odd_q;\n"
             "            ma_v <= mz_v; ma_c <= mz_c; ma_p <= mz_p;\n"
             "`else\n"
             "            ma_v <= mi_v; ma_c <= mi_c; ma_p <= mi_p;\n"
             "`endif\n")
    return s


def edit_pmac_raw_decaps(s: str) -> str:
    s = _rep(s, "    reg         db_v;  reg [6:0] db_j;  reg [11:0] db_p0, db_t, db_c1;\n",
             "    reg         db_v;  reg [6:0] db_j;  reg [11:0] db_p0, db_t, db_c1;\n"
             "`ifdef TRUSTEDGE_T3_PMAC_RAW\n"
             "    // stages Z and W register the RAM outputs (secret pair and NTT pair); two stages keep the NTT write\n"
             "    // of the second polynomial on the odd cycles\n"
             "    reg         dz_v, dw_v;  reg [6:0] dz_j, dw_j;  reg [11:0] dz_s0, dz_s1, dz_u0, dz_u1, dw_s0, dw_s1, dw_u0, dw_u1;\n"
             "`endif\n")
    s = _rep(s, """    wire [23:0] rt_d00 = secret0 * ntt_ext_rdata_pair[11:0];
    wire [23:0] rt_d11 = secret1 * ntt_ext_rdata_pair[23:12];
    wire [23:0] rt_d01 = secret0 * ntt_ext_rdata_pair[23:12];
    wire [23:0] rt_d10 = secret1 * ntt_ext_rdata_pair[11:0];
""", """`ifdef TRUSTEDGE_T3_PMAC_RAW
    wire [23:0] rt_d00 = dw_s0 * dw_u0;
    wire [23:0] rt_d11 = dw_s1 * dw_u1;
    wire [23:0] rt_d01 = dw_s0 * dw_u1;
    wire [23:0] rt_d10 = dw_s1 * dw_u0;
`else
    wire [23:0] rt_d00 = secret0 * ntt_ext_rdata_pair[11:0];
    wire [23:0] rt_d11 = secret1 * ntt_ext_rdata_pair[23:12];
    wire [23:0] rt_d01 = secret0 * ntt_ext_rdata_pair[23:12];
    wire [23:0] rt_d10 = secret1 * ntt_ext_rdata_pair[11:0];
`endif
""")
    s = _rep(s, "    wire [6:0]  dk_gidx = 7'd64 + {1'b0, di_j[6:1]};\n",
             "`ifdef TRUSTEDGE_T3_PMAC_RAW\n    wire [6:0]  dk_gidx = 7'd64 + {1'b0, dw_j[6:1]};\n`else\n"
             "    wire [6:0]  dk_gidx = 7'd64 + {1'b0, di_j[6:1]};\n`endif\n")
    s = _rep(s, "    wire [11:0] dk_gamma = di_j[0] ? (12'd3329 - dk_gfull[11:0]) : dk_gfull[11:0];\n",
             "`ifdef TRUSTEDGE_T3_PMAC_RAW\n    wire [11:0] dk_gamma = dw_j[0] ? (12'd3329 - dk_gfull[11:0]) : dk_gfull[11:0];\n`else\n"
             "    wire [11:0] dk_gamma = di_j[0] ? (12'd3329 - dk_gfull[11:0]) : dk_gfull[11:0];\n`endif\n")
    s = _rep(s, "            di_v <= 1'b0; da_v <= 1'b0; db_v <= 1'b0; di_j <= 7'd0; da_j <= 7'd0; db_j <= 7'd0;\n",
             "            di_v <= 1'b0; da_v <= 1'b0; db_v <= 1'b0; di_j <= 7'd0; da_j <= 7'd0; db_j <= 7'd0;\n"
             "`ifdef TRUSTEDGE_T3_PMAC_RAW\n"
             "            dz_v <= 1'b0; dw_v <= 1'b0; dz_j <= 7'd0; dw_j <= 7'd0;\n"
             "            dz_s0 <= 12'd0; dz_s1 <= 12'd0; dz_u0 <= 12'd0; dz_u1 <= 12'd0;\n"
             "            dw_s0 <= 12'd0; dw_s1 <= 12'd0; dw_u0 <= 12'd0; dw_u1 <= 12'd0;\n"
             "`endif\n")
    s = _rep(s, "            da_v <= di_v; da_j <= di_j;\n",
             "`ifdef TRUSTEDGE_T3_PMAC_RAW\n"
             "            dz_v <= di_v; dz_j <= di_j;\n"
             "            dz_s0 <= secret0; dz_s1 <= secret1; dz_u0 <= ntt_ext_rdata_pair[11:0]; dz_u1 <= ntt_ext_rdata_pair[23:12];\n"
             "            dw_v <= dz_v; dw_j <= dz_j; dw_s0 <= dz_s0; dw_s1 <= dz_s1; dw_u0 <= dz_u0; dw_u1 <= dz_u1;\n"
             "            da_v <= dw_v; da_j <= dw_j;\n"
             "`else\n"
             "            da_v <= di_v; da_j <= di_j;\n"
             "`endif\n")
    return s
