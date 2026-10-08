"""Build the full-system RTL with the packed-pair NTT from the published copy (hskem_rtl/).

The published copy stays untouched (Appendix E.3). This script copies it and edits five files, every
change behind one of three defines, so that every configuration of Section 8 can still be built from the
same tree:

  TRUSTEDGE_PACKED_NTT    rtl/trustedge_top.v: the shared NTT is kyber_ntt_engine_packed (same ports);
  TRUSTEDGE_HASH_OVERLAP  rtl/mlkem512/mlkem512_partial_kem_selftests.sv: H(ek), H(c) and J(z||c) of a
                          decapsulation run on a second sequencer while the decryption uses the NTT;
  TRUSTEDGE_STREAM_IO     the decapsulation and encryption controllers and the ciphertext codec: ten read
                          loops drop a wait state that the one-cycle read latency of every source RAM
                          makes redundant;
  TRUSTEDGE_FAST_BASEMUL  both pointwise multipliers: a second multiplier and Karatsuba, two multiply
                          states per coefficient pair instead of five;
  TRUSTEDGE_FAST_FEED     the hash loops drop their wait state, and u enters the NTT straight from the
                          decoded RAM (with TRUSTEDGE_STREAM_IO);
  TRUSTEDGE_STREAM_OUT    the ciphertext codec encodes while the coefficients are loaded (with
                          TRUSTEDGE_STREAM_IO);
  TRUSTEDGE_FOLD_READBACK the codec's audit digests are taken during its decode check, which reads the
                          same bytes in the same order, and the read-back pass is dropped;
  TRUSTEDGE_PREFETCH      the encryption fetches the operands of its next multiply step during the current
                          one (bound runtime key);
  TRUSTEDGE_TIGHT_LOOPS   one ciphertext byte compared per cycle, and the encryption's result writes
                          overlapped with the next pair's multiplies (with TRUSTEDGE_PREFETCH);
  TRUSTEDGE_FAST_CHECK    the codec's decode check addresses the next byte and coefficient of a group
                          one state early;
  TRUSTEDGE_FAST_Y        r enters the NTT at two cycles per pair and y returns at one cycle per
                          coefficient (runtime encryption, with TRUSTEDGE_STREAM_IO);
  TRUSTEDGE_PACKED2       (with TRUSTEDGE_PACKED_NTT) the shared NTT is kyber_ntt_engine_packed2: two
                          butterfly lanes, one per half of a word, and two fused passes;
  TRUSTEDGE_FAST_PRF      the noise sampler emits a coefficient pair per cycle while the sponge keeps
                          streaming (runtime encryption);
  TRUSTEDGE_FUSED_CMP     the decapsulation compares the re-encrypted ciphertext while the codec's decode
                          check reads it (with TRUSTEDGE_TIGHT_LOOPS);
  TRUSTEDGE_FAST_READ     the encryption's results enter the codec at one coefficient per cycle, with one
                          gap per U group of four (with TRUSTEDGE_STREAM_OUT);
  TRUSTEDGE_PIPE_CHECK    the codec's decode check reads bytes and source coefficients as two overlapped
                          streams (with TRUSTEDGE_FOLD_READBACK);
  TRUSTEDGE_PAIR_PORT     the encryption's y path writes and reads the packed2 engine a pair at a time
                          (with TRUSTEDGE_PACKED2 and TRUSTEDGE_FAST_Y);
  TRUSTEDGE_DEFER_J       J(z||c) runs during the re-encryption, after its noise sampling, instead of
                          after H(c) during the decryption (with TRUSTEDGE_FUSED_CMP);
  TRUSTEDGE_PIPE_MAC      the encryption's matrix-vector product as a four-multiplier pipeline, one
                          pair-column per cycle (bound runtime key; with TRUSTEDGE_PAIR_PORT);
  TRUSTEDGE_FAST_HASH     H(ek), H(c) and J(z||c) absorb one byte per cycle (with TRUSTEDGE_FAST_FEED);
  TRUSTEDGE_DEC_STREAM    the decryption loads u and recovers the message at one coefficient per cycle and
                          computes s^T u-hat with a four-multiplier pipeline (with TRUSTEDGE_PAIR_PORT);
  TRUSTEDGE_BG_PRF        e1 and e2 are sampled in the background during the y path's NTT waits (with
                          TRUSTEDGE_FAST_PRF);
  TRUSTEDGE_SEG_CHECK     the codec checks u0's and u1's bytes while the next polynomial is computed and
                          only v's at the end (with TRUSTEDGE_PIPE_CHECK);
  TRUSTEDGE_STREAM_INV    each inverse transform of the encryption runs while its pipelined product
                          delivers the pairs (engine stream mode; with TRUSTEDGE_PIPE_MAC);
  TRUSTEDGE_STREAM_FWD    the forward transforms of r (encryption) and u (decryption) run while their input
                          is written in the first-pass order (engine stream mode; with TRUSTEDGE_STREAM_INV);
  TRUSTEDGE_PRF_TO_NTT    r0 is sampled straight into the NTT, whose transform runs while r1 is sampled
                          (with TRUSTEDGE_BG_PRF and TRUSTEDGE_STREAM_FWD);
  TRUSTEDGE_STREAM_DEC_INV the decryption's inverse transform runs while s^T u-hat is formed (engine
                          stream mode and read-while-busy; with TRUSTEDGE_STREAM_FWD);
  TRUSTEDGE_PRF_FINE_HOLD the background sampler pauses only its squeeze and its noise-RAM writes while the
                          encryption uses that RAM (with TRUSTEDGE_BG_PRF);
  TRUSTEDGE_POLY_GUARD    an encryption's inverse transform waits only for the noise polynomial its
                          read adds; a decapsulation keeps the strict wait (with PRF_FINE_HOLD, DEFER_J);
  TRUSTEDGE_PMAC_RETIME   (chip) stage A of both pipelined products is four dedicated multipliers on the
                          RAM outputs, registered unreduced (the macros launch their reads on the falling
                          edge); the shared multipliers keep register operands only (with PIPE_MAC);
  TRUSTEDGE_SO_PIPE       (chip) the codec compresses and packs each U coefficient one cycle after its load
                          (with TRUSTEDGE_STREAM_OUT);
  (testbench)             sim/tb/tb_trustedge_spi.sv: the expected cycle counts follow from the number of
                          transforms per operation, the two phase lengths and the elements of each read
                          loop, as the testbench already does for the serial Keccak.

Without the defines the built tree behaves exactly as the published one. Every edit asserts that its
anchor occurs exactly once. The files are written with LF line ends; a unified diff of the edited files is
written for review (by default next to the tree).

usage: make_packed_system.py <hskem_rtl> <out_dir> <codeachip rtl/> [<diff file>]
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import difflib
import re
import shutil
import sys
from pathlib import Path


def rep(s: str, a: str, b: str) -> str:
    assert s.count(a) == 1, f"anchor found {s.count(a)} times: {a[:70]!r}"
    return s.replace(a, b)


def edit_top(s: str) -> str:
    a = "    kyber_ntt_engine u_shared_ntt (\n"
    return poly_guard_top(stream_dec_inv_top(stream_fwd_top(stream_inv_top(dec_stream_top(defer_j_top(pair_port_top(fused_cmp_top(rep(s, a, "`ifdef TRUSTEDGE_PACKED_NTT\n"
                     "    // packed-pair, layer-fused NTT: same ports, one 24 x 128 single-port coefficient store\n"
                     "`ifdef TRUSTEDGE_PACKED2\n"
                     "    // two lanes, two fused passes: 512 port accesses per transform\n"
                     "    kyber_ntt_engine_packed2 #(.EXTRA_STAGE(1'b1)) u_shared_ntt (\n"
                     "`else\n"
                     "    kyber_ntt_engine_packed #(.EXTRA_STAGE(1'b1)) u_shared_ntt (\n"
                     "`endif\n"
                     "`else\n" + a + "`endif\n")))))))))


def poly_guard_enc(s: str) -> str:
    """TRUSTEDGE_POLY_GUARD, encryption side (with TRUSTEDGE_PRF_FINE_HOLD): an inverse transform waits only
    for the noise polynomial its read adds (e1[0], e1[1] or e2), not for the whole background sampler. A
    polynomial is complete once the sampler waits after it and its last pair has landed. The sampler is held
    in the cycle that leaves S_INV_WAIT, so that no registered noise-RAM write lands on the read. Inside a
    decapsulation (prf_all_first) the strict wait stays: J(z||c) follows the sampler on the shared sponge, and
    finishing e2 before u0 is read lets J start earliest."""
    s = rep(s, "    output wire         r_done,             // r0 and r1 are complete\n",
            "    output wire         r_done,             // r0 and r1 are complete\n"
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "    output wire [2:0]   polys_done,         // polynomials whose last pair is in the noise RAM\n"
            "`endif\n")
    s = rep(s, "    assign r_done = busy && (poly_index >= 3'd2);\n",
            "    assign r_done = busy && (poly_index >= 3'd2);\n"
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "    // complete polynomials: those before poly_index, and poly_index itself while the sampler waits\n"
            "    // after it with its last pair written (that pair is written in the first P_WAIT cycle)\n"
            "    assign polys_done = poly_index + {2'd0, (state == P_WAIT) && !coeff_valid};\n"
            "`endif\n")
    s = rep(s, "    input  wire         runtime_input_valid,\n",
            "    input  wire         runtime_input_valid,\n"
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "    input  wire         prf_all_first,      // a decapsulation: all noise before u0 is read\n"
            "`endif\n")
    s = rep(s, """    wire prf_hold = !((state==S_PRF_START)||(state==S_PRF_WAIT)||(state==S_Y_NTT_START)||
                      (state==S_Y_NTT_WAIT)||(state==S_INV_START)||(state==S_INV_WAIT)||
                      ((state==S_Y_WRITE0) && y_ph));
""", """`ifdef TRUSTEDGE_POLY_GUARD
    wire inv_exit_hold;                      // the cycle that leaves S_INV_WAIT (assigned below)
    wire prf_hold = !((state==S_PRF_START)||(state==S_PRF_WAIT)||(state==S_Y_NTT_START)||
                      (state==S_Y_NTT_WAIT)||(state==S_INV_START)||(state==S_INV_WAIT)||
                      ((state==S_Y_WRITE0) && y_ph)) || inv_exit_hold;
`else
    wire prf_hold = !((state==S_PRF_START)||(state==S_PRF_WAIT)||(state==S_Y_NTT_START)||
                      (state==S_Y_NTT_WAIT)||(state==S_INV_START)||(state==S_INV_WAIT)||
                      ((state==S_Y_WRITE0) && y_ph));
