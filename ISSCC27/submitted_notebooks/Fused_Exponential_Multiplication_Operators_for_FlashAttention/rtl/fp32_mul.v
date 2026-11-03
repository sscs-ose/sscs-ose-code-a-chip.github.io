// ============================================================================
//  fp32_mul.v -- thin wrapper around fmul32() (see fp32_funcs.vh)
// ============================================================================
`timescale 1ns/1ps
module fp32_mul_c (
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y
);
  `include "fp32_funcs.vh"
  assign y = fmul32(a, b);
endmodule
