`timescale 1ns / 1ps

module top #(
    parameter TILE_SIZE  = 16,
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
)(
    input  wire clk,
    input  wire rst_n,
    
    // Memory Interface
    input  wire wr_en,
    input  wire [$clog2(TILE_SIZE)-1:0] wr_addr,
    input  wire [DATA_WIDTH-1:0] act_in,
    input  wire [DATA_WIDTH-1:0] wt_in,
    
    // Execution Control
    input  wire tile_valid,
    output wire done,
    output wire selected_mode, // 0 = Dense, 1 = Sparse
    output wire [ACC_WIDTH-1:0] result
);

    // Internal Signals
    wire [$clog2(TILE_SIZE)-1:0] rd_addr;
    wire [DATA_WIDTH-1:0] act_buf, wt_buf;
    wire is_zero;
    wire [$clog2(TILE_SIZE+1)-1:0] zero_count;
    wire [15:0] dense_cost, sparse_cost;
    wire use_sparse;
    wire mode_latched;
    wire mac_en, acc_en, acc_clr;
    wire signed [2*DATA_WIDTH-1:0] mac_prod;

    assign selected_mode = mode_latched;

    // Buffer Instance
    input_buffer #(
        .TILE_SIZE(TILE_SIZE),
        .DATA_WIDTH(DATA_WIDTH)
    ) buf_inst (
        .clk(clk),
        .wr_en(wr_en),
        .wr_addr(wr_addr),
        .act_in(act_in),
        .wt_in(wt_in),
        .rd_addr(rd_addr),
        .act_out(act_buf),
        .wt_out(wt_buf)
    );

    // Zero Detector Instance
    zero_detector #(
        .DATA_WIDTH(DATA_WIDTH)
    ) zd_inst (
        .act(act_buf),
        .wt(wt_buf),
        .is_zero(is_zero)
    );

    // Cost Estimator Instance
    cost_estimator #(
        .TILE_SIZE(TILE_SIZE)
    ) ce_inst (
        .zero_count(zero_count),
        .dense_cost(dense_cost),
        .sparse_cost(sparse_cost)
    );

    // Mode Selector Instance
    mode_selector ms_inst (
        .dense_cost(dense_cost),
        .sparse_cost(sparse_cost),
        .use_sparse(use_sparse)
    );

    // Controller Instance
    controller #(
        .TILE_SIZE(TILE_SIZE)
    ) ctrl_inst (
        .clk(clk),
        .rst_n(rst_n),
        .tile_valid(tile_valid),
        .is_zero(is_zero),
        .use_sparse(use_sparse),
        .rd_addr(rd_addr),
        .zero_count(zero_count),
        .mode_latched(mode_latched),
        .mac_en(mac_en),
        .acc_en(acc_en),
        .acc_clr(acc_clr),
        .done(done)
    );

    // MAC Instance
    mac #(
        .DATA_WIDTH(DATA_WIDTH)
    ) mac_inst (
        .clk(clk),
        .rst_n(rst_n),
        .enable(mac_en),
        .act(act_buf),
        .wt(wt_buf),
        .prod(mac_prod)
    );

    // Accumulator Instance
    accumulator #(
        .IN_WIDTH(2*DATA_WIDTH),
        .ACC_WIDTH(ACC_WIDTH)
    ) acc_inst (
        .clk(clk),
        .rst_n(rst_n),
        .clear(acc_clr),
        .enable(acc_en),
        .din(mac_prod),
        .acc_out(result)
    );

endmodule
