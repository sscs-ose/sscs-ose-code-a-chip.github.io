// Phase 2 generalization of the frozen Phase 1 token and arithmetic contract.
// Ports are flat packed vectors for the native Yosys SystemVerilog frontend.
// A lane i occupies bits [8*i +: 8]; PE(i,j) occupies accumulator word i*S+j.
module systolic_array #(
    parameter integer ARRAY_SIZE = 2
) (
    input  wire clk,
    input  wire rst,
    input  wire clear,
    input  wire [ARRAY_SIZE*ARRAY_SIZE-1:0] tile_mask,
    input  wire [8*ARRAY_SIZE-1:0] a_boundary,
    input  wire [8*ARRAY_SIZE-1:0] b_boundary,
    input  wire [ARRAY_SIZE-1:0] a_valid,
    input  wire [ARRAY_SIZE-1:0] b_valid,
    input  wire [ARRAY_SIZE-1:0] a_last,
    input  wire [ARRAY_SIZE-1:0] b_last,
    output wire [32*ARRAY_SIZE*ARRAY_SIZE-1:0] accumulators,
    output wire [ARRAY_SIZE*ARRAY_SIZE-1:0] result_valid,
    output reg  [ARRAY_SIZE*ARRAY_SIZE-1:0] active_mask,
    output wire tile_done
);
    // The east/south edge tokens deliberately leave the compute boundary.
    /* verilator lint_off UNUSEDSIGNAL */
    wire [8*ARRAY_SIZE*ARRAY_SIZE-1:0] forwarded_a;
    wire [8*ARRAY_SIZE*ARRAY_SIZE-1:0] forwarded_b;
    /* verilator lint_on UNUSEDSIGNAL */
    wire [ARRAY_SIZE*ARRAY_SIZE-1:0] forwarded_a_valid;
    wire [ARRAY_SIZE*ARRAY_SIZE-1:0] forwarded_b_valid;
    wire [ARRAY_SIZE*ARRAY_SIZE-1:0] forwarded_a_last;
    wire [ARRAY_SIZE*ARRAY_SIZE-1:0] forwarded_b_last;

    always @(posedge clk) begin
        if (rst)
            active_mask <= {ARRAY_SIZE*ARRAY_SIZE{1'b0}};
        else if (clear)
            active_mask <= tile_mask;
    end
    assign tile_done = (|active_mask) && ((result_valid & active_mask) == active_mask);

    generate
        if ((ARRAY_SIZE != 2) && (ARRAY_SIZE != 4) && (ARRAY_SIZE != 8)) begin : invalid_size
            initial $fatal(1, "ARRAY_SIZE must be 2, 4 or 8");
        end
        for (genvar row = 0; row < ARRAY_SIZE; row = row + 1) begin : rows
            for (genvar col = 0; col < ARRAY_SIZE; col = col + 1) begin : cols
                localparam integer CELL = row * ARRAY_SIZE + col;
                wire signed [7:0] a_in_cell;
                wire signed [7:0] b_in_cell;
                wire av, bv, al, bl;
                // Keep every accumulator cone when a physical wrapper does not
                // expose the full result bus as package-level pins.
                (* keep = 1 *) wire signed [31:0] retained_accumulator;

                if (col == 0) begin : left_boundary
                    assign a_in_cell = a_boundary[8*row +: 8];
                    assign av = a_valid[row];
                    assign al = a_last[row];
                end else begin : left_neighbor
                    assign a_in_cell = forwarded_a[8*(CELL-1) +: 8];
                    assign av = forwarded_a_valid[CELL-1];
                    assign al = forwarded_a_last[CELL-1];
                end
                if (row == 0) begin : top_boundary
                    assign b_in_cell = b_boundary[8*col +: 8];
                    assign bv = b_valid[col];
                    assign bl = b_last[col];
                end else begin : top_neighbor
                    assign b_in_cell = forwarded_b[8*(CELL-ARRAY_SIZE) +: 8];
                    assign bv = forwarded_b_valid[CELL-ARRAY_SIZE];
                    assign bl = forwarded_b_last[CELL-ARRAY_SIZE];
                end

                (* keep = 1 *) gemm_pe pe (
                    .clk(clk), .rst(rst), .clear(clear),
                    .a_in(a_in_cell), .b_in(b_in_cell),
                    .a_valid(av), .b_valid(bv), .a_last(al), .b_last(bl),
                    .a_out(forwarded_a[8*CELL +: 8]),
                    .b_out(forwarded_b[8*CELL +: 8]),
                    .a_out_valid(forwarded_a_valid[CELL]),
                    .b_out_valid(forwarded_b_valid[CELL]),
                    .a_out_last(forwarded_a_last[CELL]),
                    .b_out_last(forwarded_b_last[CELL]),
                    .accumulator(retained_accumulator),
                    .result_valid(result_valid[CELL])
                );
                assign accumulators[32*CELL +: 32] = retained_accumulator;
            end
        end
    endgenerate
endmodule
