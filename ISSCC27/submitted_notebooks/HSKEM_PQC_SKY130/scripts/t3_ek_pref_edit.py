"""TRUSTEDGE_T3_EK_PREF (with TRUSTEDGE_FAST_HASH and TRUSTEDGE_FAST_FEED): the H(ek) feed of the decapsulation (and of
the encapsulation, which shares the hash sequencer) took the first byte of every 24-bit ek word in the cycle the ekpke
macro presented it: macro (falling edge) -> byte select -> sponge absorb -> sponge_state, a half-cycle path that fails
with the macro's SPICE delay at ss (-0.66 ns, 36 endpoints in round 4).

With the define on, the word in use is held in a register (ek_cur_r) and every byte comes from it; the macro is
addressed with the next word while the current one is consumed, and ek_cur_r loads the next word when the third byte
of the current one is taken. That word has then been presented for at least a full cycle (the address changes at most
once every three bytes; while the sponge permutes nothing is taken and the address is held). The first word is
presented from ST_HEK_START, so it is stable from the falling edge in ST_HEK_REQ; a wait state (ST_HEK_WAIT, used
without FAST_FEED) loads it. One more cycle per encapsulation (none per decapsulation, where H(ek) overlaps other work); the hash input is unchanged.
SPDX-License-Identifier: Apache-2.0
"""


def _rep(s: str, a: str, b: str) -> str:
    assert s.count(a) == 1, (s.count(a), a[:80])
    return s.replace(a, b)


def edit_ek_pref(s: str) -> str:
    old_a = ("    assign ekpke_ext_pair_addr = (hk_take && (ek_byte_sub == 2'd2) && (sponge_feed_index < 10'd767)) ?\n"
             "                                 ekpke_ext_pair_addr_q + 8'd1 : ekpke_ext_pair_addr_q;\n")
    s = _rep(s, old_a,
             "`ifdef TRUSTEDGE_T3_EK_PREF\n"
             "    // word 0 from ST_HEK_START; then the word after the one in ek_cur_r\n"
             "    assign ekpke_ext_pair_addr = ((sp_state == ST_HEK_START) || (sp_state == ST_HEK_REQ)) ? 8'd0 :\n"
             "                                 ((sp_state == ST_HEK_WAIT) || (sp_state == ST_HEK_FEED)) ?\n"
             "                                 ekpke_ext_pair_addr_q + 8'd1 : ekpke_ext_pair_addr_q;\n"
             "    reg  [23:0] ek_cur_r;                  // the ek word whose bytes are fed\n"
             "    always @(posedge clk)\n"
             "        if ((sp_state == ST_HEK_WAIT) || (hk_take && (ek_byte_sub == 2'd2))) ek_cur_r <= ekpke_ext_pair_data;\n"
             "`else\n" + old_a + "`endif\n")
    old_b = ("    wire [7:0] ek_feed_byte = (ek_byte_sub == 2'd0) ?\n"
             "                              ekpke_ext_pair_data[7:0] :\n"
             "                              (ek_byte_sub == 2'd1) ?\n"
             "                              ekpke_ext_pair_data[15:8] :\n"
             "                              ekpke_ext_pair_data[23:16];\n")
    s = _rep(s, old_b,
             "`ifdef TRUSTEDGE_T3_EK_PREF\n"
             "    wire [7:0] ek_feed_byte = (ek_byte_sub == 2'd0) ? ek_cur_r[7:0] :\n"
             "                              (ek_byte_sub == 2'd1) ? ek_cur_r[15:8] : ek_cur_r[23:16];\n"
             "`else\n" + old_b + "`endif\n")
    old_c = "                ST_HEK_REQ: `DCP_HS<=ST_HEK_FEED;      // one-cycle read latency\n"
    s = _rep(s, old_c,
             "`ifdef TRUSTEDGE_T3_EK_PREF\n"
             "                ST_HEK_REQ: `DCP_HS<=ST_HEK_WAIT;      // ek_cur_r takes word 0 at the end of WAIT\n"
             "`else\n" + old_c + "`endif\n")
    return s
