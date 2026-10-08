module decoder (
    input      [31:0] instr,
    output reg [6:0]  opcodout,
    output reg [4:0]  rd,
    output reg [4:0]  rs1,
    output reg [4:0]  rs2,
    output reg [2:0]  func3,
    output reg [6:0]  func7,
    output reg [31:0] imm
);

always @(*) begin
    opcodout = 7'd0;
    rd       = 5'd0;
    rs1      = 5'd0;
    rs2      = 5'd0;
    func3    = 3'd0;
    func7    = 7'd0;
    imm      = 32'd0;

    // R-type: ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND (opcode 51)
    if (instr[6:0] == 7'd51) begin
        opcodout = instr[6:0];
        rd       = instr[11:7];
        func3    = instr[14:12];
        rs1      = instr[19:15];
        rs2      = instr[24:20];
        func7    = instr[31:25];
        imm      = 32'd0;
    end
    // I-type ALU: ADDI, SLTI, SLTIU, XORI, ORI, ANDI, SLLI, SRLI, SRAI (opcode 19)
    else if (instr[6:0] == 7'd19) begin
        opcodout = instr[6:0];
        rd       = instr[11:7];
        func3    = instr[14:12];
        rs1      = instr[19:15];
        rs2      = 5'd0;
        func7    = instr[31:25];
        imm      = {{20{instr[31]}}, instr[31:20]};
    end
    // Load: LW, LB, LH, LBU, LHU (opcode 3)
    else if (instr[6:0] == 7'd3) begin
        opcodout = instr[6:0];
        rd       = instr[11:7];
        func3    = instr[14:12];
        rs1      = instr[19:15];
        rs2      = 5'd0;
        func7    = 7'd0;
        imm      = {{20{instr[31]}}, instr[31:20]};
    end
    // Store: SW, SB, SH (opcode 35)
    else if (instr[6:0] == 7'd35) begin
        opcodout = instr[6:0];
        rd       = 5'd0;
        func3    = instr[14:12];
        rs1      = instr[19:15];
        rs2      = instr[24:20];
        func7    = instr[31:25];
        imm      = {{20{instr[31]}}, instr[31:25], instr[11:7]};
    end
    // Branch: BEQ, BNE, BLT, BGE, BLTU, BGEU (opcode 99)
    else if (instr[6:0] == 7'd99) begin
        opcodout = instr[6:0];
        rd       = 5'd0;
        func3    = instr[14:12];
        rs1      = instr[19:15];
        rs2      = instr[24:20];
        func7    = instr[31:25];
        imm      = {{19{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};
    end
    // LUI: Load Upper Immediate (opcode 55)
    else if (instr[6:0] == 7'd55) begin
        opcodout = instr[6:0];
        rd       = instr[11:7];
        rs1      = 5'd0;
        rs2      = 5'd0;
        func3    = 3'd0;
        func7    = 7'd0;
        imm      = {instr[31:12], 12'd0};
    end
    // AUIPC: Add Upper Immediate to PC (opcode 23)
    else if (instr[6:0] == 7'd23) begin
        opcodout = instr[6:0];
        rd       = instr[11:7];
        rs1      = 5'd0;
        rs2      = 5'd0;
        func3    = 3'd0;
        func7    = 7'd0;
        imm      = {instr[31:12], 12'd0};
    end
    // JAL: Jump and Link (opcode 111)
    else if (instr[6:0] == 7'd111) begin
        opcodout = instr[6:0];
        rd       = instr[11:7];
        rs1      = 5'd0;
        rs2      = 5'd0;
        func3    = 3'd0;
        func7    = 7'd0;
        imm      = {{11{instr[31]}}, instr[31], instr[19:12], instr[20], instr[30:21], 1'b0};
    end
    // JALR: Jump and Link Register (opcode 103)
    else if (instr[6:0] == 7'd103) begin
        opcodout = instr[6:0];
        rd       = instr[11:7];
        func3    = instr[14:12];
        rs1      = instr[19:15];
        rs2      = 5'd0;
        func7    = 7'd0;
        imm      = {{20{instr[31]}}, instr[31:20]};
    end
end

endmodule
