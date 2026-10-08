// Stream-mode testbench for kyber_ntt_engine_packed2: the transform is started first and its input arrives as
// pair writes, one pair every second cycle: in the forward transform's first-pass order (the order of the
// encryption's y path and of the decryption's u load), and in word order for the inverse transform (the
// order of the pipelined products). Expected values come from golden/mlkem_ref.py (vectors/ntt_fwd.hex and
// ntt_inv.hex), never from the RTL.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`include "counts.vh"

module tb_ntt_stream;
    reg clk = 0, rst_n = 0, start = 0, we = 0, we_pair = 0, stream = 0, inverse = 0;
    reg  [7:0]  waddr = 0, raddr = 0;
    reg  [15:0] wdata = 0;
    reg  [11:0] wdata_odd = 0;
    wire [15:0] rdata;
    wire [23:0] rdata_pair;
    wire busy, done;
    always #5 clk = ~clk;

    kyber_ntt_engine_packed2 #(.EXTRA_STAGE(`XSTAGE)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .inverse(inverse),
        .busy(busy), .done(done), .waddr(waddr), .wdata(wdata), .we(we),
        .rdata(rdata), .raddr(raddr), .we_pair(we_pair), .wdata_odd(wdata_odd),
        .rdata_pair(rdata_pair), .stream(stream), .re(1'b0));

    reg [15:0] vin  [0:`N_NTT*256-1];
    reg [15:0] vinv [0:`N_NTT*256-1];
    reg [15:0] vfwd [0:`N_NTT*256-1];
    integer t, i, w, errors = 0, checked = 0, cycles, after_last, cyc_ref = -1, tail_ref = -1, timing_var = 0;
    integer last_write, dir, k, f_cyc_ref = -1, f_tail_ref = -1;
    // forward first pass: group k[6:3], slot k[2:0] -> word {s0, s1, s2, g}
    function automatic [6:0] fwd_word(input [6:0] k);
        fwd_word = {k[0], k[1], k[2], k[6:3]};
    endfunction

    initial begin
        $readmemh("ntt_in.hex", vin);
        $readmemh("ntt_inv.hex", vinv);
        $readmemh("ntt_fwd.hex", vfwd);
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (t = 0; t < `N_NTT; t = t + 1) for (dir = 0; dir < 2; dir = dir + 1) begin
            // start the transform in stream mode, then deliver the k-th pair at cycle 2k + 4
            @(negedge clk); start = 1; stream = 1; inverse = dir;
            @(negedge clk); start = 0; stream = 0;
            cycles = 1;
            for (k = 0; k < 128; k = k + 1) begin
                w = dir ? k : fwd_word(k[6:0]);
                while (cycles < 2 * k + 4) begin @(negedge clk); cycles = cycles + 1; end
                we = 1; we_pair = 1; waddr = {w[6:0], 1'b0};
                wdata = vin[t * 256 + 2 * w]; wdata_odd = vin[t * 256 + 2 * w + 1];
                @(negedge clk); cycles = cycles + 1;
                we = 0; we_pair = 0;
            end
            last_write = cycles;
            while (!done) begin @(negedge clk); cycles = cycles + 1; end
            after_last = cycles - last_write;
            if (dir) begin
                if (cyc_ref >= 0 && (cycles != cyc_ref || after_last != tail_ref)) timing_var = timing_var + 1;
                cyc_ref = cycles; tail_ref = after_last;
            end else begin
                if (f_cyc_ref >= 0 && (cycles != f_cyc_ref || after_last != f_tail_ref)) timing_var = timing_var + 1;
                f_cyc_ref = cycles; f_tail_ref = after_last;
            end
            @(negedge clk); raddr = 0;
            for (i = 0; i < 256; i = i + 1) begin
                @(negedge clk);
                raddr = i + 1;
                if (rdata !== (dir ? vinv[t * 256 + i] : vfwd[t * 256 + i])) begin
                    if (errors < 10)
                        $display("MISMATCH vec=%0d inv=%0d idx=%0d got=%0d exp=%0d", t, dir, i, rdata,
                                 dir ? vinv[t * 256 + i] : vfwd[t * 256 + i]);
                    errors = errors + 1;
                end
                checked = checked + 1;
            end
        end
        $display("NTT_STREAM_RESULT vectors=%0d coeffs_checked=%0d errors=%0d fwd_from_start=%0d fwd_after_last_pair=%0d inv_from_start=%0d inv_after_last_pair=%0d timing_variations=%0d",
                 `N_NTT, checked, errors, f_cyc_ref, f_tail_ref, cyc_ref, tail_ref, timing_var);
        if (errors == 0 && timing_var == 0) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
