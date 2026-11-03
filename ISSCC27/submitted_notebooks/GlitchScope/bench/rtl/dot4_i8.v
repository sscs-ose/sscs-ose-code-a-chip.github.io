// AI-accelerator processing element: 4-lane signed int8 dot product (as in a
// systolic-array / vector-unit PE), inputs and output registered, latency 2.
module dot4_i8 (input clk,
                input signed [7:0] a0, a1, a2, a3, b0, b1, b2, b3,
                output reg signed [17:0] y);
  reg signed [7:0] ra0, ra1, ra2, ra3, rb0, rb1, rb2, rb3;
  always @(posedge clk) begin
    ra0 <= a0; ra1 <= a1; ra2 <= a2; ra3 <= a3;
    rb0 <= b0; rb1 <= b1; rb2 <= b2; rb3 <= b3;
    y <= ra0 * rb0 + ra1 * rb1 + ra2 * rb2 + ra3 * rb3;
  end
endmodule
