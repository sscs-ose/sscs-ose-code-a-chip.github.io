module ControlLogic (
    input      [6:0] opcode,
    output reg       reg_write,
    output reg       mem_read,
    output reg       mem_write,
    output reg       alu_src,
    output reg [1:0] mem_to_reg,
    output reg       branch,
    output reg       jump,
    output reg [1:0] alu_op
);

    // RISC-V 32I Opcodes
    localparam OPCODE_R_TYPE = 7'd51;  // 7'b0110011: ADD, SUB, SLT, etc.
    localparam OPCODE_I_TYPE = 7'd19;  // 7'b0010011: ADDI, SLTI, etc.
    localparam OPCODE_LOAD   = 7'd3;   // 7'b0000011: LW, LB, LH
    localparam OPCODE_STORE  = 7'd35;  // 7'b0100011: SW, SB, SH
    localparam OPCODE_BRANCH = 7'd99;  // 7'b1100011: BEQ, BNE, BLT, BGE
    localparam OPCODE_LUI    = 7'd55;  // 7'b0110111: LUI
    localparam OPCODE_AUIPC  = 7'd23;  // 7'b0010111: AUIPC
    localparam OPCODE_JAL    = 7'd111; // 7'b1101111: JAL
    localparam OPCODE_JALR   = 7'd103; // 7'b1100111: JALR

    always @(*) begin
        reg_write  = 1'b0;
        mem_read   = 1'b0;
        mem_write  = 1'b0;
        alu_src    = 1'b0;
        mem_to_reg = 2'b00;
        branch     = 1'b0;
        jump       = 1'b0;
        alu_op     = 2'b00;

        case (opcode)
            OPCODE_R_TYPE: begin
                reg_write  = 1'b1;
                alu_src    = 1'b0;
                mem_to_reg = 2'b00;
                alu_op     = 2'b10;
            end

            OPCODE_I_TYPE: begin
                reg_write  = 1'b1;
                alu_src    = 1'b1;
                mem_to_reg = 2'b00;
                alu_op     = 2'b10;
            end

            OPCODE_LOAD: begin
                reg_write  = 1'b1;
                mem_read   = 1'b1;
                alu_src    = 1'b1;
                mem_to_reg = 2'b01;
                alu_op     = 2'b00;
            end

            OPCODE_STORE: begin
                mem_write  = 1'b1;
                alu_src    = 1'b1;
                alu_op     = 2'b00;
            end

            OPCODE_BRANCH: begin
                branch     = 1'b1;
                alu_src    = 1'b0;
                alu_op     = 2'b01;
            end

            OPCODE_LUI: begin
                reg_write  = 1'b1;
                mem_to_reg = 2'b11;
                alu_op     = 2'b11;
            end

            OPCODE_AUIPC: begin
                reg_write  = 1'b1;
                alu_src    = 1'b1;
                mem_to_reg = 2'b00;
                alu_op     = 2'b00;
            end

            OPCODE_JAL: begin
                reg_write  = 1'b1;
                jump       = 1'b1;
                mem_to_reg = 2'b10;
            end

            OPCODE_JALR: begin
                reg_write  = 1'b1;
                jump       = 1'b1;
                alu_src    = 1'b1;
                mem_to_reg = 2'b10;
                alu_op     = 2'b00;
            end

            default: begin
                reg_write  = 1'b0;
                mem_read   = 1'b0;
                mem_write  = 1'b0;
                alu_src    = 1'b0;
                mem_to_reg = 2'b00;
                branch     = 1'b0;
                jump       = 1'b0;
                alu_op     = 2'b00;
            end
        endcase
    end

endmodule
