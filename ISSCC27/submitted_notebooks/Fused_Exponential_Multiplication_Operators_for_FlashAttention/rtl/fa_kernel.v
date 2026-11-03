// ============================================================================
//  fa_kernel.v -- one FlashAttention-2 query block (Fig.1/Fig.2 foreground)
//
//  D lanes, one key/value vector per cycle (II=1).
//  The dot product is a pipelined binary adder tree (LV = log2(D) stages,
//  registered every level -> latency LV+1).  The m/l/o update is one cycle:
//      s  = dot(q, k)
//      mn = max(m, s)
//      VARIANT=0 (baseline): e1 = exp_pwl(m-mn), e2 = exp_pwl(s-mn)
//                            o <- o*e1 + v*e2 ,  l <- l*e1 + e2
//      VARIANT=1 (ExpMul)  : o <- ExpMul(m-mn,o) + ExpMul(s-mn,v)
//                            l <- ExpMul(m-mn,l) + ExpMul(s-mn,1)
//  Final attention = o * rcp(l).
// ============================================================================
`timescale 1ns/1ps

module fa_kernel #(
    parameter D = 16,
    parameter VARIANT = 0,      // 0 = baseline, 1 = ExpMul
    parameter MODE = 0          // ExpMul variant: 0 exp-only, 1 mantissa
) (
    input  wire clk,
    input  wire rst_n,
    input  wire init,
    input  wire valid_in,
    input  wire [32*D-1:0] q_flat,
    input  wire [32*D-1:0] k_flat,
    input  wire [32*D-1:0] v_flat,
    output reg  [32*D-1:0] o_flat,
    output reg  [31:0] l_out,
    output reg  [31:0] m_out,
    output wire [32*D-1:0] attn_flat
);
  `include "fp32_funcs.vh"
  function [31:0] fmax32f(input [31:0] a, input [31:0] b);
    reg gt;
    begin
      gt = (a[31] ^ b[31]) ? (~a[31])
                           : (a[31] ? (a[30:0] < b[30:0]) : (a[30:0] > b[30:0]));
      fmax32f = gt ? a : b;
    end
  endfunction
  localparam LV = $clog2(D);
  localparam [31:0] NEG_BIG = 32'hF149F2CA;   // -1e30

  wire [31:0] q [0:D-1];
  wire [31:0] k [0:D-1];
  wire [31:0] v [0:D-1];
  genvar gi;
  generate
    for (gi = 0; gi < D; gi = gi + 1) begin : g_unpack
      assign q[gi] = q_flat[32*gi +: 32];
      assign k[gi] = k_flat[32*gi +: 32];
      assign v[gi] = v_flat[32*gi +: 32];
    end
  endgenerate

  // ---------------- pipelined dot-product tree ------------------------
  reg [31:0] st  [0:LV][0:D-1];
  reg [31:0] vd  [0:LV][0:D-1];
  reg        val [0:LV];

  integer i, s, j;
  always @(posedge clk) begin
    if (!rst_n) begin
      val[0] <= 1'b0;
      for (i = 0; i < D; i = i + 1) begin
        st[0][i] <= 32'h0;
        vd[0][i] <= 32'h0;
      end
      for (s = 1; s <= LV; s = s + 1) begin
        val[s] <= 1'b0;
        for (i = 0; i < (D >> s); i = i + 1) begin
          st[s][i] <= 32'h0;
          vd[s][i] <= 32'h0;
        end
      end
    end else begin
      val[0] <= valid_in;
      for (i = 0; i < D; i = i + 1) begin
        st[0][i] <= fmul32(q[i], k[i]);
        vd[0][i] <= v[i];
      end
      for (s = 1; s <= LV; s = s + 1) begin
        val[s] <= val[s-1];
        for (i = 0; i < (D >> s); i = i + 1) begin
          st[s][i] <= fadd32(st[s-1][2*i], st[s-1][2*i+1]);
          vd[s][i] <= vd[s-1][2*i];
        end
      end
    end
  end

  // ---------------- one-cycle update ----------------------------------
  wire [31:0] sc  = st[LV][0];
  wire [31:0] mn  = fmax32f(m_out, sc);
  wire [31:0] neg = {~mn[31], mn[30:0]};
  wire [31:0] x1  = fadd32(m_out, neg);
  wire [31:0] x2  = fadd32(sc, neg);
  wire [31:0] e1, e2;
  exp_pwl u_e1 (.x(x1), .y(e1));
  exp_pwl u_e2 (.x(x2), .y(e2));

  wire [31:0] l_n;
  wire [31:0] o_n [0:D-1];

  generate
    if (VARIANT == 0) begin : g_base
      assign l_n = fadd32(fmul32(l_out, e1), e2);
      for (gi = 0; gi < D; gi = gi + 1) begin : g_lane
        assign o_n[gi] = fadd32(fmul32(o_flat[32*gi +: 32], e1),
                                fmul32(vd[LV][gi], e2));
      end
    end else begin : g_exp
      wire [31:0] em_l1, em_l2;
      expmul #(.MODE(MODE)) u_l1 (.x(x1), .v(l_out),        .y(em_l1));
      expmul #(.MODE(MODE)) u_l2 (.x(x2), .v(32'h3F800000), .y(em_l2));
      assign l_n = fadd32(em_l1, em_l2);
      for (gi = 0; gi < D; gi = gi + 1) begin : g_lane
        wire [31:0] a1, a2;
        expmul #(.MODE(MODE)) u_o1 (.x(x1), .v(o_flat[32*gi +: 32]), .y(a1));
        expmul #(.MODE(MODE)) u_o2 (.x(x2), .v(vd[LV][gi]),          .y(a2));
        assign o_n[gi] = fadd32(a1, a2);
      end
    end
  endgenerate

  always @(posedge clk) begin
    if (!rst_n) begin
      l_out  <= 32'h0;
      m_out  <= NEG_BIG;
      o_flat <= {32*D{1'b0}};
    end else if (init) begin
      l_out  <= 32'h0;
      m_out  <= NEG_BIG;
      o_flat <= {32*D{1'b0}};
    end else if (val[LV]) begin
      l_out <= l_n;
      m_out <= mn;
      for (j = 0; j < D; j = j + 1) o_flat[32*j +: 32] <= o_n[j];
    end
  end

  // ---------------- final division: o * rcp(l) -------------------------
  wire [31:0] rcp;
  rcp_pwl u_rcp (.x(l_out), .y(rcp));
  generate
    for (gi = 0; gi < D; gi = gi + 1) begin : g_div
      assign attn_flat[32*gi +: 32] = fmul32(o_flat[32*gi +: 32], rcp);
    end
  endgenerate
endmodule
