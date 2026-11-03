// Registered 4x4 multiply-accumulate: acc <= acc + a*b  (10-bit accumulator)
module mac(input clk, input clr, input [3:0] a, input [3:0] b, output [9:0] acc);
  reg [3:0] ra, rb;
  reg [9:0] r;
  always @(posedge clk) begin
    ra <= a; rb <= b;
    r  <= clr ? 10'd0 : r + ra * rb;
  end
  assign acc = r;
endmodule
