`timescale 1ps/1ps
module tb;
  reg clk = 0, clr = 1; reg [3:0] a = 0, b = 0; wire [9:0] acc;
  mac dut(.clk(clk), .clr(clr), .a(a), .b(b), .acc(acc));
  always #2500 clk = ~clk;                 // 200 MHz
  integer i, seed = 5;
  initial begin
    $dumpfile("mac.vcd"); $dumpvars(1, tb);
    repeat (2) @(posedge clk);
    #200 clr = 0;
    for (i = 0; i < 300; i = i + 1) begin
      @(posedge clk); #200;                // inputs change 200 ps after the edge
      a = $random(seed); b = $random(seed);
      if (i % 64 == 63) clr = 1; else clr = 0;
    end
    @(posedge clk); $finish;
  end
endmodule
