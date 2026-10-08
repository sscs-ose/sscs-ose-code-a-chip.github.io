// Physical-design wrapper for keccak_f1600_iter.
// The permutation core has 1600-bit state ports, which cannot be pinned out
// of a small macro.  This wrapper loads/reads the state one 64-bit lane at a
// time.  It is identical for both SERIAL_ROUND variants, so the area/timing
// difference between the two runs is attributable to the core alone.
// SPDX-License-Identifier: Apache-2.0
module keccak_lane_wrapper #(
    parameter SERIAL_ROUND = 1'b0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        zeroize,
    input  wire        lane_we,
    input  wire [4:0]  lane_idx,
    input  wire [63:0] lane_wdata,
    output wire [63:0] lane_rdata,
    input  wire        start,
    output wire        busy,
    output wire        done
);
    reg  [1599:0] load_q;
    wire [1599:0] state_out;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            load_q <= 1600'd0;
        else if (zeroize)
            load_q <= 1600'd0;
        else if (lane_we && lane_idx < 5'd25)
            load_q[lane_idx * 64 +: 64] <= lane_wdata;
    end

    keccak_f1600_iter #(.SERIAL_ROUND(SERIAL_ROUND)) u_core (
        .clk(clk), .rst_n(rst_n), .zeroize(zeroize), .start(start),
        .state_in(load_q), .state_out(state_out), .busy(busy), .done(done));

    assign lane_rdata = state_out[lane_idx * 64 +: 64];
endmodule
