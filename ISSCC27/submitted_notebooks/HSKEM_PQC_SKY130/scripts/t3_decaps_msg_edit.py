"""Two slow-corner timing fixes of the decapsulation's SRAM reads (ASIC SRAM configuration).

TRUSTEDGE_T3_MSG_PIPE: message recovery (ST_MSG_CAP) subtracted two macro outputs (the decoded v coefficient and the
NTT store's coefficient), formed the message bit and wrote the byte, the message digest and recovered_message_q before
the next edge, half a cycle after the macros presented the data (-2.7 ns at ss). With the define on, ST_MSG_CAP only
registers the two read values and the coefficient index (stage P); the bit, the byte, both digests and the message
register are updated one cycle later from the registers, and a drain state (ST_MSG_DRAIN) processes the last
coefficient before the hash step starts. One more cycle per decapsulation; the message and digests are unchanged.

TRUSTEDGE_T3_PP_EARLY (with TRUSTEDGE_T3_MAC_DEEP): stage R added the product RAM's output to the finished pair and wrote
it into the NTT in the cycle the macro presented it (-1.3 ns at ss, 756 endpoints of the NTT's input bank). The product
RAM is addressed by a pipeline register, so it is now read one stage earlier (dx_j instead of dy_j), its output is
registered (pp_r) and stage R adds the register. No cycle is added.
SPDX-License-Identifier: Apache-2.0
"""


def _rep(s: str, a: str, b: str) -> str:
    assert s.count(a) == 1, (s.count(a), a[:80])
    return s.replace(a, b)


