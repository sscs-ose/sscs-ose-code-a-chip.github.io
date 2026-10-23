// Vector-driven testbench for keccak_f1600_iter (both SERIAL_ROUND variants).
// Expected states come from golden/mlkem_ref.py (validated against hashlib).
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`include "counts.vh"
`ifndef SERIAL
`define SERIAL 0
`endif

module tb_keccak;
    reg clk = 0, rst_n = 0, start = 0, zeroize = 0;
    reg  [1599:0] state_in = 0;
    wire [1599:0] state_out;
    wire busy, done;

    always #5 clk = ~clk;

    keccak_f1600_iter #(.SERIAL_ROUND(`SERIAL)) dut (
        .clk(clk), .rst_n(rst_n), .zeroize(zeroize), .start(start),
        .state_in(state_in), .state_out(state_out), .busy(busy), .done(done));

    reg [1599:0] vin  [0:`N_KECCAK-1];
    reg [1599:0] vout [0:`N_KECCAK-1];
    integer t, errors = 0, cycles = 0, cyc_ref = 0, timing_var = 0;

    initial begin
        $readmemh("keccak_in.hex", vin);
        $readmemh("keccak_out.hex", vout);
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (t = 0; t < `N_KECCAK; t = t + 1) begin
            @(negedge clk); state_in = vin[t]; start = 1;
            @(negedge clk); start = 0;
            cycles = 1;
            while (!done) begin @(negedge clk); cycles = cycles + 1; end
            if (cyc_ref != 0 && cycles != cyc_ref) timing_var = timing_var + 1;
            cyc_ref = cycles;
            if (state_out !== vout[t]) begin
                if (errors < 5) $display("MISMATCH vec=%0d", t);
                errors = errors + 1;
            end
        end
        // zeroize must clear the state register
        @(negedge clk); zeroize = 1; @(negedge clk); zeroize = 0;
        if (state_out !== 1600'd0) begin
            $display("ZEROIZE_FAIL"); errors = errors + 1;
        end
        $display("KECCAK_RESULT serial=%0d vectors=%0d errors=%0d cycles=%0d timing_variations=%0d",
                 `SERIAL, `N_KECCAK, errors, cycles, timing_var);
        if (errors == 0 && timing_var == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
