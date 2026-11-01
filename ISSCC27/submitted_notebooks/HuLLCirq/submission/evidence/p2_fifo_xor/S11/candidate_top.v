module release_fifo_xor_top (
    input wire clk_pipe,
    input wire rst_pipe_n,
    input wire [7:0] data_i,
    input wire data_i_valid,
    output wire data_i_ready,
    output wire [7:0] data_o,
    output wire data_o_valid,
    input wire data_o_ready
);
    wire [7:0] xor_data;
    wire xor_valid;
    wire xor_ready;

    release_fifo2 u_6e6f64655f326266333064306661616565 (
        .clk_pipe(clk_pipe),
        .rst_pipe_n(rst_pipe_n),
        .data_i(data_i),
        .data_i_valid(data_i_valid),
        .data_i_ready(data_i_ready),
        .data_o(xor_data),
        .data_o_valid(xor_valid),
        .data_o_ready(xor_ready)
    );

    release_xor_byte u_6e6f64655f636562653736353733323431 (
        .clk_pipe(clk_pipe),
        .rst_pipe_n(rst_pipe_n),
        .data_i(xor_data),
        .data_i_valid(xor_valid),
        .data_i_ready(xor_ready),
        .data_o(data_o),
        .data_o_valid(data_o_valid),
        .data_o_ready(data_o_ready)
    );

endmodule