def edit_decaps_msg(s: str) -> str:
    # ---- MSG_PIPE
    s = _rep(s, "    localparam [12:0] Q13 = 13'd3329;\n",
             "    localparam [12:0] Q13 = 13'd3329;\n"
             "`ifdef TRUSTEDGE_T3_MSG_PIPE\n    localparam [5:0] ST_MSG_DRAIN = 6'd54;   // the last recovered coefficient is processed\n`endif\n")
    old_w = """    wire [12:0] subtract_wide = {1'b0,decoded_ext_data} + Q13 -
                                {1'b0,ntt_ext_rdata[11:0]};
"""
    s = _rep(s, old_w, """`ifdef TRUSTEDGE_T3_MSG_PIPE
    // stage P: the two RAM outputs and the coefficient index of the last ST_MSG_CAP cycle
    reg         mp_v;  reg [7:0] mp_idx;  reg [11:0] mp_d, mp_u;
    wire [12:0] subtract_wide = {1'b0,mp_d} + Q13 - {1'b0,mp_u};
`else
""" + old_w + "`endif\n")
    old_b = """    wire [7:0] message_byte_next = message_byte_q |
                                   ({7'd0,recovered_bit} << coeff_index[2:0]);
"""
    s = _rep(s, old_b, "`ifdef TRUSTEDGE_T3_MSG_PIPE\n"
                       "    wire [7:0] message_byte_next = message_byte_q |\n"
                       "                                   ({7'd0,recovered_bit} << mp_idx[2:0]);\n"
                       "`else\n" + old_b + "`endif\n")
    s = _rep(s, "            result0_q<=0;result1_q<=0;message_byte_q<=0;\n",
             "            result0_q<=0;result1_q<=0;message_byte_q<=0;\n"
             "`ifdef TRUSTEDGE_T3_MSG_PIPE\n            mp_v<=1'b0; mp_idx<=8'd0; mp_d<=12'd0; mp_u<=12'd0;\n`endif\n")
    s = _rep(s, "            case (state)\n                ST_IDLE: if (encaps_start && !busy) begin\n",
             "`ifdef TRUSTEDGE_T3_MSG_PIPE\n"
             "            mp_v <= 1'b0;\n"
             "            if (mp_v) begin                       // the coefficient taken in the last cycle\n"
             "                coeff_digest_q<=coeff_digest_next;\n"
             "                message_byte_q<=message_byte_next;\n"
             "                if(mp_idx[2:0]==3'd7) begin\n"
             "                    message_digest_q<=message_digest_next;\n"
             "                    recovered_message_q[mp_idx[7:3]*8 +: 8] <= message_byte_next;\n"
             "                    message_byte_q<=0;\n"
             "                end\n"
             "            end\n"
             "`endif\n"
             "            case (state)\n                ST_IDLE: if (encaps_start && !busy) begin\n")
    cap = """                ST_MSG_CAP: begin
                    coeff_digest_q<=coeff_digest_next;
                    message_byte_q<=message_byte_next;
                    if(coeff_index[2:0]==3'd7) begin
                        message_digest_q<=message_digest_next;
                        recovered_message_q[coeff_index[7:3]*8 +: 8] <=
                            message_byte_next;
                        message_byte_q<=0;
                    end
                    if(coeff_index==8'd255) begin
"""
    a = s.index(cap) + len(cap)
    tail = "                    end else begin coeff_index<=coeff_index+1'b1;\n"
    b = s.index(tail, a)
    last = s[a:b]                                    # what the last coefficient starts (hash step)
    s = s[:a - len(cap)] + """                ST_MSG_CAP: begin
`ifdef TRUSTEDGE_T3_MSG_PIPE
                    mp_v<=1'b1; mp_idx<=coeff_index; mp_d<=decoded_ext_data; mp_u<=ntt_ext_rdata[11:0];
                    if(coeff_index==8'd255) begin
                        state<=ST_MSG_DRAIN;
`else
                    coeff_digest_q<=coeff_digest_next;
                    message_byte_q<=message_byte_next;
                    if(coeff_index[2:0]==3'd7) begin
                        message_digest_q<=message_digest_next;
                        recovered_message_q[coeff_index[7:3]*8 +: 8] <=
                            message_byte_next;
                        message_byte_q<=0;
                    end
                    if(coeff_index==8'd255) begin
""" + last + "`endif\n" + s[b:]
    s = _rep(s, "                // handled by the hash sequencer below\n",
             "`ifdef TRUSTEDGE_T3_MSG_PIPE\n                ST_MSG_DRAIN: begin\n" + last + "                end\n`endif\n"
             "                // handled by the hash sequencer below\n")
    # ---- PP_EARLY
    s = _rep(s, "    wire [6:0]  dk_prj = dy_j;             // the product RAM is read when the pair is two stages before stage R\n",
             "`ifdef TRUSTEDGE_T3_PP_EARLY\n"
             "    wire [6:0]  dk_prj = dx_j;             // read three stages before stage R; pp_r holds the data for stage R\n"
             "`else\n"
             "    wire [6:0]  dk_prj = dy_j;             // the product RAM is read when the pair is two stages before stage R\n"
             "`endif\n")
    s = _rep(s, "    wire [11:0] dk_res0 = add_mod_q(product_pair_q[11:0], dk_c0);\n    wire [11:0] dk_res1 = add_mod_q(product_pair_q[23:12], db_c1);\n",
             "`ifdef TRUSTEDGE_T3_PP_EARLY\n"
             "    reg  [23:0] pp_r;\n"
             "    always @(posedge clk) pp_r <= product_pair_q;\n"
             "    wire [11:0] dk_res0 = add_mod_q(pp_r[11:0], dk_c0);\n    wire [11:0] dk_res1 = add_mod_q(pp_r[23:12], db_c1);\n"
             "`else\n"
             "    wire [11:0] dk_res0 = add_mod_q(product_pair_q[11:0], dk_c0);\n    wire [11:0] dk_res1 = add_mod_q(product_pair_q[23:12], db_c1);\n"
             "`endif\n")
    # the accumulation of ST_ACCUM reads the product RAM at pair_index, which is fixed from MUL0 on, so the registered copy
    # (taken at the end of MUL1) holds the same word in ST_ACCUM
    s = _rep(s, "    wire [11:0] accum0=add_mod_q(product_pair_q[11:0],base0);\n    wire [11:0] accum1=add_mod_q(product_pair_q[23:12],base1);\n",
             "`ifdef TRUSTEDGE_T3_PP_EARLY\n"
             "    wire [11:0] accum0=add_mod_q(pp_r[11:0],base0);\n    wire [11:0] accum1=add_mod_q(pp_r[23:12],base1);\n"
             "`else\n"
             "    wire [11:0] accum0=add_mod_q(product_pair_q[11:0],base0);\n    wire [11:0] accum1=add_mod_q(product_pair_q[23:12],base1);\n"
             "`endif\n")
    return s
