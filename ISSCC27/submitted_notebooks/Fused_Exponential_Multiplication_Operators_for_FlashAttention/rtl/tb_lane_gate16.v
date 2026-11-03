// ============================================================================
//  tb_lane_gate16.v -- gate-level stimulus (bf16 lane) for post-route VCD
// ============================================================================
`timescale 1ns/1ps
module tb;
  reg clk = 0;
  reg rst_n = 0;
  reg en = 1;
  reg [15:0] x1, x2, v;
  reg [15:0] r;
  wire [15:0] o_q, l_q;
  integer i;

`ifdef TOP
  `TOP dut (.clk(clk), .rst_n(rst_n), .en(en), .x1(x1), .x2(x2), .v(v),
           .o_q(o_q), .l_q(l_q));
`endif

  always #10 clk = ~clk;          // 50 MHz

  initial begin
    $dumpfile("lane.vcd");
    $dumpvars(0, tb);
    x1 = 0; x2 = 0; v = 0;
    #60 rst_n = 1;
    for (i = 0; i < 300; i = i + 1) begin
      @(negedge clk);
      r = $random;  x1 = {1'b1, 8'd120 + r[2:0], r[6:0]};
      r = $random;  x2 = {1'b1, 8'd121 + r[2:0], r[6:0]};
      r = $random;  v  = {r[0], 8'd122 + r[3:1], r[6:0]};
    end
    #40 $finish;
  end
endmodule
