// Gate-level testbench for the routed Keccak blocks (keccak_lane_wrapper).
// Loads each input state lane by lane, runs one permutation, reads the result
// back lane by lane and compares it with the golden model. With VCD_OUT defined,
// switching activity is recorded for exactly one permutation (from start to
// done) of vector VCD_VEC, for activity-based power analysis.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`include "counts.vh"
`ifndef CLK_HALF
`define CLK_HALF 5
`endif

module tb_keccak_lanes;
    reg clk = 0, rst_n = 0, start = 0, zeroize = 0, lane_we = 0;
    reg  [4:0]  lane_idx = 0;
    reg  [63:0] lane_wdata = 0;
    wire [63:0] lane_rdata;
    wire busy, done;

    always #(`CLK_HALF) clk = ~clk;

    keccak_lane_wrapper dut (
        .clk(clk), .rst_n(rst_n), .zeroize(zeroize), .lane_we(lane_we), .lane_idx(lane_idx),
        .lane_wdata(lane_wdata), .lane_rdata(lane_rdata), .start(start), .busy(busy), .done(done));

    reg [1599:0] vin  [0:`N_KECCAK-1];
    reg [1599:0] vout [0:`N_KECCAK-1];
    integer t, i, errors = 0, cycles = 0, cyc_ref = 0, timing_var = 0;

    initial begin
        $readmemh("keccak_in.hex", vin);
        $readmemh("keccak_out.hex", vout);
`ifdef VCD_OUT
        $dumpfile(`VCD_OUT);
        $dumpvars(0, dut);
        $dumpoff;
`endif
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (t = 0; t < `N_KECCAK; t = t + 1) begin
            for (i = 0; i < 25; i = i + 1) begin
                @(negedge clk); lane_we = 1; lane_idx = i; lane_wdata = vin[t][i * 64 +: 64];
            end
            @(negedge clk); lane_we = 0;
            @(negedge clk); start = 1;
`ifdef VCD_OUT
            if (t == `VCD_VEC) $dumpon;
`endif
            @(negedge clk); start = 0;
            cycles = 1;
            while (!done) begin @(negedge clk); cycles = cycles + 1; end
`ifdef VCD_OUT
            if (t == `VCD_VEC) $dumpoff;
`endif
            if (cyc_ref != 0 && cycles != cyc_ref) timing_var = timing_var + 1;
            cyc_ref = cycles;
            for (i = 0; i < 25; i = i + 1) begin
                lane_idx = i; #(`CLK_HALF);         // let the read multiplexer settle (gate delays)
                if (lane_rdata !== vout[t][i * 64 +: 64]) begin
                    if (errors < 5) $display("MISMATCH vec=%0d lane=%0d", t, i);
                    errors = errors + 1;
                end
                @(negedge clk);
            end
        end
        $display("KECCAK_RESULT vectors=%0d errors=%0d cycles=%0d timing_variations=%0d",
                 `N_KECCAK, errors, cyc_ref, timing_var);
        if (errors == 0 && timing_var == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
