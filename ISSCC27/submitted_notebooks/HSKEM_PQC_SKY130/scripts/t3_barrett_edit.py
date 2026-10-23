"""TRUSTEDGE_T3_BARRETT_1C: slow-corner timing of every generic Barrett reducer (rtl/math/barrett_reduce.v).

With M = 5039 = floor(2^24 / 3329) the remainder a - floor(a M / 2^24) q is below 2q for every 24-bit input a (checked
exhaustively over all 2^24 inputs: largest value 5713), so one conditional subtraction gives a mod q; the second and third
are never taken. With the define on the reducer keeps only the first (as rtl/barrett_reduce_1c.v does): the results are
bit-identical and two 25-bit compare-and-subtract stages leave every reduction path. No cycle changes.
SPDX-License-Identifier: Apache-2.0
"""


def edit_barrett(s: str) -> str:
    a = "    assign r = r3[11:0];\n"
    assert s.count(a) == 1 and s.count("wire [24:0] r1 =") == 1, "unexpected barrett_reduce.v"
    return s.replace(a, "`ifdef TRUSTEDGE_T3_BARRETT_1C\n    assign r = r1[11:0];      // r0 < 2q for every 24-bit input\n"
                        "`else\n" + a + "`endif\n")
