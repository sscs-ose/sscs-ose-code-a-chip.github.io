// Barrett reduction mod q = 3329 with a single conditional subtraction.
//
// Derived from rtl/barrett_reduce.v. For every 24-bit input the quotient
// estimate t = floor(a*M / 2^24), M = floor(2^24 / q) = 5039, is at most one
// below the true quotient, so r0 = a - t*q lies in [0, 2q) and one subtraction
// suffices. This is proven formally for all 2^24 inputs (formal/, SAT) and
// confirmed exhaustively; the original second and third subtraction stages are
// redundant and sat on the NTT critical path.
// SPDX-License-Identifier: Apache-2.0
module barrett_reduce_1c #(
    parameter integer Q = 3329
) (
    input  wire [23:0] a,
    output wire [11:0] r
);
    localparam integer M = 5039;
    wire [36:0] prod = a * M[12:0];
    wire [12:0] t    = prod[36:24];
    wire [24:0] tq   = t * Q[11:0];
    wire [24:0] r0   = {1'b0, a} - tq;
    wire [24:0] r1   = (r0 >= Q) ? (r0 - Q) : r0;
    assign r = r1[11:0];
endmodule
