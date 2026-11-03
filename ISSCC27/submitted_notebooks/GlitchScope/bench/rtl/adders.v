// Benchmark adders. Sub-modules are kept as hierarchy during technology
// mapping so ABC cannot erase the architecture, then flattened.
module ha(input a, b, output s, co); assign s = a ^ b; assign co = a & b; endmodule
module fa(input a, b, ci, output s, co);
  assign s  = a ^ b ^ ci;
  assign co = (a & b) | (ci & (a ^ b));
endmodule

module rca8(input [7:0] a, b, output [8:0] s);
  wire [8:0] c;
  ha u0(.a(a[0]), .b(b[0]), .s(s[0]), .co(c[1]));
  genvar i;
  generate for (i = 1; i < 8; i = i + 1) begin : g
    fa u(.a(a[i]), .b(b[i]), .ci(c[i]), .s(s[i]), .co(c[i+1]));
  end endgenerate
  assign s[8] = c[8];
endmodule

// Kogge-Stone parallel-prefix adder
module pg(input a, b, output g, p);  assign g = a & b; assign p = a ^ b; endmodule
module bcell(input gi, pi, gk, pk, output go, po); assign go = gi | (pi & gk); assign po = pi & pk; endmodule
module gcell(input gi, pi, gk, output go); assign go = gi | (pi & gk); endmodule
module sumx(input p, c, output s); assign s = p ^ c; endmodule

module ks8(input [7:0] a, b, output [8:0] s);
  wire [7:0] g0, p0;
  genvar i;
  generate for (i = 0; i < 8; i = i + 1) begin : pgs
    pg u(.a(a[i]), .b(b[i]), .g(g0[i]), .p(p0[i]));
  end endgenerate
  // level 1 (distance 1)
  wire [7:0] g1, p1; assign g1[0] = g0[0]; assign p1[0] = p0[0];
  generate for (i = 1; i < 8; i = i + 1) begin : l1
    if (i == 1) begin : gg gcell u(.gi(g0[i]), .pi(p0[i]), .gk(g0[i-1]), .go(g1[i])); assign p1[i] = p0[i]; end
    else begin : bb bcell u(.gi(g0[i]), .pi(p0[i]), .gk(g0[i-1]), .pk(p0[i-1]), .go(g1[i]), .po(p1[i])); end
  end endgenerate
  // level 2 (distance 2)
  wire [7:0] g2, p2; assign g2[1:0] = g1[1:0]; assign p2[1:0] = p1[1:0];
  generate for (i = 2; i < 8; i = i + 1) begin : l2
    if (i < 4) begin : gg gcell u(.gi(g1[i]), .pi(p1[i]), .gk(g1[i-2]), .go(g2[i])); assign p2[i] = p1[i]; end
    else begin : bb bcell u(.gi(g1[i]), .pi(p1[i]), .gk(g1[i-2]), .pk(p1[i-2]), .go(g2[i]), .po(p2[i])); end
  end endgenerate
  // level 3 (distance 4)
  wire [7:0] g3; assign g3[3:0] = g2[3:0];
  generate for (i = 4; i < 8; i = i + 1) begin : l3
    gcell u(.gi(g2[i]), .pi(p2[i]), .gk(g2[i-4]), .go(g3[i]));
  end endgenerate
  assign s[0] = p0[0];
  generate for (i = 1; i < 8; i = i + 1) begin : sm
    sumx u(.p(p0[i]), .c(g3[i-1]), .s(s[i]));
  end endgenerate
  assign s[8] = g3[7];
endmodule
