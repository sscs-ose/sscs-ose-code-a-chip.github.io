`timescale 1ns/1ps
`default_nettype none
module integration_smoke_tb;
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
    nebula_cpu_npu_top dut (.*);
    logic pending;
    logic [31:0] saved_addr, data0, data1, host;
    int cycles, requests, responses, commits, npu_requests, npu_responses, npu_edge;
    bit first_fetch;

    function automatic logic [31:0] instruction(input logic [31:0] addr);
        case (addr)
            32'h80000000: instruction = 32'h800000b7;
            32'h80000004: instruction = 32'h10008093;
            32'h80000008: instruction = 32'h01100113;
            32'h8000000c: instruction = 32'h0020a023;
            32'h80000010: instruction = 32'h0000a183;
            32'h80000014: instruction = 32'hfff00113;
            32'h80000018: instruction = 32'h002080a3;
            32'h8000001c: instruction = 32'h0000a203;
            32'h80000020: instruction = 32'h0031828b;
            32'h80000024: instruction = 32'h0050a223;
            32'h80000028: instruction = 32'h0040a303;
            32'h8000002c: instruction = 32'h8003f3b7;
            32'h80000030: instruction = 32'h00100413;
            32'h80000034: instruction = 32'h0083a023;
            32'h80000038: instruction = 32'h0003a483;
            32'h8000003c: instruction = 32'h00002503;
            default: instruction = 32'h00000013;
        endcase
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) imem_rdata <= 32'h00000013;
        else if (imem_valid) imem_rdata <= instruction(imem_addr);
    end
    assign dmem_req_ready = rst_n && !pending;
    assign dmem_rsp_valid = rst_n && pending;
    assign dmem_rsp_err = pending && saved_addr == 0;
    assign dmem_rsp_rdata = saved_addr == 32'h80000100 ? data0 :
        saved_addr == 32'h80000104 ? data1 : saved_addr == 32'h8003f000 ? host : 0;

    task automatic check_request;
        logic expected_write;
        logic [31:0] expected_addr, expected_data;
        logic [3:0] expected_mask;
        expected_write = 0; expected_addr = 32'h80000100;
        expected_data = 0; expected_mask = 0;
        case (requests)
            0: begin expected_write = 1; expected_data = 17; expected_mask = 15; end
            1: begin end
            2: begin expected_write = 1; expected_data = 32'h0000ff00; expected_mask = 2; end
            3: begin end
            4: begin expected_write = 1; expected_addr = 32'h80000104;
                expected_data = 289; expected_mask = 15; end
            5: expected_addr = 32'h80000104;
            6: begin expected_write = 1; expected_addr = 32'h8003f000;
                expected_data = 1; expected_mask = 15; end
            7: expected_addr = 32'h8003f000;
            8: expected_addr = 0;
            default: $fatal(1, "unexpected data transaction");
        endcase
        if ({dmem_req_write,dmem_req_addr,dmem_req_wdata,dmem_req_wstrb} !==
            {expected_write,expected_addr,expected_data,expected_mask})
            $fatal(1, "data request mismatch index=%0d", requests);
        $display("REQUEST %0d write=%0d addr=%08x data=%08x mask=%x",
            requests,dmem_req_write,dmem_req_addr,dmem_req_wdata,dmem_req_wstrb);
    endtask

    task automatic check_commit;
        logic [4:0] rd;
        logic [31:0] value, store_addr, store_data;
        logic [3:0] mask;
        rd = 0; value = 0; store_addr = 0; store_data = 0; mask = 0;
        case (commits)
            0: begin rd = 1; value = 32'h80000000; end
            1: begin rd = 1; value = 32'h80000100; end
            2: begin rd = 2; value = 17; end
            3: begin store_addr = 32'h80000100; store_data = 17; mask = 15; end
            4: begin rd = 3; value = 17; end
            5: begin rd = 2; value = 32'hffffffff; end
            6: begin store_addr = 32'h80000100; store_data = 32'h0000ff00; mask = 2; end
            7: begin rd = 4; value = 32'h0000ff11; end
            8: begin rd = 5; value = 289; end
            9: begin store_addr = 32'h80000104; store_data = 289; mask = 15; end
            10: begin rd = 6; value = 289; end
            11: begin rd = 7; value = 32'h8003f000; end
            12: begin rd = 8; value = 1; end
            13: begin store_addr = 32'h8003f000; store_data = 1; mask = 15; end
            14: begin rd = 9; value = 1; end
            default: $fatal(1, "unexpected retirement");
        endcase
        if (commit_pc !== 32'h80000000 + 32'(4*commits) ||
            commit_insn !== instruction(commit_pc) || commit_rd !== rd ||
            commit_wdata !== value || commit_mem_addr !== store_addr ||
            commit_mem_wdata !== store_data || commit_mem_wstrb !== mask)
            $fatal(1, "retirement mismatch index=%0d pc=%08x rd=%0d data=%08x", commits,commit_pc,commit_rd,commit_wdata);
        $display("COMMIT %0d pc=%08x rd=%0d data=%08x", commits,commit_pc,commit_rd,commit_wdata);
        commits++;
    endtask

    task automatic step;
        logic qfire, rfire, qwrite;
        logic [31:0] qaddr, qdata;
        logic [3:0] qmask;
        #50;
        qfire = dmem_req_valid && dmem_req_ready;
        rfire = dmem_rsp_valid && dmem_rsp_ready;
        qwrite = dmem_req_write; qaddr = dmem_req_addr;
        qdata = dmem_req_wdata; qmask = dmem_req_wstrb;
        if (!rst_n) begin
            if (imem_valid || dmem_req_valid || dmem_rsp_ready || commit_valid || trap_valid ||
                dut.core.enabled_npu.npu.req_ready || dut.core.enabled_npu.npu.rsp_valid)
                $fatal(1, "valid output during reset");
        end else begin
            if (imem_valid) begin
                if (imem_addr[1:0] != 0) $fatal(1, "unaligned instruction request");
                if (!first_fetch) begin
                    if (imem_addr !== 32'h80000000) $fatal(1, "reset PC mismatch");
                    first_fetch = 1;
                end
            end
            if (qfire) begin
                if (pending) $fatal(1, "multiple outstanding requests");
                check_request();
            end
            if (rfire) begin
                if (!pending || dmem_rsp_err !== (responses == 8))
                    $fatal(1, "response ownership/error mismatch");
                $display("RESPONSE %0d error=%0d data=%08x", responses,dmem_rsp_err,dmem_rsp_rdata);
            end
            if (dut.core.enabled_npu.npu.req_valid && dut.core.enabled_npu.npu.req_ready) begin
                if (npu_requests != 0 || dut.core.enabled_npu.npu.req_a !== 17 ||
                    dut.core.enabled_npu.npu.req_b !== 17) $fatal(1, "NPU operands mismatch");
                npu_edge = cycles; npu_requests++;
            end
            if (dut.core.enabled_npu.npu.rsp_valid && dut.core.enabled_npu.npu.rsp_ready) begin
                if (npu_responses != 0 || dut.core.enabled_npu.npu.rsp_data !== 289)
                    $fatal(1, "NPU response mismatch");
                npu_responses++;
            end
        end
        clk = 1;
        #1;
        if (rst_n) begin
            if (npu_requests == 1 && cycles == npu_edge + 2 &&
                (!dut.core.enabled_npu.npu.rsp_valid || dut.core.enabled_npu.npu.rsp_data !== 289))
                $fatal(1, "NPU n+2 response missing");
            if (commit_valid && trap_valid) $fatal(1, "commit/trap collision");
            if (commit_valid) check_commit();
            if (trap_valid) begin
                if (trap_pc !== 32'h8000003c || trap_cause !== 5 || trap_tval !== 0 ||
                    commits != 15 || requests != 9 || responses != 9 || pending ||
                    npu_requests != 1 || npu_responses != 1 || !first_fetch ||
                    data0 !== 32'h0000ff11 || data1 !== 289 || host !== 1)
                    $fatal(1, "invalid-address trap/final state mismatch");
                $display("INTEGRATION_SMOKE_PASS directed_transactions=10 dmem=9 npu=1 normal_retirements=15 traps=1 reset_low_ns=300");
                $finish;
            end
            if (rfire) begin pending = 0; responses++; end
            if (qfire) begin
                saved_addr = qaddr; pending = 1; requests++;
                if (qwrite) begin
                    for (int lane = 0; lane < 4; lane++) if (qmask[lane]) begin
                        case (qaddr)
                            32'h80000100: data0[8*lane +: 8] = qdata[8*lane +: 8];
                            32'h80000104: data1[8*lane +: 8] = qdata[8*lane +: 8];
                            32'h8003f000: host[8*lane +: 8] = qdata[8*lane +: 8];
                            default: $fatal(1, "unexpected write target");
                        endcase
                    end
                end
            end
        end
        #49; clk = 0; cycles++;
    endtask

    initial begin
        clk = 0; rst_n = 0; pending = 0; saved_addr = 0;
        data0 = 0; data1 = 0; host = 0;
        cycles = 0; requests = 0; responses = 0; commits = 0;
        npu_requests = 0; npu_responses = 0; npu_edge = -1; first_fetch = 0;
        repeat (3) step();
        rst_n = 1;
        repeat (200) step();
        $fatal(1, "integration smoke timeout");
    end
endmodule
`default_nettype wire
