// ============================================================================
//  exp_pwl.v -- baseline exponential unit (8-segment PWL after range reduction)
//      y  = x * log2(e)                     (FP32 multiply)
//      k  = floor(|y|), f = frac(|y|)       Q6.10 of |y|
//      2^f = c[i] + s[i]*t                  8-segment LUT, t in [0,1)
//      e^x = 2^(-k) * 2^f                   exponent-field adjust
//  Also contains rcp_pwl (1/x, x >= 1) used for the final o/l division.
// ============================================================================
`timescale 1ns/1ps

module exp_pwl (
    input  wire [31:0] x,
    output wire [31:0] y
);
  `include "fp32_funcs.vh"
// t7/128 as binary32
function [31:0] u7_to_float(input [6:0] t);
  begin
    if (t == 7'd0) u7_to_float = 32'h0;
    else if (t[6]) u7_to_float = {1'b0, 8'd126, t[5:0], 17'd0};
    else if (t[5]) u7_to_float = {1'b0, 8'd125, t[4:0], 18'd0};
    else if (t[4]) u7_to_float = {1'b0, 8'd124, t[3:0], 19'd0};
    else if (t[3]) u7_to_float = {1'b0, 8'd123, t[2:0], 20'd0};
    else if (t[2]) u7_to_float = {1'b0, 8'd122, t[1:0], 21'd0};
    else if (t[1]) u7_to_float = {1'b0, 8'd121, t[0],    22'd0};
    else           u7_to_float = {1'b0, 8'd120, 23'd0};
  end
endfunction

  localparam [31:0] LOG2E = 32'h3FB8AA3B;   // 1.4426950
  localparam [31:0] ONE   = 32'h3F800000;

  wire [31:0] yy = fmul32(x, LOG2E);

  wire [7:0]  ey = yy[30:23];
  wire [22:0] my = yy[22:0];
  wire [23:0] My = {1'b1, my};
  wire [7:0]  sh = 8'd140 - ey;
  wire [23:0] xh_r = (sh >= 8'd24 || ey == 8'd0 || yy[31] == 1'b0)
                     ? 24'd0 : ((My + (24'd1 << (sh - 8'd1))) >> sh);
  wire [15:0] a = (xh_r > 24'd22528) ? 16'd22528 : xh_r[15:0];  // |y| <= 21.64

  wire [4:0]  k   = (a + 16'd1023) >> 10;   // ceil(|y|)
  wire [9:0]  fq  = ({5'd0, k} << 10) - a; // fractional part
  wire [2:0]  idx = fq[9:7];
  wire [6:0]  t7  = fq[6:0];
  wire [31:0] tf  = u7_to_float(t7);
  wire [31:0] c   = lut_c(idx);
  wire [31:0] s   = lut_s(idx);
  wire [31:0] p   = fadd32(c, fmul32(s, tf));

  wire [7:0]  ep  = 8'd127 - {3'b000, k};
  assign y = (a == 16'd0) ? ONE :
             (ep == 8'd0) ? 32'h0 :
                            {1'b0, ep, p[22:0]};

  function [31:0] lut_c(input [2:0] i);
    case (i)
      3'd0: lut_c = 32'h3F800000;  3'd1: lut_c = 32'h3F8B95C2;
      3'd2: lut_c = 32'h3F9837F0;  3'd3: lut_c = 32'h3FA5FED7;
      3'd4: lut_c = 32'h3FB504F3;  3'd5: lut_c = 32'h3FC5672A;
      3'd6: lut_c = 32'h3FD744FD;  default: lut_c = 32'h3FEAC0C7;
    endcase
  endfunction

  function [31:0] lut_s(input [2:0] i);
    case (i)
      3'd0: lut_s = 32'h3DB95C1E;  3'd1: lut_s = 32'h3DCA22E7;
      3'd2: lut_s = 32'h3DDC6E66;  3'd3: lut_s = 32'h3DF061C9;
      3'd4: lut_s = 32'h3E0311B7;  3'd5: lut_s = 32'h3E0EEE96;
      3'd6: lut_s = 32'h3E1BDE51;  default: lut_s = 32'h3E29F9C9;
    endcase
  endfunction
endmodule

// ---------------------------------------------------------------------------
//  rcp_pwl.v -- 1/x for x >= 1 (8-segment PWL on the mantissa)
// ---------------------------------------------------------------------------
module rcp_pwl (
    input  wire [31:0] x,
    output wire [31:0] y
);
  `include "fp32_funcs.vh"
// t7/128 as binary32
function [31:0] u7_to_float_r(input [6:0] t);
  begin
    if (t == 7'd0) u7_to_float_r = 32'h0;
    else if (t[6]) u7_to_float_r = {1'b0, 8'd126, t[5:0], 17'd0};
    else if (t[5]) u7_to_float_r = {1'b0, 8'd125, t[4:0], 18'd0};
    else if (t[4]) u7_to_float_r = {1'b0, 8'd124, t[3:0], 19'd0};
    else if (t[3]) u7_to_float_r = {1'b0, 8'd123, t[2:0], 20'd0};
    else if (t[2]) u7_to_float_r = {1'b0, 8'd122, t[1:0], 21'd0};
    else if (t[1]) u7_to_float_r = {1'b0, 8'd121, t[0],    22'd0};
    else           u7_to_float_r = {1'b0, 8'd120, 23'd0};
  end
endfunction

  wire [7:0]  e  = x[30:23];
  wire [22:0] m  = x[22:0];
  wire [2:0]  idx = m[22:20];
  wire [6:0]  t7  = m[19:13];
  wire [31:0] tf  = u7_to_float_r(t7);
  wire [31:0] c   = rlut_c(idx);
  wire [31:0] s   = rlut_s(idx);
  wire [31:0] p   = fadd32(c, fmul32(s, tf));
  wire [7:0]  ep  = 8'd254 - e;
  assign y = (e == 8'd0 || ep == 8'd0) ? 32'h0 : {1'b0, ep, p[22:0]};

  function [31:0] rlut_c(input [2:0] i);
    case (i)
      3'd0: rlut_c = 32'h3F800000;  3'd1: rlut_c = 32'h3F638E39;
      3'd2: rlut_c = 32'h3F4CCCCD;  3'd3: rlut_c = 32'h3F3A2E8C;
      3'd4: rlut_c = 32'h3F2AAAAB;  3'd5: rlut_c = 32'h3F1D89D9;
      3'd6: rlut_c = 32'h3F124925;  default: rlut_c = 32'h3F088889;
    endcase
  endfunction

  function [31:0] rlut_s(input [2:0] i);
    case (i)
      3'd0: rlut_s = 32'hBDE38E39;  3'd1: rlut_s = 32'hBDB60B61;
      3'd2: rlut_s = 32'hBD94F209;  3'd3: rlut_s = 32'hBD783E10;
      3'd4: rlut_s = 32'hBD520D21;  3'd5: rlut_s = 32'hBD340B41;
      3'd6: rlut_s = 32'hBD1C09C1;  default: rlut_s = 32'hBD088889;
    endcase
  endfunction
endmodule
