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
    return rep(s, a, "`ifdef TRUSTEDGE_PACKED_NTT\n"
                     "    // packed-pair, layer-fused NTT: same ports, one 24 x 128 single-port coefficient store\n"
                     "    kyber_ntt_engine_packed #(.EXTRA_STAGE(1'b1)) u_shared_ntt (\n"
                     "`else\n" + a + "`endif\n")


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
    return head + s


def edit_encrypt(s: str) -> str:
    # step D in the encryption: the noise and NTT RAMs answer one cycle after the address
    for a, b in (("S_Y_FETCH: state<=S_Y_WAIT;", "S_Y_FETCH: state<=S_Y_WRITE0;"),
                 ("S_Y_READ_REQ: state<=S_Y_READ_WAIT;", "S_Y_READ_REQ: state<=S_Y_READ_CAP;"),
                 ("S_READ_REQ: state<=S_READ_WAIT;", "S_READ_REQ: state<=S_READ_LOAD;")):
        s = rep(s, "                " + a + "\n",
                "`ifdef TRUSTEDGE_STREAM_IO\n                " + b + "      // one-cycle read latency\n"
                "`else\n                " + a + "\n`endif\n")
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
`ifdef TRUSTEDGE_PACKED_NTT
    localparam integer NTT_FWD_SAVED = NTT_FWD_DIFF;
    localparam integer NTT_INV_SAVED = NTT_INV_DIFF;
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
`ifdef TRUSTEDGE_HASH_OVERLAP
    localparam integer DECRYPT_CYCLES = 9239 + 2 * (NTT_FWD_DIFF - NTT_FWD_SAVED) +
        (NTT_INV_DIFF - NTT_INV_SAVED) - DECRYPT_STREAM_SAVED;
    localparam integer HASH_CYCLES = 7668 + 18 * KECCAK_EXTRA_CYCLES_PER_PERM;
    localparam integer DECAPS_OVERLAP_SAVED =
        ((DECRYPT_CYCLES < HASH_CYCLES) ? DECRYPT_CYCLES : HASH_CYCLES) - 1;
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
        READBACK_STREAM_SAVED - CODEC_STREAM_SAVED;      // the codec stage runs on fixed inputs
    localparam [15:0] EXPECTED_RUNTIME_ENCRYPT_CYCLES = EXPECTED_RUNTIME_ENCRYPT_CYCLES_OLD -
        2 * NTT_FWD_SAVED - 3 * NTT_INV_SAVED - ENCRYPT_STREAM_SAVED;
    localparam integer EXPECTED_ENCAPS_CYCLES_RAW = EXPECTED_ENCAPS_CYCLES_RAW_OLD -
        2 * NTT_FWD_SAVED - 3 * NTT_INV_SAVED + ENCAPS_HANDOVER_CYCLES - ENCRYPT_STREAM_SAVED;
    localparam integer EXPECTED_DECAPS_CYCLES_RAW = EXPECTED_DECAPS_CYCLES_RAW_OLD -
        4 * NTT_FWD_SAVED - 4 * NTT_INV_SAVED - DECAPS_OVERLAP_SAVED - ENCRYPT_STREAM_SAVED -
        COMPARE_STREAM_SAVED - DECRYPT_STREAM_SAVED;
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
    for f in ("kyber_ntt_engine_packed.sv", "barrett_reduce_1c.v"):
        shutil.copy(cac_rtl / f, dst / "rtl/kyber" / f)
    diff_out.write_bytes("".join(diff).encode())
    print(f"{dst}: {len(EDITS)} files edited, diff {sum(1 for l in diff if l[:1] in '+-')} lines")


if __name__ == "__main__":
    out = Path(sys.argv[2])
    main(Path(sys.argv[1]), out, Path(sys.argv[3]),
         Path(sys.argv[4]) if len(sys.argv) > 4 else out.parent / (out.name + ".diff"))
