`timescale 1ns / 1ps

module mac #(
    parameter DATA_WIDTH = 8
)(
    input  wire clk,
    input  wire rst_n,
    input  wire enable,
    input  wire signed [DATA_WIDTH-1:0] act,
    input  wire signed [DATA_WIDTH-1:0] wt,
    output reg  signed [2*DATA_WIDTH-1:0] prod
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            prod <= {2*DATA_WIDTH{1'b0}};
        end else if (enable) begin
            prod <= act * wt;
        end
        // FIX: When !enable, hold last value (saves switching power).
        // Original code forced prod <= 0, causing unnecessary toggling.
    end

endmodule
