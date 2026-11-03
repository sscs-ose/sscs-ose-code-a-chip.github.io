`default_nettype none
module rv32i_five_stage_cpu #(parameter ENABLE_XNEBULA = 0) (
    input logic clk,
    input logic rst_n,
    output logic imem_valid,
    output logic [31:0] imem_addr,
    input logic [31:0] imem_rdata,
    output logic dmem_req_valid,
    input logic dmem_req_ready,
    output logic dmem_req_write,
    output logic [31:0] dmem_req_addr,
    output logic [31:0] dmem_req_wdata,
    output logic [3:0] dmem_req_wstrb,
    input logic dmem_rsp_valid,
    output logic dmem_rsp_ready,
    input logic [31:0] dmem_rsp_rdata,
    input logic dmem_rsp_err,
    output logic commit_valid,
    output logic [31:0] commit_pc,
    output logic [31:0] commit_insn,
    output logic [4:0] commit_rd,
    output logic [31:0] commit_wdata,
    output logic [31:0] commit_mem_addr,
    output logic [3:0] commit_mem_wstrb,
    output logic [31:0] commit_mem_wdata,
    output logic trap_valid,
    output logic [31:0] trap_pc,
    output logic [31:0] trap_cause,
    output logic [31:0] trap_tval
);

    typedef struct packed {
        logic lui, auipc, jal, jalr, branch_op, load_op, store_op;
        logic opimm, opreg, fence_op, ecall, ebreak, mret, csr, xdot;
        logic uses_a, uses_b, rd_write, csr_write, legal;
    } decode_t;

    function automatic decode_t decode(input logic [31:0] word);
        decode_t d;
        logic [6:0] op, f7;
        logic [2:0] f3;
        logic [11:0] ca;
        logic csr_known, csr_ro;
        begin
            d = '0;
            op = word[6:0]; f3 = word[14:12]; f7 = word[31:25]; ca = word[31:20];
            d.lui = op == 7'h37;
            d.auipc = op == 7'h17;
            d.jal = op == 7'h6f;
            d.jalr = op == 7'h67 && f3 == 0;
            d.branch_op = op == 7'h63 && (f3 == 0 || f3 == 1 || f3 >= 4);
            d.load_op = op == 7'h03 && (f3 <= 2 || f3 == 4 || f3 == 5);
            d.store_op = op == 7'h23 && f3 <= 2;
            d.opimm = op == 7'h13 && (f3 == 0 || f3 == 2 || f3 == 3 ||
                f3 == 4 || f3 == 6 || f3 == 7 || (f3 == 1 && f7 == 0) ||
                (f3 == 5 && (f7 == 0 || f7 == 7'h20)));
            d.opreg = op == 7'h33 && (f7 == 0 || (f7 == 7'h20 && (f3 == 0 || f3 == 5)));
            d.fence_op = op == 7'h0f && f3 == 0;
            d.ecall = word == 32'h00000073;
            d.ebreak = word == 32'h00100073;
            d.mret = word == 32'h30200073;
            d.csr = op == 7'h73 && (f3 == 1 || f3 == 2 || f3 == 3 || f3 >= 5);
            d.xdot = ENABLE_XNEBULA == 1 && op == 7'h0b && f3 == 0 && f7 == 0;
            d.uses_a = d.opimm || d.opreg || d.load_op || d.store_op || d.branch_op ||
                d.jalr || d.xdot || (d.csr && !word[14]);
            d.uses_b = d.opreg || d.store_op || d.branch_op || d.xdot;
            d.rd_write = d.lui || d.auipc || d.jal || d.jalr || d.load_op ||
                d.opimm || d.opreg || d.csr || d.xdot;
            d.csr_write = d.csr && (f3 == 1 || f3 == 5 || word[19:15] != 0);
            csr_known = ca == 12'h300 || ca == 12'h301 || ca == 12'h305 ||
                ca == 12'h340 || ca == 12'h341 || ca == 12'h342 || ca == 12'h343 || ca == 12'hf14;
            csr_ro = ca == 12'h301 || ca == 12'hf14;
            d.legal = (d.rd_write || d.branch_op || d.store_op || d.fence_op ||
                d.ecall || d.ebreak || d.mret) &&
                !(d.csr && (!csr_known || (csr_ro && d.csr_write)));
            decode = d;
        end
    endfunction

    typedef struct packed {
        logic [31:0] pc, insn;
        logic fault;
        logic [31:0] cause, tval;
        logic [31:0] a_snap, b_snap;
    } ex_token_t;
    typedef struct packed {
        logic [31:0] pc, insn;
        logic fault;
        logic [31:0] cause, tval;
        logic [4:0] rd;
        logic rd_write;
        logic [31:0] result;
        logic load_op, store_op;
        logic [31:0] ea;
        logic [2:0] f3;
        logic [31:0] bus_addr, bus_data;
        logic [3:0] bus_mask;
        logic csr_write;
        logic [11:0] csr_addr;
        logic [31:0] csr_new;
        logic mret;
    } mem_token_t;

    logic [31:0] fetch_pc, if_pc, if_word;
    logic if_v, if_held, if_fault, ex_v, mem_v, wb_v;
    ex_token_t ex;
    mem_token_t mem, wb, ex_to_mem, mem_to_wb;
    logic [31:0] rf [0:31];
    logic [31:0] mstatus, mtvec, mscratch, mepc, mcause, mtval;
    logic mem_sent, xdot_issued;
    logic [31:0] id_word, id_a, id_b;
    decode_t id_d, ex_d;
    logic [4:0] id_rs1, id_rs2, ex_rs1, ex_rs2, ex_rd;
    logic [2:0] ex_f3;
    logic [31:0] ex_a, ex_b, imm_i, imm_s, imm_b, imm_u, imm_j;
    logic [31:0] alu_b, alu_result, ea, target, csr_old, csr_source, csr_new;
    logic branch_taken, control_taken, misaligned, target_bad, ex_final_fault;
    logic [31:0] ex_final_cause, ex_final_tval;
    logic wb_trap, wb_normal, wb_return, wb_flush, wb_rf_write;
    logic mem_req_fire, mem_rsp_fire, mem_error, mem_advance, mem_available, mem_known_fault;
    logic [31:0] mem_shifted, load_result, completed_result;
    logic mem_can_forward, a_match, b_match, operands_ready;
    logic ex_eligible, ex_advance, ex_redirect, ex_fault_selected, front_flush;
    logic csr_serial_busy, id_serial_wait, id_load_use, id_advance;
    logic id_decode_fault, fetch_block, fetch_room, fetch_fire, fetch_bad;
    logic npu_kill, npu_req_valid, npu_req_ready, npu_rsp_ready, npu_rsp_valid;
    logic [31:0] npu_rsp_data;
    logic npu_req_fire, npu_rsp_fire;

    assign id_word = if_held ? if_word : imem_rdata;
    assign id_d = decode(id_word);
    assign ex_d = decode(ex.insn);
    assign id_rs1 = id_word[19:15];
    assign id_rs2 = id_word[24:20];
    assign ex_rs1 = ex.insn[19:15];
    assign ex_rs2 = ex.insn[24:20];
    assign ex_rd = ex.insn[11:7];
    assign ex_f3 = ex.insn[14:12];
    assign wb_trap = rst_n && wb_v && wb.fault;
    assign wb_normal = rst_n && wb_v && !wb.fault;
    assign wb_return = wb_normal && wb.mret;
    assign wb_flush = wb_trap || wb_return;
    assign wb_rf_write = wb_normal && wb.rd_write && wb.rd != 0;
    assign id_a = id_rs1 == 0 ? 32'b0 : wb_rf_write && wb.rd == id_rs1 ? wb.result : rf[id_rs1];
    assign id_b = id_rs2 == 0 ? 32'b0 : wb_rf_write && wb.rd == id_rs2 ? wb.result : rf[id_rs2];

    assign dmem_req_valid = rst_n && mem_v && (mem.load_op || mem.store_op) &&
        !mem.fault && !mem_sent && !wb_flush;
    assign dmem_req_write = dmem_req_valid && mem.store_op;
    assign dmem_req_addr = rst_n ? mem.bus_addr : 32'b0;
    assign dmem_req_wdata = rst_n ? mem.bus_data : 32'b0;
    assign dmem_req_wstrb = rst_n ? mem.bus_mask : 4'b0;
    assign dmem_rsp_ready = rst_n && mem_v && (mem.load_op || mem.store_op) &&
        !mem.fault && mem_sent && !wb_flush;
    assign mem_req_fire = dmem_req_valid && dmem_req_ready;
    assign mem_rsp_fire = dmem_rsp_valid && dmem_rsp_ready;
    assign mem_error = mem_rsp_fire && dmem_rsp_err;
    assign mem_advance = rst_n && mem_v && !wb_flush &&
        (!(mem.load_op || mem.store_op) || mem.fault || mem_rsp_fire);
    assign mem_available = !mem_v || mem_advance;
    assign mem_known_fault = mem_v && mem.fault;
    assign mem_shifted = dmem_rsp_rdata >> {mem.ea[1:0], 3'b000};
    always_comb begin
        case (mem.f3)
            3'd0: load_result = {{24{mem_shifted[7]}}, mem_shifted[7:0]};
            3'd1: load_result = {{16{mem_shifted[15]}}, mem_shifted[15:0]};
            3'd4: load_result = {24'b0, mem_shifted[7:0]};
            3'd5: load_result = {16'b0, mem_shifted[15:0]};
            default: load_result = dmem_rsp_rdata;
        endcase
    end
    assign completed_result = mem.load_op ? load_result : mem.result;
    assign mem_can_forward = mem_v && !mem.fault && !mem_error && mem.rd_write &&
        mem.rd != 0 && (!mem.load_op || mem_rsp_fire);
    assign a_match = ex_d.uses_a && ex_rs1 != 0 && mem_v && !mem.fault &&
        mem.rd_write && mem.rd == ex_rs1;
    assign b_match = ex_d.uses_b && ex_rs2 != 0 && mem_v && !mem.fault &&
        mem.rd_write && mem.rd == ex_rs2;
    assign operands_ready = !(a_match && !mem_can_forward) && !(b_match && !mem_can_forward);
    assign ex_a = ex_rs1 == 0 ? 32'b0 : a_match && mem_can_forward ? completed_result :
        wb_rf_write && wb.rd == ex_rs1 ? wb.result : ex.a_snap;
    assign ex_b = ex_rs2 == 0 ? 32'b0 : b_match && mem_can_forward ? completed_result :
        wb_rf_write && wb.rd == ex_rs2 ? wb.result : ex.b_snap;

    assign imm_i = {{20{ex.insn[31]}}, ex.insn[31:20]};
    assign imm_s = {{20{ex.insn[31]}}, ex.insn[31:25], ex.insn[11:7]};
    assign imm_b = {{19{ex.insn[31]}}, ex.insn[31], ex.insn[7], ex.insn[30:25], ex.insn[11:8], 1'b0};
    assign imm_u = {ex.insn[31:12], 12'b0};
    assign imm_j = {{11{ex.insn[31]}}, ex.insn[31], ex.insn[19:12], ex.insn[20], ex.insn[30:21], 1'b0};
    assign alu_b = ex_d.opimm ? imm_i : ex_b;
    always_comb begin
        case (ex_f3)
            3'd0: alu_result = ex_d.opreg && ex.insn[31:25] == 7'h20 ? ex_a - alu_b : ex_a + alu_b;
            3'd1: alu_result = ex_a << alu_b[4:0];
            3'd2: alu_result = {31'b0, ($signed(ex_a) < $signed(alu_b))};
            3'd3: alu_result = {31'b0, (ex_a < alu_b)};
            3'd4: alu_result = ex_a ^ alu_b;
            3'd5: alu_result = ex.insn[31:25] == 7'h20 ? $unsigned($signed(ex_a) >>> alu_b[4:0]) : ex_a >> alu_b[4:0];
            3'd6: alu_result = ex_a | alu_b;
            default: alu_result = ex_a & alu_b;
        endcase
        case (ex_f3)
            3'd0: branch_taken = ex_a == ex_b;
            3'd1: branch_taken = ex_a != ex_b;
            3'd4: branch_taken = $signed(ex_a) < $signed(ex_b);
            3'd5: branch_taken = $signed(ex_a) >= $signed(ex_b);
            3'd6: branch_taken = ex_a < ex_b;
            default: branch_taken = ex_a >= ex_b;
        endcase
    end
    assign ea = ex_a + (ex_d.store_op ? imm_s : imm_i);
    assign control_taken = ex_d.jal || ex_d.jalr || (ex_d.branch_op && branch_taken);
    assign target = ex_d.jalr ? (ex_a + imm_i) & 32'hfffffffe : ex.pc + (ex_d.jal ? imm_j : imm_b);
    assign target_bad = control_taken && target[1:0] != 0;
    assign misaligned = (ex_d.load_op || ex_d.store_op) &&
        (((ex_f3 == 1 || ex_f3 == 5) && ea[0]) || (ex_f3 == 2 && ea[1:0] != 0));
    assign ex_final_fault = ex.fault || misaligned || target_bad;
    assign ex_final_cause = ex.fault ? ex.cause : misaligned ? (ex_d.store_op ? 32'd6 : 32'd4) : 32'd0;
    assign ex_final_tval = ex.fault ? ex.tval : misaligned ? ea : target;
    always_comb begin
        case (ex.insn[31:20])
            12'h300: csr_old = mstatus;
            12'h301: csr_old = 32'h40000100;
            12'h305: csr_old = mtvec;
            12'h340: csr_old = mscratch;
            12'h341: csr_old = mepc;
            12'h342: csr_old = mcause;
            12'h343: csr_old = mtval;
            default: csr_old = 0;
        endcase
    end
    assign csr_source = ex.insn[14] ? {27'b0, ex_rs1} : ex_a;
    assign csr_new = ex_f3 == 1 || ex_f3 == 5 ? csr_source :
        ex_f3 == 2 || ex_f3 == 6 ? csr_old | csr_source : csr_old & ~csr_source;

    assign npu_kill = !rst_n || wb_flush || mem_error || mem_known_fault;
    assign ex_eligible = rst_n && ex_v && !wb_flush && !mem_error && !mem_known_fault &&
        mem_available && operands_ready;
    assign npu_req_valid = ex_eligible && ex_d.xdot && !ex_final_fault && !xdot_issued && !npu_kill;
    assign npu_rsp_ready = ex_eligible && ex_d.xdot && xdot_issued && !ex_final_fault && !npu_kill;
    generate
        if (ENABLE_XNEBULA == 1) begin : enabled_npu
            nebula_npu_dot4 npu (
                .clk(clk), .rst_n(rst_n), .kill(npu_kill),
                .req_valid(npu_req_valid), .req_ready(npu_req_ready), .req_a(ex_a), .req_b(ex_b),
                .rsp_valid(npu_rsp_valid), .rsp_ready(npu_rsp_ready), .rsp_data(npu_rsp_data)
            );
        end else begin : disabled_npu
            assign npu_req_ready = 1'b0;
            assign npu_rsp_valid = 1'b0;
            assign npu_rsp_data = 32'b0;
        end
    endgenerate
    assign npu_req_fire = npu_req_valid && npu_req_ready;
    assign npu_rsp_fire = npu_rsp_valid && npu_rsp_ready;
    assign ex_advance = ex_eligible && (!ex_d.xdot || ex_final_fault || npu_rsp_fire);
    assign ex_redirect = ex_advance && !ex_final_fault && control_taken;
    assign ex_fault_selected = ex_advance && ex_final_fault;
    assign front_flush = wb_flush || mem_error || mem_known_fault || ex_redirect || ex_fault_selected;
    assign csr_serial_busy = (ex_v && (ex_d.csr || ex_d.mret)) ||
        (mem_v && mem.insn[6:0] == 7'h73) || (wb_v && wb.insn[6:0] == 7'h73);
    assign id_serial_wait = if_v && (id_d.csr || id_d.mret) && (ex_v || mem_v || wb_v);
    assign id_load_use = if_v && ex_v && ex_d.load_op && !ex.fault && ex_rd != 0 &&
        ((id_d.uses_a && id_rs1 == ex_rd) || (id_d.uses_b && id_rs2 == ex_rd));
    assign id_advance = rst_n && if_v && (!ex_v || ex_advance) && !front_flush &&
        !id_load_use && !csr_serial_busy && !id_serial_wait;
    assign id_decode_fault = !id_d.legal || id_d.ecall || id_d.ebreak;
    assign fetch_block = front_flush || csr_serial_busy || (if_v && id_decode_fault) ||
        (ex_v && ex.fault) || (ex_v && ex_d.xdot && !ex_advance) || id_serial_wait;
    assign fetch_room = !if_v || id_advance;
    assign imem_valid = rst_n && fetch_room && !fetch_block && fetch_pc[1:0] == 0;
    assign imem_addr = rst_n ? fetch_pc : 32'b0;
    assign fetch_fire = imem_valid;
    assign fetch_bad = rst_n && fetch_room && !fetch_block && fetch_pc[1:0] != 0;

    always_comb begin
        ex_to_mem = '0;
        ex_to_mem.pc = ex.pc; ex_to_mem.insn = ex.insn;
        ex_to_mem.fault = ex_final_fault;
        ex_to_mem.cause = ex_final_cause; ex_to_mem.tval = ex_final_tval;
        ex_to_mem.rd = ex_rd;
        ex_to_mem.rd_write = ex_d.rd_write && !ex_final_fault;
        ex_to_mem.result = ex_d.xdot ? npu_rsp_data : ex_d.lui ? imm_u :
            ex_d.auipc ? ex.pc + imm_u : ex_d.jal || ex_d.jalr ? ex.pc + 4 :
            ex_d.csr ? csr_old : alu_result;
        ex_to_mem.load_op = ex_d.load_op && !ex_final_fault;
        ex_to_mem.store_op = ex_d.store_op && !ex_final_fault;
        ex_to_mem.ea = ea; ex_to_mem.f3 = ex_f3;
        ex_to_mem.bus_addr = ea & 32'hfffffffc;
        if (ex_d.store_op) begin
            case (ex_f3)
                3'd0: begin
                    ex_to_mem.bus_mask = 4'b0001 << ea[1:0];
                    ex_to_mem.bus_data = (ex_b & 32'hff) << {ea[1:0], 3'b000};
                end
                3'd1: begin
                    ex_to_mem.bus_mask = 4'b0011 << ea[1:0];
                    ex_to_mem.bus_data = (ex_b & 32'hffff) << {ea[1:0], 3'b000};
                end
                3'd2: begin
                    ex_to_mem.bus_mask = 4'hf;
                    ex_to_mem.bus_data = ex_b;
                end
                default: begin end
            endcase
        end
        ex_to_mem.csr_write = ex_d.csr_write && !ex_final_fault;
        ex_to_mem.csr_addr = ex.insn[31:20];
        ex_to_mem.csr_new = csr_new;
        ex_to_mem.mret = ex_d.mret && !ex_final_fault;
        mem_to_wb = mem;
        mem_to_wb.result = completed_result;
        mem_to_wb.fault = mem.fault || mem_error;
        if (mem_error) begin
            mem_to_wb.cause = mem.store_op ? 32'd7 : 32'd5;
            mem_to_wb.tval = mem.ea;
        end
        mem_to_wb.rd_write = mem.rd_write && !mem.fault && !mem_error;
        mem_to_wb.store_op = mem.store_op && !mem.fault && !mem_error;
        mem_to_wb.csr_write = mem.csr_write && !mem.fault && !mem_error;
        mem_to_wb.mret = mem.mret && !mem.fault && !mem_error;
    end

    integer i;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fetch_pc <= 32'h80000000;
            if_v <= 0; if_pc <= 0; if_word <= 0; if_held <= 0; if_fault <= 0;
            ex_v <= 0; mem_v <= 0; wb_v <= 0;
            ex <= '0; mem <= '0; wb <= '0;
            mem_sent <= 0; xdot_issued <= 0;
            for (i = 0; i < 32; i = i + 1) rf[i] <= 0;
            mstatus <= 32'h1800; mtvec <= 32'h80000000;
            mscratch <= 0; mepc <= 0; mcause <= 0; mtval <= 0;
            commit_valid <= 0; commit_pc <= 0; commit_insn <= 0;
            commit_rd <= 0; commit_wdata <= 0;
            commit_mem_addr <= 0; commit_mem_wdata <= 0; commit_mem_wstrb <= 0;
            trap_valid <= 0; trap_pc <= 0; trap_cause <= 0; trap_tval <= 0;
        end else begin
            if (wb_trap) fetch_pc <= mtvec;
            else if (wb_return) fetch_pc <= mepc;
            else if (ex_redirect) fetch_pc <= target;
            else if (fetch_fire) fetch_pc <= fetch_pc + 4;

            if (front_flush) begin
                if_v <= 0; if_pc <= 0; if_word <= 0; if_held <= 0; if_fault <= 0;
            end else if (fetch_fire || fetch_bad) begin
                if_v <= 1; if_pc <= fetch_pc; if_held <= 0; if_fault <= fetch_bad;
            end else if (id_advance) begin
                if_v <= 0; if_held <= 0; if_fault <= 0;
            end else if (if_v && !if_held) begin
                // A blocked ID must retain its paired response even if invalid bus data changes.
                if_word <= imem_rdata; if_held <= 1;
            end

            if (wb_flush || mem_error || mem_known_fault) begin
                ex_v <= 0; ex <= '0;
            end else if (id_advance) begin
                ex_v <= 1;
                ex.pc <= if_pc; ex.insn <= id_word;
                ex.a_snap <= id_a; ex.b_snap <= id_b;
                ex.fault <= if_fault || id_decode_fault;
                ex.cause <= if_fault ? 32'd0 : !id_d.legal ? 32'd2 : id_d.ebreak ? 32'd3 : 32'd11;
                ex.tval <= if_fault ? if_pc : !id_d.legal ? id_word : 32'd0;
            end else begin
                if (ex_advance) ex_v <= 0;
                if (ex_v && ex_d.uses_a && wb_rf_write && ex_rs1 == wb.rd) ex.a_snap <= wb.result;
                if (ex_v && ex_d.uses_b && wb_rf_write && ex_rs2 == wb.rd) ex.b_snap <= wb.result;
            end
            if (npu_kill || ex_advance) xdot_issued <= 0;
            else if (npu_req_fire) xdot_issued <= 1;

            if (wb_flush || mem_error) begin
                mem_v <= 0; mem <= '0;
            end else if (ex_advance) begin
                mem_v <= 1; mem <= ex_to_mem;
            end else if (mem_advance) mem_v <= 0;
            if (wb_flush || mem_rsp_fire || ex_advance) mem_sent <= 0;
            else if (mem_req_fire) mem_sent <= 1;
            wb_v <= mem_advance;
            wb <= mem_advance ? mem_to_wb : '0;

            rf[0] <= 0;
            if (wb_rf_write) rf[wb.rd] <= wb.result;
            if (wb_trap) begin
                mstatus <= 32'h1800 | (mstatus[3] ? 32'h80 : 32'b0);
                mepc <= wb.pc & 32'hfffffffc;
                mcause <= wb.cause; mtval <= wb.tval;
            end else if (wb_return) mstatus <= 32'h1880 | (mstatus[7] ? 32'h8 : 32'b0);
            else if (wb_normal && wb.csr_write) begin
                case (wb.csr_addr)
                    12'h300: mstatus <= (wb.csr_new & 32'h88) | 32'h1800;
                    12'h305: mtvec <= wb.csr_new & 32'hfffffffc;
                    12'h340: mscratch <= wb.csr_new;
                    12'h341: mepc <= wb.csr_new & 32'hfffffffc;
                    12'h342: mcause <= wb.csr_new;
                    12'h343: mtval <= wb.csr_new;
                    default: begin end
                endcase
            end
            commit_valid <= wb_normal;
            commit_pc <= wb_normal ? wb.pc : 32'b0;
            commit_insn <= wb_normal ? wb.insn : 32'b0;
            commit_rd <= wb_rf_write ? wb.rd : 5'b0;
            commit_wdata <= wb_rf_write ? wb.result : 32'b0;
            commit_mem_addr <= wb_normal && wb.store_op ? wb.bus_addr : 32'b0;
            commit_mem_wdata <= wb_normal && wb.store_op ? wb.bus_data : 32'b0;
            commit_mem_wstrb <= wb_normal && wb.store_op ? wb.bus_mask : 4'b0;
            trap_valid <= wb_trap;
            trap_pc <= wb_trap ? wb.pc : 32'b0;
            trap_cause <= wb_trap ? wb.cause : 32'b0;
            trap_tval <= wb_trap ? wb.tval : 32'b0;
        end
    end
endmodule
`default_nettype wire
