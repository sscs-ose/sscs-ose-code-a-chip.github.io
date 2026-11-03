`timescale 1ns/1ps
module rv32i_five_stage_cpu #(parameter bit ENABLE_XNEBULA = 1'b0) (
    input logic clk, rst_n,
    output logic imem_valid,
    output logic [31:0] imem_addr,
    input logic [31:0] imem_rdata,
    output logic dmem_req_valid,
    input logic dmem_req_ready,
    output logic dmem_req_write,
    output logic [31:0] dmem_req_addr, dmem_req_wdata,
    output logic [3:0] dmem_req_wstrb,
    input logic dmem_rsp_valid,
    output logic dmem_rsp_ready,
    input logic [31:0] dmem_rsp_rdata,
    input logic dmem_rsp_err,
    output logic commit_valid,
    output logic [31:0] commit_pc, commit_insn,
    output logic [4:0] commit_rd,
    output logic [31:0] commit_wdata, commit_mem_addr,
    output logic [3:0] commit_mem_wstrb,
    output logic [31:0] commit_mem_wdata,
    output logic trap_valid,
    output logic [31:0] trap_pc, trap_cause, trap_tval
);
    typedef enum logic [3:0] { A_ADD, A_SUB, A_SLL, A_SLT, A_SLTU,
        A_XOR, A_SRL, A_SRA, A_OR, A_AND, A_LUI } alu_t;
    typedef struct packed {
        logic valid;
        logic [31:0] pc, insn, a, b, imm;
        logic [4:0] rs1, rs2, rd;
        logic use1, use2, regwrite, immediate, pc_operand;
        alu_t alu;
        logic branch, jal, jalr, load, store, csr, mret, dot;
        logic [2:0] f3;
        logic [11:0] csr_addr;
        logic csr_write;
        logic exc;
        logic [31:0] cause, tval;
    } decode_t;
    typedef struct packed {
        logic valid;
        logic [31:0] pc, insn, result;
        logic [4:0] rd;
        logic regwrite, load, store, issued;
        logic [31:0] addr, store_data;
        logic [3:0] strobes;
        logic [2:0] f3;
        logic csr_write, mret;
        logic [11:0] csr_addr;
        logic [31:0] csr_data;
        logic exc;
        logic [31:0] cause, tval;
    } result_t;

    logic [31:0] gpr [0:31];
    logic [31:0] mstatus, mtvec, mscratch, mepc, mcause, mtval;
    // IF/ID metadata uses the external synchronous instruction register on the live path.
    logic [31:0] fetch_pc, if_id_pc, if_id_insn;
    logic if_id_valid, if_id_saved;
    decode_t decoded, id_ex;
    result_t ex_result, ex_mem, mem_result, mem_wb;
    logic [31:0] insn, operand_a, operand_b, alu_a, alu_b;
    logic [31:0] target, csr_old, csr_source, shifted_load;
    logic branch_taken;
    logic mem_done, mem_bad, older_stop, wb_redirect;
    logic ex_fire, id_fire, ex_redirect, csr_wait;
    logic npu_req_valid, npu_req_ready, npu_rsp_valid, npu_rsp_ready;
    logic [31:0] npu_rsp_data;
    logic npu_kill, dot_issued;

    generate
        if (ENABLE_XNEBULA) begin : gen_xnebula
            nebula_npu_dot4 dot4 (
                .clk(clk), .rst_n(rst_n), .req_valid(npu_req_valid),
                .req_ready(npu_req_ready), .req_a(operand_a), .req_b(operand_b),
                .rsp_valid(npu_rsp_valid), .rsp_ready(npu_rsp_ready),
                .rsp_data(npu_rsp_data), .kill(npu_kill)
            );
        end else begin : gen_base
            assign npu_req_ready = 1'b0;
            assign npu_rsp_valid = 1'b0;
            assign npu_rsp_data = 32'b0;
        end
    endgenerate

    always_comb begin
        insn = if_id_saved ? if_id_insn : imem_rdata;
        decoded = '0;
        decoded.valid = if_id_valid;
        decoded.pc = if_id_pc;
        decoded.insn = insn;
        decoded.rs1 = insn[19:15];
        decoded.rs2 = insn[24:20];
        decoded.rd = insn[11:7];
        decoded.f3 = insn[14:12];
        decoded.csr_addr = insn[31:20];
        decoded.a = insn[19:15] == 0 ? 32'b0 : gpr[insn[19:15]];
        decoded.b = insn[24:20] == 0 ? 32'b0 : gpr[insn[24:20]];
        if (mem_wb.valid && !mem_wb.exc && mem_wb.regwrite && mem_wb.rd != 0) begin
            if (mem_wb.rd == decoded.rs1) decoded.a = mem_wb.result;
            if (mem_wb.rd == decoded.rs2) decoded.b = mem_wb.result;
        end
        decoded.alu = A_ADD;
        decoded.imm = {{20{insn[31]}}, insn[31:20]};
        decoded.cause = 32'd2;
        decoded.tval = insn;
        case (insn[6:0])
            7'h37: begin
                decoded.regwrite = 1;
                decoded.alu = A_LUI;
                decoded.immediate = 1;
                decoded.imm = {insn[31:12], 12'b0};
            end
            7'h17: begin
                decoded.regwrite = 1;
                decoded.pc_operand = 1;
                decoded.immediate = 1;
                decoded.imm = {insn[31:12], 12'b0};
            end
            7'h6f: begin
                decoded.jal = 1;
                decoded.regwrite = 1;
                decoded.imm = {{11{insn[31]}}, insn[31], insn[19:12],
                    insn[20], insn[30:21], 1'b0};
            end
            7'h67: begin
                decoded.jalr = 1;
                decoded.regwrite = 1;
                decoded.use1 = 1;
                decoded.exc = insn[14:12] != 0;
            end
            7'h63: begin
                decoded.branch = 1;
                decoded.use1 = 1;
                decoded.use2 = 1;
                decoded.imm = {{19{insn[31]}}, insn[31], insn[7],
                    insn[30:25], insn[11:8], 1'b0};
                decoded.exc = insn[14:12] == 2 || insn[14:12] == 3;
            end
            7'h03: begin
                decoded.load = 1;
                decoded.regwrite = 1;
                decoded.use1 = 1;
                decoded.immediate = 1;
                decoded.exc = !(insn[14:12] == 0 || insn[14:12] == 1 ||
                    insn[14:12] == 2 || insn[14:12] == 4 || insn[14:12] == 5);
            end
            7'h23: begin
                decoded.store = 1;
                decoded.use1 = 1;
                decoded.use2 = 1;
                decoded.immediate = 1;
                decoded.imm = {{20{insn[31]}}, insn[31:25], insn[11:7]};
                decoded.exc = insn[14:12] > 2;
            end
            7'h13, 7'h33: begin
                decoded.regwrite = 1;
                decoded.use1 = 1;
                decoded.use2 = insn[6:0] == 7'h33;
                decoded.immediate = insn[6:0] == 7'h13;
                case (insn[14:12])
                    0: begin
                        if (insn[6:0] == 7'h33 && insn[30]) decoded.alu = A_SUB;
                        else decoded.alu = A_ADD;
                    end
                    1: decoded.alu = A_SLL;
                    2: decoded.alu = A_SLT;
                    3: decoded.alu = A_SLTU;
                    4: decoded.alu = A_XOR;
                    5: begin
                        if (insn[30]) decoded.alu = A_SRA;
                        else decoded.alu = A_SRL;
                    end
                    6: decoded.alu = A_OR;
                    7: decoded.alu = A_AND;
                endcase
                if (insn[6:0] == 7'h33)
                    decoded.exc = !(insn[31:25] == 0 ||
                        (insn[31:25] == 7'h20 && (insn[14:12] == 0 || insn[14:12] == 5)));
                else if (insn[14:12] == 1)
                    decoded.exc = insn[31:25] != 0;
                else if (insn[14:12] == 5)
                    decoded.exc = !(insn[31:25] == 0 || insn[31:25] == 7'h20);
            end
            7'h0f: decoded.exc = insn[14:12] != 0;
            7'h73: begin
                if (insn == 32'h30200073) decoded.mret = 1;
                else if (insn == 32'h00000073 || insn == 32'h00100073) begin
                    decoded.exc = 1;
                    decoded.cause = insn[20] ? 32'd3 : 32'd11;
                    decoded.tval = 0;
                end else if (insn[14:12] != 0 && insn[14:12] != 4) begin
                    decoded.csr = 1;
                    decoded.regwrite = 1;
                    decoded.use1 = !insn[14];
                    decoded.csr_write = insn[13:12] == 1 || insn[19:15] != 0;
                    case (insn[31:20])
                        12'h300,12'h305,12'h340,12'h341,12'h342,12'h343: decoded.exc = 0;
                        12'h301,12'hf14: decoded.exc = decoded.csr_write;
                        default: decoded.exc = 1;
                    endcase
                end else decoded.exc = 1;
            end
            7'h0b: begin
                decoded.dot = 1;
                decoded.regwrite = 1;
                decoded.use1 = 1;
                decoded.use2 = 1;
                decoded.exc = !ENABLE_XNEBULA || insn[31:25] != 0 || insn[14:12] != 0;
            end
            default: decoded.exc = 1;
        endcase
    end

    // MEM completes only an owned response; its extracted result also feeds EX bypass.
    always_comb begin
        mem_done = !ex_mem.valid || !(ex_mem.load || ex_mem.store) ||
            (ex_mem.issued && dmem_rsp_valid);
        mem_result = ex_mem;
        shifted_load = dmem_rsp_rdata >> {ex_mem.addr[1:0], 3'b0};
        if (ex_mem.load) begin
            case (ex_mem.f3)
                0: mem_result.result = {{24{shifted_load[7]}}, shifted_load[7:0]};
                1: mem_result.result = {{16{shifted_load[15]}}, shifted_load[15:0]};
                2: mem_result.result = shifted_load;
                4: mem_result.result = {24'b0, shifted_load[7:0]};
                5: mem_result.result = {16'b0, shifted_load[15:0]};
                default: mem_result.result = 0;
            endcase
        end
        if (ex_mem.valid && (ex_mem.load || ex_mem.store) && ex_mem.issued &&
            dmem_rsp_valid && dmem_rsp_err) begin
            mem_result.exc = 1;
            mem_result.cause = ex_mem.store ? 32'd7 : 32'd5;
            mem_result.tval = ex_mem.addr;
            mem_result.regwrite = 0;
            mem_result.strobes = 0;
        end
        mem_bad = ex_mem.valid && (mem_result.exc || ex_mem.mret);
        wb_redirect = mem_wb.valid && (mem_wb.exc || mem_wb.mret);
        older_stop = wb_redirect || mem_bad;
    end

    always_comb begin
        operand_a = id_ex.a;
        operand_b = id_ex.b;
        if (mem_wb.valid && mem_wb.regwrite && !mem_wb.exc && mem_wb.rd != 0) begin
            if (id_ex.use1 && id_ex.rs1 == mem_wb.rd) operand_a = mem_wb.result;
            if (id_ex.use2 && id_ex.rs2 == mem_wb.rd) operand_b = mem_wb.result;
        end
        if (ex_mem.valid && ex_mem.regwrite && !mem_result.exc && ex_mem.rd != 0 && mem_done) begin
            if (id_ex.use1 && id_ex.rs1 == ex_mem.rd) operand_a = mem_result.result;
            if (id_ex.use2 && id_ex.rs2 == ex_mem.rd) operand_b = mem_result.result;
        end
        if (id_ex.use1 && id_ex.rs1 == 0) operand_a = 0;
        if (id_ex.use2 && id_ex.rs2 == 0) operand_b = 0;
        alu_a = id_ex.pc_operand ? id_ex.pc : operand_a;
        alu_b = id_ex.immediate ? id_ex.imm : operand_b;
        ex_result = '0;
        ex_result.valid = id_ex.valid;
        ex_result.pc = id_ex.pc;
        ex_result.insn = id_ex.insn;
        ex_result.rd = id_ex.rd;
        ex_result.regwrite = id_ex.regwrite;
        ex_result.load = id_ex.load;
        ex_result.store = id_ex.store;
        ex_result.f3 = id_ex.f3;
        ex_result.exc = id_ex.exc;
        ex_result.cause = id_ex.cause;
        ex_result.tval = id_ex.tval;
        ex_result.mret = id_ex.mret;
        case (id_ex.alu)
            A_ADD: ex_result.result = alu_a + alu_b;
            A_SUB: ex_result.result = alu_a - alu_b;
            A_SLL: ex_result.result = alu_a << alu_b[4:0];
            A_SLT: ex_result.result = {31'b0, $signed(alu_a) < $signed(alu_b)};
            A_SLTU: ex_result.result = {31'b0, alu_a < alu_b};
            A_XOR: ex_result.result = alu_a ^ alu_b;
            A_SRL: ex_result.result = alu_a >> alu_b[4:0];
            A_SRA: ex_result.result = $signed(alu_a) >>> alu_b[4:0];
            A_OR: ex_result.result = alu_a | alu_b;
            A_AND: ex_result.result = alu_a & alu_b;
            A_LUI: ex_result.result = alu_b;
            default: ex_result.result = 0;
        endcase
        ex_result.addr = operand_a + id_ex.imm;
        if (id_ex.store) begin
            case (id_ex.f3)
                0: begin
                    ex_result.strobes = 4'b0001 << ex_result.addr[1:0];
                    ex_result.store_data = {24'b0, operand_b[7:0]} << {ex_result.addr[1:0],3'b0};
                end
                1: begin
                    ex_result.strobes = 4'b0011 << ex_result.addr[1:0];
                    ex_result.store_data = {16'b0, operand_b[15:0]} << {ex_result.addr[1:0],3'b0};
                end
                2: begin ex_result.strobes = 4'b1111; ex_result.store_data = operand_b; end
                default: begin end
            endcase
        end
        if (!id_ex.exc && (id_ex.load || id_ex.store) &&
            ((id_ex.f3[1:0] == 1 && ex_result.addr[0]) ||
             (id_ex.f3[1:0] == 2 && ex_result.addr[1:0] != 0))) begin
            ex_result.exc = 1;
            ex_result.cause = id_ex.store ? 32'd6 : 32'd4;
            ex_result.tval = ex_result.addr;
        end
        branch_taken = 0;
        case (id_ex.f3)
            0: branch_taken = operand_a == operand_b;
            1: branch_taken = operand_a != operand_b;
            4: branch_taken = $signed(operand_a) < $signed(operand_b);
            5: branch_taken = $signed(operand_a) >= $signed(operand_b);
            6: branch_taken = operand_a < operand_b;
            7: branch_taken = operand_a >= operand_b;
            default: branch_taken = 0;
        endcase
        target = id_ex.jalr ? ((operand_a + id_ex.imm) & 32'hfffffffe) : id_ex.pc + id_ex.imm;
        if (id_ex.jal || id_ex.jalr) ex_result.result = id_ex.pc + 4;
        if (!id_ex.exc && (id_ex.jal || id_ex.jalr || (id_ex.branch && branch_taken)) && target[1:0] != 0) begin
            ex_result.exc = 1;
            ex_result.cause = 0;
            ex_result.tval = target;
        end
        csr_old = 0;
        case (id_ex.csr_addr)
            12'h300: csr_old = mstatus;
            12'h301: csr_old = 32'h40000100;
            12'h305: csr_old = mtvec;
            12'h340: csr_old = mscratch;
            12'h341: csr_old = mepc;
            12'h342: csr_old = mcause;
            12'h343: csr_old = mtval;
            default: csr_old = 0;
        endcase
        csr_source = id_ex.f3[2] ? {27'b0,id_ex.rs1} : operand_a;
        if (id_ex.csr) begin
            ex_result.result = csr_old;
            ex_result.csr_write = id_ex.csr_write;
            ex_result.csr_addr = id_ex.csr_addr;
            case (id_ex.f3[1:0])
                1: ex_result.csr_data = csr_source;
                2: ex_result.csr_data = csr_old | csr_source;
                3: ex_result.csr_data = csr_old & ~csr_source;
                default: ex_result.csr_data = 0;
            endcase
        end
        if (id_ex.dot) ex_result.result = npu_rsp_data;
        if (ex_result.exc) begin
            ex_result.regwrite = 0;
            ex_result.load = 0;
            ex_result.store = 0;
            ex_result.strobes = 0;
            ex_result.csr_write = 0;
            ex_result.mret = 0;
        end
    end

    assign csr_wait = id_ex.csr && !id_ex.exc && (ex_mem.valid || mem_wb.valid);
    assign ex_fire = id_ex.valid && mem_done && !older_stop && !csr_wait &&
        (!id_ex.dot || id_ex.exc || (dot_issued && npu_rsp_valid));
    assign ex_redirect = ex_fire && !ex_result.exc &&
        (id_ex.jal || id_ex.jalr || (id_ex.branch && branch_taken));
    assign id_fire = if_id_valid && (!id_ex.valid || ex_fire) && !older_stop &&
        !ex_redirect && !(ex_fire && (ex_result.exc || ex_result.mret));
    assign imem_valid = rst_n && (!if_id_valid || id_fire) && !older_stop &&
        !ex_redirect && !(ex_fire && (ex_result.exc || ex_result.mret));
    assign imem_addr = fetch_pc;
    assign npu_kill = !rst_n || wb_redirect;
    assign npu_req_valid = rst_n && id_ex.valid && id_ex.dot && !id_ex.exc &&
        !dot_issued && mem_done && !older_stop;
    assign npu_rsp_ready = rst_n && id_ex.valid && id_ex.dot && dot_issued &&
        mem_done && !older_stop;

    // The EX offer becomes the identical MEM offer if ready is low at entry.
    always_comb begin
        dmem_req_valid = 0;
        dmem_req_write = 0;
        dmem_req_addr = 0;
        dmem_req_wdata = 0;
        dmem_req_wstrb = 0;
        if (rst_n && !wb_redirect) begin
            if (ex_mem.valid && (ex_mem.load || ex_mem.store) && !ex_mem.issued) begin
                dmem_req_valid = 1;
                dmem_req_write = ex_mem.store;
                dmem_req_addr = {ex_mem.addr[31:2],2'b0};
                dmem_req_wdata = ex_mem.store_data;
                dmem_req_wstrb = ex_mem.strobes;
            end else if (ex_fire && (ex_result.load || ex_result.store)) begin
                dmem_req_valid = 1;
                dmem_req_write = ex_result.store;
                dmem_req_addr = {ex_result.addr[31:2],2'b0};
                dmem_req_wdata = ex_result.store_data;
                dmem_req_wstrb = ex_result.strobes;
            end
        end
        dmem_rsp_ready = rst_n && ex_mem.valid && (ex_mem.load || ex_mem.store) &&
            ex_mem.issued && !wb_redirect;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fetch_pc <= 32'h80000000;
            if_id_valid <= 0;
            if_id_saved <= 0;
            if_id_pc <= 0;
            if_id_insn <= 0;
            id_ex <= '0;
            ex_mem <= '0;
            mem_wb <= '0;
            dot_issued <= 0;
            for (integer i=0; i<32; i=i+1) gpr[i] <= 0;
            mstatus <= 32'h00001800;
            mtvec <= 32'h80000000;
            mscratch <= 0;
            mepc <= 0;
            mcause <= 0;
            mtval <= 0;
            commit_valid <= 0;
            commit_pc <= 0;
            commit_insn <= 0;
            commit_rd <= 0;
            commit_wdata <= 0;
            commit_mem_addr <= 0;
            commit_mem_wstrb <= 0;
            commit_mem_wdata <= 0;
            trap_valid <= 0;
            trap_pc <= 0;
            trap_cause <= 0;
            trap_tval <= 0;
        end else begin
            commit_valid <= 0;
            trap_valid <= 0;
            mem_wb.valid <= 0;
            if (mem_wb.valid) begin
                if (mem_wb.exc) begin
                    trap_valid <= 1;
                    trap_pc <= mem_wb.pc;
                    trap_cause <= mem_wb.cause;
                    trap_tval <= mem_wb.tval;
                    mepc <= {mem_wb.pc[31:2],2'b0};
                    mcause <= mem_wb.cause;
                    mtval <= mem_wb.tval;
                    mstatus <= 32'h1800 | (mstatus[3] ? 32'h80 : 32'b0);
                end else begin
                    commit_valid <= 1;
                    commit_pc <= mem_wb.pc;
                    commit_insn <= mem_wb.insn;
                    commit_rd <= mem_wb.regwrite ? mem_wb.rd : 5'b0;
                    commit_wdata <= mem_wb.regwrite && mem_wb.rd != 0 ? mem_wb.result : 32'b0;
                    commit_mem_addr <= mem_wb.store ? {mem_wb.addr[31:2],2'b0} : 32'b0;
                    commit_mem_wstrb <= mem_wb.store ? mem_wb.strobes : 4'b0;
                    commit_mem_wdata <= mem_wb.store ? mem_wb.store_data : 32'b0;
                    if (mem_wb.regwrite && mem_wb.rd != 0) gpr[mem_wb.rd] <= mem_wb.result;
                    if (mem_wb.csr_write) begin
                        case (mem_wb.csr_addr)
                            12'h300: mstatus <= (mem_wb.csr_data & 32'h88) | 32'h1800;
                            12'h305: mtvec <= mem_wb.csr_data & 32'hfffffffc;
                            12'h340: mscratch <= mem_wb.csr_data;
                            12'h341: mepc <= mem_wb.csr_data & 32'hfffffffc;
                            12'h342: mcause <= mem_wb.csr_data;
                            12'h343: mtval <= mem_wb.csr_data;
                            default: begin end
                        endcase
                    end
                    if (mem_wb.mret) mstatus <= 32'h1880 | (mstatus[7] ? 32'h8 : 32'b0);
                end
            end
            if (wb_redirect) begin
                fetch_pc <= mem_wb.exc ? mtvec : mepc;
                if_id_valid <= 0;
                if_id_saved <= 0;
                id_ex.valid <= 0;
                ex_mem.valid <= 0;
                mem_wb.valid <= 0;
                dot_issued <= 0;
            end else begin
                if (mem_done) begin
                    mem_wb <= mem_result;
                    mem_wb.valid <= ex_mem.valid;
                    ex_mem.valid <= 0;
                    if (ex_fire) begin
                        ex_mem <= ex_result;
                        ex_mem.issued <= dmem_req_valid && dmem_req_ready;
                    end
                end else if (dmem_req_valid && dmem_req_ready) ex_mem.issued <= 1;
                if (npu_req_valid && npu_req_ready) dot_issued <= 1;
                if (ex_fire) begin
                    id_ex.valid <= 0;
                    dot_issued <= 0;
                end else if (id_ex.valid) begin
                    // Preserve bypassed sources when their producer drains during a hold.
                    id_ex.a <= operand_a;
                    id_ex.b <= operand_b;
                end
                if (id_fire) begin
                    id_ex <= decoded;
                    dot_issued <= 0;
                    if_id_valid <= 0;
                    if_id_saved <= 0;
                end
                if (if_id_valid && !id_fire && !if_id_saved) begin
                    if_id_insn <= imem_rdata;
                    if_id_saved <= 1;
                end
                if (imem_valid) begin
                    if_id_pc <= fetch_pc;
                    if_id_valid <= 1;
                    if_id_saved <= 0;
                    fetch_pc <= fetch_pc + 4;
                end
                if (ex_redirect) begin
                    fetch_pc <= target;
                    if_id_valid <= 0;
                    if_id_saved <= 0;
                    id_ex.valid <= 0;
                end
            end
        end
    end
endmodule
