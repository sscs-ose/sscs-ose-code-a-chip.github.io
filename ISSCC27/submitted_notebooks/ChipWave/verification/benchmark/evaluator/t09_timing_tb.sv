`timescale 1ns/1ps
// Evaluator-owned, fixed-port timing probe. No DUT hierarchy is inspected.
module tb_t09_timing;
  localparam logic [31:0] RESET_PC = 32'h8000_0000;
  logic clk, rst_n;
  logic imem_valid;
  logic [31:0] imem_addr, imem_rdata;
  logic dmem_req_valid, dmem_req_ready, dmem_req_write;
  logic [31:0] dmem_req_addr, dmem_req_wdata;
  logic [3:0] dmem_req_wstrb;
  logic dmem_rsp_valid, dmem_rsp_ready, dmem_rsp_err;
  logic [31:0] dmem_rsp_rdata;
  logic commit_valid, trap_valid;
  logic [31:0] commit_pc, commit_insn, commit_wdata;
  logic [4:0] commit_rd;
  logic [31:0] commit_mem_addr, commit_mem_wdata;
  logic [3:0] commit_mem_wstrb;
  logic [31:0] trap_pc, trap_cause, trap_tval;
  logic [31:0] rom [0:255];
  logic [31:0] memory [0:255];
  logic pending_response, blocked_request;
  logic [68:0] held_request;
  int cycle_count, retired_count, retire_limit;
  int response_cycles, ready_delay, ready_wait, response_due;
  logic [31:0] response_data;
  string image;

  rv32i_five_stage_cpu dut (.*);

  function automatic logic [31:0] instruction_at(input logic [31:0] address);
    if (address[1:0] == 0 && address >= RESET_PC && address < RESET_PC+1024)
      return rom[(address-RESET_PC)>>2];
    return 32'h0000_0013;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) imem_rdata <= 32'h0000_0013;
    else if (imem_valid) imem_rdata <= instruction_at(imem_addr);
  end

  task automatic step;
    bit accept_request, accept_response, waiting_ready;
    logic [68:0] request;
    #2;
    dmem_req_ready = rst_n && !pending_response && ready_wait >= ready_delay;
    dmem_rsp_valid = rst_n && pending_response && cycle_count >= response_due;
    dmem_rsp_rdata = response_data;
    #1;
    accept_request = rst_n && dmem_req_valid && dmem_req_ready;
    accept_response = rst_n && dmem_rsp_valid && dmem_rsp_ready;
    waiting_ready = rst_n && dmem_req_valid && !dmem_req_ready && !pending_response;
    request = {dmem_req_write, dmem_req_addr, dmem_req_wdata, dmem_req_wstrb};
    if (rst_n) begin
      if (blocked_request && (!dmem_req_valid || request !== held_request))
        $fatal(1, "request changed under backpressure");
      blocked_request = dmem_req_valid && !dmem_req_ready;
      held_request = request;
      if (imem_valid)
        $display("TIMING {\"kind\":\"fetch\",\"cycle\":%0d,\"pc\":\"%08h\"}", cycle_count, imem_addr);
      if (accept_request) begin
        if (dmem_req_addr >= 1024 || dmem_req_addr[1:0] != 0)
          $fatal(1, "invalid timing-probe memory request");
        $display("TIMING {\"kind\":\"request\",\"cycle\":%0d,\"addr\":\"%08h\",\"write\":%0d,\"data\":\"%08h\",\"strb\":%0d}", cycle_count, dmem_req_addr, dmem_req_write, dmem_req_wdata, dmem_req_wstrb);
      end
      if (accept_response)
        $display("TIMING {\"kind\":\"response\",\"cycle\":%0d}", cycle_count);
    end
    clk = 1;
    #2;
    if (rst_n) begin
      if (trap_valid)
        $fatal(1, "unexpected trap pc=%h cause=%0d tval=%h", trap_pc, trap_cause, trap_tval);
      if (commit_valid) begin
        $display("TIMING {\"kind\":\"commit\",\"cycle\":%0d,\"pc\":\"%08h\",\"insn\":\"%08h\",\"rd\":%0d,\"data\":\"%08h\",\"mem_addr\":\"%08h\",\"mem_data\":\"%08h\",\"strb\":%0d}", cycle_count, commit_pc, commit_insn, commit_rd, commit_wdata, commit_mem_addr, commit_mem_wdata, commit_mem_wstrb);
        retired_count++;
      end
      if (accept_response) pending_response = 0;
      if (accept_request) begin
        pending_response = 1;
        response_due = cycle_count + response_cycles;
        response_data = memory[request[67:36]>>2];
        if (request[68]) begin
          for (int lane=0; lane<4; lane++)
            if (request[lane]) memory[request[67:36]>>2][8*lane+:8] = request[4+8*lane+:8];
        end
        ready_wait = 0;
      end else if (waiting_ready)
        ready_wait++;
      else if (!dmem_req_valid && !pending_response) ready_wait = 0;
    end
    clk = 0;
    #2;
    cycle_count++;
  endtask

  initial begin
    clk = 0; rst_n = 0;
    dmem_req_ready = 0; dmem_rsp_valid = 0; dmem_rsp_err = 0;
    dmem_rsp_rdata = 0; response_data = 0;
    cycle_count = 0; retired_count = 0;
    pending_response = 0; blocked_request = 0;
    ready_wait = 0; response_due = 0;
    response_cycles = 1; ready_delay = 0; retire_limit = 16;
    if (!$value$plusargs("IMAGE=%s", image)) $fatal(1, "missing IMAGE");
    void'($value$plusargs("RETIRES=%d", retire_limit));
    void'($value$plusargs("RESPONSE_CYCLES=%d", response_cycles));
    void'($value$plusargs("READY_DELAY=%d", ready_delay));
    for (int i=0; i<256; i++) begin
      rom[i] = 32'h0000_0013;
      memory[i] = 0;
    end
    memory[64] = 32'h1234_5678;
    $readmemh(image, rom);
    step(); step(); rst_n = 1;
    for (int i=0; i<2000 && retired_count<retire_limit; i++) step();
    if (retired_count != retire_limit || pending_response)
      $fatal(1, "timing probe timeout or unfinished bus transaction retired=%0d", retired_count);
    $display("TIMING {\"kind\":\"done\",\"cycles\":%0d,\"retired\":%0d,\"memory_104\":\"%08h\"}", cycle_count, retired_count, memory[65]);
    $display("TIMING_PASS");
    $finish;
  end
endmodule
