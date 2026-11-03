`default_nettype none
// CPU
// Maquina de estados - FETCH → WAIT → DECODE → EXEC → MEM → WRITE
//   S_FETCH:  PC → BRAM, inicia lectura
//   S_WAIT:   espera 1 ciclo, instruccion llega al final de este estado
//   S_DECODE: captura IR, lee registros, configura ALU
//   S_EXEC:   ALU opera, captura resultado
//   S_MEM:    acceso a memoria / GPIO
//   S_WB:     writeback a regfile, actualiza PC
module cpu_core (
    input  wire        clk,
    input  wire        rst_n,
    output wire [8:0]  pc_out,
    input  wire [15:0] instruction_in,
    output reg  [7:0]  mem_addr,
    output reg  [7:0]  mem_wdata,
    input  wire [7:0]  mem_rdata,
    output reg         mem_we,
    output reg         mem_re,
    output reg  [7:0]  gpio_out,
    output wire [7:0]  debug_pc,
    output wire [7:0]  debug_state,
    output wire [15:0] debug_instr
);
    localparam S_FETCH  = 3'd0;
    localparam S_WAIT   = 3'd1;
    localparam S_DECODE = 3'd2;
    localparam S_EXEC   = 3'd3;
    localparam S_MEM    = 3'd4;
    localparam S_WB     = 3'd5;

    reg [2:0]  st;
    reg [8:0]  pc;
    reg [15:0] ir;

    assign pc_out      = pc;
    assign debug_pc    = pc[7:0];
    assign debug_state = {5'b0, st};
    assign debug_instr = ir;

    // Campos del IR
    wire [2:0] f_op  = ir[15:13];
    wire [2:0] f_rd  = ir[12:10];
    wire [2:0] f_rs1 = ir[9:7];
    wire [2:0] f_fn3 = ir[6:4];
    wire [3:0] f_imm = ir[3:0];
    wire [8:0] f_tgt = ir[8:0];
    wire [2:0] f_rs2  = ir[6:4];   // rs2 para R-type (ALU-Reg)   [FIX]
    wire [2:0] f_fn3r = ir[3:1];   // funct3 para R-type (ALU-Reg) [FIX]
    wire [7:0] se8   = {{4{f_imm[3]}}, f_imm};
    wire [8:0] se9   = {{5{f_imm[3]}}, f_imm};

    // Regfile
    reg [7:0]  regs [1:7];
    reg [2:0]  rs1_addr_r, rs2_addr_r;
    wire [7:0] rs1_data = (rs1_addr_r == 0) ? 8'd0 : regs[rs1_addr_r];
    wire [7:0] rs2_data = (rs2_addr_r == 0) ? 8'd0 : regs[rs2_addr_r];

    // ALU
    reg  [7:0] alu_a, alu_b;
    reg  [2:0] alu_op;
    reg  [8:0] alu_r9;
    always @(*) begin
        case (alu_op)
            3'b000: alu_r9 = {1'b0,alu_a} + {1'b0,alu_b};
            3'b001: alu_r9 = {1'b0,alu_a} - {1'b0,alu_b};
            3'b010: alu_r9 = {1'b0,alu_a & alu_b};
            3'b011: alu_r9 = {1'b0,alu_a | alu_b};
            3'b100: alu_r9 = {1'b0,alu_a ^ alu_b};
            3'b101: alu_r9 = {1'b0,alu_a << alu_b[2:0]};
            3'b110: alu_r9 = {1'b0,alu_a >> alu_b[2:0]};
            3'b111: alu_r9 = {8'd0, (alu_a < alu_b) ? 1'b1 : 1'b0};
            default: alu_r9 = 9'd0;
        endcase
    end
    wire [7:0] alu_out = alu_r9[7:0];
    wire       alu_z   = (alu_out == 8'd0);

    // Latches
    reg [7:0] res_lat;
    reg       z_lat;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st       <= S_FETCH;
            pc       <= 9'd0;
            ir       <= 16'd0;
            mem_we   <= 0;
            mem_re   <= 0;
            gpio_out <= 8'd0;
            alu_a    <= 8'd0;
            alu_b    <= 8'd0;
            alu_op   <= 3'd0;
            res_lat  <= 8'd0;
            z_lat    <= 0;
            rs1_addr_r <= 3'd0;
            rs2_addr_r <= 3'd0;
            for (i=1;i<=7;i=i+1) regs[i] <= 8'd0;
        end else begin
            mem_we <= 0;
            mem_re <= 0;

            case (st)

                S_FETCH: begin
                    
                    st <= S_WAIT;
                end

                S_WAIT: begin
                    
                    st <= S_DECODE;
                end

                S_DECODE: begin
                    // Capturar instruccion
                    ir <= instruction_in;
                    // Leer registros usando campos de instruction_in directamente
                    rs1_addr_r <= instruction_in[9:7];

                    case (instruction_in[15:13])
                        3'b001: rs2_addr_r <= instruction_in[6:4]; // R-type: rs2 en [6:4]  [FIX]
                        3'b011: rs2_addr_r <= instruction_in[12:10]; // STORE: dato en f_rd
                        3'b100: rs2_addr_r <= instruction_in[12:10]; // BEQ: rs1 en f_rd
                        default: rs2_addr_r <= 3'd0;
                    endcase
                    st <= S_EXEC;
                end

                S_EXEC: begin
                    // Registros ya disponibles: rs1_data, rs2_data
                    alu_a <= rs1_data;

                    case (f_op)
                        3'b000: begin // ALU-I
                            alu_op <= f_fn3;
                            alu_b  <= se8;
                        end
                        3'b001: begin // ALU-R
                            alu_op <= f_fn3r;   // funct3 de R-type en [3:1]  [FIX]
                            alu_b  <= rs2_data;
                        end
                        3'b010: begin // LOAD: addr = rs1 + imm
                            alu_op <= 3'b000;
                            alu_b  <= se8;
                        end
                        3'b011: begin // STORE: addr = rs1 + imm
                            alu_op <= 3'b000;
                            alu_b  <= se8;
                        end
                        3'b100: begin // BEQ: comparar rs1 con rs2
                            // rs2_addr_r=f_rd=BEQ.rs1, rs1_addr_r=f_rs1=BEQ.rs2
                            // z_lat = (BEQ.rs1 == BEQ.rs2)
                            z_lat  <= (rs1_data == rs2_data);
                            alu_op <= 3'b000;
                            alu_b  <= 8'd0;
                        end
                        3'b110: begin // OUT
                            alu_op <= 3'b000;
                            alu_b  <= 8'd0;
                        end
                        default: begin
                            alu_op <= 3'b000;
                            alu_b  <= 8'd0;
                        end
                    endcase
                    st <= S_MEM;
                end

                S_MEM: begin
                    res_lat <= alu_out;
                    if (f_op != 3'b100) z_lat <= alu_z; 

                    case (f_op)
                        3'b010: begin // LOAD
                            mem_addr <= alu_out;
                            mem_re   <= 1'b1;
                        end
                        3'b011: begin // STORE
                            mem_addr  <= alu_out;
                            mem_wdata <= rs2_data; // dato = rs2 original
                            mem_we    <= 1'b1;
                        end
                        3'b110: begin // OUT
                            gpio_out <= rs1_data;
                        end
                        default: ;
                    endcase
                    st <= S_WB;
                end

                S_WB: begin
                    case (f_op)
                        3'b000, 3'b001: begin // ALU-I / ALU-R
                            if (f_rd != 0) regs[f_rd] <= res_lat;
                            pc <= pc + 9'd1;
                        end
                        3'b010: begin // LOAD
                            if (f_rd != 0) regs[f_rd] <= mem_rdata;
                            pc <= pc + 9'd1;
                        end
                        3'b011: pc <= pc + 9'd1; // STORE
                        3'b100: begin // BEQ
                            if (z_lat) pc <= pc + 9'd1 + se9;
                            else       pc <= pc + 9'd1;
                        end
                        3'b101: begin // JAL
                            if (f_rd != 0) regs[f_rd] <= pc[7:0] + 8'd1;
                            pc <= f_tgt;
                        end
                        3'b110: pc <= pc + 9'd1; // OUT
                        3'b111: pc <= f_tgt;      // JUMP
                        default: pc <= pc + 9'd1;
                    endcase
                    st <= S_FETCH;
                end

                default: st <= S_FETCH;
            endcase
        end
    end

endmodule
`default_nettype wire