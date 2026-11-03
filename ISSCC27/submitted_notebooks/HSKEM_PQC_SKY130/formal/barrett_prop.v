// Property wrapper: barrett_reduce must equal a mod 3329 for every input.
// SPDX-License-Identifier: Apache-2.0
module barrett_prop (input wire [23:0] a, output wire ok, output wire ok_range);
    wire [11:0] r;
    barrett_reduce u_dut (.a(a), .r(r));
    // reference: remainder via the synthesizer's own constant divider
    wire [23:0] ref_r = a % 24'd3329;
    assign ok = (r == ref_r[11:0]) && (ref_r[23:12] == 12'd0);
    // the product range actually used by the NTT: a <= 3328*3328
    assign ok_range = (a > 24'd11075584) | ok;
endmodule