`endif
""")
    s = rep(s, "    wire ntt_busy,ntt_done;\n", """    wire ntt_busy,ntt_done;
`ifdef TRUSTEDGE_POLY_GUARD
    // the read of noise polynomial poly_index+2 needs that polynomial only: the sampler has completed it
    // (e2, the last one, is complete when the sampler is done)
    wire [2:0] prf_polys;
    wire prf_poly_ok = prf_bg_done_q || !runtime_valid_q ||
                       (!prf_all_first && (prf_polys > ({1'b0, poly_index} + 3'd2)));
    wire inv_exit = (state == S_INV_WAIT) && (ntt_done || inv_seen_q) && prf_poly_ok;
    assign inv_exit_hold = inv_exit;
`endif
""")
    s = rep(s, "        .hold(prf_hold),.r_done(prf_r_done),\n",
            "        .hold(prf_hold),.r_done(prf_r_done),\n"
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "        .polys_done(prf_polys),\n"
            "`endif\n")
    s = rep(s, "                    if ((ntt_done || inv_seen_q) && (prf_bg_done_q || !runtime_valid_q)) begin\n",
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "                    if (inv_exit) begin\n"
            "`else\n"
            "                    if ((ntt_done || inv_seen_q) && (prf_bg_done_q || !runtime_valid_q)) begin\n"
            "`endif\n")
    return s


def poly_guard_dec(s: str) -> str:
    """TRUSTEDGE_POLY_GUARD, decapsulation side (with TRUSTEDGE_DEFER_J): while J(z||c) is still to run, the
    re-encryption's sampler finishes all five noise polynomials before u0 is read."""
    s = rep(s, "    output wire       hash_active,         // the hash sequencer drives the shared sponge\n",
            "    output wire       hash_active,         // the hash sequencer drives the shared sponge\n"
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "    output wire       prf_all_first,       // the re-encryption reads u0 only after all noise\n"
            "`endif\n")
    s = rep(s, "    reg encaps_mode_q;\n", """    reg encaps_mode_q;
`ifdef TRUSTEDGE_POLY_GUARD
    assign prf_all_first = reencrypt_active && !encaps_mode_q && j_pending_q;
`endif
""")
    return s


def poly_guard_top(s: str) -> str:
    """TRUSTEDGE_POLY_GUARD wiring: the decapsulation's request for the strict noise wait."""
    s = rep(s, "    wire        mlkem512_decaps_hash_active;\n",
            "    wire        mlkem512_decaps_hash_active;\n"
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "    wire        mlkem512_decaps_prf_all_first;\n"
            "`endif\n")
    s = rep(s, "        .hash_active(mlkem512_decaps_hash_active),\n",
            "        .hash_active(mlkem512_decaps_hash_active),\n"
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "        .prf_all_first(mlkem512_decaps_prf_all_first),\n"
            "`endif\n")
    s = rep(s, "        .runtime_input_valid(mlkem512_encaps_input_valid_mux),\n",
            "        .runtime_input_valid(mlkem512_encaps_input_valid_mux),\n"
            "`ifdef TRUSTEDGE_POLY_GUARD\n"
            "        .prf_all_first(mlkem512_decaps_prf_all_first),\n"
            "`endif\n")
    return s


def prf_fine_hold(s: str) -> str:
    """TRUSTEDGE_PRF_FINE_HOLD (with TRUSTEDGE_BG_PRF): while the encryption uses the noise RAM, the background
    sampler only stops squeezing bytes and emitting coefficients; it keeps absorbing and its permutations keep
    running, so that with the serial Keccak its RAM work still fits into the windows before u0 is read out."""
    s = rep(s, """`ifdef TRUSTEDGE_BG_PRF
    wire prf_held = hold && busy && (poly_index >= 3'd2);
    assign r_done = busy && (poly_index >= 3'd2);
""", """`ifdef TRUSTEDGE_BG_PRF
`ifdef TRUSTEDGE_PRF_FINE_HOLD
    wire prf_held = 1'b0;                                       // the state machine always runs ...
    wire emit_hold = hold && busy && (poly_index >= 3'd2);      // ... but squeezes and emits only unheld
`else
    wire prf_held = hold && busy && (poly_index >= 3'd2);
    wire emit_hold = 1'b0;
`endif
    assign r_done = busy && (poly_index >= 3'd2);
""")
    s = rep(s, """`else
    wire prf_held = 1'b0;
    wire sponge_in_valid = (state == P_RUN) && (feed_index < 6'd33);
`endif
""", """`else
    wire prf_held = 1'b0;
    wire emit_hold = 1'b0;
    wire sponge_in_valid = (state == P_RUN) && (feed_index < 6'd33);
`endif
""")
    s = rep(s, "    assign sponge_ext_out_ready = (state == P_RUN) && !prf_held;\n",
            "    assign sponge_ext_out_ready = (state == P_RUN) && !prf_held && !emit_hold;\n")
    s = rep(s, "                .out_ready((state == P_RUN) && !prf_held), .busy(), .done(sponge_done),\n",
            "                .out_ready((state == P_RUN) && !prf_held && !emit_hold), .busy(), .done(sponge_done),\n")
    s = rep(s, """                    // emit one pair of the finished block per cycle while the next block streams in
                    if (emit_left != 3'd0) begin""", """                    // emit one pair of the finished block per cycle while the next block streams in
                    if ((emit_left != 3'd0) && !emit_hold) begin""")
    s = rep(s, """                    if (sponge_out_valid) begin
                        prf_digest <= digest_step(prf_digest, sponge_out_byte);
                        word_q <= word_with_byte;
                        if (block_byte == last_block_byte) begin
                            block_q <= word_with_byte;
                            word_q <= 32'd0;
                            block_byte <= 3'd0;
                            emit_left <= eta1_poly ? 3'd2 : 3'd4;""", """                    if (sponge_out_valid && !emit_hold) begin
                        prf_digest <= digest_step(prf_digest, sponge_out_byte);
                        word_q <= word_with_byte;
                        if (block_byte == last_block_byte) begin
                            block_q <= word_with_byte;
                            word_q <= 32'd0;
                            block_byte <= 3'd0;
                            emit_left <= eta1_poly ? 3'd2 : 3'd4;""")
    return s


def prf_to_ntt(s: str) -> str:
    """TRUSTEDGE_PRF_TO_NTT (with TRUSTEDGE_BG_PRF, TRUSTEDGE_STREAM_FWD and TRUSTEDGE_PAIR_PORT): r0's
    coefficient pairs go from the sampler straight into the idle NTT (r0 itself is never needed again, only
    r0-hat), whose forward transform starts as soon as r0 is complete and runs while r1 is sampled. The y path
    then reads r0-hat back and continues with r1 as before; a flag keeps the transform's completion in case
    it ends before r1 is complete."""
    s = rep(s, "    output wire         r_done,             // r0 and r1 are complete\n",
            "    output wire         r_done,             // r0 and r1 are complete\n"
            "`ifdef TRUSTEDGE_PRF_TO_NTT\n"
            "    output wire         r0_done,            // r0 is complete\n"
            "`endif\n")
    s = rep(s, "    assign r_done = busy && (poly_index >= 3'd2);\n",
            "    assign r_done = busy && (poly_index >= 3'd2);\n"
            "`ifdef TRUSTEDGE_PRF_TO_NTT\n"
            "    assign r0_done = busy && (poly_index >= 3'd1);\n"
            "`endif\n")
    s = rep(s, "        .hold(prf_hold),.r_done(prf_r_done),\n",
            "        .hold(prf_hold),.r_done(prf_r_done),\n"
            "`ifdef TRUSTEDGE_PRF_TO_NTT\n"
            "        .r0_done(prf_r0_done),\n"
            "`endif\n")
    s = rep(s, "    wire prf_r_done;\n", """    wire prf_r_done;
`ifdef TRUSTEDGE_PRF_TO_NTT
    wire prf_r0_done;
`endif
""")
    s = rep(s, "    wire pair_on = USE_EXTERNAL_NTT;            // the shared packed2 engine takes and returns whole pairs\n",
            """    wire pair_on = USE_EXTERNAL_NTT;            // the shared packed2 engine takes and returns whole pairs
`ifdef TRUSTEDGE_PRF_TO_NTT
    // r0's pairs (sampler polynomial 0) are written into the NTT instead of the noise RAM
    wire r0_wr = prf_coeff_valid && (prf_coeff_addr[10:8] == 3'd0) && pair_on;
    reg  r0_started_q, r0_ntt_done_q;
    wire r0_ntt_start = (state==S_PRF_WAIT) && prf_r0_done && !r0_started_q;
`endif
""")
    # the noise RAM no longer takes r0 (FPGA arrays and ASIC macros)
    s = rep(s, """        if (prf_coeff_valid) begin
`ifdef TRUSTEDGE_FAST_PRF
            noise_even_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;""", """`ifdef TRUSTEDGE_PRF_TO_NTT
        if (prf_coeff_valid && !r0_wr) begin
`else
        if (prf_coeff_valid) begin
`endif
`ifdef TRUSTEDGE_FAST_PRF
            noise_even_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;""")
    s = rep(s, """    wire noise_even_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && (pair_on || !y_read_index[0]));
    wire noise_odd_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && (pair_on || y_read_index[0]));
""", """`ifdef TRUSTEDGE_PRF_TO_NTT
    wire noise_even_we = (prf_coeff_valid && !r0_wr) || ((state == S_Y_READ_CAP) && (pair_on || !y_read_index[0]));
    wire noise_odd_we = (prf_coeff_valid && !r0_wr) || ((state == S_Y_READ_CAP) && (pair_on || y_read_index[0]));
`else
    wire noise_even_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && (pair_on || !y_read_index[0]));
    wire noise_odd_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && (pair_on || y_read_index[0]));
`endif
""")
    # the NTT port: r0's pair writes and the start of its transform
    s = rep(s, "    wire ntt_start=(state==S_INV_START)||pmac_stream_start||y_stream_start;\n", """`ifdef TRUSTEDGE_PRF_TO_NTT
    wire ntt_start=(state==S_INV_START)||pmac_stream_start||y_stream_start||r0_ntt_start;
`else
    wire ntt_start=(state==S_INV_START)||pmac_stream_start||y_stream_start;
`endif
""")
    s = rep(s, "    wire ntt_we=y_ntt_write||data_ntt_write||pmac_wr;\n", """`ifdef TRUSTEDGE_PRF_TO_NTT
    wire ntt_we=y_ntt_write||data_ntt_write||pmac_wr||r0_wr;
`else
    wire ntt_we=y_ntt_write||data_ntt_write||pmac_wr;
`endif
""")
    s = rep(s, """`ifdef TRUSTEDGE_PIPE_MAC
        pmac_wr ? {mr_p,1'b0} :
`endif
""", """`ifdef TRUSTEDGE_PIPE_MAC
        pmac_wr ? {mr_p,1'b0} :
`endif
`ifdef TRUSTEDGE_PRF_TO_NTT
        r0_wr ? {prf_coeff_addr[7:1],1'b0} :
`endif
""")
    s = rep(s, """`ifdef TRUSTEDGE_PIPE_MAC
        pmac_wr ? {4'd0,mr_r0} :
`endif
""", """`ifdef TRUSTEDGE_PIPE_MAC
        pmac_wr ? {4'd0,mr_r0} :
`endif
`ifdef TRUSTEDGE_PRF_TO_NTT
        r0_wr ? {4'd0,prf_coeff_data} :
`endif
""")
    s = rep(s, """    assign ntt_ext_we_pair = pair_on && (((state==S_Y_WRITE0) && !y_ph) || pmac_wr);
""", """`ifdef TRUSTEDGE_PRF_TO_NTT
    assign ntt_ext_we_pair = pair_on && (((state==S_Y_WRITE0) && !y_ph) || pmac_wr || r0_wr);
`else
    assign ntt_ext_we_pair = pair_on && (((state==S_Y_WRITE0) && !y_ph) || pmac_wr);
`endif
""")
    s = rep(s, "    assign ntt_ext_wdata_odd = pmac_wr ? mr_r1 : noise_odd_q;\n", """`ifdef TRUSTEDGE_PRF_TO_NTT
    assign ntt_ext_wdata_odd = pmac_wr ? mr_r1 : r0_wr ? prf_coeff_data_odd : noise_odd_q;
`else
    assign ntt_ext_wdata_odd = pmac_wr ? mr_r1 : noise_odd_q;
`endif
""")
    # control
    s = rep(s, "            if (prf_done) begin runtime_prf_ok_q<=prf_pass; prf_bg_done_q<=1'b1; end\n", """            if (prf_done) begin runtime_prf_ok_q<=prf_pass; prf_bg_done_q<=1'b1; end
`ifdef TRUSTEDGE_PRF_TO_NTT
            if (r0_ntt_start) r0_started_q<=1'b1;
            if (ntt_done && r0_started_q) r0_ntt_done_q<=1'b1;   // the first completion after the start
`endif
""")
    s = rep(s, "                S_PRF_START: begin prf_bg_done_q<=1'b0; state<=S_PRF_WAIT; end\n", """`ifdef TRUSTEDGE_PRF_TO_NTT
                S_PRF_START: begin prf_bg_done_q<=1'b0; r0_started_q<=1'b0; r0_ntt_done_q<=1'b0;
                    state<=S_PRF_WAIT; end
`else
                S_PRF_START: begin prf_bg_done_q<=1'b0; state<=S_PRF_WAIT; end
`endif
""")
    s = rep(s, """                S_PRF_WAIT: if(prf_r_done) begin        // e1 and e2 follow in the background
                    y_poly<=0;y_pair<=0;state<=S_Y_FETCH; end
""", """`ifdef TRUSTEDGE_PRF_TO_NTT
                S_PRF_WAIT: if(prf_r_done) begin        // r0 is in the NTT already, being transformed
                    y_poly<=0;y_pair<=0;state<=S_Y_NTT_WAIT; end
`else
                S_PRF_WAIT: if(prf_r_done) begin        // e1 and e2 follow in the background
                    y_poly<=0;y_pair<=0;state<=S_Y_FETCH; end
`endif
""")
    s = rep(s, "                S_Y_NTT_WAIT: if(ntt_done) begin y_read_index<=0;state<=S_Y_READ_REQ;end\n", """`ifdef TRUSTEDGE_PRF_TO_NTT
                S_Y_NTT_WAIT: if(ntt_done || (!y_poly && r0_ntt_done_q)) begin y_read_index<=0;state<=S_Y_READ_REQ;end
`else
                S_Y_NTT_WAIT: if(ntt_done) begin y_read_index<=0;state<=S_Y_READ_REQ;end
`endif
""")
    return s


def stream_dec_inv_top(s: str) -> str:
    """TRUSTEDGE_STREAM_DEC_INV wiring: the decapsulation (owner 4) may read the store while its stream-mode
    transform runs; every other user leaves re low (also without the define, so the engine port is driven)."""
    s = rep(s, "        .rdata_pair(shared_ntt_rdata_pair), .stream(shared_ntt_stream),\n",
            "        .rdata_pair(shared_ntt_rdata_pair), .stream(shared_ntt_stream), .re(shared_ntt_re),\n")
    s = rep(s, "    wire        mlkem512_decaps_ntt_req_stream;\n",
            "    wire        mlkem512_decaps_ntt_req_stream;\n"
            "    wire        mlkem512_decaps_ntt_req_re;\n"
            "`ifdef TRUSTEDGE_STREAM_DEC_INV\n"
            "    wire        shared_ntt_re = (shared_ntt_owner == 3'd4) && mlkem512_decaps_ntt_req_re;\n"
            "`else\n"
            "    wire        shared_ntt_re = 1'b0;\n"
            "`endif\n")
    s = rep(s, "        .ntt_ext_stream(mlkem512_decaps_ntt_req_stream),\n",
            "        .ntt_ext_stream(mlkem512_decaps_ntt_req_stream),\n"
            "`ifdef TRUSTEDGE_STREAM_DEC_INV\n"
            "        .ntt_ext_re(mlkem512_decaps_ntt_req_re),\n"
            "`endif\n")
    return s


def stream_dec_inv(s: str) -> str:
    """TRUSTEDGE_STREAM_DEC_INV (with TRUSTEDGE_STREAM_FWD and TRUSTEDGE_DEC_STREAM): when u1's forward transform
    ends, the inverse transform is started in stream mode in the same store. The second product pass reads
    u1-hat with re on its issue cycles and writes its finished pairs, in word order, into the transform's
    first pass on the other cycles; a first-pass group is stored only after its products were computed from
    the words it replaces. When the last pair is written, only the rest of the transform remains."""
    s = rep(s, "    output wire       ntt_ext_stream,\n", """    output wire       ntt_ext_stream,
`ifdef TRUSTEDGE_STREAM_DEC_INV
    output wire       ntt_ext_re,
`endif
""")
    s = rep(s, "    wire        u_pair_wr = (state == ST_U_WRITE) && coeff_index[0];\n", """    wire        u_pair_wr = (state == ST_U_WRITE) && coeff_index[0];
`ifdef TRUSTEDGE_STREAM_DEC_INV
    wire        dk_inv_start = (state == ST_NTT_WAIT) && ntt_ext_done && poly_index;
`endif
""")
    s = rep(s, "    assign ntt_ext_stream = (state == ST_U_REQ);\n", """`ifdef TRUSTEDGE_STREAM_DEC_INV
    assign ntt_ext_stream = (state == ST_U_REQ) || dk_inv_start;
    assign ntt_ext_re = dk_issue && poly_index;            // u1-hat while the inverse transform runs
`else
    assign ntt_ext_stream = (state == ST_U_REQ);
`endif
""")
    s = rep(s, "    assign ntt_ext_start=(state==ST_U_REQ)||(state==ST_INV_START);\n", """`ifdef TRUSTEDGE_STREAM_DEC_INV
    assign ntt_ext_start=(state==ST_U_REQ)||(state==ST_INV_START)||dk_inv_start;
`else
    assign ntt_ext_start=(state==ST_U_REQ)||(state==ST_INV_START);
`endif
""")
    s = rep(s, "    assign ntt_ext_inverse=(state==ST_INV_START);\n", """`ifdef TRUSTEDGE_STREAM_DEC_INV
    assign ntt_ext_inverse=(state==ST_INV_START)||dk_inv_start;
`else
    assign ntt_ext_inverse=(state==ST_INV_START);
`endif
""")
    s = rep(s, """                        else state<=ST_INV_START;
                    end
                end
""", """`ifdef TRUSTEDGE_STREAM_DEC_INV
                        else state<=ST_INV_WAIT;          // the inverse transform runs already
`else
                        else state<=ST_INV_START;
`endif
                    end
                end
""")
    return s


def stream_fwd_top(s: str) -> str:
    """TRUSTEDGE_STREAM_FWD wiring (with TRUSTEDGE_STREAM_INV): the decapsulation (owner 4) may also start a
    transform in stream mode."""
    s = rep(s, "    wire        mlkem512_encaps_ntt_req_stream;\n",
            "    wire        mlkem512_encaps_ntt_req_stream;\n"
            "    wire        mlkem512_decaps_ntt_req_stream;\n")
    s = rep(s, "`ifdef TRUSTEDGE_STREAM_INV\n"
               "    wire        shared_ntt_stream = (shared_ntt_owner == 3'd3) && mlkem512_encaps_ntt_req_stream;\n",
            "`ifdef TRUSTEDGE_STREAM_FWD\n"
            "    wire        shared_ntt_stream = ((shared_ntt_owner == 3'd3) && mlkem512_encaps_ntt_req_stream) ||\n"
            "                                    ((shared_ntt_owner == 3'd4) && mlkem512_decaps_ntt_req_stream);\n"
            "`elsif TRUSTEDGE_STREAM_INV\n"
            "    wire        shared_ntt_stream = (shared_ntt_owner == 3'd3) && mlkem512_encaps_ntt_req_stream;\n")
    s = rep(s, "        .ntt_ext_wdata(mlkem512_decaps_ntt_req_wdata),\n",
            "        .ntt_ext_wdata(mlkem512_decaps_ntt_req_wdata),\n"
            "`ifdef TRUSTEDGE_STREAM_FWD\n"
            "        .ntt_ext_stream(mlkem512_decaps_ntt_req_stream),\n"
            "`endif\n")
    return s


def stream_fwd_enc(s: str) -> str:
    """TRUSTEDGE_STREAM_FWD in the encryption (with TRUSTEDGE_STREAM_INV and TRUSTEDGE_PAIR_PORT): the forward
    transform of r is started in stream mode when the y path begins, and r is written one pair every second
    cycle in the transform's first-pass order (group g, slot s: word {s0, s1, s2, g}); the noise RAM is
    read only on the other cycles, which the background sampler may use."""
    s = rep(s, "    reg [7:0] y_read_index;\n", """    reg [7:0] y_read_index;
`ifdef TRUSTEDGE_STREAM_FWD
    reg  y_ph;                                   // the y path writes a pair on every second cycle
    wire [6:0] y_word = {y_pair[0], y_pair[1], y_pair[2], y_pair[6:3]};
`endif
""")
    s = rep(s, "    wire ntt_start=(state==S_INV_START)||(state==S_Y_NTT_START)||pmac_stream_start;\n", """`ifdef TRUSTEDGE_STREAM_FWD
    wire y_stream_start = (state==S_Y_FETCH) && pair_on;
    wire ntt_start=(state==S_INV_START)||pmac_stream_start||y_stream_start;
`else
    wire ntt_start=(state==S_INV_START)||(state==S_Y_NTT_START)||pmac_stream_start;
`endif
""")
    s = rep(s, "    assign ntt_ext_stream=pmac_stream_start;\n", """`ifdef TRUSTEDGE_STREAM_FWD
    assign ntt_ext_stream=pmac_stream_start||y_stream_start;
`else
    assign ntt_ext_stream=pmac_stream_start;
`endif
""")
    s = rep(s, "    wire y_ntt_write=(state==S_Y_WRITE0)||(state==S_Y_WRITE1);\n", """`ifdef TRUSTEDGE_STREAM_FWD
    wire y_ntt_write=((state==S_Y_WRITE0) && !y_ph)||(state==S_Y_WRITE1);
`else
    wire y_ntt_write=(state==S_Y_WRITE0)||(state==S_Y_WRITE1);
`endif
""")
    s = rep(s, """    wire [7:0] ntt_addr = y_ntt_write ?
        ((state==S_Y_WRITE0)?{y_pair,1'b0}:{y_pair,1'b1}) :
""", """`ifdef TRUSTEDGE_STREAM_FWD
    wire [7:0] ntt_addr = y_ntt_write ?
        ((state==S_Y_WRITE0)?{y_word,1'b0}:{y_pair,1'b1}) :
`else
    wire [7:0] ntt_addr = y_ntt_write ?
        ((state==S_Y_WRITE0)?{y_pair,1'b0}:{y_pair,1'b1}) :
`endif
""")
    s = rep(s, """`ifdef TRUSTEDGE_PAIR_PORT
            noise_read_addr = (((state==S_Y_WRITE1) || (pair_on && (state==S_Y_WRITE0))) && (y_pair!=7'd127)) ?
                                                                       {2'd0,y_poly,y_pair+7'd1} :
`else""", """`ifdef TRUSTEDGE_STREAM_FWD
            noise_read_addr = (state!=S_Y_WRITE1) ? {2'd0,y_poly,y_word} :  // y_pair advances with each write
`elsif TRUSTEDGE_PAIR_PORT
            noise_read_addr = (((state==S_Y_WRITE1) || (pair_on && (state==S_Y_WRITE0))) && (y_pair!=7'd127)) ?
                                                                       {2'd0,y_poly,y_pair+7'd1} :
`else""")
    s = rep(s, "    assign ntt_ext_we_pair = pair_on && ((state==S_Y_WRITE0) || pmac_wr);\n", """`ifdef TRUSTEDGE_STREAM_FWD
    assign ntt_ext_we_pair = pair_on && (((state==S_Y_WRITE0) && !y_ph) || pmac_wr);
`else
    assign ntt_ext_we_pair = pair_on && ((state==S_Y_WRITE0) || pmac_wr);
`endif
""")
    s = rep(s, """    wire prf_hold = !((state==S_PRF_START)||(state==S_PRF_WAIT)||(state==S_Y_NTT_START)||
                      (state==S_Y_NTT_WAIT)||(state==S_INV_START)||(state==S_INV_WAIT));
""", """`ifdef TRUSTEDGE_STREAM_FWD
    wire prf_hold = !((state==S_PRF_START)||(state==S_PRF_WAIT)||(state==S_Y_NTT_START)||
                      (state==S_Y_NTT_WAIT)||(state==S_INV_START)||(state==S_INV_WAIT)||
                      ((state==S_Y_WRITE0) && y_ph));
    // (the sampler's RAM write is registered and lands one cycle after its unheld cycle: unheld on the
    // y path's read cycles, it writes on the following pair-write cycle, when the y path reads nothing)
`else
    wire prf_hold = !((state==S_PRF_START)||(state==S_PRF_WAIT)||(state==S_Y_NTT_START)||
                      (state==S_Y_NTT_WAIT)||(state==S_INV_START)||(state==S_INV_WAIT));
`endif
""")
    s = rep(s, """                S_Y_WRITE0: if (pair_on) begin               // the whole pair was written
                    if (y_pair==127) state<=S_Y_NTT_START;
                    else begin y_pair<=y_pair+1'b1; state<=S_Y_WRITE0; end
                end else state<=S_Y_WRITE1;
""", """`ifdef TRUSTEDGE_STREAM_FWD
                S_Y_WRITE0: if (pair_on) begin               // a pair on every second cycle
                    if (!y_ph) begin
                        if (y_pair==127) state<=S_Y_NTT_WAIT;  // the transform runs already
                        else begin y_pair<=y_pair+1'b1; y_ph<=1'b1; end
                    end else y_ph<=1'b0;
                end else state<=S_Y_WRITE1;
`else
                S_Y_WRITE0: if (pair_on) begin               // the whole pair was written
                    if (y_pair==127) state<=S_Y_NTT_START;
                    else begin y_pair<=y_pair+1'b1; state<=S_Y_WRITE0; end
                end else state<=S_Y_WRITE1;
`endif
""")
    s = rep(s, "                S_Y_FETCH: state<=S_Y_WRITE0;      // one-cycle read latency\n", """`ifdef TRUSTEDGE_STREAM_FWD
                S_Y_FETCH: begin y_ph<=1'b0; state<=S_Y_WRITE0; end  // the stream transform starts now
`else
                S_Y_FETCH: state<=S_Y_WRITE0;      // one-cycle read latency
`endif
""")
    return s


def stream_fwd_dec(s: str) -> str:
    """TRUSTEDGE_STREAM_FWD in the decapsulation (with TRUSTEDGE_DEC_STREAM): the forward transform of u_i is
    started in stream mode when its load begins; the decoded RAM is read in the transform's first-pass order,
    one coefficient per cycle, and every second cycle the completed pair is written."""
    s = rep(s, "    output wire [11:0] ntt_ext_wdata_odd,\n", """    output wire [11:0] ntt_ext_wdata_odd,
`ifdef TRUSTEDGE_STREAM_FWD
    output wire       ntt_ext_stream,
`endif
""")
    s = rep(s, "    wire [11:0] dk_c0;                     // stage R: the finished even coefficient\n", """    wire [11:0] dk_c0;                     // stage R: the finished even coefficient
`ifdef TRUSTEDGE_STREAM_FWD
    // the u load in the forward transform's first-pass order: coefficient i is half i[0] of word
    // {s0, s1, s2, g} with g = i[7:4] and s = i[3:1]
    function automatic [7:0] u_order(input [7:0] i);
        u_order = {i[1], i[2], i[3], i[7:4], i[0]};
    endfunction
    reg  [11:0] u_even_q;
    wire        u_pair_wr = (state == ST_U_WRITE) && coeff_index[0];
`endif
""")
    s = rep(s, """    assign ntt_ext_we=(state==ST_U_WRITE)||(state==ST_WRITE0)||
                      (state==ST_WRITE1)||dk_wr;
    assign ntt_ext_we_pair = dk_wr;
    assign ntt_ext_wdata_odd = dk_res1;
    assign ntt_ext_addr=(state==ST_U_WRITE)?coeff_index:
""", """`ifdef TRUSTEDGE_STREAM_FWD
    assign ntt_ext_we=u_pair_wr||(state==ST_WRITE0)||(state==ST_WRITE1)||dk_wr;
    assign ntt_ext_we_pair = dk_wr || u_pair_wr;
    assign ntt_ext_wdata_odd = u_pair_wr ? decoded_ext_data : dk_res1;
    assign ntt_ext_stream = (state == ST_U_REQ);
    assign ntt_ext_addr=(state==ST_U_WRITE)?{u_order(coeff_index)>>1,1'b0}:
`else
    assign ntt_ext_we=(state==ST_U_WRITE)||(state==ST_WRITE0)||
                      (state==ST_WRITE1)||dk_wr;
    assign ntt_ext_we_pair = dk_wr;
    assign ntt_ext_wdata_odd = dk_res1;
    assign ntt_ext_addr=(state==ST_U_WRITE)?coeff_index:
`endif
""")
    s = rep(s, "    assign ntt_ext_wdata=(state==ST_U_WRITE)?{4'd0,decoded_ext_data}:\n", """`ifdef TRUSTEDGE_STREAM_FWD
    assign ntt_ext_wdata=(state==ST_U_WRITE)?{4'd0,u_even_q}:
`else
    assign ntt_ext_wdata=(state==ST_U_WRITE)?{4'd0,decoded_ext_data}:
`endif
""")
    s = rep(s, "    assign ntt_ext_start=(state==ST_NTT_START)||(state==ST_INV_START);\n", """`ifdef TRUSTEDGE_STREAM_FWD
    assign ntt_ext_start=(state==ST_U_REQ)||(state==ST_INV_START);
`else
    assign ntt_ext_start=(state==ST_NTT_START)||(state==ST_INV_START);
`endif
""")
    s = rep(s, """                ST_U_REQ: begin decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_WRITE;end  // one ahead
""", """`ifdef TRUSTEDGE_STREAM_FWD
                ST_U_REQ: begin decoded_ext_addr<={1'b0,poly_index,u_order(8'd1)};state<=ST_U_WRITE;end
`else
                ST_U_REQ: begin decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_WRITE;end  // one ahead
`endif
""")
    s = rep(s, """                ST_U_WRITE: begin
                    if(coeff_index==8'd255) state<=ST_NTT_START;
                    else begin coeff_index<=coeff_index+1'b1;
`ifdef TRUSTEDGE_DEC_STREAM
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_WRITE;end
`else
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_REQ;end
`endif
                end
""", """`ifdef TRUSTEDGE_STREAM_FWD
                ST_U_WRITE: begin                    // the decoded address runs one coefficient ahead
                    if (!coeff_index[0]) u_even_q<=decoded_ext_data;
                    if(coeff_index==8'd255) state<=ST_NTT_WAIT;      // the transform runs already
                    else begin coeff_index<=coeff_index+1'b1;
                        decoded_ext_addr<={1'b0,poly_index,u_order(coeff_index+8'd2)};end
                end
`else
                ST_U_WRITE: begin
                    if(coeff_index==8'd255) state<=ST_NTT_START;
                    else begin coeff_index<=coeff_index+1'b1;
`ifdef TRUSTEDGE_DEC_STREAM
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_WRITE;end
`else
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_REQ;end
`endif
                end
`endif
""")
    return s


def stream_inv_top(s: str) -> str:
    """TRUSTEDGE_STREAM_INV wiring: the encryption (owner 3) may start the inverse transform in stream mode;
    every other user leaves the stream input low (also without the define, so the engine port is driven)."""
    s = rep(s, "        .rdata_pair(shared_ntt_rdata_pair),\n",
            "        .rdata_pair(shared_ntt_rdata_pair), .stream(shared_ntt_stream),\n")
    s = rep(s, "    wire [23:0] shared_ntt_rdata_pair;\n",
            "    wire [23:0] shared_ntt_rdata_pair;\n"
            "    wire        mlkem512_encaps_ntt_req_stream;\n"
            "`ifdef TRUSTEDGE_STREAM_INV\n"
            "    wire        shared_ntt_stream = (shared_ntt_owner == 3'd3) && mlkem512_encaps_ntt_req_stream;\n"
            "`else\n"
            "    wire        shared_ntt_stream = 1'b0;\n"
            "`endif\n")
    s = rep(s, "        .ntt_ext_we_pair(mlkem512_encaps_ntt_req_we_pair),\n",
            "        .ntt_ext_we_pair(mlkem512_encaps_ntt_req_we_pair),\n"
            "`ifdef TRUSTEDGE_STREAM_INV\n"
            "        .ntt_ext_stream(mlkem512_encaps_ntt_req_stream),\n"
            "`endif\n")
    return s


def defer_j_top(s: str) -> str:
    """TRUSTEDGE_DEFER_J: while the decapsulation's hash sequencer runs J(z||c) during the re-encryption,
    the decapsulation owns the shared sponge (the encryption has finished its noise sampling)."""
    s = rep(s, """    wire shared_sponge_owner_decaps = mlkem512_decaps_busy &&
                                      !mlkem512_decaps_reencrypt_active;
""", """`ifdef TRUSTEDGE_DEFER_J
    wire        mlkem512_decaps_hash_active;
    wire shared_sponge_owner_decaps = mlkem512_decaps_busy &&
                                      (!mlkem512_decaps_reencrypt_active || mlkem512_decaps_hash_active);
`else
    wire shared_sponge_owner_decaps = mlkem512_decaps_busy &&
                                      !mlkem512_decaps_reencrypt_active;
`endif
""")
    s = rep(s, "        .reencrypt_active(mlkem512_decaps_reencrypt_active),\n",
            "        .reencrypt_active(mlkem512_decaps_reencrypt_active),\n"
            "`ifdef TRUSTEDGE_DEFER_J\n"
            "        .hash_active(mlkem512_decaps_hash_active),\n"
            "`endif\n")
    return s


def pair_port_top(s: str) -> str:
    """TRUSTEDGE_PAIR_PORT wiring (with TRUSTEDGE_PACKED2): the encryption, which owns the shared NTT as
    owner 3 (encapsulation and the decapsulation's re-encryption), may write and read a whole pair; every
    other owner leaves the pair write low."""
    s = rep(s, "    kyber_ntt_engine_packed2 #(.EXTRA_STAGE(1'b1)) u_shared_ntt (\n",
            "    kyber_ntt_engine_packed2 #(.EXTRA_STAGE(1'b1)) u_shared_ntt (\n"
            "        .we_pair(shared_ntt_we_pair), .wdata_odd(shared_ntt_wdata_odd),\n"
            "        .rdata_pair(shared_ntt_rdata_pair),\n")
    s = rep(s, "`ifdef TRUSTEDGE_PACKED_NTT\n    // packed-pair, layer-fused NTT: same ports",
            "    wire        mlkem512_encaps_ntt_req_we_pair;\n"
            "    wire [11:0] mlkem512_encaps_ntt_req_wdata_odd;\n"
            "    wire [23:0] shared_ntt_rdata_pair;\n"
            "`ifdef TRUSTEDGE_PAIR_PORT\n"
            "    wire        shared_ntt_we_pair = (shared_ntt_owner == 3'd3) && mlkem512_encaps_ntt_req_we_pair;\n"
            "`else\n"
            "    wire        shared_ntt_we_pair = 1'b0;\n"
            "`endif\n"
            "    wire [11:0] shared_ntt_wdata_odd = mlkem512_encaps_ntt_req_wdata_odd;\n"
            "`ifdef TRUSTEDGE_PACKED_NTT\n    // packed-pair, layer-fused NTT: same ports")
    s = rep(s, "        .ntt_ext_wdata(mlkem512_encaps_ntt_req_wdata),\n",
            "        .ntt_ext_wdata(mlkem512_encaps_ntt_req_wdata),\n"
            "`ifdef TRUSTEDGE_PAIR_PORT\n"
            "        .ntt_ext_we_pair(mlkem512_encaps_ntt_req_we_pair),\n"
            "        .ntt_ext_wdata_odd(mlkem512_encaps_ntt_req_wdata_odd),\n"
            "        .ntt_ext_rdata_pair(shared_ntt_rdata_pair),\n"
            "`endif\n")
    return s


def fused_cmp_top(s: str) -> str:
    """TRUSTEDGE_FUSED_CMP wiring: the codec's decode-check read address and byte strobe reach the
    decapsulation controller; the byte itself already arrives on the shared ciphertext data wire."""
    s = rep(s, "    wire [9:0]  mlkem512_decaps_ciphertext_byte_addr;\n",
            "    wire [9:0]  mlkem512_decaps_ciphertext_byte_addr;\n"
            "`ifdef TRUSTEDGE_FUSED_CMP\n"
            "    wire        mlkem512_ct_check_active, mlkem512_ct_check_byte;\n"
            "    wire [9:0]  mlkem512_ct_check_addr;\n"
            "`endif\n")
    s = rep(s, "        .ciphertext_read_data(mlkem512_ciphertext_byte_data),\n",
            "        .ciphertext_read_data(mlkem512_ciphertext_byte_data),\n"
            "`ifdef TRUSTEDGE_FUSED_CMP\n"
            "        .ct_check_active(mlkem512_ct_check_active), .ct_check_byte(mlkem512_ct_check_byte),\n"
            "        .ct_check_addr(mlkem512_ct_check_addr),\n"
            "`endif\n")
    s = rep(s, "        .ciphertext_ext_data(mlkem512_ciphertext_byte_data),\n",
            "        .ciphertext_ext_data(mlkem512_ciphertext_byte_data),\n"
            "`ifdef TRUSTEDGE_FUSED_CMP\n"
            "        .ct_check_active(mlkem512_ct_check_active), .ct_check_byte(mlkem512_ct_check_byte),\n"
            "        .ct_check_addr(mlkem512_ct_check_addr),\n"
            "`endif\n")
    return s


FAST_HASH_DECL = """`ifdef TRUSTEDGE_FAST_HASH
    // One byte per cycle into the sponge (TRUSTEDGE_FAST_HASH): the feed states repeat, and the address of
    // the next byte is presented in the same cycle in which the sponge accepts the current one, so the
    // byte is ready in the next cycle; while the sponge permutes (in_ready low) the address is held.
    wire hk_take = (sp_state == ST_HEK_FEED) && sponge_ext_in_ready;
    assign ekpke_ext_pair_addr = (hk_take && (ek_byte_sub == 2'd2) && (sponge_feed_index < 10'd767)) ?
                                 ekpke_ext_pair_addr_q + 8'd1 : ekpke_ext_pair_addr_q;
    assign rho_ext_addr = (hk_take && (sponge_feed_index >= 10'd768)) ? rho_ext_addr_q + 5'd1 : rho_ext_addr_q;
    assign ciphertext_ext_addr = ((sp_state == ST_HC_FEED) && sponge_ext_in_ready &&
                                  (sponge_feed_index != 10'd767)) ?
                                 ciphertext_ext_addr_q + 10'd1 : ciphertext_ext_addr_q;
`ifdef TRUSTEDGE_FUSED_CMP
    // The decode check (fused comparison) has priority on the reference RAM. J, which may still run when the
    // check starts (serial Keccak with the segmented check), consumes a ciphertext byte only if the RAM
    // served its address in the previous cycle, and otherwise presents the address again.
    reg j_ref_ok;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) j_ref_ok <= 1'b1;
        else        j_ref_ok <= !(fused_window && ct_check_active);
    wire j_take_ok = (sponge_feed_index < 10'd32) || j_ref_ok;
`else
    wire j_take_ok = 1'b1;
`endif
    wire [9:0] ref_rd_index = ((sp_state == ST_J_FEED) && sponge_ext_in_ready && j_take_ok &&
                               (sponge_feed_index >= 10'd31)) ? sponge_feed_index - 10'd31 : compare_index;
`else
    assign ekpke_ext_pair_addr = ekpke_ext_pair_addr_q;
    assign rho_ext_addr = rho_ext_addr_q;
    assign ciphertext_ext_addr = ciphertext_ext_addr_q;
    wire [9:0] ref_rd_index = compare_index;
    wire j_take_ok = 1'b1;
`endif
"""


def fast_hash(s: str) -> str:
    """TRUSTEDGE_FAST_HASH (with TRUSTEDGE_FAST_FEED): H(ek), H(c) and J(z||c) absorb one byte per cycle
    instead of one per request/feed pair. The three external read addresses become wires driven from
    registers (identical without the define), and the reference RAM's read index of J looks ahead in the
    same way."""
    import re
    for n in ("ciphertext_ext_addr", "ekpke_ext_pair_addr", "rho_ext_addr"):
        s = re.sub(r"\b" + n + r"\b", n + "_q", s)
    s = rep(s, "    output reg [7:0]  ekpke_ext_pair_addr_q,\n", "    output wire [7:0] ekpke_ext_pair_addr,\n")
    s = rep(s, "    output reg [4:0]  rho_ext_addr_q,\n", "    output wire [4:0] rho_ext_addr,\n")
    s = rep(s, "    output reg [9:0]  ciphertext_ext_addr_q,\n", "    output wire [9:0] ciphertext_ext_addr,\n")
    s = rep(s, "    wire fused_window = (state == ST_REENC_WAIT) && !encaps_mode_q;\n`endif\n",
            "    wire fused_window = (state == ST_REENC_WAIT) && !encaps_mode_q;\n`endif\n"
            "    reg [7:0] ekpke_ext_pair_addr_q;\n    reg [4:0] rho_ext_addr_q;\n    reg [9:0] ciphertext_ext_addr_q;\n"
            + FAST_HASH_DECL)
    # the reference RAM's last read alternative (FPGA array and ASIC macro)
    s = rep(s, "                                               compare_index + 10'd1 : compare_index];\n`else\n",
            "                                               compare_index + 10'd1 : ref_rd_index];\n`else\n")
    s = rep(s, "        (state == ST_CMP_CHECK) ? cmp_ref_next : compare_index;\n",
            "        (state == ST_CMP_CHECK) ? cmp_ref_next : ref_rd_index;\n")
    # the feed states repeat while bytes remain
    for st in ("HEK", "HC"):
        s = rep(s, "                        `DCP_HS<=ST_" + st + "_REQ;\n",
                "`ifdef TRUSTEDGE_FAST_HASH\n                        `DCP_HS<=ST_" + st + "_FEED;\n`else\n"
                "                        `DCP_HS<=ST_" + st + "_REQ;\n`endif\n")
    s = rep(s, "                ST_J_FEED: if(sponge_ext_in_ready) begin\n",
            "                ST_J_FEED: if(sponge_ext_in_ready && j_take_ok) begin\n")
    s = rep(s, "                                 (sp_state == ST_J_FEED);\n",
            "                                 ((sp_state == ST_J_FEED) && j_take_ok);\n")
    s = rep(s, "`endif\n                        `DCP_HS<=ST_J_REQ;\n",
            "`endif\n`ifdef TRUSTEDGE_FAST_HASH\n                        `DCP_HS<=ST_J_FEED;\n`else\n"
            "                        `DCP_HS<=ST_J_REQ;\n`endif\n")
    return s


DEC_DECL = """`ifdef TRUSTEDGE_DEC_STREAM
    // Pipelined decryption product (TRUSTEDGE_DEC_STREAM, state ST_MUL2): pair j of u-hat (a whole NTT
    // word) and of s-hat is addressed in the issue cycle, the RAMs answer one cycle later (stage A:
    // three products), stage B multiplies by gamma, stage R finishes the pair. The first polynomial
    // issues one pair per cycle and stores the products; the second issues on even cycles, because its
    // finished pairs return to the NTT through the same single port on the odd cycles.
    reg  [8:0]  dk_t;
    wire        dk_issue = (state == ST_MUL2) &&
                           (poly_index ? ((dk_t[0] == 1'b0) && (dk_t < 9'd256)) : (dk_t < 9'd128));
    wire [6:0]  dk_j = poly_index ? dk_t[7:1] : dk_t[6:0];
    reg         di_v;  reg [6:0] di_j;
    reg         da_v;  reg [6:0] da_j;  reg [11:0] da_p0, da_p1, da_p3, da_g;
    reg         db_v;  reg [6:0] db_j;  reg [11:0] db_p0, db_t, db_c1;
    wire        dk_pwr = (state == ST_MUL2) && !poly_index && db_v;     // first polynomial: product RAM
    wire        dk_wr  = (state == ST_MUL2) && poly_index && db_v;      // second polynomial: into the NTT
    wire [11:0] dk_c0;                     // stage R: the finished even coefficient
`endif
"""
DEC_DATAPATH = """`ifdef TRUSTEDGE_DEC_STREAM
    wire [11:0] dk_sa = add_mod_q(secret0, secret1);
    wire [11:0] dk_sb = add_mod_q(ntt_ext_rdata_pair[11:0], ntt_ext_rdata_pair[23:12]);
    wire [23:0] dk_prod3 = dk_sa * dk_sb;
    wire [11:0] dk_red3;
    barrett_reduce u_dec_reduce3(.a(dk_prod3), .r(dk_red3));
    wire [6:0]  dk_gidx = 7'd64 + {1'b0, di_j[6:1]};
    wire [15:0] dk_gfull = kyber_zeta(dk_gidx);
    wire [11:0] dk_gamma = di_j[0] ? (12'd3329 - dk_gfull[11:0]) : dk_gfull[11:0];
`ifdef TRUSTEDGE_PMAC_RETIME
    // stage A as in the encryption: four dedicated multipliers on the RAM outputs, products unreduced
    wire [23:0] rt_d00 = secret0 * ntt_ext_rdata_pair[11:0];
    wire [23:0] rt_d11 = secret1 * ntt_ext_rdata_pair[23:12];
    wire [23:0] rt_d01 = secret0 * ntt_ext_rdata_pair[23:12];
    wire [23:0] rt_d10 = secret1 * ntt_ext_rdata_pair[11:0];
    reg  [23:0] da_r0, da_r1, da_r2, da_r3;
    wire [11:0] dq0, dq1, dq2, dq3;
    barrett_reduce u_rt_dreduce0(.a(da_r0), .r(dq0));
    barrett_reduce u_rt_dreduce1(.a(da_r1), .r(dq1));
    barrett_reduce u_rt_dreduce2(.a(da_r2), .r(dq2));
    barrett_reduce u_rt_dreduce3(.a(da_r3), .r(dq3));
    wire [11:0] dk_odd = add_mod_q(dq2, dq3);
`else
    wire [11:0] dq0 = da_p0, dq1 = da_p1, dq3 = da_p3;
    wire [11:0] dk_odd = sub_mod_q(sub_mod_q(dq3, dq0), dq1);
`endif
    wire [23:0] dk_prod4 = dq1 * da_g;
    wire [11:0] dk_red4;
    barrett_reduce u_dec_reduce4(.a(dk_prod4), .r(dk_red4));
    assign dk_c0 = add_mod_q(db_p0, db_t);
    wire [11:0] dk_res0 = add_mod_q(product_pair_q[11:0], dk_c0);
    wire [11:0] dk_res1 = add_mod_q(product_pair_q[23:12], db_c1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            di_v <= 1'b0; da_v <= 1'b0; db_v <= 1'b0; di_j <= 7'd0; da_j <= 7'd0; db_j <= 7'd0;
            da_p0 <= 12'd0; da_p1 <= 12'd0; da_p3 <= 12'd0; da_g <= 12'd0;
            db_p0 <= 12'd0; db_t <= 12'd0; db_c1 <= 12'd0;
        end else begin
            di_v <= dk_issue; di_j <= dk_j;
            da_v <= di_v; da_j <= di_j;
            da_p0 <= mul_reduced; da_p1 <= mul2_reduced; da_p3 <= dk_red3; da_g <= dk_gamma;
`ifdef TRUSTEDGE_PMAC_RETIME
            da_r0 <= rt_d00; da_r1 <= rt_d11; da_r2 <= rt_d01; da_r3 <= rt_d10;
`endif
            db_v <= da_v; db_j <= da_j;
            db_p0 <= dq0; db_t <= dk_red4; db_c1 <= dk_odd;
        end
    end
`endif
"""


def dec_stream(s: str) -> str:
    """TRUSTEDGE_DEC_STREAM (with TRUSTEDGE_FAST_FEED, TRUSTEDGE_FAST_BASEMUL, TRUSTEDGE_PREFETCH and
    TRUSTEDGE_PAIR_PORT): u enters the NTT and the message is recovered at one coefficient per cycle (the
    decoded-RAM address runs one ahead, the NTT read address looks ahead), and s^T u-hat is computed by a
    four-multiplier pipeline that reads u-hat a pair at a time."""
    s = rep(s, "    input  wire [15:0] ntt_ext_rdata,\n", """    input  wire [15:0] ntt_ext_rdata,
`ifdef TRUSTEDGE_DEC_STREAM
    output wire       ntt_ext_we_pair,
    output wire [11:0] ntt_ext_wdata_odd,
    input  wire [23:0] ntt_ext_rdata_pair,
`endif
""")
    s = rep(s, "    reg [9:0] ciphertext_ext_addr_q;\n", "    reg [9:0] ciphertext_ext_addr_q;\n" + DEC_DECL)
    s = rep(s, "    wire [11:0] base1 = sub_mod_q(sub_mod_q(p3_q, p0_q), p1_q);\n",
            "    wire [11:0] base1 = sub_mod_q(sub_mod_q(p3_q, p0_q), p1_q);\n" + DEC_DATAPATH)
    # the two existing multipliers take the first two products of stage A
    s = rep(s, "            ST_MUL2: begin mul_lhs=p1_q; mul_rhs=gamma; end\n", """`ifdef TRUSTEDGE_DEC_STREAM
`ifndef TRUSTEDGE_PMAC_RETIME
            ST_MUL2: begin mul_lhs=secret0; mul_rhs=ntt_ext_rdata_pair[11:0]; end
`endif
`else
            ST_MUL2: begin mul_lhs=p1_q; mul_rhs=gamma; end
`endif
""")
    s = rep(s, "        else if (state == ST_MUL1) begin mul2_lhs = fast_sa; mul2_rhs = fast_sb; end\n",
            """        else if (state == ST_MUL1) begin mul2_lhs = fast_sa; mul2_rhs = fast_sb; end
`ifdef TRUSTEDGE_DEC_STREAM
`ifndef TRUSTEDGE_PMAC_RETIME
        else if (state == ST_MUL2) begin mul2_lhs = secret1; mul2_rhs = ntt_ext_rdata_pair[23:12]; end
`endif
`endif
""")
    # product RAM: one write port (the pipeline), read at stage B for the second polynomial
    s = rep(s, """    always @(posedge clk)
        product_pair_q <= product_pair_ram[pair_index];
""", """`ifdef TRUSTEDGE_DEC_STREAM
    always @(posedge clk) begin
        if (dk_pwr) product_pair_ram[db_j] <= {db_c1, dk_c0};
        product_pair_q <= product_pair_ram[(state == ST_MUL2) ? da_j : pair_index];
    end
`else
    always @(posedge clk)
        product_pair_q <= product_pair_ram[pair_index];
`endif
""")
    s = rep(s, """                        product_pair_ram[pair_index]<={base1,base0};
""", """`ifndef TRUSTEDGE_DEC_STREAM
                        product_pair_ram[pair_index]<={base1,base0};
`endif
""")
    s = rep(s, """    wire product_pair_write = (state == ST_ACCUM) && !poly_index;
    te_sram_1rw #(
        .WIDTH(24), .DEPTH(128), .ADDR_WIDTH(7)
    ) u_product_pair_sram (
        .clk(clk), .we(product_pair_write),
        .addr(pair_index), .wdata({base1, base0}), .rdata(product_pair_q)
    );
""", """`ifdef TRUSTEDGE_DEC_STREAM
    te_sram_1rw #(
        .WIDTH(24), .DEPTH(128), .ADDR_WIDTH(7)
    ) u_product_pair_sram (
        .clk(clk), .we(dk_pwr),
        .addr(dk_pwr ? db_j : (state == ST_MUL2) ? da_j : pair_index),
        .wdata({db_c1, dk_c0}), .rdata(product_pair_q)
    );
`else
    wire product_pair_write = (state == ST_ACCUM) && !poly_index;
    te_sram_1rw #(
        .WIDTH(24), .DEPTH(128), .ADDR_WIDTH(7)
    ) u_product_pair_sram (
        .clk(clk), .we(product_pair_write),
        .addr(pair_index), .wdata({base1, base0}), .rdata(product_pair_q)
    );
`endif
""")
    # the NTT port
    s = rep(s, """    assign ntt_ext_we=(state==ST_U_WRITE)||(state==ST_WRITE0)||
                      (state==ST_WRITE1);
    assign ntt_ext_addr=(state==ST_U_WRITE)?coeff_index:
""", """`ifdef TRUSTEDGE_DEC_STREAM
    assign ntt_ext_we=(state==ST_U_WRITE)||(state==ST_WRITE0)||
                      (state==ST_WRITE1)||dk_wr;
    assign ntt_ext_we_pair = dk_wr;
    assign ntt_ext_wdata_odd = dk_res1;
    assign ntt_ext_addr=(state==ST_U_WRITE)?coeff_index:
                        (state==ST_MUL2)?(dk_wr ? {db_j,1'b0} : {dk_j,1'b0}):
                        (state==ST_MSG_CAP)?(coeff_index+8'd1):
`else
    assign ntt_ext_we=(state==ST_U_WRITE)||(state==ST_WRITE0)||
                      (state==ST_WRITE1);
    assign ntt_ext_addr=(state==ST_U_WRITE)?coeff_index:
`endif
""")
    s = rep(s, """                          (state==ST_WRITE0)?{4'd0,result0_q}:
                          {4'd0,result1_q};
""", """`ifdef TRUSTEDGE_DEC_STREAM
                          dk_wr?{4'd0,dk_res0}:
`endif
                          (state==ST_WRITE0)?{4'd0,result0_q}:
                          {4'd0,result1_q};
""")
    # control: u at one coefficient per cycle
    s = rep(s, "                ST_U_REQ: state<=ST_U_WRITE;    // the NTT takes the decoded word directly\n", """`ifdef TRUSTEDGE_DEC_STREAM
                ST_U_REQ: begin decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_WRITE;end  // one ahead
`else
                ST_U_REQ: state<=ST_U_WRITE;    // the NTT takes the decoded word directly
`endif
""")
    s = rep(s, """                    else begin coeff_index<=coeff_index+1'b1;
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_REQ;end
""", """                    else begin coeff_index<=coeff_index+1'b1;
`ifdef TRUSTEDGE_DEC_STREAM
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_WRITE;end
`else
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_U_REQ;end
`endif
""")
    # control: the pipelined product after each forward transform
    s = rep(s, """                ST_NTT_WAIT: if(ntt_ext_done) begin pair_index<=0;
                    dkpke_ext_pair_addr<={poly_index,7'd0};state<=ST_PAIR_REQ0;end
""", """                ST_NTT_WAIT: if(ntt_ext_done) begin pair_index<=0;
`ifdef TRUSTEDGE_DEC_STREAM
                    dk_t<=9'd0;
                    dkpke_ext_pair_addr<={poly_index,7'd0};state<=ST_MUL2;end
`else
                    dkpke_ext_pair_addr<={poly_index,7'd0};state<=ST_PAIR_REQ0;end
`endif
""")
    s = rep(s, "                ST_MUL2: begin p2_q<=mul_reduced;state<=ST_MUL3;end\n", """`ifdef TRUSTEDGE_DEC_STREAM
                ST_MUL2: begin                    // the pipelined product of one polynomial
                    dk_t<=dk_t+9'd1;
                    if (dk_issue) dkpke_ext_pair_addr<={poly_index,dk_j+7'd1};
                    if (db_v && (db_j==7'd127)) begin
                        if (!poly_index) begin poly_index<=1'b1;
                            coeff_index<=0;decoded_ext_addr<=10'd256;state<=ST_U_REQ;end
                        else state<=ST_INV_START;
                    end
                end
`else
                ST_MUL2: begin p2_q<=mul_reduced;state<=ST_MUL3;end
`endif
""")
    # control: the message at one coefficient per cycle
    s = rep(s, """                ST_MSG_REQ: state<=ST_MSG_CAP;      // one-cycle read latency
""", """`ifdef TRUSTEDGE_DEC_STREAM
                ST_MSG_REQ: begin decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_MSG_CAP;end  // one ahead
`else
                ST_MSG_REQ: state<=ST_MSG_CAP;      // one-cycle read latency
`endif
""")
    s = rep(s, """                    end else begin coeff_index<=coeff_index+1'b1;
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_MSG_REQ;end
""", """                    end else begin coeff_index<=coeff_index+1'b1;
`ifdef TRUSTEDGE_DEC_STREAM
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_MSG_CAP;end
`else
                        decoded_ext_addr<=decoded_ext_addr+1'b1;state<=ST_MSG_REQ;end
`endif
""")
    return s


def dec_stream_top(s: str) -> str:
    """TRUSTEDGE_DEC_STREAM wiring: the decapsulation (owner 4) also writes and reads pairs."""
    s = rep(s, "    wire        mlkem512_encaps_ntt_req_we_pair;\n",
            "    wire        mlkem512_encaps_ntt_req_we_pair;\n"
            "    wire        mlkem512_decaps_ntt_req_we_pair;\n"
            "    wire [11:0] mlkem512_decaps_ntt_req_wdata_odd;\n")
    s = rep(s, "    wire        shared_ntt_we_pair = (shared_ntt_owner == 3'd3) && mlkem512_encaps_ntt_req_we_pair;\n",
            "`ifdef TRUSTEDGE_DEC_STREAM\n"
            "    wire        shared_ntt_we_pair = ((shared_ntt_owner == 3'd3) && mlkem512_encaps_ntt_req_we_pair) ||\n"
            "                                     ((shared_ntt_owner == 3'd4) && mlkem512_decaps_ntt_req_we_pair);\n"
            "`else\n"
            "    wire        shared_ntt_we_pair = (shared_ntt_owner == 3'd3) && mlkem512_encaps_ntt_req_we_pair;\n"
            "`endif\n")
    s = rep(s, "    wire [11:0] shared_ntt_wdata_odd = mlkem512_encaps_ntt_req_wdata_odd;\n",
            "`ifdef TRUSTEDGE_DEC_STREAM\n"
            "    wire [11:0] shared_ntt_wdata_odd = (shared_ntt_owner == 3'd4) ? mlkem512_decaps_ntt_req_wdata_odd :\n"
            "                                       mlkem512_encaps_ntt_req_wdata_odd;\n"
            "`else\n"
            "    wire [11:0] shared_ntt_wdata_odd = mlkem512_encaps_ntt_req_wdata_odd;\n"
            "`endif\n")
    s = rep(s, "        .ntt_ext_wdata(mlkem512_decaps_ntt_req_wdata),\n",
            "        .ntt_ext_wdata(mlkem512_decaps_ntt_req_wdata),\n"
            "`ifdef TRUSTEDGE_DEC_STREAM\n"
            "        .ntt_ext_we_pair(mlkem512_decaps_ntt_req_we_pair),\n"
            "        .ntt_ext_wdata_odd(mlkem512_decaps_ntt_req_wdata_odd),\n"
            "        .ntt_ext_rdata_pair(shared_ntt_rdata_pair),\n"
            "`endif\n")
    return s


def defer_j(s: str) -> str:
    """TRUSTEDGE_DEFER_J (with TRUSTEDGE_HASH_OVERLAP and TRUSTEDGE_FUSED_CMP): during the decryption the
    hash sequencer runs H(ek) and H(c) only (H(c) also copies the received ciphertext into the reference
    RAM). J(z||c) needs only z and that copy, and its result only at the final selection, so it starts in
    the re-encryption once the encryption's five noise-sampling sponge jobs have completed (their done
    pulses are counted), while the encryption no longer uses the sponge; it ends long before the decode
    check reads the reference RAM. The decapsulation then waits for the sequencer before selecting K."""
    s = rep(s, "    output reg        reencrypt_active,\n", """    output reg        reencrypt_active,
`ifdef TRUSTEDGE_DEFER_J
    output wire       hash_active,         // the hash sequencer drives the shared sponge
`endif
""")
    s = rep(s, "    wire [5:0] sp_state = (hstate != ST_IDLE) ? hstate : state;\n",
            """    wire [5:0] sp_state = (hstate != ST_IDLE) ? hstate : state;
`ifdef TRUSTEDGE_DEFER_J
    assign hash_active = (hstate != ST_IDLE);
    reg       j_pending_q;                 // J(z||c) still to run during the re-encryption
    reg [2:0] prf_jobs_q;                  // noise-sampling sponge jobs completed since the re-encryption began
`endif
""")
    s = rep(s, """                        hstate<=ST_HEK_START;hjob_hc_q<=1'b1;hjob_j_q<=1'b1;
""", """`ifdef TRUSTEDGE_DEFER_J
                        hstate<=ST_HEK_START;hjob_hc_q<=1'b1;hjob_j_q<=1'b0;j_pending_q<=1'b1;
`else
                        hstate<=ST_HEK_START;hjob_hc_q<=1'b1;hjob_j_q<=1'b1;
`endif
""")
    s = rep(s, """                    fused_diff_q<=8'd0; fused_count_q<=10'd0;
`endif
                    state<=ST_REENC_WAIT;
""", """                    fused_diff_q<=8'd0; fused_count_q<=10'd0;
`endif
`ifdef TRUSTEDGE_DEFER_J
                    prf_jobs_q<=3'd0;
`endif
                    state<=ST_REENC_WAIT;
""")
    s = rep(s, """                ST_REENC_WAIT: begin
                  if (fused_window && ct_check_byte) begin     // one re-encrypted byte against its reference
""", """                ST_REENC_WAIT: begin
`ifdef TRUSTEDGE_DEFER_J
                  if (j_pending_q && !encaps_mode_q) begin
                    if (sponge_ext_done && (prf_jobs_q != 3'd5)) prf_jobs_q<=prf_jobs_q+3'd1;
                    if ((prf_jobs_q == 3'd5) && (hstate == ST_IDLE)) begin   // the sponge is free again
                      hstate<=ST_J_START; hjob_hc_q<=1'b0; hjob_j_q<=1'b0; j_pending_q<=1'b0;
                    end
                  end
`endif
                  if (fused_window && ct_check_byte) begin     // one re-encrypted byte against its reference
""")
    s = rep(s, """                    ciphertext_match_q<=(fused_diff_q==8'd0);
                    reencrypt_active<=1'b0;
                    state<=ST_HASH_DONE;
""", """                    ciphertext_match_q<=(fused_diff_q==8'd0);
                    reencrypt_active<=1'b0;
`ifdef TRUSTEDGE_DEFER_J
                    state<=ST_HASH_JOIN2;         // J(z||c) has completed by now; one join cycle
`else
                    state<=ST_HASH_DONE;
`endif
""")
    # the reset branch of the controller
    s = rep(s, "            hstate <= ST_IDLE; hjob_hc_q <= 1'b0; hjob_j_q <= 1'b0;\n",
            """            hstate <= ST_IDLE; hjob_hc_q <= 1'b0; hjob_j_q <= 1'b0;
`ifdef TRUSTEDGE_DEFER_J
            j_pending_q <= 1'b0; prf_jobs_q <= 3'd0;
`endif
""")
    return s


def fused_cmp_decaps(s: str) -> str:
    """TRUSTEDGE_FUSED_CMP (with TRUSTEDGE_TIGHT_LOOPS): during the re-encryption, the codec's decode check
    reads the new ciphertext bytes 0..767 in order; the reference copy of the received ciphertext is read
    at the same address, and every checked byte is folded into the difference. When the re-encryption ends
    with all 768 bytes compared, the separate comparison pass is skipped."""
    s = rep(s, "    input  wire [7:0] ciphertext_ext_data,\n", """    input  wire [7:0] ciphertext_ext_data,
`ifdef TRUSTEDGE_FUSED_CMP
    input  wire       ct_check_active,     // the codec's decode check is addressing ct_check_addr
    input  wire       ct_check_byte,       // ciphertext_ext_data is the byte addressed in the last cycle
    input  wire [9:0] ct_check_addr,
`endif
""")
    s = rep(s, "    reg general_runtime_mode_q;\n", """    reg general_runtime_mode_q;
`ifdef TRUSTEDGE_FUSED_CMP
    reg [7:0] fused_diff_q;
    reg [9:0] fused_count_q;
    wire fused_window = (state == ST_REENC_WAIT) && !encaps_mode_q;
`endif
""")
    # the reference RAM follows the codec's address during the re-encryption (ASIC macro and FPGA array)
    s = rep(s, """    wire [9:0] ciphertext_ref_sram_addr = ciphertext_ref_write ? sponge_feed_index :
        (state == ST_CMP_CHECK) ? cmp_ref_next : compare_index;
""", """    wire [9:0] ciphertext_ref_sram_addr = ciphertext_ref_write ? sponge_feed_index :
`ifdef TRUSTEDGE_FUSED_CMP
        (fused_window && ct_check_active) ? ct_check_addr :
`endif
        (state == ST_CMP_CHECK) ? cmp_ref_next : compare_index;
""")
    s = rep(s, """        ciphertext_ref_q <= ciphertext_ref_ram[(state == ST_CMP_CHECK) && (compare_index != 10'd767) ?
                                               compare_index + 10'd1 : compare_index];
""", """`ifdef TRUSTEDGE_FUSED_CMP
        ciphertext_ref_q <= ciphertext_ref_ram[(fused_window && ct_check_active) ? ct_check_addr :
                                               (state == ST_CMP_CHECK) && (compare_index != 10'd767) ?
                                               compare_index + 10'd1 : compare_index];
`else
        ciphertext_ref_q <= ciphertext_ref_ram[(state == ST_CMP_CHECK) && (compare_index != 10'd767) ?
                                               compare_index + 10'd1 : compare_index];
`endif
""")
    s = rep(s, """                    reencrypt_pass_q<=1'b0;
                    state<=ST_REENC_WAIT;
""", """                    reencrypt_pass_q<=1'b0;
`ifdef TRUSTEDGE_FUSED_CMP
                    fused_diff_q<=8'd0; fused_count_q<=10'd0;
`endif
                    state<=ST_REENC_WAIT;
""")
    s = rep(s, """                ST_REENC_WAIT: if(reencrypt_done) begin
                    reencrypt_pass_q<=reencrypt_pass;
""", """`ifdef TRUSTEDGE_FUSED_CMP
                ST_REENC_WAIT: begin
                  if (fused_window && ct_check_byte) begin     // one re-encrypted byte against its reference
                    fused_diff_q<=fused_diff_q | (ciphertext_ref_q ^ ciphertext_ext_data);
                    fused_count_q<=fused_count_q+10'd1;
                  end
                  if(reencrypt_done && !encaps_mode_q && (fused_count_q==10'd768)) begin
                    reencrypt_pass_q<=reencrypt_pass;
                    ciphertext_match_q<=(fused_diff_q==8'd0);
                    reencrypt_active<=1'b0;
                    state<=ST_HASH_DONE;
                  end else if(reencrypt_done) begin
`else
                ST_REENC_WAIT: if(reencrypt_done) begin
`endif
                    reencrypt_pass_q<=reencrypt_pass;
""")
    s = rep(s, """                        compare_index<=10'd0;
                        compare_diff_q<=8'd0;
                        ciphertext_ext_addr<=10'd0;
                        state<=ST_CMP_REQ;
                    end
                end
""", """                        compare_index<=10'd0;
                        compare_diff_q<=8'd0;
                        ciphertext_ext_addr<=10'd0;
                        state<=ST_CMP_REQ;
                    end
                end
`ifdef TRUSTEDGE_FUSED_CMP
                end
`endif
""")
    return s


def edit_decaps(s: str) -> str:
    start = s.index("module mlkem512_decaps_partial_selftest")
    head, s = s[:start], s[start:]
    s = rep(s, "ST_J_FEED=6'd49, ST_J_OUT=6'd50, ST_HASH_DONE=6'd51;",
            "ST_J_FEED=6'd49, ST_J_OUT=6'd50, ST_HASH_DONE=6'd51,\n"
            "        ST_HASH_JOIN=6'd52, ST_HASH_JOIN2=6'd53;")
    s = rep(s, "    reg [5:0] state;\n",
            "    reg [5:0] state;\n"
            "    // Hash sequencer (TRUSTEDGE_HASH_OVERLAP): H(ek), H(c) and J(z||c) depend only on the inputs, so\n"
            "    // they run on hstate while the decryption uses the NTT; hjob_* select the hashes after H(ek).\n"
            "    // The sequencer drives the sponge whenever it is active. Without the define, hstate stays idle.\n"
            "    reg [5:0] hstate;\n"
            "    reg       hjob_hc_q, hjob_j_q;\n"
            "`ifdef TRUSTEDGE_HASH_OVERLAP\n"
            "    wire [5:0] sp_state = (hstate != ST_IDLE) ? hstate : state;\n"
            "`else\n"
            "    wire [5:0] sp_state = state;\n"
            "`endif\n")
    # everything that drives the sponge or the ciphertext reference RAM looks at sp_state
    s = rep(s, "wire ciphertext_ref_write = (state == ST_HC_FEED) &&",
            "wire ciphertext_ref_write = (sp_state == ST_HC_FEED) &&")
    i = s.index("    wire hash_start_state = (state == ST_HEK_START)")
    j = s.index("(state == ST_J_OUT);", i) + len("(state == ST_J_OUT);")
    s = s[:i] + s[i:j].replace("(state == ST_", "(sp_state == ST_") + s[j:]
    # the hash handlers move into a second case statement on `DCP_HS
    i1 = s.index("                ST_HEK_START: begin"); i2 = s.index("                ST_G_START: begin")
    i3 = s.index("                ST_J_START: begin"); i4 = s.index("                ST_REENC_START: begin")
    assert i1 < i2 < i3 < i4
    hand = s[i1:i2] + s[i3:i4]
    s = (s[:i1] + "                // handled by the hash sequencer below\n"
         "                ST_HEK_START, ST_HEK_REQ, ST_HEK_WAIT, ST_HEK_FEED, ST_HEK_OUT,\n"
         "                ST_HC_START, ST_HC_REQ, ST_HC_WAIT, ST_HC_FEED, ST_HC_OUT,\n"
         "                ST_J_START, ST_J_REQ, ST_J_WAIT, ST_J_FEED, ST_J_OUT: ;\n" + s[i2:i3] + s[i4:])
    for a, b in [("state<=encaps_mode_q?ST_G_START:ST_HC_START;", "`DCP_HS<=`DCP_HEK_NEXT;"),
                 ("state<=encaps_mode_q?ST_HASH_DONE:ST_G_START;", "`DCP_HS<=`DCP_HC_NEXT;"),
                 ("if(sponge_ext_done&&sponge_output_complete) state<=ST_REENC_START;",
                  "if(sponge_ext_done&&sponge_output_complete) `DCP_HS<=`DCP_J_NEXT;")]:
        hand = rep(hand, a, b)
    hand = re.sub(r"(?<![A-Za-z_])state\s*<=", "`DCP_HS<=", hand)
    assert not re.search(r"(?<![A-Za-z_`])state\b", hand.replace("`DCP_HS", "")), "state left in handlers"
    s = rep(s, "                default: state <= ST_IDLE;\n            endcase\n",
            "                default: state <= ST_IDLE;\n            endcase\n"
            "            // hash handlers: on hstate with TRUSTEDGE_HASH_OVERLAP, otherwise on state as before\n"
            "            case (`DCP_HS)\n" + hand + "                default: ;\n            endcase\n")
    # main-FSM changes
    s = rep(s, "            general_runtime_mode_q<=1'b0;\n            state <= ST_IDLE;\n",
            "            general_runtime_mode_q<=1'b0;\n            state <= ST_IDLE;\n"
            "            hstate <= ST_IDLE; hjob_hc_q <= 1'b0; hjob_j_q <= 1'b0;\n")
    s = rep(s, "                        reencrypt_active<=1'b0;\n                        state<=ST_HEK_START;\n",
            "                        reencrypt_active<=1'b0;\n"
            "`ifdef TRUSTEDGE_HASH_OVERLAP\n"
            "                        hstate<=ST_HEK_START;hjob_hc_q<=1'b0;hjob_j_q<=1'b0;\n"
            "                        state<=ST_HASH_JOIN;\n"
            "`else\n"
            "                        state<=ST_HEK_START;\n"
            "`endif\n")
    s = rep(s, "                        reencrypt_active<=1'b0;\n                        state<=ST_U_REQ;\n",
            "                        reencrypt_active<=1'b0;\n"
            "`ifdef TRUSTEDGE_HASH_OVERLAP\n"
            "                        hstate<=ST_HEK_START;hjob_hc_q<=1'b1;hjob_j_q<=1'b1;\n"
            "`endif\n"
            "                        state<=ST_U_REQ;\n")
    k = s.index("                    if(coeff_index==8'd255) begin", s.index("ST_MSG_CAP: begin"))
    k2 = s.index("                    end else begin coeff_index<=coeff_index+1'b1;", k)
    blk = s[k:k2]; f = blk.index("\n") + 1
    s = (s[:k] + blk[:f] + "`ifdef TRUSTEDGE_HASH_OVERLAP\n"
         "                        state<=ST_HASH_JOIN;      // the hash sequencer may still be running\n"
         "`else\n" + blk[f:] + "`endif\n" + s[k2:])
    s = rep(s, "                    if(sponge_ext_done&&sponge_output_complete)\n"
               "                        state<=encaps_mode_q?ST_REENC_START:ST_J_START;\n",
            "                    if(sponge_ext_done&&sponge_output_complete)\n"
            "`ifdef TRUSTEDGE_HASH_OVERLAP\n"
            "                        state<=ST_REENC_START;      // J(z||c) is already done\n"
            "`else\n"
            "                        state<=encaps_mode_q?ST_REENC_START:ST_J_START;\n"
            "`endif\n")
    s = rep(s, "                        reencrypt_active<=1'b0;\n                        state<=ST_HC_START;\n",
            "                        reencrypt_active<=1'b0;\n"
            "`ifdef TRUSTEDGE_HASH_OVERLAP\n"
            "                        hstate<=ST_HC_START;hjob_hc_q<=1'b0;hjob_j_q<=1'b0;\n"
            "                        state<=ST_HASH_JOIN2;\n"
            "`else\n"
            "                        state<=ST_HC_START;\n"
            "`endif\n")
    s = rep(s, "                ST_HASH_DONE: begin\n",
            "                ST_HASH_JOIN: if(hstate==ST_IDLE) state<=ST_G_START;\n"
            "                ST_HASH_JOIN2: if(hstate==ST_IDLE) state<=ST_HASH_DONE;\n"
            "                ST_HASH_DONE: begin\n")
    macros = ("`ifdef TRUSTEDGE_HASH_OVERLAP\n`define DCP_HS hstate\n"
              "`define DCP_HEK_NEXT (hjob_hc_q ? ST_HC_START : ST_IDLE)\n"
              "`define DCP_HC_NEXT (hjob_j_q ? ST_J_START : ST_IDLE)\n`define DCP_J_NEXT ST_IDLE\n"
              "`else\n`define DCP_HS state\n"
              "`define DCP_HEK_NEXT (encaps_mode_q ? ST_G_START : ST_HC_START)\n"
              "`define DCP_HC_NEXT (encaps_mode_q ? ST_HASH_DONE : ST_G_START)\n"
              "`define DCP_J_NEXT ST_REENC_START\n`endif\n")
    end = s.index("endmodule")
    s = (macros + s[:end] + "endmodule\n`undef DCP_HS\n`undef DCP_HEK_NEXT\n`undef DCP_HC_NEXT\n"
         "`undef DCP_J_NEXT" + s[end + len("endmodule"):])
    # step D: the decoded-coefficient, key, NTT and ciphertext RAMs all answer one cycle after the address
    # register, which every request state already presents, so the wait states are redundant
    for a in ("ST_U_REQ: state<=ST_U_WAIT;", "ST_PAIR_REQ0: state<=ST_PAIR_WAIT0;",
              "ST_PAIR_REQ1: state<=ST_PAIR_WAIT1;", "ST_MSG_REQ: state<=ST_MSG_WAIT;"):
        req, nxt = a.split(": state<=")
        b = req + ": state<=" + nxt.replace("_WAIT", "_CAP")
        s = rep(s, "                " + a + "\n",
                "`ifdef TRUSTEDGE_STREAM_IO\n                " + b + "      // one-cycle read latency\n"
                "`else\n                " + a + "\n`endif\n")
    s = rep(s, """                ST_CMP_REQ: begin
                    ciphertext_ext_addr<=compare_index;
                    state<=ST_CMP_WAIT;
                end
""", """                ST_CMP_REQ: begin
                    ciphertext_ext_addr<=compare_index;
`ifdef TRUSTEDGE_STREAM_IO
                    state<=ST_CMP_CHECK;      // the address was set with the previous byte
`else
                    state<=ST_CMP_WAIT;
`endif
                end
""")
    s = rep(s, """                    end else begin
                        compare_index<=compare_index+1'b1;
                        state<=ST_CMP_REQ;
                    end
""", """                    end else begin
                        compare_index<=compare_index+1'b1;
`ifdef TRUSTEDGE_STREAM_IO
                        ciphertext_ext_addr<=compare_index+1'b1;
`endif
                        state<=ST_CMP_REQ;
                    end
""")
    s = fast_basemul(s, "ST_", "s0_q", "s1_q", "u0_q", "u1_q", "gamma", "u_dec_reduce")
    s = fast_feed(s)
    s = dec_prefetch(s)
    s = tight_compare(s)
    s = fused_cmp_decaps(s)
    s = defer_j(s)
    s = fast_hash(s)
    s = dec_stream(s)
    s = stream_fwd_dec(s)
    s = stream_dec_inv(s)
    s = poly_guard_dec(s)
    return head + s


def tight_compare(s: str) -> str:
    """TRUSTEDGE_TIGHT_LOOPS in the comparison: the ciphertext address runs two bytes ahead and the
    reference address one byte ahead of the byte being compared, so one byte is compared per cycle."""
    s = rep(s, """    wire [9:0] ciphertext_ref_sram_addr = ciphertext_ref_write ?
        sponge_feed_index : compare_index;
""", """`ifdef TRUSTEDGE_TIGHT_LOOPS
    wire [9:0] cmp_ref_next = (compare_index == 10'd767) ? 10'd767 : compare_index + 10'd1;
    wire [9:0] ciphertext_ref_sram_addr = ciphertext_ref_write ? sponge_feed_index :
        (state == ST_CMP_CHECK) ? cmp_ref_next : compare_index;
`else
    wire [9:0] ciphertext_ref_sram_addr = ciphertext_ref_write ?
        sponge_feed_index : compare_index;
`endif
""")
    s = rep(s, """        ciphertext_ref_q <= ciphertext_ref_ram[compare_index];
""", """`ifdef TRUSTEDGE_TIGHT_LOOPS
        ciphertext_ref_q <= ciphertext_ref_ram[(state == ST_CMP_CHECK) && (compare_index != 10'd767) ?
                                               compare_index + 10'd1 : compare_index];
`else
        ciphertext_ref_q <= ciphertext_ref_ram[compare_index];
`endif
""")
    s = rep(s, """                ST_CMP_REQ: begin
                    ciphertext_ext_addr<=compare_index;
`ifdef TRUSTEDGE_STREAM_IO
""", """                ST_CMP_REQ: begin
`ifdef TRUSTEDGE_TIGHT_LOOPS
                    ciphertext_ext_addr<=compare_index+1'b1;      // presented during the first check
`else
                    ciphertext_ext_addr<=compare_index;
`endif
`ifdef TRUSTEDGE_STREAM_IO
""")
    s = rep(s, """                        compare_index<=compare_index+1'b1;
`ifdef TRUSTEDGE_STREAM_IO
                        ciphertext_ext_addr<=compare_index+1'b1;
`endif
                        state<=ST_CMP_REQ;
""", """                        compare_index<=compare_index+1'b1;
`ifdef TRUSTEDGE_TIGHT_LOOPS
                        ciphertext_ext_addr<=(compare_index==10'd766) ? 10'd767 : compare_index+10'd2;
                        state<=ST_CMP_CHECK;
`else
`ifdef TRUSTEDGE_STREAM_IO
                        ciphertext_ext_addr<=compare_index+1'b1;
`endif
                        state<=ST_CMP_REQ;
`endif
""")
    return s


def dec_prefetch(s: str) -> str:
    """TRUSTEDGE_PREFETCH in the decryption (with TRUSTEDGE_FAST_BASEMUL): while a pair is multiplied, the
    next pair's u0 is addressed in MUL0 and captured after MUL1, its u1 is addressed in MUL1 and captured
    after ACCUM, and its secret pair is addressed from MUL1 and captured after ACCUM; each register is
    overwritten only after its last use, and the result writes of the second polynomial follow the reads."""
    s = rep(s, """                         (state==ST_PAIR_CAP1))?{pair_index,1'b1}:coeff_index;
""", """`ifdef TRUSTEDGE_PREFETCH
                         (state==ST_PAIR_CAP1))?{pair_index,1'b1}:
                        (state==ST_MUL0)?{pair_index+7'd1,1'b0}:
                        (state==ST_MUL1)?{pair_index+7'd1,1'b1}:coeff_index;
`else
                         (state==ST_PAIR_CAP1))?{pair_index,1'b1}:coeff_index;
`endif
""")
    s = rep(s, """`ifdef TRUSTEDGE_FAST_BASEMUL
                ST_MUL0: begin p0_q<=mul_reduced;p1_q<=mul2_reduced;state<=ST_MUL1;end
                ST_MUL1: begin p2_q<=mul_reduced;p3_q<=mul2_reduced;state<=ST_ACCUM;end
""", """`ifdef TRUSTEDGE_FAST_BASEMUL
`ifdef TRUSTEDGE_PREFETCH
                ST_MUL0: begin p0_q<=mul_reduced;p1_q<=mul2_reduced;
                    if(pair_index!=7'd127) dkpke_ext_pair_addr<={poly_index,pair_index+7'd1};
                    state<=ST_MUL1;end
                ST_MUL1: begin p2_q<=mul_reduced;p3_q<=mul2_reduced;
                    if(pair_index!=7'd127) u0_q<=ntt_ext_rdata[11:0];     // the next pair's u0
                    state<=ST_ACCUM;end
`else
                ST_MUL0: begin p0_q<=mul_reduced;p1_q<=mul2_reduced;state<=ST_MUL1;end
                ST_MUL1: begin p2_q<=mul_reduced;p3_q<=mul2_reduced;state<=ST_ACCUM;end
`endif
""")
    s = rep(s, """                        else begin pair_index<=pair_index+1'b1;
                            dkpke_ext_pair_addr<={1'b0,pair_index+1'b1};state<=ST_PAIR_REQ0;end
                    end else begin result0_q<=accum0;result1_q<=accum1;state<=ST_WRITE0;end
""", """`ifdef TRUSTEDGE_PREFETCH
                        else begin pair_index<=pair_index+1'b1;
                            u1_q<=ntt_ext_rdata[11:0];s0_q<=secret0;s1_q<=secret1;state<=ST_MUL0;end
                    end else begin result0_q<=accum0;result1_q<=accum1;
                        if(pair_index!=7'd127) begin u1_q<=ntt_ext_rdata[11:0];s0_q<=secret0;s1_q<=secret1;end
                        state<=ST_WRITE0;end
`else
                        else begin pair_index<=pair_index+1'b1;
                            dkpke_ext_pair_addr<={1'b0,pair_index+1'b1};state<=ST_PAIR_REQ0;end
                    end else begin result0_q<=accum0;result1_q<=accum1;state<=ST_WRITE0;end
`endif
""")
    s = rep(s, """                    else begin pair_index<=pair_index+1'b1;
                        dkpke_ext_pair_addr<={1'b1,pair_index+1'b1};state<=ST_PAIR_REQ0;end
""", """`ifdef TRUSTEDGE_PREFETCH
                    else begin pair_index<=pair_index+1'b1;state<=ST_MUL0;end
`else
                    else begin pair_index<=pair_index+1'b1;
                        dkpke_ext_pair_addr<={1'b1,pair_index+1'b1};state<=ST_PAIR_REQ0;end
`endif
""")
    return s


def fast_feed(s: str) -> str:
    """TRUSTEDGE_FAST_FEED: the three hash loops drop their wait state (the ek, ciphertext and reference
    RAMs answer one cycle after an address that the request state already presents; J sets the reference
    address together with the next byte), and u is written into the NTT straight from the decoded RAM."""
    for h in ("HEK", "HC"):
        s = rep(s, f"                ST_{h}_REQ: `DCP_HS<=ST_{h}_WAIT;\n",
                "`ifdef TRUSTEDGE_FAST_FEED\n"
                f"                ST_{h}_REQ: `DCP_HS<=ST_{h}_FEED;      // one-cycle read latency\n"
                "`else\n"
                f"                ST_{h}_REQ: `DCP_HS<=ST_{h}_WAIT;\n"
                "`endif\n")
    s = rep(s, """                        compare_index<=sponge_feed_index-10'd32;
                    `DCP_HS<=ST_J_WAIT;
""", """                        compare_index<=sponge_feed_index-10'd32;
`ifdef TRUSTEDGE_FAST_FEED
                    `DCP_HS<=ST_J_FEED;      // the reference address was set with the previous byte
`else
                    `DCP_HS<=ST_J_WAIT;
`endif
""")
    s = rep(s, """                        sponge_feed_index<=sponge_feed_index+1'b1;
                        `DCP_HS<=ST_J_REQ;
""", """                        sponge_feed_index<=sponge_feed_index+1'b1;
`ifdef TRUSTEDGE_FAST_FEED
                        if(sponge_feed_index>=10'd31)
                            compare_index<=sponge_feed_index-10'd31;
`endif
                        `DCP_HS<=ST_J_REQ;
""")
    s = rep(s, "                ST_U_REQ: state<=ST_U_CAP;      // one-cycle read latency\n",
            "`ifdef TRUSTEDGE_FAST_FEED\n"
            "                ST_U_REQ: state<=ST_U_WRITE;    // the NTT takes the decoded word directly\n"
            "`else\n"
            "                ST_U_REQ: state<=ST_U_CAP;      // one-cycle read latency\n"
            "`endif\n")
    s = rep(s, "    assign ntt_ext_wdata=(state==ST_U_WRITE)?{4'd0,decoded_q}:\n",
            "`ifdef TRUSTEDGE_FAST_FEED\n"
            "    assign ntt_ext_wdata=(state==ST_U_WRITE)?{4'd0,decoded_ext_data}:\n"
            "`else\n"
            "    assign ntt_ext_wdata=(state==ST_U_WRITE)?{4'd0,decoded_q}:\n"
            "`endif\n")
    return s


def edit_encrypt(s: str) -> str:
    # step D in the encryption: the noise and NTT RAMs answer one cycle after the address
    for a, b in (("S_Y_FETCH: state<=S_Y_WAIT;", "S_Y_FETCH: state<=S_Y_WRITE0;"),
                 ("S_Y_READ_REQ: state<=S_Y_READ_WAIT;", "S_Y_READ_REQ: state<=S_Y_READ_CAP;"),
                 ("S_READ_REQ: state<=S_READ_WAIT;", "S_READ_REQ: state<=S_READ_LOAD;")):
        s = rep(s, "                " + a + "\n",
                "`ifdef TRUSTEDGE_STREAM_IO\n                " + b + "      // one-cycle read latency\n"
                "`else\n                " + a + "\n`endif\n")
    s = fast_basemul(s, "S_", "operand_a0_q", "operand_a1_q", "operand_b0_q", "operand_b1_q", "gamma_q", "u_reduce")
    s = poly_guard_enc(prf_fine_hold(prf_to_ntt(stream_fwd_enc(stream_inv(bg_prf(pipe_mac(pair_port(fast_read(fast_prf(fast_y(tight_writes(prefetch(s)))))))))))))
    s = rep(s, "    wire codec_start=(state==S_CODEC_START);\n", """    wire codec_start=(state==S_CODEC_START);
`ifdef TRUSTEDGE_SEG_CHECK
    // the codec checks u0 and u1 while the next polynomial is computed (TRUSTEDGE_SEG_CHECK)
    wire codec_seg_start=(state==S_READ_LOAD)&&(read_index==8'd255)&&(poly_index!=2'd2);
`endif
""")
    s = rep(s, "        .start(codec_start),.busy(codec_busy),.done(codec_done),.pass(codec_pass),\n",
            """        .start(codec_start),.busy(codec_busy),.done(codec_done),.pass(codec_pass),
`ifdef TRUSTEDGE_SEG_CHECK
        .seg_start(codec_seg_start),
`endif
""")
    s = rep(s, "                S_READ_REQ: state<=S_READ_LOAD;      // one-cycle read latency\n", """`ifdef TRUSTEDGE_SEG_CHECK
                S_READ_REQ: if(!codec_busy) state<=S_READ_LOAD;  // (the codec has paused long before)
`else
                S_READ_REQ: state<=S_READ_LOAD;      // one-cycle read latency
`endif
""")
    s = rep(s, "    output wire [7:0]   ciphertext_read_data,\n", """    output wire [7:0]   ciphertext_read_data,
`ifdef TRUSTEDGE_FUSED_CMP
    output wire         ct_check_active,
    output wire         ct_check_byte,
    output wire [9:0]   ct_check_addr,
`endif
""")
    s = rep(s, "        .ct_read_data(ciphertext_read_data),", """`ifdef TRUSTEDGE_FUSED_CMP
        .ct_check_active(ct_check_active),.ct_check_byte(ct_check_byte),.ct_check_addr(ct_check_addr),
`endif
        .ct_read_data(ciphertext_read_data),""")
    return s


PMAC_DECL = """`ifdef TRUSTEDGE_PIPE_MAC
    // Pipelined matrix-vector product (state S_MUL2, bound runtime key): step k = (pair k[7:1], column k[0])
    // is addressed in cycle k; the operand RAMs answer one cycle later (stage A: a0*b0, a1*b1 and
    // (a0+a1)*(b0+b1)), stage B multiplies a1*b1 by gamma, stage R adds the two columns, and the finished
    // pair is written into the NTT in the next cycle. Four multipliers, one step per cycle.
    reg  [8:0]  mk_t;                      // cycle within the product of one output polynomial
    wire        mk_issuing = (state == S_MUL2) && (mk_t < 9'd256);
    reg         mi_v, mi_c;  reg [6:0] mi_p;                          // step addressed in the last cycle
    reg         ma_v, ma_c;  reg [6:0] ma_p;  reg [11:0] ma_p0, ma_p1, ma_p3, ma_g;
    reg         mb_v, mb_c;  reg [6:0] mb_p;  reg [11:0] mb_p0, mb_t, mb_c1;
    reg         mr_v;        reg [6:0] mr_p;  reg [11:0] mr_r0, mr_r1, macc0, macc1;
    wire        pmac_wr = (state == S_MUL2) && mr_v;               // a finished pair goes to the NTT
`endif
"""

PMAC_DATAPATH = """`ifdef TRUSTEDGE_PIPE_MAC
    // stage A (operands straight from the RAM outputs; the first two products use the existing pair of
    // multipliers in this state, the third and the gamma product are the two added ones). S_MUL2 is entered
    // with a bound runtime key only (pf_on), so the operands are the key RAM outputs themselves and the KAT
    // operand functions stay off the multiplier paths.
    wire [11:0] pm_sa = add_mod_q(key_operand_a0, key_operand_a1);
    wire [11:0] pm_sb = add_mod_q(noise_even_q, noise_odd_q);
    wire [23:0] pm_prod3 = pm_sa * pm_sb;
    wire [11:0] pm_red3;
    barrett_reduce u_reduce3(.a(pm_prod3), .r(pm_red3));
    wire [6:0]  pm_gidx = 7'd64 + {1'b0, mi_p[6:1]};
    wire [15:0] pm_gfull = kyber_zeta(pm_gidx);
    wire [11:0] pm_gamma = mi_p[0] ? (12'd3329 - pm_gfull[11:0]) : pm_gfull[11:0];
`ifdef TRUSTEDGE_PMAC_RETIME
    // stage A is four dedicated multipliers on the RAM outputs: a macro read, which arrives half a cycle
    // after the edge, reaches the unreduced products through one multiplier and nothing else, and stage B,
    // which starts at a register, reduces them. The odd product is a0 b1 + a1 b0, so no adder precedes a
    // multiplier, and the shared multipliers keep register operands only.
    wire [23:0] rt_p00 = key_operand_a0 * noise_even_q;
    wire [23:0] rt_p11 = key_operand_a1 * noise_odd_q;
    wire [23:0] rt_p01 = key_operand_a0 * noise_odd_q;
    wire [23:0] rt_p10 = key_operand_a1 * noise_even_q;
    reg  [23:0] ma_r0, ma_r1, ma_r2, ma_r3;
    wire [11:0] rp0, rp1, rp2, rp3;
    barrett_reduce u_rt_reduce0(.a(ma_r0), .r(rp0));
    barrett_reduce u_rt_reduce1(.a(ma_r1), .r(rp1));
    barrett_reduce u_rt_reduce2(.a(ma_r2), .r(rp2));
    barrett_reduce u_rt_reduce3(.a(ma_r3), .r(rp3));
    wire [11:0] pm_odd = add_mod_q(rp2, rp3);
`else
    wire [11:0] rp0 = ma_p0, rp1 = ma_p1, rp3 = ma_p3;
    wire [11:0] pm_odd = sub_mod_q(sub_mod_q(rp3, rp0), rp1);
`endif
    // stage B
    wire [23:0] pm_prod4 = rp1 * ma_g;
    wire [11:0] pm_red4;
    barrett_reduce u_reduce4(.a(pm_prod4), .r(pm_red4));
    // stage R
    wire [11:0] pm_c0 = add_mod_q(mb_p0, mb_t);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mi_v <= 1'b0; ma_v <= 1'b0; mb_v <= 1'b0; mr_v <= 1'b0;
            mi_c <= 1'b0; mi_p <= 7'd0; ma_c <= 1'b0; ma_p <= 7'd0; mb_c <= 1'b0; mb_p <= 7'd0; mr_p <= 7'd0;
            ma_p0 <= 12'd0; ma_p1 <= 12'd0; ma_p3 <= 12'd0; ma_g <= 12'd0;
            mb_p0 <= 12'd0; mb_t <= 12'd0; mb_c1 <= 12'd0;
            mr_r0 <= 12'd0; mr_r1 <= 12'd0; macc0 <= 12'd0; macc1 <= 12'd0;
        end else begin
            mi_v <= mk_issuing; mi_c <= mk_t[0]; mi_p <= mk_t[7:1];
            ma_v <= mi_v; ma_c <= mi_c; ma_p <= mi_p;
            ma_p0 <= mul_reduced; ma_p1 <= mul2_reduced; ma_p3 <= pm_red3; ma_g <= pm_gamma;
`ifdef TRUSTEDGE_PMAC_RETIME
            ma_r0 <= rt_p00; ma_r1 <= rt_p11; ma_r2 <= rt_p01; ma_r3 <= rt_p10;
`endif
            mb_v <= ma_v; mb_c <= ma_c; mb_p <= ma_p;
            mb_p0 <= rp0; mb_t <= pm_red4; mb_c1 <= pm_odd;
            mr_v <= mb_v && mb_c;
            mr_p <= mb_p;
            if (mb_v && !mb_c) begin macc0 <= pm_c0; macc1 <= mb_c1; end
            if (mb_v && mb_c) begin mr_r0 <= add_mod_q(macc0, pm_c0); mr_r1 <= add_mod_q(macc1, mb_c1); end
        end
    end
`endif
"""


def stream_inv(s: str) -> str:
    """TRUSTEDGE_STREAM_INV (with TRUSTEDGE_PIPE_MAC): the inverse transform of each output polynomial is
    started in stream mode one cycle before its pipelined product, whose pairs (in word order, one every
    second cycle) enter the transform's first pass directly; when the last pair is written, only the rest
    of the transform remains."""
    s = rep(s, "    output wire [11:0]  ntt_ext_wdata_odd,\n", """    output wire [11:0]  ntt_ext_wdata_odd,
`ifdef TRUSTEDGE_STREAM_INV
    output wire         ntt_ext_stream,
`endif
""")
    s = rep(s, "    wire ntt_start=(state==S_INV_START)||(state==S_Y_NTT_START);\n", """`ifdef TRUSTEDGE_STREAM_INV
    wire pmac_stream_start = (state==S_PAIR_INIT) && pf_on && pair_on;
    wire ntt_start=(state==S_INV_START)||(state==S_Y_NTT_START)||pmac_stream_start;
`else
    wire ntt_start=(state==S_INV_START)||(state==S_Y_NTT_START);
`endif
""")
    s = rep(s, "    assign ntt_ext_inverse=(state==S_INV_START);\n", """`ifdef TRUSTEDGE_STREAM_INV
    assign ntt_ext_inverse=(state==S_INV_START)||pmac_stream_start;
    assign ntt_ext_stream=pmac_stream_start;
`else
    assign ntt_ext_inverse=(state==S_INV_START);
`endif
""")
    s = rep(s, "                    if (mr_v && (mr_p==7'd127)) state<=S_INV_START;\n", """`ifdef TRUSTEDGE_STREAM_INV
                    if (mr_v && (mr_p==7'd127)) state<=S_INV_WAIT;   // the transform is already running
`else
                    if (mr_v && (mr_p==7'd127)) state<=S_INV_START;
`endif
""")
    return s


def bg_prf(s: str) -> str:
    """TRUSTEDGE_BG_PRF (with TRUSTEDGE_FAST_PRF): the encryption waits for r0 and r1 only. e1[0], e1[1] and
    e2 are needed first when u0 is read out, so the sampler finishes them in the background; it is frozen
    (no sponge handshake, no noise-RAM write) whenever the encryption itself uses the noise RAM, which
    leaves it the NTT waits of the y path. Its pass flag is taken whenever it completes; reading u0 out
    waits for it, a guard the fixed schedule never exercises."""
    # sampler: hold input, r_done output, everything frozen while held
    s = rep(s, "    input  wire [255:0] coins,\n", """    input  wire [255:0] coins,
`ifdef TRUSTEDGE_BG_PRF
    input  wire         hold,               // the encryption uses the noise RAM: no progress
    output wire         r_done,             // r0 and r1 are complete
`endif
""")
    s = rep(s, "    wire sponge_in_valid = (state == P_RUN) && (feed_index < 6'd33);\n", """`ifdef TRUSTEDGE_BG_PRF
    wire prf_held = hold && busy && (poly_index >= 3'd2);
    assign r_done = busy && (poly_index >= 3'd2);
    wire sponge_in_valid = (state == P_RUN) && (feed_index < 6'd33) && !prf_held;
`else
    wire prf_held = 1'b0;
    wire sponge_in_valid = (state == P_RUN) && (feed_index < 6'd33);
`endif
""")
    s = rep(s, "    assign sponge_ext_out_ready = (state == P_RUN);\n",
            "    assign sponge_ext_out_ready = (state == P_RUN) && !prf_held;\n")
    s = rep(s, "                .out_ready(state == P_RUN), .busy(), .done(sponge_done),\n",
            "                .out_ready((state == P_RUN) && !prf_held), .busy(), .done(sponge_done),\n")
    s = rep(s, """            if (busy && cycles != 16'hFFFF)
                cycles <= cycles + 16'd1;
            case (state)
                P_IDLE: begin
""", """            if (busy && cycles != 16'hFFFF)
                cycles <= cycles + 16'd1;
            if (!prf_held)
            case (state)
                P_IDLE: begin
""")
    # encryption controller
    s = rep(s, "        .busy(),.done(prf_done),.pass(prf_pass),\n", """        .busy(),.done(prf_done),.pass(prf_pass),
`ifdef TRUSTEDGE_BG_PRF
        .hold(prf_hold),.r_done(prf_r_done),
`endif
""")
    s = rep(s, "    wire prf_start=(state==S_PRF_START);\n", """    wire prf_start=(state==S_PRF_START);
`ifdef TRUSTEDGE_BG_PRF
    // the sampler may write the noise RAM only while the encryption leaves it alone
    wire prf_hold = !((state==S_PRF_START)||(state==S_PRF_WAIT)||(state==S_Y_NTT_START)||
                      (state==S_Y_NTT_WAIT)||(state==S_INV_START)||(state==S_INV_WAIT));
    wire prf_r_done;
    reg  prf_bg_done_q;
    reg  inv_seen_q;                         // the inverse transform has ended (S_INV_WAIT)
`endif
""")
    s = rep(s, """                S_PRF_WAIT: if(prf_done) begin runtime_prf_ok_q<=prf_pass;
                    y_poly<=0;y_pair<=0;state<=prf_pass?S_Y_FETCH:S_CODEC_WAIT; end
""", """`ifdef TRUSTEDGE_BG_PRF
                S_PRF_WAIT: if(prf_r_done) begin        // e1 and e2 follow in the background
                    y_poly<=0;y_pair<=0;state<=S_Y_FETCH; end
`else
                S_PRF_WAIT: if(prf_done) begin runtime_prf_ok_q<=prf_pass;
                    y_poly<=0;y_pair<=0;state<=prf_pass?S_Y_FETCH:S_CODEC_WAIT; end
`endif
""")
    s = rep(s, "                S_INV_WAIT: if(ntt_done) begin read_index<=0;state<=S_READ_REQ;end\n", """`ifdef TRUSTEDGE_BG_PRF
                S_INV_WAIT: begin                   // the transform's done pulse is kept until the
                    if (ntt_done) inv_seen_q<=1'b1;     // sampler has finished as well
                    if ((ntt_done || inv_seen_q) && (prf_bg_done_q || !runtime_valid_q)) begin
                        inv_seen_q<=1'b0; read_index<=0; state<=S_READ_REQ; end
                end
`else
                S_INV_WAIT: if(ntt_done) begin read_index<=0;state<=S_READ_REQ;end
`endif
""")
    # the sampler's completion is taken in any state (before the case, so a state's own assignment wins)
    s = rep(s, "            runtime_prf_ok_q<=0;operand_wait_q<=0;\n", """            runtime_prf_ok_q<=0;operand_wait_q<=0;
`ifdef TRUSTEDGE_BG_PRF
            prf_bg_done_q<=1'b0; inv_seen_q<=1'b0;
`endif
""")
    s = rep(s, "            if(busy&&cycles!=16'hFFFF) cycles<=cycles+16'd1;\n            case(state)\n",
            """            if(busy&&cycles!=16'hFFFF) cycles<=cycles+16'd1;
`ifdef TRUSTEDGE_BG_PRF
            if (prf_done) begin runtime_prf_ok_q<=prf_pass; prf_bg_done_q<=1'b1; end
`endif
            case(state)
""")
    s = rep(s, "                S_PRF_START: state<=S_PRF_WAIT;\n", """`ifdef TRUSTEDGE_BG_PRF
                S_PRF_START: begin prf_bg_done_q<=1'b0; state<=S_PRF_WAIT; end
`else
                S_PRF_START: state<=S_PRF_WAIT;
`endif
""")
    return s


def pipe_mac(s: str) -> str:
    """TRUSTEDGE_PIPE_MAC (with TRUSTEDGE_FAST_BASEMUL, TRUSTEDGE_PREFETCH and TRUSTEDGE_PAIR_PORT): with a
    bound runtime key, every output polynomial's product runs as a four-multiplier pipeline at one
    pair-column per cycle. The operand RAMs (KeyGen matrix and ekPKE, imported key, noise) all answer one
    cycle after their address, so step k is addressed in cycle k and the 256 steps take 260 cycles; the
    finished pairs are written into the NTT a pair at a time."""
    s = rep(s, "    reg operand_wait_q;\n", "    reg operand_wait_q;\n" + PMAC_DECL)
    # operand addresses of the addressed step
    s = rep(s, """    assign matrix_ext_pair_addr = pf_window ? {pf_col, poly_index[0], pf_pair} :
                                              {column_index, poly_index[0], pair_index};
    assign ekpke_ext_pair_addr = pf_window ? {pf_col, pf_pair} : {column_index, pair_index};
""", """`ifdef TRUSTEDGE_PIPE_MAC
    assign matrix_ext_pair_addr = mk_issuing ? {mk_t[0], poly_index[0], mk_t[7:1]} :
                                  pf_window ? {pf_col, poly_index[0], pf_pair} :
                                              {column_index, poly_index[0], pair_index};
    assign ekpke_ext_pair_addr = mk_issuing ? {mk_t[0], mk_t[7:1]} :
                                 pf_window ? {pf_col, pf_pair} : {column_index, pair_index};
`else
    assign matrix_ext_pair_addr = pf_window ? {pf_col, poly_index[0], pf_pair} :
                                              {column_index, poly_index[0], pair_index};
    assign ekpke_ext_pair_addr = pf_window ? {pf_col, pf_pair} : {column_index, pair_index};
`endif
""")
    s = rep(s, "        else if ((state==S_READ_REQ)||(state==S_READ_WAIT)||(state==S_READ_LOAD))\n",
            """`ifdef TRUSTEDGE_PIPE_MAC
        else if (state==S_MUL2)
            noise_read_addr = ({9'd0, mk_t[0]} * 10'd128) + {3'd0, mk_t[7:1]};
`endif
        else if ((state==S_READ_REQ)||(state==S_READ_WAIT)||(state==S_READ_LOAD))
""")
    # the existing two multipliers take the first two products of stage A
    s = rep(s, "            S_MUL2: begin mul_lhs=p1_q; mul_rhs=gamma_q; end\n", """`ifdef TRUSTEDGE_PIPE_MAC
`ifndef TRUSTEDGE_PMAC_RETIME
            S_MUL2: begin mul_lhs=key_operand_a0; mul_rhs=noise_even_q; end   // bound key only
`endif
`else
            S_MUL2: begin mul_lhs=p1_q; mul_rhs=gamma_q; end
`endif
""")
    s = rep(s, "        else if (state == S_MUL1) begin mul2_lhs = fast_sa; mul2_rhs = fast_sb; end\n",
            """        else if (state == S_MUL1) begin mul2_lhs = fast_sa; mul2_rhs = fast_sb; end
`ifdef TRUSTEDGE_PIPE_MAC
`ifndef TRUSTEDGE_PMAC_RETIME
        else if (state == S_MUL2) begin mul2_lhs = key_operand_a1; mul2_rhs = noise_odd_q; end   // bound key only
`endif
`endif
""")
    s = rep(s, "    wire [11:0] base1 = sub_mod_q(sub_mod_q(p3_q, p0_q), p1_q);\n",
            "    wire [11:0] base1 = sub_mod_q(sub_mod_q(p3_q, p0_q), p1_q);\n" + PMAC_DATAPATH)
    # the NTT port: one pair per finished step pair
    s = rep(s, "    wire ntt_we=y_ntt_write||data_ntt_write;\n", """`ifdef TRUSTEDGE_PIPE_MAC
    wire ntt_we=y_ntt_write||data_ntt_write||pmac_wr;
`else
    wire ntt_we=y_ntt_write||data_ntt_write;
`endif
""")
    s = rep(s, """    wire [7:0] ntt_addr = y_ntt_write ?
        ((state==S_Y_WRITE0)?{y_pair,1'b0}:{y_pair,1'b1}) :
""", """    wire [7:0] ntt_addr = y_ntt_write ?
        ((state==S_Y_WRITE0)?{y_pair,1'b0}:{y_pair,1'b1}) :
`ifdef TRUSTEDGE_PIPE_MAC
        pmac_wr ? {mr_p,1'b0} :
`endif
""")
    s = rep(s, """    wire [15:0] ntt_wdata = y_ntt_write ?
        ((state==S_Y_WRITE0)?{4'd0,noise_even_q}:{4'd0,noise_odd_q}) :
""", """    wire [15:0] ntt_wdata = y_ntt_write ?
        ((state==S_Y_WRITE0)?{4'd0,noise_even_q}:{4'd0,noise_odd_q}) :
`ifdef TRUSTEDGE_PIPE_MAC
        pmac_wr ? {4'd0,mr_r0} :
`endif
""")
    s = rep(s, """    assign ntt_ext_we_pair = pair_on && (state==S_Y_WRITE0);   // with ntt_wdata = noise_even_q
    assign ntt_ext_wdata_odd = noise_odd_q;
""", """`ifdef TRUSTEDGE_PIPE_MAC
    assign ntt_ext_we_pair = pair_on && ((state==S_Y_WRITE0) || pmac_wr);
    assign ntt_ext_wdata_odd = pmac_wr ? mr_r1 : noise_odd_q;
`else
    assign ntt_ext_we_pair = pair_on && (state==S_Y_WRITE0);   // with ntt_wdata = noise_even_q
    assign ntt_ext_wdata_odd = noise_odd_q;
`endif
""")
    # control
    s = rep(s, """                    operand_wait_q<=runtime_key_bound_q;
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end
                // Runtime PRF RAM already needed one wait state.""", """                    operand_wait_q<=runtime_key_bound_q;
`ifdef TRUSTEDGE_PIPE_MAC
                    mk_t<=9'd0;
                    if (pf_on && pair_on) state<=S_MUL2; else
`endif
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end
                // Runtime PRF RAM already needed one wait state.""")
    s = rep(s, "                S_MUL2: begin p2_q<=mul_reduced;state<=S_MUL3;end\n", """`ifdef TRUSTEDGE_PIPE_MAC
                S_MUL2: begin                    // the pipelined product; the last pair is written now
                    mk_t<=mk_t+9'd1;
                    if (mr_v && (mr_p==7'd127)) state<=S_INV_START;
                end
`else
                S_MUL2: begin p2_q<=mul_reduced;state<=S_MUL3;end
`endif
""")
    return s


def pair_port(s: str) -> str:
    """TRUSTEDGE_PAIR_PORT (with TRUSTEDGE_FAST_Y and an external packed2 engine): r enters the NTT one
    pair per cycle (both parity RAMs are read together), and y-hat returns one pair per cycle into both
    parity RAMs."""
    s = rep(s, "    input  wire [15:0]  ntt_ext_rdata,\n", """    input  wire [15:0]  ntt_ext_rdata,
`ifdef TRUSTEDGE_PAIR_PORT
    output wire         ntt_ext_we_pair,
    output wire [11:0]  ntt_ext_wdata_odd,
    input  wire [23:0]  ntt_ext_rdata_pair,
`endif
""")
    s = rep(s, "            noise_read_addr = ((state==S_Y_WRITE1) && (y_pair!=7'd127)) ? {2'd0,y_poly,y_pair+7'd1} :\n",
            """`ifdef TRUSTEDGE_PAIR_PORT
            noise_read_addr = (((state==S_Y_WRITE1) || (pair_on && (state==S_Y_WRITE0))) && (y_pair!=7'd127)) ?
                                                                       {2'd0,y_poly,y_pair+7'd1} :
`else
            noise_read_addr = ((state==S_Y_WRITE1) && (y_pair!=7'd127)) ? {2'd0,y_poly,y_pair+7'd1} :
`endif
""")
    s = rep(s, "    wire y_phase = (state==S_Y_FETCH)||(state==S_Y_WAIT)||\n", """`ifdef TRUSTEDGE_PAIR_PORT
    wire pair_on = USE_EXTERNAL_NTT;            // the shared packed2 engine takes and returns whole pairs
    wire [7:0] y_last = pair_on ? 8'd254 : 8'd255;
    wire [7:0] y_step = pair_on ? 8'd2 : 8'd1;
`endif
    wire y_phase = (state==S_Y_FETCH)||(state==S_Y_WAIT)||
""")
    # FPGA arrays: both halves of the returned pair
    s = rep(s, """        end else if (state==S_Y_READ_CAP) begin
            if (y_read_index[0])
                noise_odd_ram[{2'd0,y_poly,y_read_index[7:1]}] <= ntt_rdata[11:0];
            else
                noise_even_ram[{2'd0,y_poly,y_read_index[7:1]}] <= ntt_rdata[11:0];
        end
""", """        end else if (state==S_Y_READ_CAP) begin
`ifdef TRUSTEDGE_PAIR_PORT
            if (pair_on) begin
                noise_even_ram[{2'd0,y_poly,y_read_index[7:1]}] <= ntt_ext_rdata_pair[11:0];
                noise_odd_ram[{2'd0,y_poly,y_read_index[7:1]}] <= ntt_ext_rdata_pair[23:12];
            end else
`endif
            if (y_read_index[0])
                noise_odd_ram[{2'd0,y_poly,y_read_index[7:1]}] <= ntt_rdata[11:0];
            else
                noise_even_ram[{2'd0,y_poly,y_read_index[7:1]}] <= ntt_rdata[11:0];
        end
""")
    # ASIC macros
    s = rep(s, """    wire noise_even_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && !y_read_index[0]);
    wire noise_odd_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && y_read_index[0]);
""", """`ifdef TRUSTEDGE_PAIR_PORT
    wire noise_even_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && (pair_on || !y_read_index[0]));
    wire noise_odd_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && (pair_on || y_read_index[0]));
`else
    wire noise_even_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && !y_read_index[0]);
    wire noise_odd_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && y_read_index[0]);
`endif
""")
    s = rep(s, """            .wdata(prf_coeff_valid ? prf_coeff_data_odd : noise_mem_wdata), .rdata(noise_odd_q)
""", """`ifdef TRUSTEDGE_PAIR_PORT
            .wdata(prf_coeff_valid ? prf_coeff_data_odd :
                   pair_on ? ntt_ext_rdata_pair[23:12] : noise_mem_wdata), .rdata(noise_odd_q)
`else
            .wdata(prf_coeff_valid ? prf_coeff_data_odd : noise_mem_wdata), .rdata(noise_odd_q)
`endif
""")
    # NTT port: the read-back address advances by a pair
    s = rep(s, """            (((state==S_Y_READ_CAP) && (y_read_index!=8'd255)) ? y_read_index+8'd1 : y_read_index) :
""", """`ifdef TRUSTEDGE_PAIR_PORT
            (((state==S_Y_READ_CAP) && (y_read_index!=y_last)) ? y_read_index+y_step : y_read_index) :
`else
            (((state==S_Y_READ_CAP) && (y_read_index!=8'd255)) ? y_read_index+8'd1 : y_read_index) :
`endif
""")
    s = rep(s, "    assign ntt_ext_wdata=ntt_wdata;\n", """    assign ntt_ext_wdata=ntt_wdata;
`ifdef TRUSTEDGE_PAIR_PORT
    assign ntt_ext_we_pair = pair_on && (state==S_Y_WRITE0);   // with ntt_wdata = noise_even_q
    assign ntt_ext_wdata_odd = noise_odd_q;
`endif
""")
    # control
    s = rep(s, "                S_Y_WRITE0: state<=S_Y_WRITE1;\n", """`ifdef TRUSTEDGE_PAIR_PORT
                S_Y_WRITE0: if (pair_on) begin               // the whole pair was written
                    if (y_pair==127) state<=S_Y_NTT_START;
                    else begin y_pair<=y_pair+1'b1; state<=S_Y_WRITE0; end
                end else state<=S_Y_WRITE1;
`else
                S_Y_WRITE0: state<=S_Y_WRITE1;
`endif
""")
    s = rep(s, "                S_Y_READ_CAP: begin if(y_read_index==255) state<=S_Y_NEXT;\n", """`ifdef TRUSTEDGE_PAIR_PORT
                S_Y_READ_CAP: begin if(y_read_index==y_last) state<=S_Y_NEXT;
`else
                S_Y_READ_CAP: begin if(y_read_index==255) state<=S_Y_NEXT;
`endif
""")
    s = rep(s, "                    else begin y_read_index<=y_read_index+1'b1;state<=S_Y_READ_CAP;end end\n", """`ifdef TRUSTEDGE_PAIR_PORT
                    else begin y_read_index<=y_read_index+y_step;state<=S_Y_READ_CAP;end end
`else
                    else begin y_read_index<=y_read_index+1'b1;state<=S_Y_READ_CAP;end end
`endif
""")
    return s


def fast_read(s: str) -> str:
    """TRUSTEDGE_FAST_READ (with TRUSTEDGE_STREAM_IO and TRUSTEDGE_STREAM_OUT): reading the results into the
    codec, the NTT and noise addresses of the next coefficient are presented in the load state, so one
    coefficient enters the codec per cycle. In the two U polynomials, every fourth coefficient is followed by
    one request state: the codec writes a packed group as five bytes, one per cycle, so a group of four
    coefficients may arrive no faster than every five cycles."""
    s = rep(s, "            noise_read_addr=(({1'b0,poly_index}+3'd2)*10'd128)+read_index[7:1];\n",
            """`ifdef TRUSTEDGE_FAST_READ
            noise_read_addr=(({1'b0,poly_index}+3'd2)*10'd128)+read_next[7:1];
`else
            noise_read_addr=(({1'b0,poly_index}+3'd2)*10'd128)+read_index[7:1];
`endif
""")
    s = rep(s, "        (state==S_NTT_WRITE1)?coeff_index1:read_index;\n", """`ifdef TRUSTEDGE_FAST_READ
        (state==S_NTT_WRITE1)?coeff_index1:read_next;
`else
        (state==S_NTT_WRITE1)?coeff_index1:read_index;
`endif
""")
    s = rep(s, "    reg [7:0] read_index;\n", """    reg [7:0] read_index;
`ifdef TRUSTEDGE_FAST_READ
    // the coefficient addressed in this cycle: the next one while loading (a request state that follows
    // a group presents it again); the U polynomials pause after every group of four
    wire read_gap = (poly_index != 2'd2) && (read_index[1:0] == 2'd3);
    wire [7:0] read_next = (state==S_READ_LOAD) ? read_index + 8'd1 : read_index;
`endif
""")
    s = rep(s, "                    else begin read_index<=read_index+1'b1;state<=S_READ_REQ;end end\n", """`ifdef TRUSTEDGE_FAST_READ
                    else begin read_index<=read_index+1'b1;state<=read_gap?S_READ_REQ:S_READ_LOAD;end end
`else
                    else begin read_index<=read_index+1'b1;state<=S_READ_REQ;end end
`endif
""")
    return s


def fast_prf(s: str) -> str:
    """TRUSTEDGE_FAST_PRF: the noise sampler keeps the sponge streaming while it emits a finished CBD block,
    two coefficients (an even/odd pair) per cycle into the two parity RAMs. An eta1 block (3 bytes, 4
    coefficients) is emitted in 2 cycles and an eta2 block (4 bytes, 8 coefficients) in 4, never slower than
    the next block arrives, so only the last block of each polynomial adds cycles."""
    s = rep(s, "    output reg [11:0]   coeff_data,\n", """    output reg [11:0]   coeff_data,
`ifdef TRUSTEDGE_FAST_PRF
    output reg [11:0]   coeff_data_odd,     // with coeff_valid: the odd partner of coeff_data (even address)
`endif
""")
    s = rep(s, "    reg sponge_done_seen;\n", """    reg sponge_done_seen;
`ifdef TRUSTEDGE_FAST_PRF
    reg [2:0] emit_left;                    // coefficient pairs of block_q still to emit
    reg [1:0] emit_sub;                     // next pair within block_q
`endif
""")
    s = rep(s, "    assign sponge_ext_out_ready = (state == P_RUN);\n", """    assign sponge_ext_out_ready = (state == P_RUN);
`ifdef TRUSTEDGE_FAST_PRF
    wire emit_last_pair = (coeff_index == 9'd254);
`endif
""")
    s = rep(s, """            coeff_data <= 12'd0;
            prf_digest <= 32'd0;
""", """            coeff_data <= 12'd0;
`ifdef TRUSTEDGE_FAST_PRF
            coeff_data_odd <= 12'd0;
            emit_left <= 3'd0;
            emit_sub <= 2'd0;
`endif
            prf_digest <= 32'd0;
""")
    s = rep(s, """                    word_q <= 32'd0;
                    sponge_done_seen <= 1'b0;
                    sponge_start <= 1'b1;
                    state <= P_RUN;
""", """                    word_q <= 32'd0;
                    sponge_done_seen <= 1'b0;
                    sponge_start <= 1'b1;
`ifdef TRUSTEDGE_FAST_PRF
                    emit_left <= 3'd0;
`endif
                    state <= P_RUN;
""")
    s = rep(s, """                P_RUN: begin
                    if (sponge_in_valid && sponge_in_ready)
                        feed_index <= feed_index + 6'd1;
                    if (sponge_out_valid) begin
                        prf_digest <= digest_step(prf_digest, sponge_out_byte);
                        word_q <= word_with_byte;
                        if (block_byte == last_block_byte) begin
                            block_q <= word_with_byte;
                            word_q <= 32'd0;
                            block_byte <= 3'd0;
                            state <= P_EMIT;
                        end else begin
                            block_byte <= block_byte + 3'd1;
                        end
                    end
                end
""", """                P_RUN: begin
                    if (sponge_in_valid && sponge_in_ready)
                        feed_index <= feed_index + 6'd1;
`ifdef TRUSTEDGE_FAST_PRF
                    // emit one pair of the finished block per cycle while the next block streams in
                    if (emit_left != 3'd0) begin
                        coeff_valid <= 1'b1;
                        coeff_addr <= (poly_index * 11'd256) + coeff_index;
                        coeff_data <= eta1_poly ? cbd3_coeff[{emit_sub[0], 1'b0}][11:0] :
                                                  cbd2_coeff[{emit_sub, 1'b0}][11:0];
                        coeff_data_odd <= eta1_poly ? cbd3_coeff[{emit_sub[0], 1'b1}][11:0] :
                                                      cbd2_coeff[{emit_sub, 1'b1}][11:0];
                        emit_left <= emit_left - 3'd1;
                        emit_sub <= emit_sub + 2'd1;
                        if (emit_last_pair) begin
                            coeff_index <= 9'd255;    // all 256 coefficients emitted
                            state <= P_WAIT;
                        end else
                            coeff_index <= coeff_index + 9'd2;
                    end
                    if (sponge_out_valid) begin
                        prf_digest <= digest_step(prf_digest, sponge_out_byte);
                        word_q <= word_with_byte;
                        if (block_byte == last_block_byte) begin
                            block_q <= word_with_byte;
                            word_q <= 32'd0;
                            block_byte <= 3'd0;
                            emit_left <= eta1_poly ? 3'd2 : 3'd4;
                            emit_sub <= 2'd0;
                        end else begin
                            block_byte <= block_byte + 3'd1;
                        end
                    end
`else
                    if (sponge_out_valid) begin
                        prf_digest <= digest_step(prf_digest, sponge_out_byte);
                        word_q <= word_with_byte;
                        if (block_byte == last_block_byte) begin
                            block_q <= word_with_byte;
                            word_q <= 32'd0;
                            block_byte <= 3'd0;
                            state <= P_EMIT;
                        end else begin
                            block_byte <= block_byte + 3'd1;
                        end
                    end
`endif
                end
""")
    # the encryption controller: both parity RAMs take a pair in the same cycle
    s = rep(s, "    wire [11:0] prf_coeff_data;\n", """    wire [11:0] prf_coeff_data;
`ifdef TRUSTEDGE_FAST_PRF
    wire [11:0] prf_coeff_data_odd;
`endif
""")
    s = rep(s, "        .coeff_data(prf_coeff_data),.prf_digest(prf_digest),.cycles(prf_cycles),\n",
            """        .coeff_data(prf_coeff_data),.prf_digest(prf_digest),.cycles(prf_cycles),
`ifdef TRUSTEDGE_FAST_PRF
        .coeff_data_odd(prf_coeff_data_odd),
`endif
""")
    s = rep(s, """        if (prf_coeff_valid) begin
            if (prf_coeff_addr[0])
                noise_odd_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;
            else
                noise_even_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;
        end else""", """        if (prf_coeff_valid) begin
`ifdef TRUSTEDGE_FAST_PRF
            noise_even_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;
            noise_odd_ram[prf_coeff_addr[10:1]] <= prf_coeff_data_odd;
`else
            if (prf_coeff_addr[0])
                noise_odd_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;
            else
                noise_even_ram[prf_coeff_addr[10:1]] <= prf_coeff_data;
`endif
        end else""")
    s = rep(s, """    wire noise_even_we = (prf_coeff_valid && !prf_coeff_addr[0]) ||
                         ((state == S_Y_READ_CAP) && !y_read_index[0]);
    wire noise_odd_we = (prf_coeff_valid && prf_coeff_addr[0]) ||
                        ((state == S_Y_READ_CAP) && y_read_index[0]);
""", """`ifdef TRUSTEDGE_FAST_PRF
    wire noise_even_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && !y_read_index[0]);
    wire noise_odd_we = prf_coeff_valid || ((state == S_Y_READ_CAP) && y_read_index[0]);
`else
    wire noise_even_we = (prf_coeff_valid && !prf_coeff_addr[0]) ||
                         ((state == S_Y_READ_CAP) && !y_read_index[0]);
    wire noise_odd_we = (prf_coeff_valid && prf_coeff_addr[0]) ||
                        ((state == S_Y_READ_CAP) && y_read_index[0]);
`endif
""")
    s = rep(s, """            .wdata(noise_mem_wdata), .rdata(noise_odd_q)
""", """`ifdef TRUSTEDGE_FAST_PRF
            .wdata(prf_coeff_valid ? prf_coeff_data_odd : noise_mem_wdata), .rdata(noise_odd_q)
`else
            .wdata(noise_mem_wdata), .rdata(noise_odd_q)
`endif
""")
    return s


def fast_y(s: str) -> str:
    """TRUSTEDGE_FAST_Y: loading r into the NTT, the noise address of the next pair is presented with the
    odd write of the current one, two cycles per pair; reading y back, the NTT address of the next
    coefficient is presented with the capture of the current one, one cycle per coefficient."""
    s = rep(s, "            noise_read_addr={2'd0,y_poly,y_pair};\n", """`ifdef TRUSTEDGE_FAST_Y
            noise_read_addr = ((state==S_Y_WRITE1) && (y_pair!=7'd127)) ? {2'd0,y_poly,y_pair+7'd1} :
                                                                       {2'd0,y_poly,y_pair};
`else
            noise_read_addr={2'd0,y_poly,y_pair};
`endif
""")
    s = rep(s, "                    else begin y_pair<=y_pair+1'b1;state<=S_Y_FETCH;end end\n", """`ifdef TRUSTEDGE_FAST_Y
                    else begin y_pair<=y_pair+1'b1;state<=S_Y_WRITE0;end end
`else
                    else begin y_pair<=y_pair+1'b1;state<=S_Y_FETCH;end end
`endif
""")
    s = rep(s, "        ((state==S_Y_READ_REQ)||(state==S_Y_READ_WAIT)||(state==S_Y_READ_CAP)) ? y_read_index :\n", """`ifdef TRUSTEDGE_FAST_Y
        ((state==S_Y_READ_REQ)||(state==S_Y_READ_WAIT)||(state==S_Y_READ_CAP)) ?
            (((state==S_Y_READ_CAP) && (y_read_index!=8'd255)) ? y_read_index+8'd1 : y_read_index) :
`else
        ((state==S_Y_READ_REQ)||(state==S_Y_READ_WAIT)||(state==S_Y_READ_CAP)) ? y_read_index :
`endif
""")
    s = rep(s, "                    else begin y_read_index<=y_read_index+1'b1;state<=S_Y_READ_REQ;end end\n", """`ifdef TRUSTEDGE_FAST_Y
                    else begin y_read_index<=y_read_index+1'b1;state<=S_Y_READ_CAP;end end
`else
                    else begin y_read_index<=y_read_index+1'b1;state<=S_Y_READ_REQ;end end
`endif
""")
    return s


def tight_writes(s: str) -> str:
    """TRUSTEDGE_TIGHT_LOOPS in the encryption (with TRUSTEDGE_PREFETCH): the finished pair is written into
    the NTT during the next pair's two multiply states, even coefficient first, while the NTT port is
    otherwise idle; only the last pair keeps its two write states."""
    s = rep(s, "    reg operand_wait_q;\n", """    reg operand_wait_q;
`ifdef TRUSTEDGE_TIGHT_LOOPS
    reg       wr_pending;
    reg [6:0] wr_pair;
`endif
""")
    s = rep(s, "    wire data_ntt_write=(state==S_NTT_WRITE0)||(state==S_NTT_WRITE1);\n",
            """`ifdef TRUSTEDGE_TIGHT_LOOPS
    wire wr_even = wr_pending && (state==S_MUL0);
    wire wr_odd  = wr_pending && (state==S_MUL1);
    wire data_ntt_write=(state==S_NTT_WRITE0)||(state==S_NTT_WRITE1)||wr_even||wr_odd;
`else
    wire data_ntt_write=(state==S_NTT_WRITE0)||(state==S_NTT_WRITE1);
`endif
""")
    s = rep(s, """        (state==S_NTT_WRITE0)?coeff_index0:
        (state==S_NTT_WRITE1)?coeff_index1:read_index;
    wire [15:0] ntt_wdata = y_ntt_write ?
        ((state==S_Y_WRITE0)?{4'd0,noise_even_q}:{4'd0,noise_odd_q}) :
        (state==S_NTT_WRITE0)?{4'd0,result0_q}:{4'd0,result1_q};
""", """`ifdef TRUSTEDGE_TIGHT_LOOPS
        wr_even ? {wr_pair,1'b0} : wr_odd ? {wr_pair,1'b1} :
`endif
        (state==S_NTT_WRITE0)?coeff_index0:
        (state==S_NTT_WRITE1)?coeff_index1:read_index;
    wire [15:0] ntt_wdata = y_ntt_write ?
        ((state==S_Y_WRITE0)?{4'd0,noise_even_q}:{4'd0,noise_odd_q}) :
`ifdef TRUSTEDGE_TIGHT_LOOPS
        wr_even ? {4'd0,result0_q} : wr_odd ? {4'd0,result1_q} :
`endif
        (state==S_NTT_WRITE0)?{4'd0,result0_q}:{4'd0,result1_q};
""")
    s = rep(s, "                    state<=S_NTT_WRITE0;end end\n", """`ifdef TRUSTEDGE_TIGHT_LOOPS
                    if (pf_on && (pair_index != 7'd127)) begin    // written during the next pair
                        wr_pending<=1'b1; wr_pair<=pair_index; pair_index<=pair_index+1'b1;
                        column_index<=0; accum0_q<=0; accum1_q<=0; operand_wait_q<=runtime_key_bound_q;
                        state<=S_MUL0;
                    end else
`endif
                    state<=S_NTT_WRITE0;end end
""")
    s = rep(s, "                S_MUL1: begin p2_q<=mul_reduced;p3_q<=mul2_reduced;state<=S_ACCUM;end\n",
            """`ifdef TRUSTEDGE_TIGHT_LOOPS
                S_MUL1: begin p2_q<=mul_reduced;p3_q<=mul2_reduced;wr_pending<=1'b0;state<=S_ACCUM;end
`else
                S_MUL1: begin p2_q<=mul_reduced;p3_q<=mul2_reduced;state<=S_ACCUM;end
`endif
""")
    s = rep(s, "                S_PAIR_INIT: begin column_index<=0;pair_index<=0;accum0_q<=0;accum1_q<=0;\n",
            """                S_PAIR_INIT: begin column_index<=0;pair_index<=0;accum0_q<=0;accum1_q<=0;
`ifdef TRUSTEDGE_TIGHT_LOOPS
                    wr_pending<=1'b0;
`endif
""")
    return s


def prefetch(s: str) -> str:
    """TRUSTEDGE_PREFETCH: with a bound runtime key, the matrix (or t-hat), noise and twiddle operands of the
    next step (the other column, or the next pair) are addressed during the multiply and accumulate states
    of the current one, which hold the address for three cycles, longer than the two-cycle latency that the
    operand wait states cover; they are captured with the accumulation and the next step starts at once."""
    s = rep(s, "    assign matrix_ext_pair_addr = {column_index, poly_index[0], pair_index};\n"
               "    assign ekpke_ext_pair_addr = {column_index, pair_index};\n",
            """`ifdef TRUSTEDGE_PREFETCH
    wire pf_on = runtime_valid_q && runtime_key_bound_q;
    wire pf_col = ~column_index;
    wire [6:0] pf_pair = column_index ? (pair_index + 7'd1) : pair_index;
    wire pf_window = pf_on && !(column_index && (pair_index == 7'd127)) &&
        ((state==S_MUL0)||(state==S_MUL1)||(state==S_MUL2)||(state==S_MUL3)||(state==S_MUL4)||(state==S_ACCUM));
    wire [6:0] pf_gamma_index = 7'd64 + {1'b0, pf_pair[6:1]};
    wire [15:0] pf_gamma_full = kyber_zeta(pf_gamma_index);
    wire [11:0] pf_gamma = pf_pair[0] ? (12'd3329 - pf_gamma_full[11:0]) : pf_gamma_full[11:0];
    assign matrix_ext_pair_addr = pf_window ? {pf_col, poly_index[0], pf_pair} :
                                              {column_index, poly_index[0], pair_index};
    assign ekpke_ext_pair_addr = pf_window ? {pf_col, pf_pair} : {column_index, pair_index};
`else
    assign matrix_ext_pair_addr = {column_index, poly_index[0], pair_index};
    assign ekpke_ext_pair_addr = {column_index, pair_index};
`endif
""")
    s = rep(s, "            noise_read_addr=(column_index*10'd128)+pair_index;\n",
            """`ifdef TRUSTEDGE_PREFETCH
            noise_read_addr = pf_window ? (({9'd0, pf_col}*10'd128) + pf_pair) :
                                          ((column_index*10'd128) + pair_index);
`else
            noise_read_addr=(column_index*10'd128)+pair_index;
`endif
""")
    s = rep(s, """                    column_index<=1;operand_wait_q<=runtime_key_bound_q;
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end
                    else begin result0_q<=final0;result1_q<=final1;state<=S_NTT_WRITE0;end end
""", """                    column_index<=1;operand_wait_q<=runtime_key_bound_q;
`ifdef TRUSTEDGE_PREFETCH
                    if (pf_on) begin              // the operands of column 1, addressed since MUL0
                        operand_a0_q<=operand_a0;operand_a1_q<=operand_a1;
                        operand_b0_q<=noise_even_q;operand_b1_q<=noise_odd_q;
                        gamma_q<=pf_gamma;state<=S_MUL0;
                    end else
`endif
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end
                    else begin result0_q<=final0;result1_q<=final1;
`ifdef TRUSTEDGE_PREFETCH
                    if (pf_on && (pair_index != 7'd127)) begin   // the operands of the next pair
                        operand_a0_q<=operand_a0;operand_a1_q<=operand_a1;
                        operand_b0_q<=noise_even_q;operand_b1_q<=noise_odd_q;
                        gamma_q<=pf_gamma;
                    end
`endif
                    state<=S_NTT_WRITE0;end end
""")
    s = rep(s, """                    accum0_q<=0;accum1_q<=0;operand_wait_q<=runtime_key_bound_q;
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end end
""", """                    accum0_q<=0;accum1_q<=0;operand_wait_q<=runtime_key_bound_q;
`ifdef TRUSTEDGE_PREFETCH
                    if (pf_on) state<=S_MUL0; else
`endif
                    state<=runtime_valid_q?S_OPERAND_WAIT:S_OPERAND;end end
""")
    return s


def edit_codec(s: str) -> str:
    # step D in the ciphertext codec: the coefficient and ciphertext RAMs answer one cycle after the address
    # register (proc_index, decode_ct_addr), which every request state already presents. The comparison loop
    # keeps its wait state, which captures operands in the ASIC configuration, and the read-back loop
    # already returns from its accumulate state to its wait state, two cycles per byte.
    for a, b in (("ST_U_REQ: state <= ST_U_WAIT;", "ST_U_REQ: state <= ST_U_CAPTURE;"),
                 ("ST_V_REQ: state <= ST_V_WAIT;", "ST_V_REQ: state <= ST_V_CAPTURE;"),
                 ("ST_D_REQ: state <= ST_D_WAIT;", "ST_D_REQ: state <= ST_D_ACC;")):
        s = rep(s, "                " + a + "\n",
                "`ifdef TRUSTEDGE_STREAM_IO\n                " + b + "      // one-cycle read latency\n"
                "`else\n                " + a + "\n`endif\n")
    return so_pipe(seg_check(pipe_check(fused_cmp_codec(fast_check(fold_readback(stream_out(s)))))))


def so_pipe(s: str) -> str:
    """TRUSTEDGE_SO_PIPE (with TRUSTEDGE_STREAM_OUT): a U coefficient is registered in its load cycle and
    compressed and packed in the next, so that the RAM reads behind it (which reach the codec half a cycle
    after the edge on the chip) no longer pass through Compress_10. The last coefficient of u0 and of u1 is
    followed by the next polynomial's computation, so the cycle counts do not change; the two flush states
    also wait for a pending coefficient."""
    s = rep(s, "    reg [9:0]  so_addr;                      // next ciphertext byte\n",
            """    reg [9:0]  so_addr;                      // next ciphertext byte
`ifdef TRUSTEDGE_SO_PIPE
    reg        so_lv;                        // a U coefficient waits one cycle before Compress_10
    reg [11:0] so_lc;
    wire       so_idle = (so_left == 3'd0) && !so_vvalid && !so_lv;
`else
    wire       so_idle = (so_left == 3'd0) && !so_vvalid;
`endif
""")
    s = rep(s, "            so_vbyte <= 8'd0; so_vvalid <= 1'b0; so_addr <= 10'd0;\n",
            """            so_vbyte <= 8'd0; so_vvalid <= 1'b0; so_addr <= 10'd0;
`ifdef TRUSTEDGE_SO_PIPE
            so_lv <= 1'b0; so_lc <= 12'd0;
`endif
""")
    s = rep(s, """            end else if (so_vvalid) begin
                so_vvalid <= 1'b0; so_addr <= so_addr + 10'd1;
            end
""", """            end else if (so_vvalid) begin
                so_vvalid <= 1'b0; so_addr <= so_addr + 10'd1;
            end
`ifdef TRUSTEDGE_SO_PIPE
            so_lv <= 1'b0;
            if (so_lv) begin                         // the U coefficient loaded in the previous cycle
                if (so_sub == 3'd3) begin
                    so_out <= so_pack | ({30'd0, compress10(so_lc)} << 30);
                    so_left <= 3'd5; so_pack <= 40'd0; so_sub <= 3'd0;
                end else begin
                    so_pack <= so_pack | ({30'd0, compress10(so_lc)} << (so_sub * 10));
                    so_sub <= so_sub + 3'd1;
                end
            end
`endif
""")
    s = rep(s, "                so_pack <= 40'd0; so_sub <= 3'd0; so_left <= 3'd0; so_vvalid <= 1'b0; so_addr <= 10'd0;\n",
            """                so_pack <= 40'd0; so_sub <= 3'd0; so_left <= 3'd0; so_vvalid <= 1'b0; so_addr <= 10'd0;
`ifdef TRUSTEDGE_SO_PIPE
                so_lv <= 1'b0;
`endif
""")
    s = rep(s, """                    if (load_index < 10'd512) begin
                        if (so_sub == 3'd3) begin
                            so_out <= so_pack | ({30'd0, compress10(load_coeff)} << 30);
                            so_left <= 3'd5; so_pack <= 40'd0; so_sub <= 3'd0;
                        end else begin
                            so_pack <= so_pack | ({30'd0, compress10(load_coeff)} << (so_sub * 10));
                            so_sub <= so_sub + 3'd1;
                        end
                    end else if (so_sub == 3'd1) begin
""", """                    if (load_index < 10'd512) begin
`ifdef TRUSTEDGE_SO_PIPE
                        so_lv <= 1'b1; so_lc <= load_coeff;
`else
                        if (so_sub == 3'd3) begin
                            so_out <= so_pack | ({30'd0, compress10(load_coeff)} << 30);
                            so_left <= 3'd5; so_pack <= 40'd0; so_sub <= 3'd0;
                        end else begin
                            so_pack <= so_pack | ({30'd0, compress10(load_coeff)} << (so_sub * 10));
                            so_sub <= so_sub + 3'd1;
                        end
`endif
                    end else if (so_sub == 3'd1) begin
""")
    s = rep(s, "                ST_S_FLUSH: if ((so_left == 3'd0) && !so_vvalid) begin\n",
            "                ST_S_FLUSH: if (so_idle) begin\n")
    s = rep(s, "                ST_SEG_FLUSH: if ((so_left == 3'd0) && !so_vvalid) begin",
            "                ST_SEG_FLUSH: if (so_idle) begin")
    return s


def seg_check(s: str) -> str:
    """TRUSTEDGE_SEG_CHECK (with TRUSTEDGE_PIPE_CHECK): the decode check runs in three segments. After u0's
    256 coefficients are loaded (seg_start), the check reads bytes 0..319 and compares coefficients
    0..255, then pauses with busy low, so that the encryption can load the next polynomial; u1 follows in
    the same way, and the final start checks the 128 bytes of v and finishes as before. The digests and
    the decode state continue across the pauses, so every result is the same as with one pass."""
    s = rep(s, "    input  wire        start,\n", """    input  wire        start,
`ifdef TRUSTEDGE_SEG_CHECK
    input  wire        seg_start,          // check the bytes of the polynomial just loaded
`endif
""")
    s = rep(s, "    wire       b_issue = (b_addr < 10'd768) &&\n", """`ifdef TRUSTEDGE_SEG_CHECK
    localparam [4:0] ST_SEG_FLUSH = 5'd20;
    reg         seg_mode;                    // this image is checked in segments (the import is not)
    reg  [1:0]  seg_count;                   // decode-check segments completed (0, 1, 2)
    wire [9:0]  b_limit = !seg_mode ? 10'd768 :
                          (seg_count == 2'd0) ? 10'd320 : (seg_count == 2'd1) ? 10'd640 : 10'd768;
    wire       b_issue = (b_addr < b_limit) &&
`else
    wire       b_issue = (b_addr < 10'd768) &&
`endif
""")
    # pause after a segment; a new image starts again from the first segment
    s = rep(s, """                            state <= ST_IDLE;
                        end
                    end
                end
`else
                ST_D_REQ: state <= ST_D_ACC;      // one-cycle read latency
""", """                            state <= ST_IDLE;
`ifdef TRUSTEDGE_SEG_CHECK
                            seg_count <= 2'd0; seg_mode <= 1'b0;
`endif
                        end
                    end
`ifdef TRUSTEDGE_SEG_CHECK
                    if (seg_mode && (seg_count != 2'd2) && (b_addr == b_limit) && !b_pend && !g_full &&
                        (c_left == 3'd0) && !p1_v && !p2_v) begin      // the segment is checked
                        busy <= 1'b0; seg_count <= seg_count + 2'd1; state <= ST_IDLE;
                    end
`endif
                end
`else
                ST_D_REQ: state <= ST_D_ACC;      // one-cycle read latency
""")
    s = rep(s, """                ST_IDLE: begin
                    if (import_start) begin
""", """                ST_IDLE: begin
`ifdef TRUSTEDGE_SEG_CHECK
                    if (seg_start) begin
                        busy <= 1'b1; seg_mode <= 1'b1;
                        state <= ST_SEG_FLUSH;
                    end else
`endif
                    if (import_start) begin
""")
    s = rep(s, """                        // explicitly return pass=0 together with done.
                        digest_a <= 32'd0;
                        digest_b <= 32'd0;
                        decode_digest <= 32'd0;
                        decode_pass <= 1'b0;
                        cycles <= 16'd0;
""", """                        // explicitly return pass=0 together with done.
`ifdef TRUSTEDGE_SEG_CHECK
                        if (seg_count == 2'd0) begin   // after checked segments the digests continue
`endif
                        digest_a <= 32'd0;
                        digest_b <= 32'd0;
                        decode_digest <= 32'd0;
                        decode_pass <= 1'b0;
`ifdef TRUSTEDGE_SEG_CHECK
                        end
`endif
                        cycles <= 16'd0;
""")
    s = rep(s, """                ST_S_FLUSH: if ((so_left == 3'd0) && !so_vvalid) begin
                    // the state that the encoder leaves behind at the end of the V pass
                    ct_write_addr <= so_addr;
""", """`ifdef TRUSTEDGE_SEG_CHECK
                ST_SEG_FLUSH: if ((so_left == 3'd0) && !so_vvalid) begin   // the group bytes are written
                    if (seg_count == 2'd0) begin      // the first segment starts the check
                        decode_digest <= 32'h44454331; decode_error <= 1'b0; decode_pass <= 1'b0;
                        digest_a <= 32'h43543131; digest_b <= 32'h4B504B45;
                        state <= ST_D_REQ;
                    end else
                        state <= ST_D_PIPE;
                end
`endif
                ST_S_FLUSH: if ((so_left == 3'd0) && !so_vvalid) begin
                    // the state that the encoder leaves behind at the end of the V pass
                    ct_write_addr <= so_addr;
`ifdef TRUSTEDGE_SEG_CHECK
                    if (seg_count != 2'd0) state <= ST_D_PIPE;   // the v bytes remain
                    else begin
`endif
""")
    s = rep(s, """                    state <= ST_D_REQ;
                end
`endif
                ST_U_REQ: state <= ST_U_CAPTURE;      // one-cycle read latency
""", """                    state <= ST_D_REQ;
`ifdef TRUSTEDGE_SEG_CHECK
                    end
`endif
                end
`endif
                ST_U_REQ: state <= ST_U_CAPTURE;      // one-cycle read latency
""")
    s = rep(s, """            if (load_clear && !busy) begin
                loaded_coeffs <= 10'd0;
""", """            if (load_clear && !busy) begin
                loaded_coeffs <= 10'd0;
`ifdef TRUSTEDGE_SEG_CHECK
                seg_count <= 2'd0; seg_mode <= 1'b0;
`endif
""")
    s = rep(s, """            loaded_coeffs <= 10'd0;
            imported_bytes <= 10'd0;
""", """            loaded_coeffs <= 10'd0;
            imported_bytes <= 10'd0;
`ifdef TRUSTEDGE_SEG_CHECK
            seg_count <= 2'd0; seg_mode <= 1'b0;
`endif
""")
    return s


PIPE_DECL = """`ifdef TRUSTEDGE_PIPE_CHECK
    // Pipelined decode check: a byte stream reads the ciphertext RAM at one byte per cycle and assembles
    // groups (five bytes for four U coefficients, one byte for two V coefficients); a compare stream reads
    // the coefficient RAM at one coefficient per cycle in three stages (address, capture, compare). One
    // group buffer couples them; the last byte of a group is read only when the buffer will be free.
    localparam [4:0] ST_D_PIPE = 5'd19;
    reg [9:0]  b_addr;                       // next ciphertext byte to read
    reg [2:0]  i_sub;                        // position of b_addr within its U group
    reg        b_pend, b_pend_final, b_pend_v; // the byte read in the last cycle lands now
    reg [2:0]  b_sub;                        // bytes of the current group received
    reg [39:0] b_pack;
    reg [39:0] g_pack;                       // a complete group waiting for the compare stream
    reg        g_full, g_v;
    reg [39:0] c_pack;                       // the group being compared
    reg        c_v;
    reg [2:0]  c_sub, c_left;
    reg [9:0]  c_idx;                        // next coefficient to address
    reg        p1_v, p1_vph;                 // stage 1: coefficient read in flight
    reg [9:0]  p1_idx, p1_code;
    reg        p2_v;                         // stage 2: compare, digest and decoded-RAM write
    reg [9:0]  p2_idx;
    reg [11:0] p2_dec, p2_src;
    wire       b_issue_v = (b_addr >= 10'd640);
    wire       b_issue_final = b_issue_v || (i_sub == 3'd4);
    wire       c_take = g_full && (c_left <= 3'd1);
    wire       b_issue = (b_addr < 10'd768) &&
                         (!b_issue_final || ((!g_full || c_take) && !(b_pend && b_pend_final)));
`endif
"""

PIPE_WIRES = """`ifdef TRUSTEDGE_PIPE_CHECK
    wire [39:0] b_pack_next = b_pack | ({32'd0, ct_ram_q} << (b_sub * 8));
    wire [11:0] p1_dec = p1_vph ? decompress4(p1_code[3:0]) : decompress10(p1_code);
    wire [11:0] p1_src = p1_vph ? decompress4(compress4(coeff_q)) : decompress10(compress10(coeff_q));
    wire        p2_mismatch = (p2_dec != p2_src);
`endif
"""

PIPE_STATE = """`ifdef TRUSTEDGE_PIPE_CHECK
                ST_D_REQ: begin                  // start both streams
                    b_addr <= 10'd0; i_sub <= 3'd0; b_pend <= 1'b0; b_pend_final <= 1'b0; b_pend_v <= 1'b0;
                    b_sub <= 3'd0; b_pack <= 40'd0; g_full <= 1'b0; g_v <= 1'b0; g_pack <= 40'd0;
                    c_left <= 3'd0; c_sub <= 3'd0; c_idx <= 10'd0; c_v <= 1'b0; c_pack <= 40'd0;
                    p1_v <= 1'b0; p2_v <= 1'b0;
                    state <= ST_D_PIPE;
                end
                ST_D_PIPE: begin
                    // byte stream: the byte read in the last cycle lands, in order 0..767
                    if (b_pend) begin
                        digest_a <= digest_a_next;       // the read-back audit, one byte at a time
                        digest_b <= digest_b_next;
                        if (b_pend_final) begin
                            g_pack <= b_pack_next; g_v <= b_pend_v; g_full <= 1'b1;
                            b_pack <= 40'd0; b_sub <= 3'd0;
                        end else begin
                            b_pack <= b_pack_next; b_sub <= b_sub + 3'd1;
                        end
                    end
                    b_pend <= b_issue; b_pend_final <= b_issue_final; b_pend_v <= b_issue_v;
                    if (b_issue) begin
                        b_addr <= b_addr + 10'd1;
                        i_sub <= b_issue_final ? 3'd0 : i_sub + 3'd1;
                    end
                    // compare stream, stage 0: address the next coefficient of the group
                    p1_v <= (c_left != 3'd0); p1_idx <= c_idx; p1_vph <= c_v;
                    p1_code <= c_v ? {6'd0, c_pack[c_sub * 4 +: 4]} : c_pack[c_sub * 10 +: 10];
                    if (c_left != 3'd0) begin
                        c_sub <= c_sub + 3'd1; c_left <= c_left - 3'd1; c_idx <= c_idx + 10'd1;
                    end
                    if (c_take) begin                // the next group follows without a gap
                        c_pack <= g_pack; c_v <= g_v; c_sub <= 3'd0; c_left <= g_v ? 3'd2 : 3'd4;
                        g_full <= 1'b0;
                    end
                    // stage 1: both values decompressed and registered
                    p2_v <= p1_v; p2_idx <= p1_idx; p2_dec <= p1_dec; p2_src <= p1_src;
                    // stage 2
                    if (p2_v) begin
                        decode_digest <= decode_digest_step(decode_digest, p2_dec);
`ifndef TRUSTEDGE_ASIC_SRAM
                        decoded_coeff_ram[p2_idx] <= p2_dec;
`endif
                        if (p2_mismatch && import_compare_source)
                            decode_error <= 1'b1;
                        if (p2_idx == 10'd767) begin
                            decode_pass <= !(decode_error || (p2_mismatch && import_compare_source));
                            busy <= 1'b0;
                            done <= 1'b1;
                            pass <= (!check_expected ||
                                     ((digest_a == EXPECTED_DIGEST_A) &&
                                      (digest_b == EXPECTED_DIGEST_B))) &&
                                    (ct_write_addr == 10'd768) &&
                                    !(decode_error || (p2_mismatch && import_compare_source));
                            state <= ST_IDLE;
                        end
                    end
                end
`else
                ST_D_REQ: state <= ST_D_ACC;      // one-cycle read latency
`endif
"""


def pipe_check(s: str) -> str:
    """TRUSTEDGE_PIPE_CHECK (with TRUSTEDGE_STREAM_IO and TRUSTEDGE_FOLD_READBACK): the decode check reads
    the ciphertext bytes and the source coefficients as two overlapped streams, one byte and one
    coefficient per cycle, instead of alternating between them group by group."""
    s = rep(s, "    reg import_error;\n", "    reg import_error;\n" + PIPE_DECL)
    s = rep(s, "    wire [31:0] decode_digest_next = decode_digest_step(decode_digest,\n"
               "                                                          compare_decoded_coeff);\n",
            "    wire [31:0] decode_digest_next = decode_digest_step(decode_digest,\n"
            "                                                          compare_decoded_coeff);\n" + PIPE_WIRES)
    s = rep(s, """    assign ct_check_active = busy && ((state == ST_D_REQ) || (state == ST_D_WAIT) || (state == ST_D_ACC));
    assign ct_check_byte = busy && (state == ST_D_ACC);
    assign ct_check_addr = d_ct_addr;
""", """`ifdef TRUSTEDGE_PIPE_CHECK
    assign ct_check_active = busy && (state == ST_D_PIPE);
    assign ct_check_byte = busy && (state == ST_D_PIPE) && b_pend;
    assign ct_check_addr = b_addr;
`else
    assign ct_check_active = busy && ((state == ST_D_REQ) || (state == ST_D_WAIT) || (state == ST_D_ACC));
    assign ct_check_byte = busy && (state == ST_D_ACC);
    assign ct_check_addr = d_ct_addr;
`endif
""")
    # FPGA arrays: the two read ports follow the streams
    s = rep(s, "            coeff_q <= coeff_ram[d_cmp_addr];\n", """            coeff_q <= coeff_ram[d_cmp_addr];
`ifdef TRUSTEDGE_PIPE_CHECK
        else if (busy && (state == ST_D_PIPE))
            coeff_q <= coeff_ram[c_idx];
`endif
""")
    s = rep(s, "            ct_ram_q <= ciphertext_ram[d_ct_addr];\n", """            ct_ram_q <= ciphertext_ram[d_ct_addr];
`ifdef TRUSTEDGE_PIPE_CHECK
        else if (busy && (state == ST_D_PIPE))
            ct_ram_q <= ciphertext_ram[b_addr];
`endif
""")
    # ASIC macros
    s = rep(s, "    wire [9:0] coeff_mem_addr = coeff_mem_we ? load_index : coeff_mem_raddr;\n", """`ifdef TRUSTEDGE_PIPE_CHECK
    wire [9:0] coeff_mem_addr = coeff_mem_we ? load_index :
                                (busy && (state == ST_D_PIPE)) ? c_idx : coeff_mem_raddr;
`else
    wire [9:0] coeff_mem_addr = coeff_mem_we ? load_index : coeff_mem_raddr;
`endif
""")
    s = rep(s, "    wire [9:0] ct_mem_addr = ct_mem_we ? ct_mem_waddr : ct_mem_raddr;\n", """`ifdef TRUSTEDGE_PIPE_CHECK
    wire [9:0] ct_mem_addr = ct_mem_we ? ct_mem_waddr :
                             (busy && (state == ST_D_PIPE)) ? b_addr : ct_mem_raddr;
`else
    wire [9:0] ct_mem_addr = ct_mem_we ? ct_mem_waddr : ct_mem_raddr;
`endif
""")
    s = rep(s, """    wire decoded_mem_we = busy && (state == ST_D_CMP_ACC);
    wire [9:0] decoded_mem_addr = decoded_mem_we ?
        (decode_coeff_base + decode_cmp_sub) : decoded_read_addr;
""", """`ifdef TRUSTEDGE_PIPE_CHECK
    wire decoded_pipe_we = busy && (state == ST_D_PIPE) && p2_v;
    wire decoded_mem_we = decoded_pipe_we;
    wire [9:0] decoded_mem_addr = decoded_pipe_we ? p2_idx : decoded_read_addr;
    wire [11:0] decoded_mem_wdata = p2_dec;
`else
    wire decoded_mem_we = busy && (state == ST_D_CMP_ACC);
    wire [9:0] decoded_mem_addr = decoded_mem_we ?
        (decode_coeff_base + decode_cmp_sub) : decoded_read_addr;
    wire [11:0] decoded_mem_wdata = compare_decoded_coeff;
`endif
""")
    s = rep(s, "            .wdata(compare_decoded_coeff), .rdata(decoded_ram_q)\n",
            "            .wdata(decoded_mem_wdata), .rdata(decoded_ram_q)\n")
    s = rep(s, "                ST_D_REQ: state <= ST_D_ACC;      // one-cycle read latency\n", PIPE_STATE)
    # one write port only, so that the FPGA keeps the decoded image in block RAM (the old compare state
    # is unreachable with the pipeline)
    s = rep(s, """                    decoded_coeff_ram[decode_coeff_base + decode_cmp_sub] <=
                        decoded_coeff;
""", """`ifndef TRUSTEDGE_PIPE_CHECK
                    decoded_coeff_ram[decode_coeff_base + decode_cmp_sub] <=
                        decoded_coeff;
`endif
""")
    return s


def fused_cmp_codec(s: str) -> str:
    """TRUSTEDGE_FUSED_CMP: the decode check's read address and its byte strobe leave the codec."""
    s = rep(s, "    output wire [7:0]  ct_read_data,\n", """    output wire [7:0]  ct_read_data,
`ifdef TRUSTEDGE_FUSED_CMP
    output wire        ct_check_active,
    output wire        ct_check_byte,
    output wire [9:0]  ct_check_addr,
`endif
""")
    s = rep(s, "    assign ct_read_data = ct_ram_q;\n", """    assign ct_read_data = ct_ram_q;
`ifdef TRUSTEDGE_FUSED_CMP
    assign ct_check_active = busy && ((state == ST_D_REQ) || (state == ST_D_WAIT) || (state == ST_D_ACC));
    assign ct_check_byte = busy && (state == ST_D_ACC);
    assign ct_check_addr = d_ct_addr;
`endif
""")
    return s


def fast_check(s: str) -> str:
    """TRUSTEDGE_FAST_CHECK: inside a group, the decode check presents the next ciphertext byte and the
    next source coefficient during the accumulate state, so the following byte is accumulated at once and
    the following coefficient goes straight to its capture state; only the first of each group keeps its
    request state. The capture state that the ASIC configuration needs for timing stays."""
    s = rep(s, "    reg import_error;\n", """    reg import_error;
`ifdef TRUSTEDGE_FAST_CHECK
    wire d_byte_more = !((!decode_v_phase && (decode_byte_sub == 3'd4)) ||
                         (decode_v_phase && (decode_byte_sub == 3'd0)));
    wire d_cmp_more  = !((!decode_v_phase && (decode_cmp_sub == 3'd3)) ||
                         (decode_v_phase && (decode_cmp_sub == 3'd1)));
    wire [9:0] d_ct_addr = ((state == ST_D_ACC) && d_byte_more) ? decode_ct_addr + 10'd1 : decode_ct_addr;
    wire [9:0] d_cmp_addr = decode_coeff_base + decode_cmp_sub +
                            (((state == ST_D_CMP_ACC) && d_cmp_more) ? 10'd1 : 10'd0);
`else
    wire [9:0] d_ct_addr = decode_ct_addr;
    wire [9:0] d_cmp_addr = decode_coeff_base + decode_cmp_sub;
`endif
""")
    # the two read ports (ASIC macros and FPGA arrays) take the lookahead addresses
    s = rep(s, """        (decode_coeff_base + decode_cmp_sub) : proc_index;
""", """        d_cmp_addr : proc_index;
""")
    s = rep(s, """                  (state == ST_D_ACC))) ? decode_ct_addr : ct_read_addr;
""", """                  (state == ST_D_ACC))) ? d_ct_addr : ct_read_addr;
""")
    s = rep(s, """            coeff_q <= coeff_ram[decode_coeff_base + decode_cmp_sub];
""", """            coeff_q <= coeff_ram[d_cmp_addr];
""")
    s = rep(s, """            ct_ram_q <= ciphertext_ram[decode_ct_addr];
""", """            ct_ram_q <= ciphertext_ram[d_ct_addr];
""")
    s = rep(s, """                        decode_ct_addr <= decode_ct_addr + 10'd1;
                        decode_byte_sub <= decode_byte_sub + 3'd1;
                        state <= ST_D_REQ;
""", """                        decode_ct_addr <= decode_ct_addr + 10'd1;
                        decode_byte_sub <= decode_byte_sub + 3'd1;
`ifdef TRUSTEDGE_FAST_CHECK
                        state <= ST_D_ACC;            // the next byte was addressed in this cycle
`else
                        state <= ST_D_REQ;
`endif
""")
    s = rep(s, """                        decode_cmp_sub <= decode_cmp_sub + 3'd1;
                        state <= ST_D_CMP_REQ;
""", """                        decode_cmp_sub <= decode_cmp_sub + 3'd1;
`ifdef TRUSTEDGE_FAST_CHECK
                        state <= ST_D_CMP_WAIT;       // the next coefficient was addressed in this cycle
`else
                        state <= ST_D_CMP_REQ;
`endif
""")
    return s


def fold_readback(s: str) -> str:
    """TRUSTEDGE_FOLD_READBACK: the decode check reads the ciphertext bytes in the same order as the
    read-back audit (0..767), so the two audit digests are accumulated during the decode check and the
    read-back pass is dropped; the codec completes with the last decoded coefficient."""
    n = s.count("decode_digest <= 32'h44454331;\n")
    assert n == 3, n          # the decode check starts after an import, after the encoder and after a flush
    s = s.replace("decode_digest <= 32'h44454331;\n",
                  "decode_digest <= 32'h44454331;\n"
                  "`ifdef TRUSTEDGE_FOLD_READBACK\n"
                  "                            digest_a <= 32'h43543131; digest_b <= 32'h4B504B45;\n"
                  "`endif\n")
    s = rep(s, """                ST_D_ACC: begin
                    decode_pack <= decode_pack_next;
""", """                ST_D_ACC: begin
                    decode_pack <= decode_pack_next;
`ifdef TRUSTEDGE_FOLD_READBACK
                    digest_a <= digest_a_next;       // the read-back audit, one byte at a time
                    digest_b <= digest_b_next;
`endif
""")
    s = rep(s, """                            rb_addr <= 10'd0;
                            digest_a <= 32'h43543131;
                            digest_b <= 32'h4B504B45;
                            state <= ST_RB_REQ;
""", """`ifdef TRUSTEDGE_FOLD_READBACK
                            busy <= 1'b0;
                            done <= 1'b1;
                            pass <= (!check_expected ||
                                     ((digest_a == EXPECTED_DIGEST_A) &&
                                      (digest_b == EXPECTED_DIGEST_B))) &&
                                    (ct_write_addr == 10'd768) &&
                                    !(decode_error || (decode_mismatch && import_compare_source));
                            state <= ST_IDLE;
`else
                            rb_addr <= 10'd0;
                            digest_a <= 32'h43543131;
                            digest_b <= 32'h4B504B45;
                            state <= ST_RB_REQ;
`endif
""")
    return s


def stream_out(s: str) -> str:
    """TRUSTEDGE_STREAM_OUT: the codec compresses and packs every coefficient as it is loaded, in index
    order, and writes the bytes of a finished U group (five) or V pair (one) in the following cycles, so
    that the encoding pass after the start disappears; a one-cycle flush state then enters the unchanged
    decode check. The loads arrive every two cycles, which leaves room for the five byte writes."""
    s = rep(s, "        ST_D_CMP_ACC = 5'd17;\n",
            "        ST_D_CMP_ACC = 5'd17,\n        ST_S_FLUSH   = 5'd18;\n")
    s = rep(s, "    reg import_error;\n", """    reg import_error;
`ifdef TRUSTEDGE_STREAM_OUT
    reg [39:0] so_pack, so_out;              // the group being packed, the bytes being written
    reg [2:0]  so_sub, so_left;              // coefficients packed, bytes still to write
    reg [7:0]  so_vbyte;                     // a finished V byte waiting behind a U group
    reg        so_vvalid;
    reg [9:0]  so_addr;                      // next ciphertext byte
`endif
""")
    s = rep(s, """        end else if (busy && (state == ST_U_WRITE)) begin
            ct_mem_we    = 1'b1;""", """`ifdef TRUSTEDGE_STREAM_OUT
        end else if ((so_left != 3'd0) || so_vvalid) begin
            ct_mem_we    = 1'b1;
            ct_mem_waddr = so_addr;
            ct_mem_wdata = (so_left != 3'd0) ? so_out[7:0] : so_vbyte;
`endif
        end else if (busy && (state == ST_U_WRITE)) begin
            ct_mem_we    = 1'b1;""")
    s = rep(s, """            decoded_coeff_cmp_q <= 12'd0;
            canonical_source_coeff_cmp_q <= 12'd0;
`endif
        end else begin
            done <= 1'b0;
""", """            decoded_coeff_cmp_q <= 12'd0;
            canonical_source_coeff_cmp_q <= 12'd0;
`endif
`ifdef TRUSTEDGE_STREAM_OUT
            so_pack <= 40'd0; so_out <= 40'd0; so_sub <= 3'd0; so_left <= 3'd0;
            so_vbyte <= 8'd0; so_vvalid <= 1'b0; so_addr <= 10'd0;
`endif
        end else begin
            done <= 1'b0;
`ifdef TRUSTEDGE_STREAM_OUT
            if (so_left != 3'd0) begin
                so_out <= so_out >> 8; so_left <= so_left - 3'd1; so_addr <= so_addr + 10'd1;
            end else if (so_vvalid) begin
                so_vvalid <= 1'b0; so_addr <= so_addr + 10'd1;
            end
`endif
""")
    s = rep(s, """            if (load_clear && !busy) begin
                loaded_coeffs <= 10'd0;
                load_error <= 1'b0;
            end else if (load_valid && !busy) begin
                if (!load_error && (load_index == loaded_coeffs) &&
                    (loaded_coeffs < 10'd768)) begin
""", """            if (load_clear && !busy) begin
                loaded_coeffs <= 10'd0;
                load_error <= 1'b0;
`ifdef TRUSTEDGE_STREAM_OUT
                so_pack <= 40'd0; so_sub <= 3'd0; so_left <= 3'd0; so_vvalid <= 1'b0; so_addr <= 10'd0;
`endif
            end else if (load_valid && !busy) begin
                if (!load_error && (load_index == loaded_coeffs) &&
                    (loaded_coeffs < 10'd768)) begin
`ifdef TRUSTEDGE_STREAM_OUT
                    if (load_index < 10'd512) begin
                        if (so_sub == 3'd3) begin
                            so_out <= so_pack | ({30'd0, compress10(load_coeff)} << 30);
                            so_left <= 3'd5; so_pack <= 40'd0; so_sub <= 3'd0;
                        end else begin
                            so_pack <= so_pack | ({30'd0, compress10(load_coeff)} << (so_sub * 10));
                            so_sub <= so_sub + 3'd1;
                        end
                    end else if (so_sub == 3'd1) begin
                        so_vbyte <= so_pack[7:0] | {compress4(load_coeff), 4'd0};
                        so_vvalid <= 1'b1; so_pack <= 40'd0; so_sub <= 3'd0;
                    end else begin
                        so_pack <= {36'd0, compress4(load_coeff)};
                        so_sub <= 3'd1;
                    end
`endif
""")
    s = rep(s, """                            pack_bits <= 40'd0;
                            state <= ST_U_REQ;
""", """                            pack_bits <= 40'd0;
`ifdef TRUSTEDGE_STREAM_OUT
                            state <= ST_S_FLUSH;     // the bytes were written during the load
`else
                            state <= ST_U_REQ;
`endif
""")
    s = rep(s, "                ST_U_REQ: state <= ST_U_CAPTURE;      // one-cycle read latency\n",
            """`ifdef TRUSTEDGE_STREAM_OUT
                ST_S_FLUSH: if ((so_left == 3'd0) && !so_vvalid) begin
                    // the state that the encoder leaves behind at the end of the V pass
                    ct_write_addr <= so_addr;
                    decode_ct_addr <= 10'd0;
                    decode_coeff_base <= 10'd0;
                    decode_byte_sub <= 3'd0;
                    decode_cmp_sub <= 3'd0;
                    decode_pack <= 40'd0;
                    decode_v_phase <= 1'b0;
                    decode_error <= 1'b0;
                    decode_digest <= 32'h44454331;
                    state <= ST_D_REQ;
                end
`endif
                ST_U_REQ: state <= ST_U_CAPTURE;      // one-cycle read latency
""")
    return s


def fast_basemul(s: str, st: str, a0: str, a1: str, b0: str, b1: str, gamma: str, red: str) -> str:
    """TRUSTEDGE_FAST_BASEMUL: a second multiplier computes a1*b1 beside a0*b0, and the odd coefficient
    becomes (a0+a1)(b0+b1) - a0*b0 - a1*b1 mod q (Karatsuba, the sums reduced first so that the
    existing 24-bit Barrett reducer applies). A pair then takes two multiply states instead of five;
    every value stays canonical, so the results are bit-identical."""
    s = rep(s, f"            {st}MUL1: begin mul_lhs={a1}; mul_rhs={b1}; end\n",
            "`ifdef TRUSTEDGE_FAST_BASEMUL\n"
            f"            {st}MUL1: begin mul_lhs=p1_q; mul_rhs={gamma}; end\n"
            "`else\n"
            f"            {st}MUL1: begin mul_lhs={a1}; mul_rhs={b1}; end\n"
            "`endif\n")
    s = rep(s, "    wire [11:0] base1=add_mod_q(p3_q,p4_q);\n",
            "`ifdef TRUSTEDGE_FAST_BASEMUL\n"
            f"    wire [11:0] fast_sa = add_mod_q({a0}, {a1});\n"
            f"    wire [11:0] fast_sb = add_mod_q({b0}, {b1});\n"
            "    reg  [11:0] mul2_lhs, mul2_rhs;\n"
            "    always @* begin\n"
            "        mul2_lhs = 12'd0; mul2_rhs = 12'd0;\n"
            f"        if (state == {st}MUL0) begin mul2_lhs = {a1}; mul2_rhs = {b1}; end\n"
            f"        else if (state == {st}MUL1) begin mul2_lhs = fast_sa; mul2_rhs = fast_sb; end\n"
            "    end\n"
            "    wire [23:0] mul2_product = mul2_lhs * mul2_rhs;\n"
            "    wire [11:0] mul2_reduced;\n"
            f"    barrett_reduce {red}2(.a(mul2_product), .r(mul2_reduced));\n"
            "    function automatic [11:0] sub_mod_q;\n"
            "        input [11:0] x; input [11:0] y; reg [12:0] d;\n"
            "        begin d = {1'b0, x} + 13'd3329 - {1'b0, y}; sub_mod_q = (d >= 13'd3329) ? d - 13'd3329 : d[11:0]; end\n"
            "    endfunction\n"
            "    wire [11:0] base1 = sub_mod_q(sub_mod_q(p3_q, p0_q), p1_q);\n"
            "`else\n"
            "    wire [11:0] base1=add_mod_q(p3_q,p4_q);\n"
            "`endif\n")
    s = rep(s, f"                {st}MUL0: begin p0_q<=mul_reduced;state<={st}MUL1;end\n"
               f"                {st}MUL1: begin p1_q<=mul_reduced;state<={st}MUL2;end\n",
            "`ifdef TRUSTEDGE_FAST_BASEMUL\n"
            f"                {st}MUL0: begin p0_q<=mul_reduced;p1_q<=mul2_reduced;state<={st}MUL1;end\n"
            f"                {st}MUL1: begin p2_q<=mul_reduced;p3_q<=mul2_reduced;state<={st}ACCUM;end\n"
            "`else\n"
            f"                {st}MUL0: begin p0_q<=mul_reduced;state<={st}MUL1;end\n"
            f"                {st}MUL1: begin p1_q<=mul_reduced;state<={st}MUL2;end\n"
            "`endif\n")
    return s


def edit_tb(s: str) -> str:
    a = s.index("`ifdef TRUSTEDGE_ASIC_SRAM\n    localparam [15:0] EXPECTED_KYBER_CYCLES")
    b = s.index("`endif", s.index("MLKEM_STAGE_WAIT_CYCLES = 40000;", a)) + len("`endif")
    reg = s[a:b]
    for name in ("KYBER", "MLKEM512", "KPKE", "CODEC", "RUNTIME_ENCRYPT"):
        assert reg.count(f"localparam [15:0] EXPECTED_{name}_CYCLES =") == 2, name
        reg = reg.replace(f"localparam [15:0] EXPECTED_{name}_CYCLES =",
                          f"localparam integer EXPECTED_{name}_CYCLES_OLD =")
    reg = rep(reg, "    localparam integer EXPECTED_ENCAPS_CYCLES_RAW = 64652 +",
              "    localparam integer EXPECTED_ENCAPS_CYCLES_RAW_OLD = 64652 +")
    reg = rep(reg, "    localparam [15:0] EXPECTED_ENCAPS_CYCLES =\n"
                   "        (EXPECTED_ENCAPS_CYCLES_RAW > 65535) ? 16'hFFFF :\n"
                   "        EXPECTED_ENCAPS_CYCLES_RAW;\n",
              "    // decapsulation, measured with the replaced engines (results/system_sim/summary.json)\n"
              "    localparam integer EXPECTED_DECAPS_CYCLES_RAW_OLD = 95793 +\n"
              "        DECAPS_SHARED_PERMUTATIONS * KECCAK_EXTRA_CYCLES_PER_PERM;\n")
    reg = rep(reg, "    localparam [15:0] EXPECTED_ENCAPS_CYCLES = 16'd55692;\n",
              "    localparam integer EXPECTED_ENCAPS_CYCLES_RAW_OLD = 55692;\n"
              "    localparam integer EXPECTED_DECAPS_CYCLES_RAW_OLD = 81457 +\n"
              "        DECAPS_SHARED_PERMUTATIONS * KECCAK_EXTRA_CYCLES_PER_PERM;\n")
    reg += """
    // Packed-pair NTT (TRUSTEDGE_PACKED_NTT): each transform is shorter by the difference between the
    // replaced engine's cycles and the packed engine's (988 forward, 1116 inverse, EXTRA_STAGE = 1), so the
    // expected values follow from the number of transforms in each operation, like the Keccak term above.
`ifdef TRUSTEDGE_ASIC_SRAM
    localparam integer NTT_FWD_DIFF = 6274 - 988;      // single-port engine minus packed engine
    localparam integer NTT_INV_DIFF = 7554 - 1116;
`else
    localparam integer NTT_FWD_DIFF = 4482 - 988;      // dual-port engine minus packed engine
    localparam integer NTT_INV_DIFF = 5762 - 1116;
`endif
    // Two-lane engine (TRUSTEDGE_PACKED2): 568 forward and 569 inverse cycles instead of 988 and 1116.
`ifdef TRUSTEDGE_PACKED2
    localparam integer NTT_P2_FWD = 988 - 568;
    localparam integer NTT_P2_INV = 1116 - 569;
`else
    localparam integer NTT_P2_FWD = 0;
    localparam integer NTT_P2_INV = 0;
`endif
`ifdef TRUSTEDGE_PACKED_NTT
    localparam integer NTT_FWD_SAVED = NTT_FWD_DIFF + NTT_P2_FWD;
    localparam integer NTT_INV_SAVED = NTT_INV_DIFF + NTT_P2_INV;
`else
    localparam integer NTT_FWD_SAVED = 0;
    localparam integer NTT_INV_SAVED = 0;
`endif
    // Hash overlap (TRUSTEDGE_HASH_OVERLAP): H(ek), H(c) and J(z||c) run on a second sequencer during the
    // decryption, so a decapsulation saves the shorter of the two phases and pays one hand-over cycle,
    // and each of an encapsulation's two hash jobs adds one hand-over cycle. Phase lengths come from the
    // state profile (tb/decaps_state_profiler.sv): the decryption takes 9,239 cycles with the packed engine
    // (two forward and one inverse transform), the three hashes 7,668 cycles plus the serial-Keccak term
    // of their 18 permutations.
    // Step D (TRUSTEDGE_STREAM_IO): one wait cycle less per element of ten read loops. Decryption: 512
    // coefficients of u, 256 operand pairs read twice, 256 message coefficients; encryption: 256 noise pairs
    // and 512 coefficients of y (runtime inputs only), 768 results read back; codec: 768 coefficients
    // encoded and 768 bytes decoded; comparison: 768 ciphertext bytes.
`ifdef TRUSTEDGE_STREAM_IO
    localparam integer DECRYPT_STREAM_SAVED = 512 + 2 * 256 + 256;
    localparam integer READBACK_STREAM_SAVED = 768;
    localparam integer CODEC_STREAM_SAVED = 768 + 768;
    localparam integer ENCRYPT_STREAM_SAVED = 256 + 512 + READBACK_STREAM_SAVED + CODEC_STREAM_SAVED;
    localparam integer COMPARE_STREAM_SAVED = 768;
`else
    localparam integer DECRYPT_STREAM_SAVED = 0;
    localparam integer READBACK_STREAM_SAVED = 0;
    localparam integer CODEC_STREAM_SAVED = 0;
    localparam integer ENCRYPT_STREAM_SAVED = 0;
    localparam integer COMPARE_STREAM_SAVED = 0;
`endif
    // Fast pointwise products (TRUSTEDGE_FAST_BASEMUL): three multiply states less per coefficient pair,
    // 768 pairs in the encryption (3 outputs x 2 columns x 128) and 256 in the decryption.
`ifdef TRUSTEDGE_FAST_BASEMUL
    localparam integer ENCRYPT_FAST_SAVED = 3 * 768;
    localparam integer DECRYPT_FAST_SAVED = 3 * 256;
`else
    localparam integer ENCRYPT_FAST_SAVED = 0;
    localparam integer DECRYPT_FAST_SAVED = 0;
`endif
    // Fast feed (TRUSTEDGE_FAST_FEED): one cycle less per byte hashed (H(ek) 800, H(c) 768, J 800), except
    // at the five permutations inside each absorption (136-byte blocks), where the feeder waits for the
    // sponge anyway and the removed state had overlapped the permutation; and, with the streamed loops,
    // one cycle less per coefficient of u loaded (512).
`ifdef TRUSTEDGE_FAST_FEED
    localparam integer FEED_HASH_SAVED = (800 - 5) + (768 - 5) + (800 - 5);
    localparam integer FEED_ENCAPS_SAVED = (800 - 5) + (768 - 5);
`ifdef TRUSTEDGE_STREAM_IO
    localparam integer FEED_U_SAVED = 512;
`else
    localparam integer FEED_U_SAVED = 0;
`endif
`else
    localparam integer FEED_HASH_SAVED = 0;
    localparam integer FEED_ENCAPS_SAVED = 0;
    localparam integer FEED_U_SAVED = 0;
`endif
    // One byte per cycle (TRUSTEDGE_FAST_HASH): of the N - 1 gaps between the N bytes of a hash, each loses
    // its request state except the five that span a mid-absorption permutation (the first byte keeps its
    // request state, unlike the wait-state removal above, which also shortened it): N - 6 per hash.
`ifdef TRUSTEDGE_FAST_HASH
    localparam integer FAST_HASH_SAVED = (800 - 6) + (768 - 6) + (800 - 6);
    localparam integer FAST_HASH_J_SAVED = 800 - 6;
    localparam integer FAST_ENCAPS_SAVED = (800 - 6) + (768 - 6);
`else
    localparam integer FAST_HASH_SAVED = 0;
    localparam integer FAST_HASH_J_SAVED = 0;
    localparam integer FAST_ENCAPS_SAVED = 0;
`endif
    // Streamed output (TRUSTEDGE_STREAM_OUT): the encoding pass after the codec's start (U: 128 groups of
    // two cycles per coefficient and five byte writes; V: 128 pairs of two cycles per coefficient and one
    // write; with the streamed loops) gives way to one flush cycle.
`ifdef TRUSTEDGE_STREAM_OUT
    localparam integer OUT_STREAM_SAVED = 128 * (4 * 2 + 5) + 128 * (2 * 2 + 1) - 1;
`else
    localparam integer OUT_STREAM_SAVED = 0;
`endif
    // Folded read-back (TRUSTEDGE_FOLD_READBACK): the read-back pass (one request state, then two cycles
    // per byte for 768 bytes) disappears from every codec run.
`ifdef TRUSTEDGE_FOLD_READBACK
    localparam integer FOLD_SAVED = 1 + 2 * 768;
`else
    localparam integer FOLD_SAVED = 0;
`endif
    // Prefetched operands (TRUSTEDGE_PREFETCH, bound runtime key): every step but the first of each of
    // the three outputs loses its two wait states and its capture state.
`ifdef TRUSTEDGE_PREFETCH
    localparam integer PREFETCH_SAVED = 3 * 255 * 3;
    // and in the decryption, the four pair-fetch states of every pair but the first of each polynomial
    localparam integer DEC_PREFETCH_SAVED = 2 * 127 * 4;
`else
    localparam integer PREFETCH_SAVED = 0;
    localparam integer DEC_PREFETCH_SAVED = 0;
`endif
    // Tight loops (TRUSTEDGE_TIGHT_LOOPS): the comparison keeps one request state for all 768 bytes, and
    // with a bound runtime key the two write states of every pair but the last of each output vanish.
`ifdef TRUSTEDGE_TIGHT_LOOPS
    localparam integer TIGHT_CMP_SAVED = 767;
    localparam integer TIGHT_WRITE_SAVED = 3 * 127 * 2;
`else
    localparam integer TIGHT_CMP_SAVED = 0;
    localparam integer TIGHT_WRITE_SAVED = 0;
`endif
    // Fast decode check (TRUSTEDGE_FAST_CHECK): per U group four byte requests and three coefficient
    // requests less, per V pair one coefficient request less, in every codec run.
`ifdef TRUSTEDGE_FAST_CHECK
    localparam integer CHECK_SAVED = 128 * (4 + 3) + 128 * 1;
`else
    localparam integer CHECK_SAVED = 0;
`endif
    // Fast y (TRUSTEDGE_FAST_Y, runtime encryption): per polynomial of r, one fetch state for 127 of the
    // 128 pairs and one request state for 255 of the 256 coefficients read back.
`ifdef TRUSTEDGE_FAST_Y
    localparam integer FAST_Y_SAVED = 2 * (127 + 255);
`else
    localparam integer FAST_Y_SAVED = 0;
`endif
    // Fast noise sampling (TRUSTEDGE_FAST_PRF, runtime encryption): the 256 emit states of each of the five
    // noise polynomials vanish except the last block's pairs, two for eta1 = 3 and four for eta2 = 2.
    // Fused comparison (TRUSTEDGE_FUSED_CMP, decapsulation): the request state and the 768 check states.
`ifdef TRUSTEDGE_FUSED_CMP
    localparam integer FUSED_CMP_SAVED = 1 + 768;
`else
    localparam integer FUSED_CMP_SAVED = 0;
`endif
    // Fast read-back (TRUSTEDGE_FAST_READ, every encryption): of the 256 request states per polynomial, a U
    // polynomial keeps the first and one after each group of four but the last (64), the V polynomial one.
    // Pipelined decode check (TRUSTEDGE_PIPE_CHECK, every codec run): 15 states per U group and 7 per V
    // pair before (128 * 15 + 128 * 7 = 2,816); now one start state and 904 pipeline cycles (640 U bytes at
    // one per cycle, 128 V groups at two coefficients each, the fill and the three-stage drain;
    // scratchpad model of the same control equations).
    // Pair port (TRUSTEDGE_PAIR_PORT, runtime encryption): per polynomial of r, one write state per pair
    // instead of two (128) and one read-back state per pair instead of per coefficient (128).
    // Pipelined product (TRUSTEDGE_PIPE_MAC, bound runtime key): per output polynomial, the two operand
    // wait states, the operand state, 256 x (MUL0, MUL1, ACCUM) and the two write states of the last pair
    // (773 cycles) become 256 issue cycles and a four-cycle drain (260).
    // Streamed decryption (TRUSTEDGE_DEC_STREAM): u and the message keep one request state each per
    // polynomial instead of one per coefficient (2 x 255 + 255); the product's four pair-fetch states,
    // 256 x (MUL0, MUL1, ACCUM) and 128 x (WRITE0, WRITE1) (1,032 cycles) become a first pass of 128 issue
    // cycles and a three-cycle drain (131) and a second pass that issues on even cycles (258).
`ifdef TRUSTEDGE_DEC_STREAM
    localparam integer DEC_STREAM_SAVED = 2 * 255 + 255 + (8 + 3 * 256 + 2 * 128) - (131 + 258);
`else
    localparam integer DEC_STREAM_SAVED = 0;
`endif
`ifdef TRUSTEDGE_PIPE_MAC
    localparam integer PMAC_SAVED = 3 * ((2 + 1 + 3 * 256 + 2) - 260);
`else
    localparam integer PMAC_SAVED = 0;
`endif
`ifdef TRUSTEDGE_PAIR_PORT
    localparam integer PAIR_SAVED = 2 * (128 + 128);
`else
    localparam integer PAIR_SAVED = 0;
`endif
    // Segmented check (TRUSTEDGE_SEG_CHECK, every codec run): u0's and u1's segments (329 cycles each)
    // run while the next polynomial is computed; the final part checks only v: 261 pipeline cycles
    // instead of the start state and 904 (scratchpad model of the same control, pipe_model_seg.py).
    // Background noise sampling (TRUSTEDGE_BG_PRF, runtime encryption): the encryption no longer waits for
    // the three eta2 polynomials (196 cycles each with the one-round Keccak, 144 more for their single
    // permutation with the serial one) and the completion state; they run hidden in the y path's NTT waits.
`ifdef TRUSTEDGE_BG_PRF
    localparam integer BG_PRF_SAVED = 3 * (196 + ((KECCAK_EXTRA_CYCLES_PER_PERM != 0) ? 144 : 0)) + 1;
`else
    localparam integer BG_PRF_SAVED = 0;
`endif
    // Streamed inverse transform (TRUSTEDGE_STREAM_INV, runtime encryption): per output polynomial the start
    // state and the 569-cycle transform become the 327 cycles that the engine's stream mode needs after the
    // last pair (tb/tb_ntt_stream.sv) plus the cycle in which the controller sees it done.
    // Streamed forward transforms (TRUSTEDGE_STREAM_FWD): the engine needs 300 cycles after the last pair
    // (tb/tb_ntt_stream.sv) and the controller one more to see it done. y path (runtime encryption), per
    // polynomial of r: 128 pair writes, the start state and 568 cycles (697) become 255 write cycles and 301;
    // u load (decryption), per polynomial: the start state and 568 (569) become 301.
    // r0 straight into the NTT (TRUSTEDGE_PRF_TO_NTT, runtime encryption): r0's y step (fetch, 255 write
    // cycles and the 301-cycle transform end) becomes the rest of r0's transform after r1 is sampled: the
    // transform (568 cycles) starts when r0 is complete, r1 takes T_ETA1 = 285 cycles (288 more with the
    // serial Keccak, two permutations), and at least the one cycle that sees it done remains.
    localparam integer T_ETA1 = 285 + ((KECCAK_EXTRA_CYCLES_PER_PERM != 0) ? 2 * 144 : 0);
`ifdef TRUSTEDGE_PRF_TO_NTT
    localparam integer PRF_NTT_SAVED = (1 + 255 + 301) - ((568 > T_ETA1) ? (568 - T_ETA1) : 1);
`else
    localparam integer PRF_NTT_SAVED = 0;
`endif
    // Streamed decryption inverse (TRUSTEDGE_STREAM_DEC_INV): its start state and 569 cycles become the
    // 327-cycle tail after the last pair plus the cycle that sees it done.
`ifdef TRUSTEDGE_STREAM_DEC_INV
    localparam integer DEC_INV_SAVED = (1 + 569) - (327 + 1);
`else
    localparam integer DEC_INV_SAVED = 0;
`endif
    // Serial Keccak, decapsulation (TRUSTEDGE_PRF_TO_NTT, with TRUSTEDGE_POLY_GUARD): the shortened
    // re-encryption becomes bound by the shared sponge. Its u0 read waits 93 cycles, until the sampler has
    // finished e2 and J(z||c) has taken the sponge (the strict wait inside a decapsulation), and J, slowed by
    // the codec's segment checks on the reference RAM (2,341 cycles instead of 1,863), ends 325 cycles after
    // the re-encryption. Both are measured (tb/reenc_timeline_probe.sv with CAC_TL_PROBE=1, and
    // tb/decaps_state_profiler.sv); with the one-round Keccak the sampler and J end in time.
`ifdef TRUSTEDGE_PRF_TO_NTT
    localparam integer SPONGE_TAIL_CYCLES = (KECCAK_EXTRA_CYCLES_PER_PERM != 0) ? 93 + 325 : 0;
`else
    localparam integer SPONGE_TAIL_CYCLES = 0;
`endif
`ifdef TRUSTEDGE_STREAM_FWD
    localparam integer STREAM_Y_SAVED = 2 * ((128 + 1 + 568) - (255 + 300 + 1));
    localparam integer STREAM_U_SAVED = 2 * ((1 + 568) - (300 + 1));
`else
    localparam integer STREAM_Y_SAVED = 0;
    localparam integer STREAM_U_SAVED = 0;
`endif
`ifdef TRUSTEDGE_STREAM_INV
    localparam integer STREAM_INV_SAVED = 3 * ((1 + 569) - (327 + 1));
`else
    localparam integer STREAM_INV_SAVED = 0;
`endif
`ifdef TRUSTEDGE_SEG_CHECK
    localparam integer SEG_SAVED = (1 + 904) - 261;
`else
    localparam integer SEG_SAVED = 0;
`endif
`ifdef TRUSTEDGE_PIPE_CHECK
    localparam integer PIPE_SAVED = 128 * 15 + 128 * 7 - (1 + 904);
`else
    localparam integer PIPE_SAVED = 0;
`endif
`ifdef TRUSTEDGE_FAST_READ
    localparam integer READ_FAST_SAVED = 2 * (256 - 64) + (256 - 1);
`else
    localparam integer READ_FAST_SAVED = 0;
`endif
`ifdef TRUSTEDGE_FAST_PRF
    localparam integer PRF_SAVED = 2 * (256 - 2) + 3 * (256 - 4);
`else
    localparam integer PRF_SAVED = 0;
`endif
`ifdef TRUSTEDGE_HASH_OVERLAP
    localparam integer DECRYPT_CYCLES = 9239 + 2 * (NTT_FWD_DIFF - NTT_FWD_SAVED) +
        (NTT_INV_DIFF - NTT_INV_SAVED) - DECRYPT_STREAM_SAVED - DECRYPT_FAST_SAVED - FEED_U_SAVED -
        DEC_STREAM_SAVED - STREAM_U_SAVED - DEC_INV_SAVED -
        DEC_PREFETCH_SAVED;
    localparam integer HASH_CYCLES = 7668 + 18 * KECCAK_EXTRA_CYCLES_PER_PERM - FEED_HASH_SAVED -
        FAST_HASH_SAVED;
`ifdef TRUSTEDGE_DEFER_J
    // Deferred J (TRUSTEDGE_DEFER_J): J(z||c) leaves the overlap and runs hidden in the re-encryption; the
    // decryption overlaps H(ek) and H(c) only, and one join cycle precedes the selection. J takes 1,793
    // cycles with the one-round Keccak and 144 more for each of its six permutations with the serial
    // Keccak, 2,657 (both measured on the sequencer by tb/j_phase_probe.sv, CAC_J_PROBE=1; with the
    // one-round Keccak the result does not depend on J, since H(ek) and H(c) alone end before the
    // decryption).
    localparam integer J_CYCLES = ((KECCAK_EXTRA_CYCLES_PER_PERM != 0) ? 1793 + 6 * 144 : 1793) -
        FAST_HASH_J_SAVED;
    localparam integer DECAPS_OVERLAP_SAVED = J_CYCLES +
        ((DECRYPT_CYCLES < HASH_CYCLES - J_CYCLES) ? DECRYPT_CYCLES : HASH_CYCLES - J_CYCLES) - 2;
`else
    localparam integer DECAPS_OVERLAP_SAVED =
        ((DECRYPT_CYCLES < HASH_CYCLES) ? DECRYPT_CYCLES : HASH_CYCLES) - 1;
`endif
    localparam integer ENCAPS_HANDOVER_CYCLES = 2;
`else
    localparam integer DECAPS_OVERLAP_SAVED = 0;
    localparam integer ENCAPS_HANDOVER_CYCLES = 0;
`endif
    // transforms per operation (forward, inverse): NTT self-test 1/0, ML-KEM self-test 2/2, K-PKE key
    // generation 4/0, codec stage 0/3, encryption and encapsulation 2/3, decapsulation 4/4
    localparam [15:0] EXPECTED_KYBER_CYCLES = EXPECTED_KYBER_CYCLES_OLD - NTT_FWD_SAVED;
    localparam [15:0] EXPECTED_MLKEM512_CYCLES = EXPECTED_MLKEM512_CYCLES_OLD -
        2 * NTT_FWD_SAVED - 2 * NTT_INV_SAVED;
    localparam [15:0] EXPECTED_KPKE_CYCLES = EXPECTED_KPKE_CYCLES_OLD - 4 * NTT_FWD_SAVED;
    localparam [15:0] EXPECTED_CODEC_CYCLES = EXPECTED_CODEC_CYCLES_OLD - 3 * NTT_INV_SAVED -
        READBACK_STREAM_SAVED - CODEC_STREAM_SAVED - ENCRYPT_FAST_SAVED -
        OUT_STREAM_SAVED - FOLD_SAVED - CHECK_SAVED - READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED;  // the codec stage runs on fixed inputs
    localparam [15:0] EXPECTED_RUNTIME_ENCRYPT_CYCLES = EXPECTED_RUNTIME_ENCRYPT_CYCLES_OLD -
        2 * NTT_FWD_SAVED - 3 * NTT_INV_SAVED - ENCRYPT_STREAM_SAVED - ENCRYPT_FAST_SAVED -
        OUT_STREAM_SAVED - FOLD_SAVED - PREFETCH_SAVED - TIGHT_WRITE_SAVED - CHECK_SAVED - FAST_Y_SAVED - PAIR_SAVED - PMAC_SAVED -
        PRF_SAVED - BG_PRF_SAVED - STREAM_INV_SAVED - STREAM_Y_SAVED - PRF_NTT_SAVED - READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED;
    localparam integer EXPECTED_ENCAPS_CYCLES_RAW = EXPECTED_ENCAPS_CYCLES_RAW_OLD -
        2 * NTT_FWD_SAVED - 3 * NTT_INV_SAVED + ENCAPS_HANDOVER_CYCLES - ENCRYPT_STREAM_SAVED -
        ENCRYPT_FAST_SAVED - FEED_ENCAPS_SAVED - FAST_ENCAPS_SAVED - OUT_STREAM_SAVED - FOLD_SAVED - PREFETCH_SAVED -
        TIGHT_WRITE_SAVED - CHECK_SAVED - FAST_Y_SAVED - PAIR_SAVED - PMAC_SAVED -
        PRF_SAVED - BG_PRF_SAVED - STREAM_INV_SAVED - STREAM_Y_SAVED - PRF_NTT_SAVED - READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED;
    localparam integer EXPECTED_DECAPS_CYCLES_RAW = EXPECTED_DECAPS_CYCLES_RAW_OLD -
        4 * NTT_FWD_SAVED - 4 * NTT_INV_SAVED - DECAPS_OVERLAP_SAVED - ENCRYPT_STREAM_SAVED -
        COMPARE_STREAM_SAVED - DECRYPT_STREAM_SAVED - ENCRYPT_FAST_SAVED - DECRYPT_FAST_SAVED -
        FEED_HASH_SAVED - FAST_HASH_SAVED - FEED_U_SAVED - DEC_STREAM_SAVED - STREAM_U_SAVED - DEC_INV_SAVED - OUT_STREAM_SAVED - FOLD_SAVED - PREFETCH_SAVED -
        DEC_PREFETCH_SAVED - TIGHT_WRITE_SAVED - TIGHT_CMP_SAVED - CHECK_SAVED - FAST_Y_SAVED - PAIR_SAVED - PMAC_SAVED -
        PRF_SAVED - BG_PRF_SAVED - STREAM_INV_SAVED - STREAM_Y_SAVED - PRF_NTT_SAVED - FUSED_CMP_SAVED - READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED +
        SPONGE_TAIL_CYCLES;
    // the 16-bit response field saturates
    localparam [15:0] EXPECTED_ENCAPS_CYCLES =
        (EXPECTED_ENCAPS_CYCLES_RAW > 65535) ? 16'hFFFF : EXPECTED_ENCAPS_CYCLES_RAW;
    localparam [15:0] EXPECTED_DECAPS_CYCLES =
        (EXPECTED_DECAPS_CYCLES_RAW > 65535) ? 16'hFFFF : EXPECTED_DECAPS_CYCLES_RAW;"""
    s = s[:a] + reg + s[b:]
    x = "            mlkem_stage_cycles !== 16'hFFFF ||\n"
    assert s.count(x) == 2, s.count(x)
    return s.replace(x, "            mlkem_stage_cycles !== EXPECTED_DECAPS_CYCLES ||\n")


EDITS = {"rtl/trustedge_top.v": edit_top,
         "rtl/mlkem512/mlkem512_partial_kem_selftests.sv": edit_decaps,
         "rtl/mlkem512/mlkem512_kpke_encrypt_selftest.sv": edit_encrypt,
         "rtl/mlkem512/mlkem512_ciphertext_codec.sv": edit_codec,
         "sim/tb/tb_trustedge_spi.sv": edit_tb}


def main(src: Path, dst: Path, cac_rtl: Path, diff_out: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    diff = []
    for rel, fn in EDITS.items():
        old = (src / rel).read_bytes().decode().replace("\r\n", "\n")
        new = fn(old)
        (dst / rel).write_bytes(new.encode())
        diff += difflib.unified_diff(old.splitlines(True), new.splitlines(True), "a/" + rel, "b/" + rel)
    # the packed engine and its reducer, from the notebook's own rtl/
    for f in ("kyber_ntt_engine_packed.sv", "kyber_ntt_engine_packed2.sv", "barrett_reduce_1c.v"):
        shutil.copy(cac_rtl / f, dst / "rtl/kyber" / f)
    diff_out.write_bytes("".join(diff).encode())
    print(f"{dst}: {len(EDITS)} files edited, diff {sum(1 for l in diff if l[:1] in '+-')} lines")


if __name__ == "__main__":
    out = Path(sys.argv[2])
    main(Path(sys.argv[1]), out, Path(sys.argv[3]),
         Path(sys.argv[4]) if len(sys.argv) > 4 else out.parent / (out.name + ".diff"))
