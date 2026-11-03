// ============================================================================
//  tb_bf16.v -- quick numeric sanity for the bf16 lane (both variants)
// ============================================================================
`timescale 1ns/1ps
module tb_bf16;
  reg clk = 0, rst_n = 0, en = 1;
  reg [15:0] x1, x2, v;
  wire [15:0] ob, lb, oe, le;
  integer i;

  fa_lane_bf16 #(.VARIANT(0), .MODE(1)) u_b (
      .clk(clk), .rst_n(rst_n), .en(en), .x1(x1), .x2(x2), .v(v),
      .o_q(ob), .l_q(lb));
  fa_lane_bf16 #(.VARIANT(1), .MODE(1)) u_e (
      .clk(clk), .rst_n(rst_n), .en(en), .x1(x1), .x2(x2), .v(v),
      .o_q(oe), .l_q(le));

  always #10 clk = ~clk;

  initial begin
    x1 = 16'hBF80;   // -1.0
    x2 = 16'h8000;   // -0.0
    v  = 16'h3F80;   // 1.0
    #25 rst_n = 1;
    #40;
    $display("one-step  base o=%h l=%h | expmul o=%h l=%h", ob, lb, oe, le);
    // e^-1 = 0.3679 -> bf16 0x3EBC ; l = 1 + 0.3679 = 1.3672 -> 0x3FAF
    for (i = 0; i < 20; i = i + 1) begin
      @(negedge clk);
      x1 = {1'b1, 8'd124 + i[1:0], 7'd5};
      x2 = {1'b1, 8'd125, 7'd9};
      v  = {1'b0, 8'd126, 7'd3};
    end
    #20;
    $display("random-ish base o=%h l=%h | expmul o=%h l=%h", ob, lb, oe, le);
    #20 $finish;
  end
endmodule
