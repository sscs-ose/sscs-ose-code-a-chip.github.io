`timescale 1ns/1ps
module pipeline_observer;
  integer fd;
  bit ev, mv, wv, cv, rw;
  logic [31:0] ep, ei, mp, mi, wp, wi, cp, ci, data;
  logic [4:0] rd;
  initial fd = $fopen("pipeline.jsonl", "w");
  always @(posedge tb_T09.clk) begin
    if (tb_T09.rst_n) begin
      ev = tb_T09.dut.id_advance;
      ep = tb_T09.dut.if_pc; ei = tb_T09.dut.id_word;
      mv = tb_T09.dut.ex_advance;
      mp = tb_T09.dut.ex.pc; mi = tb_T09.dut.ex.insn;
      wv = tb_T09.dut.mem_advance;
      wp = tb_T09.dut.mem.pc; wi = tb_T09.dut.mem.insn;
      cv = tb_T09.dut.wb_normal;
      cp = tb_T09.dut.wb.pc; ci = tb_T09.dut.wb.insn;
      rw = tb_T09.dut.wb_rf_write;
      rd = tb_T09.dut.wb.rd; data = tb_T09.dut.wb.result;
      #1;
      assert(tb_T09.dut.ex_v == ev && (!ev ||
        (tb_T09.dut.ex.pc == ep && tb_T09.dut.ex.insn == ei))) else $fatal(1,"IF/ID -> ID/EX transfer");
      assert(tb_T09.dut.mem_v == mv && (!mv ||
        (tb_T09.dut.mem.pc == mp && tb_T09.dut.mem.insn == mi))) else $fatal(1,"ID/EX -> EX/MEM transfer");
      assert(tb_T09.dut.wb_v == wv && (!wv ||
        (tb_T09.dut.wb.pc == wp && tb_T09.dut.wb.insn == wi))) else $fatal(1,"EX/MEM -> MEM/WB transfer");
      assert(tb_T09.commit_valid == cv && (!cv ||
        (tb_T09.commit_pc == cp && tb_T09.commit_insn == ci))) else $fatal(1,"WB/event alignment");
      assert(!rw || tb_T09.dut.rf[rd] == data) else $fatal(1,"WB/RF alignment");
      assert(tb_T09.dut.rf[0] == 0) else $fatal(1,"x0 changed");
      $fdisplay(fd,"{\"cycle\":%0d,\"id_ex_valid\":%0d,\"id_ex_pc\":%0d,\"ex_mem_valid\":%0d,\"ex_mem_pc\":%0d,\"mem_wb_valid\":%0d,\"mem_wb_pc\":%0d,\"commit_valid\":%0d,\"commit_pc\":%0d,\"rf_write\":%0d,\"rf_rd\":%0d,\"rf_data\":%0d}",
        tb_T09.cycle_count,ev,ep,mv,mp,wv,wp,cv,cp,rw,rd,data);
    end
  end
  final $fclose(fd);
endmodule
bind tb_T09 pipeline_observer stage_evidence ();
