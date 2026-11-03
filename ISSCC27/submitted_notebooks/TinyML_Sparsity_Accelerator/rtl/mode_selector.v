`timescale 1ns / 1ps

module mode_selector (
    input  wire [15:0] dense_cost,
    input  wire [15:0] sparse_cost,
    output wire use_sparse // 1 = Sparse Mode, 0 = Dense Mode
);

    assign use_sparse = (sparse_cost < dense_cost) ? 1'b1 : 1'b0;

endmodule
