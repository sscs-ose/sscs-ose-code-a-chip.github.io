module release_xor_byte (
    input wire clk_pipe,
    input wire rst_pipe_n,
    input wire [7:0] data_i,
    input wire data_i_valid,
    output wire data_i_ready,
    output wire [7:0] data_o,
    output wire data_o_valid,
    input wire data_o_ready
);

assign data_o = data_i ^ 8'hA5;
assign data_o_valid = data_i_valid;
assign data_i_ready = data_o_ready;

endmodule
