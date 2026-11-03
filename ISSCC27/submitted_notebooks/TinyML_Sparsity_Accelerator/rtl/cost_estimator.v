`timescale 1ns / 1ps

module cost_estimator #(
    parameter TILE_SIZE        = 16,
    parameter DENSE_UNIT_COST  = 8'd10, // Energy/cycle weight per dense MAC
    parameter SPARSE_UNIT_COST = 8'd12, // Higher per-MAC cost due to sparse metadata lookup
    parameter OVERHEAD_COST    = 8'd25  // Control overhead cost for sparse tracking logic
)(
    input  wire [$clog2(TILE_SIZE+1)-1:0] zero_count,
    output wire [15:0] dense_cost,
    output wire [15:0] sparse_cost
);

    wire [$clog2(TILE_SIZE+1)-1:0] non_zero_count;
    assign non_zero_count = TILE_SIZE - zero_count;

    // Cost Model Formulas
    assign dense_cost  = TILE_SIZE * DENSE_UNIT_COST;
    assign sparse_cost = (non_zero_count * SPARSE_UNIT_COST) + OVERHEAD_COST;

endmodule
