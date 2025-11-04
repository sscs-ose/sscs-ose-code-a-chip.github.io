
module mult_8bits
#(
    parameter   DATA_IN_WIDTH = 8,
    parameter   DATA_OUT_WIDTH = 16
)(
    input logic signed [DATA_IN_WIDTH-1:0] A,
    input logic signed [DATA_IN_WIDTH-1:0] B,
    output logic signed [DATA_OUT_WIDTH-1:0] OUT
);

    assign OUT = A * B;

endmodule
