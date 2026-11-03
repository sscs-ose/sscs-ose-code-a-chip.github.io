// Fixed Phase 1 array: A moves right and B moves down through PE registers.
module systolic_array_2x2 (
    input  logic clk,
    input  logic rst,
    input  logic clear,
    input  logic [3:0] tile_mask,
    input  logic signed [7:0] a_boundary [0:1],
    input  logic signed [7:0] b_boundary [0:1],
    input  logic [1:0] a_valid,
    input  logic [1:0] b_valid,
    input  logic [1:0] a_last,
    input  logic [1:0] b_last,
    output logic signed [31:0] accumulators [0:3],
    output logic [3:0] result_valid,
    output logic [3:0] active_mask,
    output logic tile_done
);
    logic signed [7:0] a_00_01, a_10_11;
    logic signed [7:0] b_00_10, b_01_11;
    logic av_00_01, av_10_11, bv_00_10, bv_01_11;
    logic al_00_01, al_10_11, bl_00_10, bl_01_11;

    always_ff @(posedge clk) begin
        if (rst)
            active_mask <= 4'b0000;
        else if (clear)
            active_mask <= tile_mask;
    end
    assign tile_done = (|active_mask) && ((result_valid & active_mask) == active_mask);

    gemm_pe pe00 (
        .clk, .rst, .clear,
        .a_in(a_boundary[0]), .b_in(b_boundary[0]),
        .a_valid(a_valid[0]), .b_valid(b_valid[0]),
        .a_last(a_last[0]), .b_last(b_last[0]),
        .a_out(a_00_01), .b_out(b_00_10),
        .a_out_valid(av_00_01), .b_out_valid(bv_00_10),
        .a_out_last(al_00_01), .b_out_last(bl_00_10),
        .accumulator(accumulators[0]), .result_valid(result_valid[0])
    );
    gemm_pe pe01 (
        .clk, .rst, .clear,
        .a_in(a_00_01), .b_in(b_boundary[1]),
        .a_valid(av_00_01), .b_valid(b_valid[1]),
        .a_last(al_00_01), .b_last(b_last[1]),
        .a_out(), .b_out(b_01_11),
        .a_out_valid(), .b_out_valid(bv_01_11),
        .a_out_last(), .b_out_last(bl_01_11),
        .accumulator(accumulators[1]), .result_valid(result_valid[1])
    );
    gemm_pe pe10 (
        .clk, .rst, .clear,
        .a_in(a_boundary[1]), .b_in(b_00_10),
        .a_valid(a_valid[1]), .b_valid(bv_00_10),
        .a_last(a_last[1]), .b_last(bl_00_10),
        .a_out(a_10_11), .b_out(),
        .a_out_valid(av_10_11), .b_out_valid(),
        .a_out_last(al_10_11), .b_out_last(),
        .accumulator(accumulators[2]), .result_valid(result_valid[2])
    );
    gemm_pe pe11 (
        .clk, .rst, .clear,
        .a_in(a_10_11), .b_in(b_01_11),
        .a_valid(av_10_11), .b_valid(bv_01_11),
        .a_last(al_10_11), .b_last(bl_01_11),
        .a_out(), .b_out(), .a_out_valid(), .b_out_valid(),
        .a_out_last(), .b_out_last(),
        .accumulator(accumulators[3]), .result_valid(result_valid[3])
    );
endmodule
