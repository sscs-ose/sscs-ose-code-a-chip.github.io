`timescale 1ns/1ps
// Passive evidence only: the fixed checker and its expectations are unchanged.
module architectural_observer;
  string trace_path;
  initial begin
    #1;
    if ($value$plusargs("TRACE=%s", trace_path))
      $writememh({trace_path,".initial.hex"}, tb_cpu_elf.memory);
  end
  final begin
    if (trace_path != "")
      $writememh({trace_path,".final.hex"}, tb_cpu_elf.memory);
  end
endmodule
bind tb_cpu_elf architectural_observer image_evidence ();
