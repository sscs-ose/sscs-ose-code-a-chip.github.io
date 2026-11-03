// ============================================================================
//  bf16_ops.v -- bf16 ExpMul (Alg.3) and bf16 PWL exp, 16-bit datapath
// ============================================================================
`timescale 1ns/1ps

// ---------------------------------------------------------------------------
//  ExpMul on bfloat16:  Out = 2^-L * V  (V is bf16)
//    MODE 0: exponent field only ; MODE 1: fractional residual in mantissa
// ---------------------------------------------------------------------------
module expmul_bf16 #(
    parameter MODE = 0
) (
    input  wire [15:0] x,      // bf16, <= 0
    input  wire [15:0] v,      // bf16
    output wire [15:0] y
);
  wire [7:0] ex = x[14:7];
  wire [7:0] M  = {1'b1, x[6:0]};
  wire       neg = x[15];

  // |x|*1024 with rounding
  wire [18:0] mshift = {11'b0, M};
  wire [18:0] a_raw = (ex >= 8'd124) ? (mshift << (ex - 8'd124))
                                     : ((mshift + (19'd1 << (8'd124 - ex - 8'd1))) >> (8'd124 - ex));
  wire [15:0] a = (ex == 8'd0 || !neg) ? 16'd0 :
                  (a_raw > 19'd15360) ? 16'd15360 : a_raw[15:0];

  wire signed [16:0] xh = -$signed({1'b0, a});
  wire signed [18:0] xs = {{2{xh[16]}}, xh};
  wire signed [18:0] ss = xs + (xs >>> 1) - (xs >>> 4);
  wire        [18:0] p  = -ss[18:0];

  wire [4:0]  L  = (p + 19'd512) >> 10;
  wire [14:0] Dm = (p + 19'd4) >> 3;       // p * 2^7 / 2^10, rounded

  wire [7:0]  ev = v[14:7];
  wire [6:0]  mv = v[6:0];
  wire [14:0] magv = {ev, mv};

  wire [14:0] sub_exp = magv - {L, 7'd0};
  wire [14:0] sub_man = magv - Dm;

  wire under0 = (ev <= {3'b000, L}) || (ev == 8'd0) || (sub_exp[14:7] == 8'd0);
  wire under1 = (Dm[14:0] >= magv) || (ev == 8'd0) || (sub_man[14:7] == 8'd0);
  wire nan_inf = (ev == 8'hFF);

  wire [15:0] y0 = (ev == 8'd0) ? 16'h0 : nan_inf ? v :
                   under0 ? 16'h0 : {v[15], sub_exp};
  wire [15:0] y1 = (ev == 8'd0) ? 16'h0 : nan_inf ? v :
                   under1 ? 16'h0 : {v[15], sub_man};

  assign y = (MODE == 0) ? y0 : y1;
endmodule

// ---------------------------------------------------------------------------
//  bf16 PWL exp (baseline unit), input bf16 <= 0
// ---------------------------------------------------------------------------
module exp_pwl_bf16 (
    input  wire [15:0] x,
    output wire [15:0] y
);
  `include "bf16_funcs.vh"
  localparam [15:0] LOG2E = 16'h3FB9;   // 1.4426950 in bf16
  localparam [15:0] ONE   = 16'h3F80;

  wire [15:0] yy = fmul16(x, LOG2E);
  wire [7:0]  ey = yy[14:7];
  wire [7:0]  My = {1'b1, yy[6:0]};
  wire        negy = yy[15];

  wire [18:0] mshift = {11'b0, My};
  wire [18:0] a_raw = (ey >= 8'd124) ? (mshift << (ey - 8'd124))
                                     : ((mshift + (19'd1 << (8'd124 - ey - 8'd1))) >> (8'd124 - ey));
  wire [15:0] a = (ey == 8'd0 || !negy) ? 16'd0 :
                  (a_raw > 19'd22528) ? 16'd22528 : a_raw[15:0];

  wire [4:0]  k   = (a + 16'd1023) >> 10;
  wire [9:0]  fq  = ({5'd0, k} << 10) - a;
  wire [2:0]  idx = fq[9:7];
  wire [6:0]  t7  = fq[6:0];
  wire [15:0] tf  = u7_to_bf16(t7);
  wire [15:0] c   = lut_c(idx);
  wire [15:0] s   = lut_s(idx);
  wire [15:0] p   = fadd16(c, fmul16(s, tf));
  wire [7:0]  ep  = 8'd127 - {3'b000, k};
  assign y = (a == 16'd0) ? ONE : (ep == 8'd0) ? 16'h0 : {1'b0, ep, p[6:0]};

  function [15:0] u7_to_bf16(input [6:0] t);
    begin
      if (t == 7'd0) u7_to_bf16 = 16'h0;
      else if (t[6]) u7_to_bf16 = {1'b0, 8'd126, t[5:0]};
      else if (t[5]) u7_to_bf16 = {1'b0, 8'd125, t[4:0], 1'b0};
      else if (t[4]) u7_to_bf16 = {1'b0, 8'd124, t[3:0], 2'b0};
      else if (t[3]) u7_to_bf16 = {1'b0, 8'd123, t[2:0], 3'b0};
      else if (t[2]) u7_to_bf16 = {1'b0, 8'd122, t[1:0], 4'b0};
      else if (t[1]) u7_to_bf16 = {1'b0, 8'd121, t[0],    5'b0};
      else           u7_to_bf16 = {1'b0, 8'd120, 6'b0};
    end
  endfunction

  function [15:0] lut_c(input [2:0] i);
    case (i)
      3'd0: lut_c = 16'h3F80;  3'd1: lut_c = 16'h3F8B;
      3'd2: lut_c = 16'h3F98;  3'd3: lut_c = 16'h3FA6;
      3'd4: lut_c = 16'h3FB5;  3'd5: lut_c = 16'h3FC5;
      3'd6: lut_c = 16'h3FD7;  default: lut_c = 16'h3FEB;
    endcase
  endfunction

  function [15:0] lut_s(input [2:0] i);
    case (i)
      3'd0: lut_s = 16'h3DB9;  3'd1: lut_s = 16'h3DCA;
      3'd2: lut_s = 16'h3DDC;  3'd3: lut_s = 16'h3DF0;
      3'd4: lut_s = 16'h3E03;  3'd5: lut_s = 16'h3E0F;
      3'd6: lut_s = 16'h3E1C;  default: lut_s = 16'h3E2A;
    endcase
  endfunction
endmodule
