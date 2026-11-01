module release_saturating_array_top (
    input clk_array,
    input rst_array_n,
    input [7:0] lane00_data_i,
    input lane00_data_i_valid,
    output lane00_data_i_ready,
    input [7:0] lane01_data_i,
    input lane01_data_i_valid,
    output lane01_data_i_ready,
    input [7:0] lane10_data_i,
    input lane10_data_i_valid,
    output lane10_data_i_ready,
    input [7:0] lane11_data_i,
    input lane11_data_i_valid,
    output lane11_data_i_ready,
    output [3:0] lane00_data_o,
    output lane00_data_o_valid,
    input lane00_data_o_ready,
    output [3:0] lane01_data_o,
    output lane01_data_o_valid,
    input lane01_data_o_ready,
    output [3:0] lane10_data_o,
    output lane10_data_o_valid,
    input lane10_data_o_ready,
    output [3:0] lane11_data_o,
    output lane11_data_o_valid,
    input lane11_data_o_ready
);

    wire [3:0] lane00_data_o_int;
    wire lane00_data_o_valid_int;
    wire lane00_data_o_ready_int;
    wire [3:0] lane01_data_o_int;
    wire lane01_data_o_valid_int;
    wire lane01_data_o_ready_int;
    wire [3:0] lane10_data_o_int;
    wire lane10_data_o_valid_int;
    wire lane10_data_o_ready_int;
    wire [3:0] lane11_data_o_int;
    wire lane11_data_o_valid_int;
    wire lane11_data_o_ready_int;

    release_saturating_lane u_6e6f64655f326663666165643464353333_r0_c0 (
        .clk_array(clk_array),
        .rst_array_n(rst_array_n),
        .data_i(lane00_data_i),
        .data_i_valid(lane00_data_i_valid),
        .data_i_ready(lane00_data_i_ready),
        .data_o(lane00_data_o_int),
        .data_o_valid(lane00_data_o_valid_int),
        .data_o_ready(lane00_data_o_ready_int)
    );

    release_saturating_lane u_6e6f64655f326663666165643464353333_r0_c1 (
        .clk_array(clk_array),
        .rst_array_n(rst_array_n),
        .data_i(lane01_data_i),
        .data_i_valid(lane01_data_i_valid),
        .data_i_ready(lane01_data_i_ready),
        .data_o(lane01_data_o_int),
        .data_o_valid(lane01_data_o_valid_int),
        .data_o_ready(lane01_data_o_ready_int)
    );

    release_saturating_lane u_6e6f64655f326663666165643464353333_r1_c0 (
        .clk_array(clk_array),
        .rst_array_n(rst_array_n),
        .data_i(lane10_data_i),
        .data_i_valid(lane10_data_i_valid),
        .data_i_ready(lane10_data_i_ready),
        .data_o(lane10_data_o_int),
        .data_o_valid(lane10_data_o_valid_int),
        .data_o_ready(lane10_data_o_ready_int)
    );

    release_saturating_lane u_6e6f64655f326663666165643464353333_r1_c1 (
        .clk_array(clk_array),
        .rst_array_n(rst_array_n),
        .data_i(lane11_data_i),
        .data_i_valid(lane11_data_i_valid),
        .data_i_ready(lane11_data_i_ready),
        .data_o(lane11_data_o_int),
        .data_o_valid(lane11_data_o_valid_int),
        .data_o_ready(lane11_data_o_ready_int)
    );

    assign lane00_data_o = lane00_data_o_int;
    assign lane00_data_o_valid = lane00_data_o_valid_int;
    assign lane01_data_o = lane01_data_o_int;
    assign lane01_data_o_valid = lane01_data_o_valid_int;
    assign lane10_data_o = lane10_data_o_int;
    assign lane10_data_o_valid = lane10_data_o_valid_int;
    assign lane11_data_o = lane11_data_o_int;
    assign lane11_data_o_valid = lane11_data_o_valid_int;

    assign lane00_data_o_ready_int = lane00_data_o_ready;
    assign lane01_data_o_ready_int = lane01_data_o_ready;
    assign lane10_data_o_ready_int = lane10_data_o_ready;
    assign lane11_data_o_ready_int = lane11_data_o_ready;

endmodule
