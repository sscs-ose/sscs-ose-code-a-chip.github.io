// ============================================================================
//  tb_exp.v -- vector checker for expmul (MODE 0/1) and exp_pwl
//  Input : "<x_hex> <v_hex>"     Output: "<y0> <y1> <ypwl>"
// ============================================================================
`timescale 1ns/1ps
module tb_exp;
  reg [31:0] x, v;
  wire [31:0] y0, y1, yp;
  reg [1023:0] fin, fout;
  integer fi, fo, r;

  expmul #(.MODE(0)) u0 (.x(x), .v(v), .y(y0));
  expmul #(.MODE(1)) u1 (.x(x), .v(v), .y(y1));
  exp_pwl u2 (.x(x), .y(yp));

  initial begin
    if (!$value$plusargs("IN=%s", fin))   fin  = "vec_in.txt";
    if (!$value$plusargs("OUT=%s", fout)) fout = "vec_out.txt";
    fi = $fopen(fin, "r");
    fo = $fopen(fout, "w");
    r = $fscanf(fi, "%h %h\n", x, v);
    while (r == 2) begin
      #1;
      $fdisplay(fo, "%08x %08x %08x", y0, y1, yp);
      r = $fscanf(fi, "%h %h\n", x, v);
    end
    $fclose(fi); $fclose(fo);
    $display("done");
    $finish;
  end
endmodule
