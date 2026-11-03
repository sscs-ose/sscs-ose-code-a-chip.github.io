// ============================================================================
//  fp32_add.v -- thin wrapper around fadd32() (see fp32_funcs.vh)
// ============================================================================
`timescale 1ns/1ps
module fp32_add_c (
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y
);
  `include "fp32_funcs.vh"
  assign y = fadd32(a, b);
endmodule
