// Array multiplier 4x4 built from full adders (ripple rows)
module mul4(input [3:0] a, b, output [7:0] p);
  wire [3:0] pp [0:3];
  genvar i, j;
  generate for (i = 0; i < 4; i = i + 1) begin : r
    for (j = 0; j < 4; j = j + 1) begin : c
      assign pp[i][j] = a[j] & b[i];
    end
  end endgenerate
  // row 1
  wire [3:0] s1; wire [3:0] c1;
  ha h10(.a(pp[0][1]), .b(pp[1][0]), .s(s1[0]), .co(c1[0]));
  fa f11(.a(pp[0][2]), .b(pp[1][1]), .ci(c1[0]), .s(s1[1]), .co(c1[1]));
  fa f12(.a(pp[0][3]), .b(pp[1][2]), .ci(c1[1]), .s(s1[2]), .co(c1[2]));
  ha h13(.a(pp[1][3]), .b(c1[2]), .s(s1[3]), .co(c1[3]));
  // row 2
  wire [3:0] s2; wire [3:0] c2;
  ha h20(.a(s1[1]), .b(pp[2][0]), .s(s2[0]), .co(c2[0]));
  fa f21(.a(s1[2]), .b(pp[2][1]), .ci(c2[0]), .s(s2[1]), .co(c2[1]));
  fa f22(.a(s1[3]), .b(pp[2][2]), .ci(c2[1]), .s(s2[2]), .co(c2[2]));
  fa f23(.a(c1[3]), .b(pp[2][3]), .ci(c2[2]), .s(s2[3]), .co(c2[3]));
  // row 3
  wire [3:0] s3; wire [3:0] c3;
  ha h30(.a(s2[1]), .b(pp[3][0]), .s(s3[0]), .co(c3[0]));
  fa f31(.a(s2[2]), .b(pp[3][1]), .ci(c3[0]), .s(s3[1]), .co(c3[1]));
  fa f32(.a(s2[3]), .b(pp[3][2]), .ci(c3[1]), .s(s3[2]), .co(c3[2]));
  fa f33(.a(c2[3]), .b(pp[3][3]), .ci(c3[2]), .s(s3[3]), .co(c3[3]));
  assign p = {c3[3], s3, s2[0], s1[0], pp[0][0]};
endmodule

// 8-bit magnitude comparator (a > b)
module cmp8(input [7:0] a, b, output gt);
  assign gt = a > b;
endmodule

// ISCAS-85 c17
module c17(input N1, N2, N3, N6, N7, output N22, N23);
  wire N10, N11, N16, N19;
  nand (N10, N1, N3); nand (N11, N3, N6); nand (N16, N2, N11);
  nand (N19, N11, N7); nand (N22, N10, N16); nand (N23, N16, N19);
endmodule
