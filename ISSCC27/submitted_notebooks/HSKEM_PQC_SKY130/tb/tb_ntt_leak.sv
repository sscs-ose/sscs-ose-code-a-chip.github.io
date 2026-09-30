// Leakage-model trace generator for kyber_ntt_engine (forward NTT).
// For every clock of the transform it records the Hamming distance between
// consecutive values of the datapath registers -- the standard register-
// transition power proxy. This is a simulation model, not measured power.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`include "leak_counts.vh"

module tb_ntt_leak;
    reg clk = 0, rst_n = 0, start = 0, we = 0;
    reg  [7:0]  waddr = 0;
    reg  [15:0] wdata = 0;
    wire [15:0] rdata;
    wire busy, done;

    always #5 clk = ~clk;

    kyber_ntt_engine dut (
        .clk(clk), .rst_n(rst_n), .start(start), .inverse(1'b0),
        .busy(busy), .done(done), .waddr(waddr), .wdata(wdata), .we(we),
        .rdata(rdata), .raddr(8'd0));

    // Architectural datapath registers (identical names in both RAM variants)
    wire [139:0] regs = {dut.coeff_a_q, dut.coeff_b_q, dut.zeta_q,
                         dut.result_lo_q, dut.result_hi_q, dut.mul_reduced_q,
                         dut.ram_q_a, dut.scale_coeff_q, dut.st};
    reg  [139:0] prev;

    reg [15:0] vin [0:`N_LEAK*256-1];
    integer t, i, fd, hd;

    initial begin
        $readmemh("leak_in.hex", vin);
        fd = $fopen("leak_traces.txt", "w");
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (t = 0; t < `N_LEAK; t = t + 1) begin
            for (i = 0; i < 256; i = i + 1) begin
                @(negedge clk); we = 1; waddr = i; wdata = vin[t * 256 + i];
            end
            @(negedge clk); we = 0; start = 1;
            prev = regs;
            @(negedge clk); start = 0;
            while (!done) begin
                hd = $countones(regs ^ prev);
                $fwrite(fd, "%0d ", hd);
                prev = regs;
                @(negedge clk);
            end
            $fwrite(fd, "\n");
        end
        $fclose(fd);
        $display("LEAK_TRACES written=%0d", `N_LEAK);
        $finish;
    end
endmodule
