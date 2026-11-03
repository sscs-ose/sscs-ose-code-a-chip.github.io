"""TRUSTEDGE_T3_CODEC_RETIME: slow-corner timing of the codec's reads of its coefficient RAM (ASIC SRAM configuration).

The coefficient macro presents its read data half a cycle after the clock edge, and the codec compressed it (and
decompressed it again) before the next edge: up to -14.5 ns at ss. With the define on, a register (coeff_r) takes the raw
read data at every rising edge, and every use of the data moves one cycle later to where the design already consumed a
registered value, so no cycle is added:
  - the pipelined decode check (stage 2) and the serial one (ACC) compare the ciphertext code with Compress(coeff_r)
    instead of comparing Decompress(code) with Decompress(Compress(coeff)). Decompress_10 and Decompress_4 are injective
    for q = 3329 (checked over all 1024 and 16 codes), so the two comparisons agree for every coefficient and every code;
    the digest and the decoded-RAM write use the ciphertext side only and are unchanged;
  - the U/V encoder (not reached when TRUSTEDGE_STREAM_OUT is on: the start goes to ST_S_FLUSH) reads through its WAIT
    state and packs Compress(coeff_r).
SPDX-License-Identifier: Apache-2.0
"""


def _rep(s: str, a: str, b: str) -> str:
    assert s.count(a) == 1, (s.count(a), a[:80])
    return s.replace(a, b)


def edit_codec_retime(s: str) -> str:
    s = _rep(s, "`ifdef TRUSTEDGE_ASIC_SRAM\n    wire [11:0] coeff_q;\n    wire [7:0] ct_ram_q;\n    wire [11:0] decoded_ram_q;\n",
             "`ifdef TRUSTEDGE_ASIC_SRAM\n    wire [11:0] coeff_q;\n    wire [7:0] ct_ram_q;\n    wire [11:0] decoded_ram_q;\n"
             "`ifdef TRUSTEDGE_T3_CODEC_RETIME\n"
             "    reg  [11:0] coeff_r;                     // the coefficient RAM's read data, one edge after the macro presents it\n"
             "    always @(posedge clk) coeff_r <= coeff_q;\n"
             "`endif\n")
    s = _rep(s, "    reg [11:0] p2_dec, p2_src;\n",
             "    reg [11:0] p2_dec, p2_src;\n`ifdef TRUSTEDGE_T3_CODEC_RETIME\n    reg [9:0]  p2_code;  reg p2_vph;\n`endif\n")
    s = _rep(s, "    wire [9:0] coeff_compressed10 = compress10(coeff_q);\n    wire [3:0] coeff_compressed4 = compress4(coeff_q);\n",
             "`ifdef TRUSTEDGE_T3_CODEC_RETIME\n"
             "    wire [9:0] coeff_compressed10 = compress10(coeff_r);\n    wire [3:0] coeff_compressed4 = compress4(coeff_r);\n"
             "`else\n"
             "    wire [9:0] coeff_compressed10 = compress10(coeff_q);\n    wire [3:0] coeff_compressed4 = compress4(coeff_q);\n"
             "`endif\n")
    s = _rep(s, "    wire decode_mismatch = (compare_decoded_coeff != compare_source_coeff);\n",
             "`ifdef TRUSTEDGE_T3_CODEC_RETIME\n"
             "    reg  [9:0] code_cmp_q;                   // the ciphertext code of the compared coefficient (taken in WAIT)\n"
             "    wire decode_mismatch = decode_v_phase ? (compress4(coeff_r) != code_cmp_q[3:0]) :\n"
             "                                            (compress10(coeff_r) != code_cmp_q);\n"
             "`else\n"
             "    wire decode_mismatch = (compare_decoded_coeff != compare_source_coeff);\n"
             "`endif\n")
    s = _rep(s, "    wire        p2_mismatch = (p2_dec != p2_src);\n",
             "`ifdef TRUSTEDGE_T3_CODEC_RETIME\n"
             "    wire        p2_mismatch = p2_vph ? (compress4(coeff_r) != p2_code[3:0]) : (compress10(coeff_r) != p2_code);\n"
             "`else\n"
             "    wire        p2_mismatch = (p2_dec != p2_src);\n"
             "`endif\n")
    s = _rep(s, "                    p2_v <= p1_v; p2_idx <= p1_idx; p2_dec <= p1_dec; p2_src <= p1_src;\n",
             "`ifdef TRUSTEDGE_T3_CODEC_RETIME\n"
             "                    p2_v <= p1_v; p2_idx <= p1_idx; p2_dec <= p1_dec; p2_code <= p1_code; p2_vph <= p1_vph;\n"
             "`else\n"
             "                    p2_v <= p1_v; p2_idx <= p1_idx; p2_dec <= p1_dec; p2_src <= p1_src;\n"
             "`endif\n")
    s = _rep(s, "                    decoded_coeff_cmp_q <= decoded_coeff;\n                    canonical_source_coeff_cmp_q <= canonical_source_coeff;\n",
             "                    decoded_coeff_cmp_q <= decoded_coeff;\n"
             "`ifdef TRUSTEDGE_T3_CODEC_RETIME\n"
             "                    code_cmp_q <= decode_v_phase ? {6'd0, decoded_v4} : decoded_u10;\n"
             "`else\n"
             "                    canonical_source_coeff_cmp_q <= canonical_source_coeff;\n"
             "`endif\n")
    for ph in ("U", "V"):
        s = _rep(s, f"                ST_{ph}_REQ: state <= ST_{ph}_CAPTURE;      // one-cycle read latency\n",
                 "`ifdef TRUSTEDGE_T3_CODEC_RETIME\n"
                 f"                ST_{ph}_REQ: state <= ST_{ph}_WAIT;         // the data is packed from coeff_r\n"
                 "`else\n"
                 f"                ST_{ph}_REQ: state <= ST_{ph}_CAPTURE;      // one-cycle read latency\n"
                 "`endif\n")
    return s
