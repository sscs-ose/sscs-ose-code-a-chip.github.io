`timescale 1ns / 1ps

module instructionMemory (
    input             clk,
    input             reset,
    input      [31:0] address,
    output reg [31:0] data_out
);

    reg [31:0] memory [0:255];

    initial begin
        $readmemh("instructions.hex", memory);
    end

    always @(*) begin
        if (address[31:10] != 0) begin
            data_out = 32'h0000_0013; // Return NOP if outside range
        end else begin
            data_out = memory[address[9:2]];
        end
    end

endmodule
