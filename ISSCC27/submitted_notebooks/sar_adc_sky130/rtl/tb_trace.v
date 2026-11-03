// SPDX-License-Identifier: Apache-2.0
// Dump one conversion, trial by trial, for the animation. Same DUT and same
// ideal-DAC model as tb_sar_sequencer.v -- the figure is driven by the RTL that
// goes through the flow, not by a separate illustration of it.
`timescale 1ns/1ps
`default_nettype none

module tb_trace;
    localparam integer N = 8, FULL = 1<<N;
    localparam real VREF = 1.8, TP = 100.0;

    reg clk=0, rst_n=0, start=0;
    wire [N-1:0] d, code, code_bin;
    wire [N+1:0] phase;
    wire eoc;
    real vin, vdac;
    reg  cmp;
    integer k, trial;

    always @* begin
        vdac = 0.0;
        for (k=0;k<N;k=k+1) if (d[k]) vdac = vdac + VREF/(1<<(k+1));
    end
    always @* cmp = (vin > vdac);
    always #(TP/2.0) clk = ~clk;

    sar_sequencer #(.N(N)) dut(.clk(clk),.rst_n(rst_n),.start(start),.cmp(cmp),
        .d(d),.phase(phase),.code(code),.code_bin(code_bin),.eoc(eoc));

    initial begin
        vin = $itor($test$plusargs("vin") ? 0 : 0);
        if (!$value$plusargs("vin=%f", vin)) vin = 1.1340;   // default input
        $display("# vin %0.6f vref %0.6f n %0d", vin, VREF, N);
        $display("# trial dac_before cmp bit dac_after");
        repeat(4) @(posedge clk); rst_n=1; repeat(2) @(posedge clk);
        @(negedge clk); start=1;

        // trial i is active during phase p[i+1]; sample just before the
        // negedge capture, then again after the decision has landed.
        for (trial=0; trial<N; trial=trial+1) begin
            @(posedge clk);                     // phase advances
            #1;
            $write("%0d %0.6f %0d", trial, vdac, cmp);
            @(negedge clk); #1;                 // capture happened
            // the decision IS cmp at the capture edge; `code` does not load
            // until the read phase, so reading it here would show all zeros.
            $display(" %0d %0.6f", dut.q[trial], vdac);
        end
        @(posedge eoc); start=0; #1;        // let code_bin settle past the edge
        $display("# code %0d", code_bin);
        $finish;
    end
    initial begin #(TP*200); $fatal(1,"TIMEOUT"); end
endmodule
`default_nettype wire
