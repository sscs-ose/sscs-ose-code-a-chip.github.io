// ============================================================================
//  expmul.v -- ExpMul(x, V) = e^x * V, x <= 0
//  Algorithm 3 of arXiv:2505.14314:
//      x_hat = Fixed(Clip(x,-15,0))          Q6.10
//      S     = x_hat + (x_hat>>1) - (x_hat>>4)
//      L     = round(-S/2^10)
//      Out   = Float(S_V, E_V-L, M_V)        (MODE=0, exponent only)
//  MODE=1 folds the fractional residual into the mantissa (the released
//  implementation):  bits(V) - (-x*log2e)*2^23.
// ============================================================================
`timescale 1ns/1ps
module expmul #(
    parameter MODE = 0
) (
    input  wire [31:0] x,       // <= 0
    input  wire [31:0] v,
    output wire [31:0] y
);
  wire [7:0]  ex = x[30:23];
  wire [22:0] mx = x[22:0];
  wire [23:0] M  = {1'b1, mx};
  wire [7:0]  sh = 8'd140 - ex;          // x*1024 = M >> sh

  wire [23:0] xh_r = (sh >= 8'd24 || ex == 8'd0 || x[31] == 1'b0)
                     ? 24'd0
                     : ((M + (24'd1 << (sh - 8'd1))) >> sh);
  wire [15:0] xh_abs = (xh_r > 24'd15360) ? 16'd15360 : xh_r[15:0];
  wire signed [15:0] xh = -$signed({1'b0, xh_abs});

  wire signed [17:0] xh_s = {{2{xh[15]}}, xh};
  wire signed [17:0] s_s  = xh_s + (xh_s >>> 1) - (xh_s >>> 4);
  wire        [17:0] p    = -s_s[17:0];

  wire [4:0]  L  = (p + 18'd512) >> 10;
  wire [30:0] Dm = p << 13;

  wire [7:0]  ev  = v[30:23];
  wire [22:0] mv  = v[22:0];
  wire [30:0] magv = {ev, mv};

  wire [30:0] sub_exp = magv - {L, 23'd0};
  wire [30:0] sub_man = magv - Dm[30:0];

  wire under0 = (ev <= {3'b000, L}) || (ev == 8'd0) ||
                (sub_exp[30:23] == 8'd0);
  wire under1 = (Dm[30:0] >= magv) || (ev == 8'd0) ||
                (sub_man[30:23] == 8'd0);
  wire nan_inf = (ev == 8'hFF);

  wire [31:0] y0 = (ev == 8'd0) ? 32'h0 :
                   nan_inf      ? v :
                   under0       ? 32'h0 :
                                  {v[31], sub_exp};
  wire [31:0] y1 = (ev == 8'd0) ? 32'h0 :
                   nan_inf      ? v :
                   under1       ? 32'h0 :
                                  {v[31], sub_man};

  assign y = (MODE == 0) ? y0 : y1;
endmodule
