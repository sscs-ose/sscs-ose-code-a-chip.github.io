"""TRUSTEDGE_T3_LOAD_PIPE: slow-corner timing of the encryption's coefficient stream into the codec.

In S_READ_LOAD the NTT store and the noise RAMs present their read data half a cycle after the clock edge, and the
encryption added them (and the message for v), then the codec compressed and packed the sum, all before the next edge
(-15.5 ns at ss; the same sum is the coefficient RAM's write data, -4.7 ns). With the define on, a load cycle only registers
the two RAM outputs, the noise of the KAT mode, the message coefficient, the index and the segment flag (stage L); the
codec receives the sum one cycle later from registers, so the whole add-compress-pack path has a full cycle. The codec's
start is delayed by the same cycle (its done is a pulse, so S_CODEC_WAIT is unaffected), so the last coefficient is
loaded before the start. One more cycle per encryption; the ciphertext and digests are unchanged.
SPDX-License-Identifier: Apache-2.0
"""


def _rep(s: str, a: str, b: str) -> str:
    assert s.count(a) == 1, (s.count(a), a[:80])
    return s.replace(a, b)


def edit_load_pipe(s: str) -> str:
    a = s.index("    wire [11:0] noisy_coeff=add_mod_q(ntt_rdata[11:0],\n")
    end_txt = "    wire codec_start=(state==S_CODEC_START);\n"
    b = s.index(end_txt, a) + len(end_txt)
    orig = s[a:b]
    for x in ("wire message_bit=", "wire [11:0] message_coeff=", "wire [9:0] codec_index=", "wire codec_load_valid=(state==S_READ_LOAD);"):
        assert x in orig, x
    t3 = """    // stage L (T3): a load cycle registers the RAM outputs and the tags; the codec takes the sum one cycle later
    wire message_bit=runtime_valid_q ? runtime_message_q[read_index] :
        (read_index[0]^read_index[3]^read_index[5]);
    wire [11:0] message_coeff=message_bit?12'd1665:12'd0;
    reg         lp_v, lp_p2, lp_seg, lp_start;
    reg  [9:0]  lp_idx;
    reg  [11:0] lp_rd, lp_ns, lp_msg;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lp_v <= 1'b0; lp_p2 <= 1'b0; lp_seg <= 1'b0; lp_start <= 1'b0;
            lp_idx <= 10'd0; lp_rd <= 12'd0; lp_ns <= 12'd0; lp_msg <= 12'd0;
        end else begin
            lp_v <= (state==S_READ_LOAD);
            lp_p2 <= (poly_index==2);
            lp_idx <= (poly_index==0)?{2'd0,read_index}:
                      (poly_index==1)?(10'd256+read_index):(10'd512+read_index);
            lp_rd <= ntt_rdata[11:0];
            lp_ns <= runtime_valid_q?runtime_noise:kat_noise(poly_index,read_index);
            lp_msg <= message_coeff;
            lp_seg <= (state==S_READ_LOAD)&&(read_index==8'd255)&&(poly_index!=2'd2);
            lp_start <= (state==S_CODEC_START);
        end
    end
    wire [11:0] noisy_coeff=add_mod_q(lp_rd, lp_ns);
    wire [11:0] codec_coeff=lp_p2 ? add_mod_q(noisy_coeff,message_coeff_l) : noisy_coeff;
    wire [9:0] codec_index=lp_idx;
    wire codec_load_clear=(state==S_CODEC_CLR);
    wire codec_load_valid=lp_v;
    wire codec_start=lp_start;
""".replace("message_coeff_l", "lp_msg")
    s = s[:a] + "`ifdef TRUSTEDGE_T3_LOAD_PIPE\n" + t3 + "`else\n" + orig + "`endif\n" + s[b:]
    s = _rep(s, "    wire codec_seg_start=(state==S_READ_LOAD)&&(read_index==8'd255)&&(poly_index!=2'd2);\n",
             "`ifdef TRUSTEDGE_T3_LOAD_PIPE\n    wire codec_seg_start=lp_seg;\n`else\n"
             "    wire codec_seg_start=(state==S_READ_LOAD)&&(read_index==8'd255)&&(poly_index!=2'd2);\n`endif\n")
    return s
