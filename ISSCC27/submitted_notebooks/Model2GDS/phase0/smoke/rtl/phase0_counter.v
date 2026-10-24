`timescale 1ns/1ps

module phase0_counter (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    output reg  [7:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 8'h00;
        else if (en)
            count <= count + 8'h01;
    end
endmodule
