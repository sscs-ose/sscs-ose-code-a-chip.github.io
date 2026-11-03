// ============================================================================
//  fa_lane.v -- one lane of the FlashAttention-2 sigma* update (D=1 block)
//  Used for the post-P&R power comparison (baseline vs ExpMul).
//      baseline: o <- o*e1 + v*e2 , l <- l*e1 + e2      (PWL exp + FP mul)
//      expmul  : o <- ExpMul(x1,o)+ExpMul(x2,v) , l <- ExpMul(x1,l)+ExpMul(x2,1)
// ============================================================================
`timescale 1ns/1ps
module fa_lane #(
    parameter VARIANT = 0,
    parameter MODE = 1
) (
    input  wire clk,
    input  wire rst_n,
    input  wire en,
    input  wire [31:0] x1,
    input  wire [31:0] x2,
    input  wire [31:0] v,
    output reg  [31:0] o_q,
    output reg  [31:0] l_q
);
  `include "fp32_funcs.vh"
  wire [31:0] e1, e2, o_n, l_n;

  generate
    if (VARIANT == 0) begin : g_base
      exp_pwl u_e1 (.x(x1), .y(e1));
      exp_pwl u_e2 (.x(x2), .y(e2));
      assign o_n = fadd32(fmul32(o_q, e1), fmul32(v, e2));
      assign l_n = fadd32(fmul32(l_q, e1), e2);
    end else begin : g_exp
      wire [31:0] a1, a2, b1, b2;
      expmul #(.MODE(MODE)) u_m1 (.x(x1), .v(o_q),          .y(a1));
      expmul #(.MODE(MODE)) u_m2 (.x(x2), .v(v),            .y(a2));
      expmul #(.MODE(MODE)) u_m3 (.x(x1), .v(l_q),          .y(b1));
      expmul #(.MODE(MODE)) u_m4 (.x(x2), .v(32'h3F800000), .y(b2));
      assign o_n = fadd32(a1, a2);
      assign l_n = fadd32(b1, b2);
    end
  endgenerate

  always @(posedge clk) begin
    if (!rst_n) begin
      o_q <= 32'h0;
      l_q <= 32'h3F800000;
    end else if (en) begin
      o_q <= o_n;
      l_q <= l_n;
    end
  end
endmodule
