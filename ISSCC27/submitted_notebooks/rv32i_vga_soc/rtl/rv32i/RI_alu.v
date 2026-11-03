module RI_alu (
    input         clk,
    input  [6:0]  opcode,
    input  [31:0] op1,
    input  [31:0] op2,
    input  [31:0] imm_ext,
    input  [2:0]  func3,
    input  [6:0]  func7,

    output reg [31:0] rd
);

reg [31:0] operand2;

always @(*) begin
    if (opcode == 7'b0110011)       // R-type
        operand2 = op2;

    else if (opcode == 7'b0010011)  // I-type
        operand2 = imm_ext;

    else
        operand2 = 32'd0;

    //ALU operations
    if (func3 == 3'b000) begin

        if (opcode == 7'b0110011 &&
            func7 == 7'b0100000)
            rd = op1 - operand2;    // SUB

        else
            rd = op1 + operand2;    // ADD / ADDI
    end

    else if (func3 == 3'b001)
        rd = op1 << operand2[4:0];  // SLL / SLLI

    else if (func3 == 3'b010)
        rd = ($signed(op1) < $signed(operand2)); // SLT / SLTI

    else if (func3 == 3'b011)
        rd = (op1 < operand2);       // SLTU / SLTIU

    else if (func3 == 3'b100)
        rd = op1 ^ operand2;         // XOR / XORI

    else if (func3 == 3'b101) begin

        if (func7 == 7'b0100000)
            rd = $signed(op1) >>> operand2[4:0]; // SRA / SRAI

        else
            rd = op1 >> operand2[4:0];            // SRL / SRLI
    end

    else if (func3 == 3'b110)
        rd = op1 | operand2;          // OR / ORI

    else if (func3 == 3'b111)
        rd = op1 & operand2;          // AND / ANDI

    else
        rd = 32'd0;
end

endmodule
