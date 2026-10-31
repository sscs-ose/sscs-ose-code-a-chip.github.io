`timescale 1ns/1ps

module tb_T09;
  localparam logic [31:0] RESET_PC = 32'h8000_0000;
  localparam int INSN_COUNT = 64;
  logic clk, rst_n;
  logic imem_valid;
  logic [31:0] imem_addr, imem_rdata;
  logic dmem_req_valid, dmem_req_ready, dmem_req_write;
  logic [31:0] dmem_req_addr, dmem_req_wdata;
  logic [3:0] dmem_req_wstrb;
  logic dmem_rsp_valid, dmem_rsp_ready;
  logic [31:0] dmem_rsp_rdata;
  logic dmem_rsp_err;
  logic commit_valid, trap_valid;
  logic [31:0] commit_pc, commit_insn, commit_wdata;
  logic [4:0] commit_rd;
  logic [31:0] commit_mem_addr, commit_mem_wdata;
  logic [3:0] commit_mem_wstrb;
  logic [31:0] trap_pc, trap_cause, trap_tval;
  int fetch_cycle [0:INSN_COUNT-1];
  bit fetched [0:INSN_COUNT-1];
  int cycle_count, retired_count, seed;

  rv32i_five_stage_cpu dut (.*);

  function automatic logic [31:0] instruction(input int index);
    logic [4:0] rd;
    logic [11:0] immediate;
    rd = 5'((index % 31) + 1);
    immediate = 12'(index + 1);
    return {immediate, 5'd0, 3'b000, rd, 7'h13};
  endfunction

  function automatic logic [31:0] instruction_at(input logic [31:0] addr);
    if (addr[1:0] == 0 && addr >= RESET_PC &&
        addr < RESET_PC + 4*INSN_COUNT)
      return instruction(int'((addr - RESET_PC) >> 2));
    return 32'h0000_0013;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) imem_rdata <= 32'h0000_0013;
    else if (imem_valid) imem_rdata <= instruction_at(imem_addr);
  end

  task automatic step;
    int fetch_index;
    logic [31:0] expected_insn;
    if (clk !== 0) $fatal(1, "testbench clock phase error");
    #2;
    if (rst_n && imem_valid) begin
      if (imem_addr[1:0] != 0)
        $fatal(1, "CPU-PIPE-LAT unaligned instruction fetch addr=%h", imem_addr);
      if (imem_addr >= RESET_PC && imem_addr < RESET_PC + 4*INSN_COUNT) begin
        fetch_index = int'((imem_addr - RESET_PC) >> 2);
        if (fetched[fetch_index])
          $fatal(1, "CPU-PIPE-LAT duplicate fetch PC=%h", imem_addr);
        fetched[fetch_index] = 1;
        fetch_cycle[fetch_index] = cycle_count;
        if (fetch_index > 0 && (!fetched[fetch_index-1] ||
                               cycle_count != fetch_cycle[fetch_index-1]+1))
          $fatal(1, "CPU-PIPE-LAT unexpected fetch bubble index=%0d", fetch_index);
      end
    end
    if (rst_n && dmem_req_valid)
      $fatal(1, "CPU-DIR-INT unexpected data-memory request");
    clk = 1;
    #2;
    if (rst_n) begin
      if (trap_valid) $fatal(1, "CPU-DIR-INT unexpected trap cause=%0d", trap_cause);
      if (commit_valid && retired_count < INSN_COUNT) begin
        expected_insn = instruction(retired_count);
        if (!fetched[retired_count])
          $fatal(1, "CPU-PIPE-LAT retired instruction without fetch index=%0d",
                 retired_count);
        if (cycle_count != fetch_cycle[retired_count] + 4)
          $fatal(1, "CPU-PIPE-LAT PC=%h fetch=%0d commit=%0d expected=%0d",
                 RESET_PC + 4*retired_count, fetch_cycle[retired_count],
                 cycle_count, fetch_cycle[retired_count]+4);
        if (commit_pc !== RESET_PC + 4*retired_count ||
            commit_insn !== expected_insn ||
            commit_rd !== expected_insn[11:7] ||
            commit_wdata !== 32'(retired_count + 1) ||
            commit_mem_wstrb !== 0)
          $fatal(1, "CPU-DIR-INT commit mismatch index=%0d pc=%h insn=%h rd=%0d data=%h",
                 retired_count,commit_pc,commit_insn,commit_rd,commit_wdata);
        retired_count++;
      end
    end
    clk = 0;
    #2;
    cycle_count++;
  endtask

  initial begin
    if ($bits(dut.imem_addr) != 32 || $bits(dut.commit_pc) != 32 ||
        $bits(dut.commit_insn) != 32 || $bits(dut.dmem_req_wstrb) != 4)
      $fatal(1, "T09 fixed port width mismatch");
    seed = 20260925;
    void'($value$plusargs("SEED=%d", seed));
    clk = 0; rst_n = 0;
    dmem_req_ready = 1;
    dmem_rsp_valid = 0;
    dmem_rsp_rdata = 0;
    dmem_rsp_err = 0;
    cycle_count = 0;
    retired_count = 0;
    for (int i = 0; i < INSN_COUNT; i++) begin
      fetched[i] = 0;
      fetch_cycle[i] = -1;
    end
    step(); step();
    rst_n = 1;
    for (int i = 0; i < 300 && retired_count < INSN_COUNT; i++) step();
    if (retired_count != INSN_COUNT)
      $fatal(1, "CPU-PIPE-LAT timeout retired=%0d", retired_count);
    $display("PUBLIC_PASS T09 retired=%0d seed=%0d", retired_count, seed);
    $finish;
  end
endmodule
