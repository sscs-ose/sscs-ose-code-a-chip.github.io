`timescale 1ns / 1ps

module accumulator #(
    parameter IN_WIDTH  = 16,
    parameter ACC_WIDTH = 32
)(
    input  wire clk,
    input  wire rst_n,
    input  wire clear,
    input  wire enable,
    input  wire signed [IN_WIDTH-1:0]  din,
    output reg  signed [ACC_WIDTH-1:0] acc_out
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc_out <= {ACC_WIDTH{1'b0}};
        end else if (clear) begin
            acc_out <= {ACC_WIDTH{1'b0}};
        end else if (enable) begin
            acc_out <= acc_out + din;
        end
    end

endmodule
