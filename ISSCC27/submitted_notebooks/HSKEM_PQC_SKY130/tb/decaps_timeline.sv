// Simulation-only probe, read-only: a run-length timeline of the first decapsulation in the full-system testbench.
// (the same unit also runs encapsulations; the caller keeps the runs of decapsulation length.) One line per change of the activity flags of the shared NTT engine and the Keccak sponge, in cycles from its start.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module decaps_timeline;
    wire       busy = tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy;
    wire [3:0] flags = {tb_trustedge_spi.dut.shared_ntt_busy, tb_trustedge_spi.dut.shared_ntt_inverse,
                        tb_trustedge_spi.dut.u_shared_mlkem_sponge.busy,
                        tb_trustedge_spi.dut.u_shared_mlkem_sponge.permutation_busy};
    integer t = 0, runs = 0;
    reg active = 1'b0;
    reg [3:0] q;
    always @(posedge tb_trustedge_spi.clk) begin
        if (busy) begin
            if (!active) begin active = 1'b1; t = 0; q = 4'hx; end
            if (flags !== q) $display("TIMELINE run=%0d t=%0d ntt=%b inv=%b sponge=%b perm=%b", runs, t, flags[3], flags[2], flags[1], flags[0]);
            q = flags; t = t + 1;
        end else if (active) begin
            active = 1'b0;
            $display("TIMELINE_END run=%0d t=%0d", runs, t);
            runs = runs + 1;
        end
    end
endmodule
