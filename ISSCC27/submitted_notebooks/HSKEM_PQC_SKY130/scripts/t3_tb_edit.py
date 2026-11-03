"""Expected cycle counts of the testbench under the T3 switches (with them off the testbench is unchanged).

TRUSTEDGE_T3_MM_PIPE: one more cycle for each of the 512 pair products of key generation (K-PKE key generation, and the
stages that repeat it). TRUSTEDGE_T3_MAC_DEEP: two more pipeline stages in each pipelined product (encryption and
encapsulation +6, decapsulation +10 cycles, measured). TRUSTEDGE_T3_PMAC_RAW: one more stage in the encryption's
product (+3 per encryption and encapsulation) and two in the decapsulation's (+7 with its re-encryption, measured).
TRUSTEDGE_T3_LOAD_PIPE: +1 per encryption and for the codec stage (the codec stream is one cycle later); TRUSTEDGE_T3_MSG_PIPE: +1 per
decapsulation (drain of the message recovery); TRUSTEDGE_T3_EK_PREF: +1 per encapsulation (the wait
state that loads the first ek word), 0 per decapsulation, where H(ek) overlaps other work (measured). The numbers are measured in simulation and recorded here.
SPDX-License-Identifier: Apache-2.0
"""


def _rep(s: str, a: str, b: str) -> str:
    assert s.count(a) == 1, (s.count(a), a[:70])
    return s.replace(a, b)


def edit_tb_t3(s: str) -> str:
    s = _rep(s, "    localparam [15:0] EXPECTED_KYBER_CYCLES = EXPECTED_KYBER_CYCLES_OLD - NTT_FWD_SAVED;\n",
             """`ifdef TRUSTEDGE_T3_MM_PIPE
    localparam integer T3_KPKE_EXTRA = 512;
`else
    localparam integer T3_KPKE_EXTRA = 0;
`endif
`ifdef TRUSTEDGE_T3_MAC_DEEP
    localparam integer T3_MD_ENC = 6, T3_MD_ENCAPS = 6, T3_MD_DECAPS = 10;
`else
    localparam integer T3_MD_ENC = 0, T3_MD_ENCAPS = 0, T3_MD_DECAPS = 0;
`endif
`ifdef TRUSTEDGE_T3_PMAC_RAW
    localparam integer T3_PR_ENC = 3, T3_PR_ENCAPS = 3, T3_PR_DECAPS = 7;
`else
    localparam integer T3_PR_ENC = 0, T3_PR_ENCAPS = 0, T3_PR_DECAPS = 0;
`endif
`ifdef TRUSTEDGE_T3_LOAD_PIPE
    localparam integer T3_LP_ENC = 1, T3_LP_ENCAPS = 1, T3_LP_DECAPS = 1;
`else
    localparam integer T3_LP_ENC = 0, T3_LP_ENCAPS = 0, T3_LP_DECAPS = 0;
`endif
`ifdef TRUSTEDGE_T3_MSG_PIPE
    localparam integer T3_MP_DECAPS = 1;
`else
    localparam integer T3_MP_DECAPS = 0;
`endif
`ifdef TRUSTEDGE_T3_EK_PREF
    localparam integer T3_EP_ENCAPS = 1, T3_EP_DECAPS = 0;   // decapsulation: H(ek) overlaps other work (measured)
`else
    localparam integer T3_EP_ENCAPS = 0, T3_EP_DECAPS = 0;
`endif
    localparam integer T3_ENC_EXTRA = T3_MD_ENC + T3_PR_ENC + T3_LP_ENC;
    localparam integer T3_ENCAPS_EXTRA = T3_MD_ENCAPS + T3_PR_ENCAPS + T3_LP_ENCAPS + T3_EP_ENCAPS;
    localparam integer T3_DECAPS_EXTRA = T3_MD_DECAPS + T3_PR_DECAPS + T3_LP_DECAPS + T3_MP_DECAPS + T3_EP_DECAPS;
    localparam [15:0] EXPECTED_KYBER_CYCLES = EXPECTED_KYBER_CYCLES_OLD - NTT_FWD_SAVED;
""")
    s = _rep(s, "EXPECTED_KPKE_CYCLES_OLD - 4 * NTT_FWD_SAVED;", "EXPECTED_KPKE_CYCLES_OLD - 4 * NTT_FWD_SAVED + T3_KPKE_EXTRA;")
    # the codec stage (an encryption on fixed inputs) streams its coefficients through the same load stage
    s = _rep(s, "READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED;  // the codec stage runs on fixed inputs",
             "READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED + T3_LP_ENC;  // the codec stage runs on fixed inputs")
    s = _rep(s, "PRF_NTT_SAVED - READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED;\n    localparam integer EXPECTED_ENCAPS_CYCLES_RAW",
             "PRF_NTT_SAVED - READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED + T3_ENC_EXTRA;\n    localparam integer EXPECTED_ENCAPS_CYCLES_RAW")
    s = _rep(s, "PRF_NTT_SAVED - READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED;\n    localparam integer EXPECTED_DECAPS_CYCLES_RAW",
             "PRF_NTT_SAVED - READ_FAST_SAVED - PIPE_SAVED - SEG_SAVED + T3_ENCAPS_EXTRA;\n    localparam integer EXPECTED_DECAPS_CYCLES_RAW")
    s = _rep(s, "        SPONGE_TAIL_CYCLES;\n    // the 16-bit response field saturates", "        SPONGE_TAIL_CYCLES + T3_DECAPS_EXTRA;\n    // the 16-bit response field saturates")
    return s
