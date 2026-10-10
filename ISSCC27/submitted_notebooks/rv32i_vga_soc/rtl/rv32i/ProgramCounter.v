module ProgramCounter (
    input             clk,
    input             reset,
    input             stall,
    input      [6:0]  opcode,
    input      [31:0] imm,
    input      [31:0] rs1_data,
    input             jump,
    output reg [31:0] pcRegister
);

    always @(posedge clk) begin
        if (reset) begin
            pcRegister <= 32'd0;
        end else if (!stall) begin
            // JAL: PC-relative jump
            if (opcode == 7'd111) begin
                pcRegister <= pcRegister + imm;
            end
            // JALR: Register-indirect jump
            else if (opcode == 7'd103) begin
                pcRegister <= (rs1_data + imm) & ~32'd1;
            end
            // Branch (conditional)
            else if (opcode == 7'd99 && jump) begin
                pcRegister <= pcRegister + imm;
            end
            // Sequential execution
            else begin
                pcRegister <= pcRegister + 32'd4;
            end
        end
    end

endmodule
