`timescale 1ns/1ps
module selfcheck_cpu_tb #(parameter ENABLE = 0);
    logic clk;
    logic rst_n;
    logic imem_valid;
    logic [31:0] imem_addr;
    logic [31:0] imem_rdata;
    logic dmem_req_valid;
    logic dmem_req_ready;
    logic dmem_req_write;
    logic [31:0] dmem_req_addr;
    logic [31:0] dmem_req_wdata;
    logic [3:0] dmem_req_wstrb;
    logic dmem_rsp_valid;
    logic dmem_rsp_ready;
    logic [31:0] dmem_rsp_rdata;
    logic dmem_rsp_err;
    logic commit_valid;
    logic [31:0] commit_pc;
    logic [31:0] commit_insn;
    logic [4:0] commit_rd;
    logic [31:0] commit_wdata;
    logic [31:0] commit_mem_addr;
    logic [3:0] commit_mem_wstrb;
    logic [31:0] commit_mem_wdata;
    logic trap_valid;
    logic [31:0] trap_pc;
    logic [31:0] trap_cause;
    logic [31:0] trap_tval;
    logic [31:0] program_words [0:4095];
    logic [31:0] data_words [0:1023];
    logic [31:0] invalid_word;
    logic pending, blocked, saved_write;
    logic [31:0] saved_addr, saved_data;
    logic [3:0] saved_mask;
    logic [68:0] blocked_fields;
    int cycle, due_cycle, events, event_limit, ready_delay, response_delay, wait_edges;
    int random_seed, reset_at, reset_epoch;
    int chosen_response_delay, chosen_ready_delay;
    string program_path;

    generate
        if (ENABLE == 1) begin : extension
            nebula_cpu_npu_top dut (.*);
        end else begin : base
            rv32i_five_stage_cpu dut (.*);
        end
    endgenerate
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) imem_rdata <= 32'h13;
        else if (imem_valid)
            imem_rdata <= imem_addr >= 32'h80000000 && imem_addr < 32'h80004000 ?
                program_words[(imem_addr - 32'h80000000) >> 2] : 32'h13;
        else imem_rdata <= invalid_word;
    end

    function automatic int next_random();
        random_seed = (random_seed * 1103515245 + 12345) & 32'h7fffffff;
        return random_seed;
    endfunction

    task automatic step;
        logic request_fire, response_fire;
        logic request_write;
        logic [31:0] request_addr, request_data;
        logic [3:0] request_mask;
        int index;
        begin
            dmem_req_ready = rst_n && wait_edges >= chosen_ready_delay;
            dmem_rsp_valid = rst_n && pending && cycle >= due_cycle;
            dmem_rsp_err = pending && !(saved_addr >= 32'h80001000 && saved_addr < 32'h80002000);
            dmem_rsp_rdata = !dmem_rsp_err && pending ? data_words[(saved_addr-32'h80001000)>>2] : 32'hbad0bad0;
            #2;
            request_fire = dmem_req_valid && dmem_req_ready;
            response_fire = dmem_rsp_valid && dmem_rsp_ready;
            request_addr = dmem_req_addr; request_data = dmem_req_wdata;
            request_write = dmem_req_write; request_mask = dmem_req_wstrb;
            if (!rst_n) begin
                if (imem_valid || dmem_req_valid || dmem_rsp_ready || commit_valid || trap_valid)
                    $fatal(1, "reset did not suppress outputs");
            end else begin
                if (imem_valid) $display("F %0d %08x", cycle, imem_addr);
                if (blocked && (!dmem_req_valid || blocked_fields !==
                    {dmem_req_write,dmem_req_addr,dmem_req_wdata,dmem_req_wstrb}))
                    $fatal(1, "blocked request changed");
                blocked = dmem_req_valid && !dmem_req_ready;
                blocked_fields = {dmem_req_write,dmem_req_addr,dmem_req_wdata,dmem_req_wstrb};
                if (dmem_req_valid && !dmem_req_ready) wait_edges++;
                if (dmem_rsp_ready && !pending) $fatal(1, "unsolicited response ready");
                if (request_fire) begin
                    if (pending || request_addr[1:0] != 0) $fatal(1, "request ownership/alignment");
                    $display("Q %0d %0d %08x %x %08x", cycle, request_write, request_addr, request_mask, request_data);
                end
                if (response_fire) $display("R %0d %0d %08x", cycle, dmem_rsp_err, dmem_rsp_rdata);
            end
            clk = 1;
            #2;
            if (rst_n) begin
                if (commit_valid && trap_valid) $fatal(1, "commit/trap collision");
                if (commit_valid) begin
                    $display("C %0d %08x %08x %0d %08x %08x %x %08x", cycle,
                        commit_pc, commit_insn, commit_rd, commit_wdata,
                        commit_mem_addr, commit_mem_wstrb, commit_mem_wdata);
                    events++;
                end
                if (trap_valid) begin
                    $display("T %0d %08x %08x %08x", cycle, trap_pc, trap_cause, trap_tval);
                    events++;
                end
                if (response_fire) begin
                    if (!dmem_rsp_err && saved_write) begin
                        index = int'((saved_addr-32'h80001000)>>2);
                        for (int lane=0; lane<4; lane++)
                            if (saved_mask[lane]) data_words[index][8*lane+:8] = saved_data[8*lane+:8];
                    end
                    pending = 0;
                end
                if (request_fire) begin
                    pending = 1; saved_addr = request_addr; saved_data = request_data;
                    saved_mask = request_mask; saved_write = request_write;
                    due_cycle = cycle + chosen_response_delay;
                    wait_edges = 0;
                    if (random_seed != 0) begin
                        chosen_response_delay = 1 + next_random()%8;
                        chosen_ready_delay = next_random()%5;
                    end
                end
            end
            clk = 0;
            #2;
            cycle++;
        end
    endtask

    initial begin
        clk=0; rst_n=0; pending=0; blocked=0; wait_edges=0;
        cycle=0; events=0; reset_epoch=0;
        event_limit=1; ready_delay=0; response_delay=1; random_seed=0; reset_at=-1;
        invalid_word=32'hdeadbeef;
        if (!$value$plusargs("PROGRAM=%s",program_path)) $fatal(1,"missing PROGRAM");
        if (!$value$plusargs("EVENTS=%d",event_limit)) $fatal(1,"missing EVENTS");
        if ($value$plusargs("READY_DELAY=%d",ready_delay)) begin end
        if ($value$plusargs("RESPONSE_DELAY=%d",response_delay)) begin end
        if ($value$plusargs("RANDOM_SEED=%d",random_seed)) begin end
        if ($value$plusargs("RESET_AT=%d",reset_at)) begin end
        if ($value$plusargs("INVALID_WORD=%h",invalid_word)) begin end
        chosen_response_delay=response_delay; chosen_ready_delay=ready_delay;
        for (int j=0;j<4096;j++) program_words[j]=32'h13;
        $readmemh(program_path,program_words);
        for (int j=0;j<1024;j++) data_words[j]=32'h807fff01;
        dmem_req_ready=0; dmem_rsp_valid=0; dmem_rsp_err=0; dmem_rsp_rdata=0;
        step(); step(); rst_n=1;
        for (int j=0; j<200000 && (events<event_limit || reset_epoch==0 && reset_at>=0); j++) begin
            if (cycle==reset_at && reset_epoch==0) begin
                rst_n=0; #1;
                pending=0; blocked=0; wait_edges=0; events=0; reset_epoch=1;
                for (int k=0;k<1024;k++) data_words[k]=32'h807fff01;
                $display("Z %0d",cycle);
                step(); step(); rst_n=1;
            end
            step();
        end
        if (events != event_limit || pending) $fatal(1,"unfinished program/transaction");
        for (int j=0;j<1024;j++) $display("D %0d %08x",j,data_words[j]);
        $display("SELFCHECK_CPU_PASS events=%0d",events);
        $finish;
    end
endmodule
