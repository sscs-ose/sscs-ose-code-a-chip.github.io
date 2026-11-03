// ============================================================================
//  tb_fp32.v -- vector checker for fp32_mul_c / fp32_add_c
//  Input lines: "<a_hex> <b_hex>"; output lines: "<mul_hex> <add_hex>"
//  Run: iverilog -o sim rtl/fp32_mul.v rtl/fp32_add.v rtl/tb_fp32.v
//       vvp sim +IN=vec_in.txt +OUT=vec_out.txt
// ============================================================================
`timescale 1ns/1ps
module tb_fp32;
  reg [31:0] a, b;
  wire [31:0] ym, ya;
  reg [1023:0] fin, fout;
  integer fi, fo, r;

  fp32_mul_c u_mul (.a(a), .b(b), .y(ym));
  fp32_add_c u_add (.a(a), .b(b), .y(ya));

  initial begin
    if (!$value$plusargs("IN=%s", fin))   fin  = "vec_in.txt";
    if (!$value$plusargs("OUT=%s", fout)) fout = "vec_out.txt";
    fi = $fopen(fin, "r");
    fo = $fopen(fout, "w");
    if (fi == 0) begin $display("cannot open input"); $finish; end
    r = $fscanf(fi, "%h %h\n", a, b);
    while (r == 2) begin
      #1;
      $fdisplay(fo, "%08x %08x", ym, ya);
      r = $fscanf(fi, "%h %h\n", a, b);
    end
    $fclose(fi);
    $fclose(fo);
    $display("done");
    $finish;
  end
endmodule
