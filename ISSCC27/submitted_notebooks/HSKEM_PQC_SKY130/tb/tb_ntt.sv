// Vector-driven testbench for kyber_ntt_engine (forward and inverse NTT).
// Expected values come from golden/mlkem_ref.py, never from the RTL.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`include "counts.vh"

module tb_ntt;
    reg clk = 0, rst_n = 0, start = 0, inverse = 0, we = 0;
    reg  [7:0]  waddr = 0, raddr = 0;
    reg  [15:0] wdata = 0;
    wire [15:0] rdata;
    wire busy, done;

`ifndef CLK_HALF
`define CLK_HALF 5
`endif
    always #(`CLK_HALF) clk = ~clk;

`ifdef NTT_OPT
    // design-iteration variant (rtl/kyber_ntt_engine_opt.sv)
    kyber_ntt_engine_opt #(.BARRETT_1C(`B1C), .PIPE_MUL(`PIPE), .COEFF_W(`CW)) dut (
`else
    kyber_ntt_engine dut (
`endif
        .clk(clk), .rst_n(rst_n), .start(start), .inverse(inverse),
        .busy(busy), .done(done), .waddr(waddr), .wdata(wdata), .we(we),
        .rdata(rdata), .raddr(raddr));

    reg [15:0] vin  [0:`N_NTT*256-1];
    reg [15:0] vfwd [0:`N_NTT*256-1];
    reg [15:0] vinv [0:`N_NTT*256-1];

    integer t, i, dir, errors = 0, checked = 0, cycles, cyc_fwd = 0, cyc_inv = 0, timing_var = 0;

    task automatic run_one(input integer base, input integer inv);
        begin
            // load coefficients
            for (i = 0; i < 256; i = i + 1) begin
                @(negedge clk); we = 1; waddr = i; wdata = vin[base + i];
            end
            @(negedge clk); we = 0;
            // start and count cycles until done
            @(negedge clk); inverse = inv; start = 1;
`ifdef VCD_OUT
            // activity window for power analysis: exactly one forward transform
            // of a random polynomial (vector `VCD_VEC; the first four are corner cases)
            if (!inv && base == `VCD_VEC * 256) $dumpon;
`endif
            @(negedge clk); start = 0;
            cycles = 1;
            while (!done) begin @(negedge clk); cycles = cycles + 1; end
`ifdef VCD_OUT
            if (!inv && base == `VCD_VEC * 256) $dumpoff;
`endif
            // constant-time check: latency must not depend on the data
            if (inv) begin
                if (cyc_inv != 0 && cycles != cyc_inv) timing_var = timing_var + 1;
                cyc_inv = cycles;
            end else begin
                if (cyc_fwd != 0 && cycles != cyc_fwd) timing_var = timing_var + 1;
                cyc_fwd = cycles;
            end
            // read back (one-cycle RAM latency)
            @(negedge clk); raddr = 0;
            for (i = 0; i < 256; i = i + 1) begin
                @(negedge clk);
                raddr = i + 1;
`ifdef RD_SAMPLE_DELAY
                // the OpenRAM model drives dout0 only DELAY after the falling edge
                #(`RD_SAMPLE_DELAY);
`endif
                if (rdata !==(inv ? vinv[base + i] : vfwd[base + i])) begin
                    if (errors < 10)
                        $display("MISMATCH vec=%0d inv=%0d idx=%0d got=%0d exp=%0d",
                                 base / 256, inv, i, rdata,
                                 inv ? vinv[base + i] : vfwd[base + i]);
                    errors = errors + 1;
                end
                checked = checked + 1;
            end
        end
    endtask

    initial begin
        $readmemh("ntt_in.hex", vin);
        $readmemh("ntt_fwd.hex", vfwd);
        $readmemh("ntt_inv.hex", vinv);
`ifdef VCD_OUT
        $dumpfile(`VCD_OUT);
        $dumpvars(0, dut);
        $dumpoff;
`endif
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (t = 0; t < `N_NTT; t = t + 1)
            for (dir = 0; dir < 2; dir = dir + 1)
                run_one(t * 256, dir);
        $display("NTT_RESULT vectors=%0d coeffs_checked=%0d errors=%0d cycles_fwd=%0d cycles_inv=%0d timing_variations=%0d",
                 `N_NTT, checked, errors, cyc_fwd, cyc_inv, timing_var);
        if (errors == 0 && timing_var == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
