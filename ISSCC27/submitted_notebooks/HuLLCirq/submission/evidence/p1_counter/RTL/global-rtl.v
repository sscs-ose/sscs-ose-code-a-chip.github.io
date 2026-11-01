module release_counter_top(
    input clk_ctr,
    input rst_ctr,
    input [3:0] data_in,
    input data_in_valid,
    output data_in_ready,
    output [3:0] data_out,
    output data_out_valid,
    input data_out_ready
);
    wire data_in_ready_int;
    wire data_out_valid_int;

    release_counter u_6e6f64655f373132373437663732343133 (
        .clk_ctr(clk_ctr),
        .rst_ctr(rst_ctr),
        .data_in(data_in),
        .data_in_valid(data_in_valid),
        .data_in_ready(data_in_ready_int),
        .data_out(data_out),
        .data_out_valid(data_out_valid_int),
        .data_out_ready(data_out_ready)
    );

    assign data_in_ready = data_in_ready_int;
    assign data_out_valid = data_out_valid_int;
endmodule
