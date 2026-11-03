"""TRUSTEDGE_T3_MM_PIPE: slow-corner timing of the serial matrix multiplier of key generation.

The shared multiplier's product is registered and reduced one state later, and the gamma of the pair is registered; the
states run in the order MUL0 MUL1 MUL3 MUL4 MUL2 MUL5, so that p1 is reduced before it is multiplied by gamma. One more
cycle per pair; with the define off the module is unchanged.
SPDX-License-Identifier: Apache-2.0
"""


def _rep(s: str, a: str, b: str) -> str:
    assert s.count(a) == 1, (s.count(a), a[:70])
    return s.replace(a, b)


def edit_matrix_mac(s: str) -> str:
    s = _rep(s, "                     S_DK_HASH = 6'd35;\n", "                     S_DK_HASH = 6'd35,\n                     S_MUL5 = 6'd36;\n")
    s = _rep(s, "    reg [11:0] p4_q;\n", """    reg [11:0] p4_q;
`ifdef TRUSTEDGE_T3_MM_PIPE
    reg [23:0] mm_prod_q;
    reg [11:0] gamma_q;
`endif
""")
    s = _rep(s, "            S_MUL2: begin mul_lhs = p1_q; mul_rhs = gamma; end\n", """`ifdef TRUSTEDGE_T3_MM_PIPE
            S_MUL2: begin mul_lhs = p1_q; mul_rhs = gamma_q; end
`else
            S_MUL2: begin mul_lhs = p1_q; mul_rhs = gamma; end
`endif
""")
    s = _rep(s, "    barrett_reduce u_mac_reduce (.a(mul_product), .r(mul_reduced));\n", """`ifdef TRUSTEDGE_T3_MM_PIPE
    always @(posedge clk) begin mm_prod_q <= mul_product; gamma_q <= gamma; end
    barrett_reduce u_mac_reduce (.a(mm_prod_q), .r(mul_reduced));
`else
    barrett_reduce u_mac_reduce (.a(mul_product), .r(mul_reduced));
`endif
""")
    s = _rep(s, """                S_MUL0: begin p0_q <= mul_reduced; state <= S_MUL1; end
                S_MUL1: begin p1_q <= mul_reduced; state <= S_MUL2; end
                S_MUL2: begin p2_q <= mul_reduced; state <= S_MUL3; end
                S_MUL3: begin p3_q <= mul_reduced; state <= S_MUL4; end
                S_MUL4: begin p4_q <= mul_reduced; state <= S_ACCUMULATE; end
""", """`ifdef TRUSTEDGE_T3_MM_PIPE
                S_MUL0: state <= S_MUL1;                                   // mm_prod_q <= a0 b0
                S_MUL1: begin p0_q <= mul_reduced; state <= S_MUL3; end    // mm_prod_q <= a1 b1
                S_MUL3: begin p1_q <= mul_reduced; state <= S_MUL4; end    // mm_prod_q <= a0 b1
                S_MUL4: begin p3_q <= mul_reduced; state <= S_MUL2; end    // mm_prod_q <= a1 b0
                S_MUL2: begin p4_q <= mul_reduced; state <= S_MUL5; end    // mm_prod_q <= p1 gamma
                S_MUL5: begin p2_q <= mul_reduced; state <= S_ACCUMULATE; end
`else
                S_MUL0: begin p0_q <= mul_reduced; state <= S_MUL1; end
                S_MUL1: begin p1_q <= mul_reduced; state <= S_MUL2; end
                S_MUL2: begin p2_q <= mul_reduced; state <= S_MUL3; end
                S_MUL3: begin p3_q <= mul_reduced; state <= S_MUL4; end
                S_MUL4: begin p4_q <= mul_reduced; state <= S_ACCUMULATE; end
`endif
""")
    return s
