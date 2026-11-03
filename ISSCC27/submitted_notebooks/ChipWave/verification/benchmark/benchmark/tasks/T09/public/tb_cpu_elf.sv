`timescale 1ns/1ps

module tb_cpu_elf;
  localparam logic [31:0] BASE = 32'h8000_0000;
  localparam logic [31:0] TOHOST = 32'h8003_f000;
  localparam int MEM_BYTES = 256*1024;
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
  logic [7:0] memory [0:MEM_BYTES-1];
  string image_file;
  string trace_file;
  string reset_when;
  int trace_fd;
  int seed, max_cycles, cycle_count, commit_count, trap_count;
  int unsigned response_delay_mask;
  int backpressure_cycles;
  int unsigned rng;
  bit pending_response, pending_error;
  bit pending_request_write;
  int response_delay;
  logic [31:0] pending_data;
  bit held_request, host_written, host_committed;
  bit passed;
  bit reset_done;
  logic [31:0] held_addr, held_wdata, host_value;
  logic [3:0] held_strb;
  bit held_write;
  typedef struct packed {
    logic [31:0] addr;
    logic [31:0] data;
    logic [3:0] strb;
  } store_record_t;
  store_record_t store_queue[$];

  rv32i_five_stage_cpu dut (.*);

  function automatic bit in_memory(input logic [31:0] addr);
    return addr >= BASE && addr <= BASE + MEM_BYTES - 4;
  endfunction

  function automatic logic [31:0] read_word(input logic [31:0] addr);
    int offset;
    offset = int'(addr - BASE);
    return {memory[offset+3],memory[offset+2],memory[offset+1],memory[offset]};
  endfunction

  task automatic step;
    logic [31:0] next_instruction;
    store_record_t store_record;
    bit accepted, response_taken;
    bit error_now;
    if (clk !== 0) $fatal(1, "testbench clock phase error");
    dmem_req_ready = !pending_response && (cycle_count % 3 != 1);
    dmem_rsp_valid = pending_response && response_delay == 0;
    dmem_rsp_rdata = pending_data;
    dmem_rsp_err = pending_error;
    #2;
    next_instruction = imem_rdata;
    if (rst_n && imem_valid) begin
      if (imem_addr[1:0] != 0 || !in_memory(imem_addr))
        $fatal(1, "CPU-ELF instruction fetch outside image addr=%h cycle=%0d",
               imem_addr, cycle_count);
      next_instruction = read_word(imem_addr);
    end
    if (held_request && (!dmem_req_valid ||
                         {dmem_req_addr,dmem_req_write,dmem_req_wstrb,dmem_req_wdata} !==
                         {held_addr,held_write,held_strb,held_wdata}))
      $fatal(1, "CPU-PIPE-MEM request changed under backpressure cycle=%0d", cycle_count);
    held_request = rst_n && dmem_req_valid && !dmem_req_ready;
    if (held_request) backpressure_cycles++;
    if (held_request) begin
      held_addr = dmem_req_addr;
      held_write = dmem_req_write;
      held_strb = dmem_req_wstrb;
      held_wdata = dmem_req_wdata;
    end
    accepted = rst_n && dmem_req_valid && dmem_req_ready;
    response_taken = rst_n && dmem_rsp_valid && dmem_rsp_ready;
    if (accepted) begin
      if (dmem_req_addr[1:0] != 0)
        $fatal(1, "CPU-PIPE-MEM unaligned word bus address=%h", dmem_req_addr);
      error_now = !in_memory(dmem_req_addr) && dmem_req_addr != TOHOST;
      pending_response = 1;
      pending_error = error_now;
      pending_request_write = dmem_req_write;
      pending_data = error_now ? 0 :
                     dmem_req_addr == TOHOST ? host_value : read_word(dmem_req_addr);
      rng ^= rng << 13;
      rng ^= rng >> 17;
      rng ^= rng << 5;
      response_delay = int'(rng % 8);
      response_delay_mask |= 1 << (response_delay + 1);
      if (dmem_req_write && !error_now) begin
        if (dmem_req_wstrb == 0)
          $fatal(1, "CPU-ELF store request has zero byte strobes");
        store_queue.push_back('{addr:dmem_req_addr, data:dmem_req_wdata,
                                strb:dmem_req_wstrb});
        if (dmem_req_addr == TOHOST) begin
          if (dmem_req_wstrb != 4'hf)
            $fatal(1, "CPU-ELF tohost write must be a full word");
          host_value = dmem_req_wdata;
          if (host_value != 0) host_written = 1;
        end else begin
          for (int byte_index = 0; byte_index < 4; byte_index++)
            if (dmem_req_wstrb[byte_index])
              memory[int'(dmem_req_addr-BASE)+byte_index] =
                dmem_req_wdata[8*byte_index +: 8];
        end
      end
    end
    clk = 1;
    #2;
    imem_rdata = next_instruction;
    if (!rst_n && (commit_valid || trap_valid))
      $fatal(1, "CPU-PIPE-RESET commit/trap visible during reset");
    if (rst_n) begin
      if (commit_valid) begin
        commit_count++;
        if (commit_mem_wstrb != 0) begin
          if (store_queue.size() == 0)
            $fatal(1, "CPU-ELF store committed without accepted bus write");
          store_record = store_queue.pop_front();
          if (commit_mem_addr !== store_record.addr ||
              commit_mem_wstrb !== store_record.strb)
            $fatal(1, "CPU-ELF store commit address/strobes differ from bus write");
          for (int byte_index = 0; byte_index < 4; byte_index++)
            if (store_record.strb[byte_index] &&
                commit_mem_wdata[8*byte_index +: 8] !==
                store_record.data[8*byte_index +: 8])
              $fatal(1, "CPU-ELF store commit data differ from bus write");
        end
        if (trace_fd != 0)
          $fdisplay(trace_fd,
            "{\"kind\":\"commit\",\"cycle\":%0d,\"pc\":%0d,\"insn\":%0d,\"rd\":%0d,\"wdata\":%0d,\"mem_addr\":%0d,\"mem_wstrb\":%0d,\"mem_wdata\":%0d}",
            cycle_count, commit_pc, commit_insn, commit_rd, commit_wdata,
            commit_mem_addr, commit_mem_wstrb, commit_mem_wdata);
        if (commit_mem_wstrb != 0 && commit_mem_addr == TOHOST) begin
          host_committed = 1;
          if (commit_mem_wstrb != 4'hf || commit_mem_wdata !== host_value)
            $fatal(1, "CPU-ELF tohost commit differs from bus write");
        end
      end
      if (trap_valid) begin
        trap_count++;
        if (trace_fd != 0)
          $fdisplay(trace_fd,
            "{\"kind\":\"trap\",\"cycle\":%0d,\"pc\":%0d,\"cause\":%0d,\"tval\":%0d}",
            cycle_count, trap_pc, trap_cause, trap_tval);
      end
    end
    clk = 0;
    #2;
    cycle_count++;
    if (response_taken) pending_response = 0;
    else if (pending_response && response_delay > 0) response_delay--;
  endtask

  initial begin
    if (!$value$plusargs("IMAGE=%s", image_file))
      $fatal(1, "CPU-ELF IMAGE plusarg required");
    trace_fd = 0;
    if ($value$plusargs("TRACE=%s", trace_file)) begin
      trace_fd = $fopen(trace_file, "w");
      if (trace_fd == 0) $fatal(1, "CPU-ELF cannot open trace output");
    end
    seed = 20260925;
    max_cycles = 100000;
    reset_when = "";
    void'($value$plusargs("SEED=%d", seed));
    void'($value$plusargs("MAX_CYCLES=%d", max_cycles));
    void'($value$plusargs("RESET_WHEN=%s", reset_when));
    $readmemh(image_file, memory);
    clk = 0; rst_n = 0; imem_rdata = 32'h0000_0013;
    dmem_req_ready = 0; dmem_rsp_valid = 0;
    dmem_rsp_rdata = 0; dmem_rsp_err = 0;
    pending_response = 0; pending_error = 0; pending_request_write = 0;
    pending_data = 0; response_delay = 0;
    held_request = 0; host_written = 0; host_committed = 0;
    passed = 0;
    reset_done = 0;
    host_value = 0;
    cycle_count = 0; commit_count = 0; trap_count = 0;
    response_delay_mask = 0;
    backpressure_cycles = 0;
    rng = 32'(seed) ^ 32'h9e37_79b9;
    step(); step();
    rst_n = 1;
    for (int i = 0; i < max_cycles; i++) begin
      step();
      if (reset_when != "" && !reset_done &&
          ((reset_when == "alu" && commit_valid &&
            (commit_insn[6:0] == 7'h13 || commit_insn[6:0] == 7'h33)) ||
           (reset_when == "branch" && commit_valid && commit_insn[6:0] == 7'h63) ||
           (reset_when == "load_wait" && pending_response &&
            !pending_request_write && response_delay > 0))) begin
        reset_done = 1;
        $display("CPU_RESET_INJECT phase=%s cycle=%0d", reset_when, cycle_count);
        rst_n = 0;
        pending_response = 0;
        pending_error = 0;
        pending_request_write = 0;
        response_delay = 0;
        held_request = 0;
        host_written = 0;
        host_committed = 0;
        host_value = 0;
        store_queue.delete();
        $readmemh(image_file, memory);
        if (trace_fd != 0) begin
          $fclose(trace_fd);
          trace_fd = $fopen(trace_file, "w");
          if (trace_fd == 0) $fatal(1, "CPU-PIPE-RESET cannot reopen trace");
        end
        step();
        step();
        imem_rdata = 32'h0000_0013;
        rst_n = 1;
      end
      if (host_written && host_committed) begin
        if (host_value != 1)
          $fatal(1, "CPU-ELF program failed tohost=%h", host_value);
        passed = 1;
        break;
      end
    end
    if (!passed)
      $fatal(1, "CPU-ELF timeout cycles=%0d commits=%0d traps=%0d tohost=%h",
             cycle_count, commit_count, trap_count, host_value);
    if (reset_when != "" && !reset_done)
      $fatal(1, "CPU-PIPE-RESET requested phase not observed: %s", reset_when);
    if (store_queue.size() != 0)
      $fatal(1, "CPU-ELF accepted stores remain uncommitted: %0d", store_queue.size());
    $display("CPU_ELF_PASS cycles=%0d commits=%0d traps=%0d tohost=%h seed=%0d delays=%h backpressure=%0d",
             cycle_count, commit_count, trap_count, host_value, seed,
             response_delay_mask, backpressure_cycles);
    if (trace_fd != 0) $fclose(trace_fd);
    $finish;
  end
endmodule
