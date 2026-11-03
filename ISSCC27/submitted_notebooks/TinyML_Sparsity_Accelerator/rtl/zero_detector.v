`timescale 1ns / 1ps

module zero_detector #(
    parameter DATA_WIDTH = 8
)(
    input  wire [DATA_WIDTH-1:0] act,
    input  wire [DATA_WIDTH-1:0] wt,
    output wire is_zero
);

    // Identifies zero activation or zero weight
    assign is_zero = (act == {DATA_WIDTH{1'b0}}) || (wt == {DATA_WIDTH{1'b0}});

endmodule
