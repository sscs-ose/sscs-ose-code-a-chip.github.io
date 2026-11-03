// VCD dump of module `VCD_TOP (set with -DVCD_TOP=<module>) for power
// analysis; file name from +vcd=<path>.
module vcd_dump;
  reg [8*512-1:0] fname;
  initial
    if ($value$plusargs("vcd=%s", fname)) begin
      $dumpfile(fname);
      $dumpvars(0, `VCD_TOP);
    end
endmodule
