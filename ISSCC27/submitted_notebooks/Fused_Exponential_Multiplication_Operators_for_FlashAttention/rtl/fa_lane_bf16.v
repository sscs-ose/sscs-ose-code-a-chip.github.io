// ============================================================================
//  fa_lane_bf16.v -- one lane of the sigma* update in bfloat16
//    baseline: o <- o*e1 + v*e2 , l <- l*e1 + e2     (bf16 PWL exp + bf16 mul)
//    ExpMul  : o <- ExpMul(x1,o)+ExpMul(x2,v) , l <- ExpMul(x1,l)+ExpMul(x2,1)
// ============================================================================
`timescale 1ns/1ps
module fa_lane_bf16 #(
    parameter VARIANT = 0,
    parameter MODE = 1
) (
    input  wire clk,
    input  wire rst_n,
    input  wire en,
    input  wire [15:0] x1,
    input  wire [15:0] x2,
    input  wire [15:0] v,
    output reg  [15:0] o_q,
    output reg  [15:0] l_q
);
  `include "bf16_funcs.vh"
  wire [15:0] e1, e2, o_n, l_n;

  generate
    if (VARIANT == 0) begin : g_base
      exp_pwl_bf16 u_e1 (.x(x1), .y(e1));
      exp_pwl_bf16 u_e2 (.x(x2), .y(e2));
      assign o_n = fadd16(fmul16(o_q, e1), fmul16(v, e2));
      assign l_n = fadd16(fmul16(l_q, e1), e2);
    end else begin : g_exp
      wire [15:0] a1, a2, b1, b2;
      expmul_bf16 #(.MODE(MODE)) u_m1 (.x(x1), .v(o_q),     .y(a1));
      expmul_bf16 #(.MODE(MODE)) u_m2 (.x(x2), .v(v),       .y(a2));
      expmul_bf16 #(.MODE(MODE)) u_m3 (.x(x1), .v(l_q),     .y(b1));
      expmul_bf16 #(.MODE(MODE)) u_m4 (.x(x2), .v(16'h3F80),.y(b2));
      assign o_n = fadd16(a1, a2);
      assign l_n = fadd16(b1, b2);
    end
  endgenerate

  always @(posedge clk) begin
    if (!rst_n) begin
      o_q <= 16'h0;
      l_q <= 16'h3F80;
    end else if (en) begin
      o_q <= o_n;
      l_q <= l_n;
    end
  end
endmodule
