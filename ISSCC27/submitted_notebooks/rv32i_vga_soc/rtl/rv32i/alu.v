module alu(
    input             clk,
    input      [6:0]  opcode,
    input      [31:0] pc,           // Program Counter input for AUIPC / JAL / JALR
    input      [31:0] op1,
    input      [31:0] op2,
    input      [31:0] imm,
    input      [2:0]  func3,
    input      [6:0]  func7,
    output reg        doesB,
    output reg [31:0] rw
);

wire [31:0] ri_result;
wire jump;

RI_alu ri_alu(
    .clk(clk),
    .opcode(opcode),
    .op1(op1),
    .op2(op2),
    .imm_ext(imm),
    .func3(func3),
    .func7(func7),
    .rd(ri_result)
);

bAlu bAlu(
    .clk(clk),
    .op1(op1), 
    .op2(op2),
    .func3(func3),
    .jump(jump)
);

always @(*) begin
    // Default values to prevent unwanted latches
    rw    = 32'd0;
    doesB = 1'b0;

    // R-type (51) and I-type (19) ALU operations
    if (opcode == 7'd19 || opcode == 7'd51) begin
        rw = ri_result;
    end
    // Load (3) and Store (35): Address calculation = rs1 + imm
    else if (opcode == 7'd3 || opcode == 7'd35) begin
        rw = op1 + imm;
    end
    // LUI (55): Load Upper Immediate (rd = imm)
    else if (opcode == 7'd55) begin
        rw = imm;
    end
    // AUIPC (23): Add Upper Immediate to PC (rd = PC + imm)
    else if (opcode == 7'd23) begin
        rw = pc + imm;
    end
    // JAL (111) & JALR (103): Save return address (rd = PC + 4)
    else if (opcode == 7'd111 || opcode == 7'd103) begin
        rw = pc + 32'd4;
    end
    // Branch (99): Condition result to doesB
    else if (opcode == 7'd99) begin
        doesB = jump;
    end
end

endmodule
