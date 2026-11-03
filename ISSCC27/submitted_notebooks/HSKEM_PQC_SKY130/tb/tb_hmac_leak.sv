// Leakage-model trace generator for the session HMAC (hmac_sha256_fixed, the chip's configuration with the sliding
// SHA-256 schedule). One trace is one HMAC-SHA-256 of a 28-byte frame message: for every clock from start to done it
// records the Hamming distance between consecutive values of the HMAC's state registers (the latched key and message,
// the compression inputs, the inner digest and the output, and the compression core's working variables, schedule
// words and chaining value) -- the register-transition power proxy of tb/tb_ntt_leak.sv. This is a simulation model,
// not measured power. Inputs: hmac_in.hex, two lines per trace (key, message, 64 hex digits each); every digest is
// written to hmac_digests.txt so that golden/leakage_hmac.py checks it against Python's hmac module.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`include "hmac_counts.vh"

module tb_hmac_leak;
    reg clk = 0, rst_n = 0, start = 0;
    reg  [255:0] key = 0, message = 0;
    wire busy, done;
    wire [255:0] digest;
    always #5 clk = ~clk;

    hmac_sha256_fixed #(.SHA256_SLIDING_SCHEDULE(1'b1)) dut (
        .clk(clk), .rst_n(rst_n), .scrub(1'b0), .start(start), .key(key), .message(message),
        .message_len(6'd28), .busy(busy), .done(done), .digest(digest));

    wire [2047:0] w_bits;
    wire [255:0]  h_bits;
    genvar gw;
    generate for (gw = 0; gw < 64; gw = gw + 1) begin : g_w
        assign w_bits[gw * 32 +: 32] = dut.u_compress.w[gw];
    end
    for (gw = 0; gw < 8; gw = gw + 1) begin : g_h
        assign h_bits[gw * 32 +: 32] = dut.u_compress.init_h[gw];
    end endgenerate
    localparam integer W = 256 * 5 + 512 + 6 + 3 + 2048 + 256 + 8 * 32 + 6 + 256;
    wire [W-1:0] regs = {dut.key_latched, dut.message_latched, dut.comp_state_in, dut.comp_block_in,
                         dut.inner_digest, dut.digest, dut.message_len_latched, dut.state,
                         w_bits, h_bits, dut.u_compress.a, dut.u_compress.b, dut.u_compress.c, dut.u_compress.d,
                         dut.u_compress.e, dut.u_compress.f, dut.u_compress.g, dut.u_compress.h,
                         dut.u_compress.round, dut.u_compress.state_out};
    reg [W-1:0] prev;
    reg [255:0] vin [0:2*`N_HMAC-1];
    integer t, fd, fdd, hd;

    initial begin
        $readmemh("hmac_in.hex", vin);
        fd = $fopen("leak_traces.txt", "w");
        fdd = $fopen("hmac_digests.txt", "w");
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (t = 0; t < `N_HMAC; t = t + 1) begin
            @(negedge clk); key = vin[2 * t]; message = vin[2 * t + 1]; start = 1;
            prev = regs;
            @(negedge clk); start = 0;
            while (!done) begin
                hd = $countones(regs ^ prev);
                $fwrite(fd, "%0d ", hd);
                prev = regs;
                @(negedge clk);
            end
            $fwrite(fd, "\n");
            $fwrite(fdd, "%064h\n", digest);
        end
        $fclose(fd); $fclose(fdd);
        $display("HMAC_LEAK_TRACES written=%0d", `N_HMAC);
        $finish;
    end
endmodule
