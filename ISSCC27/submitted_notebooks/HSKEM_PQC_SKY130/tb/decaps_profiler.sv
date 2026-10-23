// Non-intrusive cycle profiler for ML-KEM decapsulation in the full-system
// testbench. It is compiled as a second top-level module next to
// tb_trustedge_spi and only reads signals through hierarchical references, so
// neither the published RTL nor the testbench is modified.
//
// For every decapsulation (the busy interval of u_mlkem512_decaps_partial) it
// counts the cycles in which the shared NTT engine, the Keccak sponge and the
// Keccak permutation itself are busy, and the number of transforms started.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module decaps_profiler;
    integer n_decaps = 0;
    integer cyc, ntt_busy, sponge_busy, perm_busy, ntt_and_sponge, ntt_starts, ntt_inv_starts, perm_starts;
    reg     active = 1'b0;

    always @(posedge tb_trustedge_spi.clk) begin
        if (tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy) begin
            if (!active) begin
                active = 1'b1;
                cyc = 0; ntt_busy = 0; sponge_busy = 0; perm_busy = 0; ntt_and_sponge = 0;
                ntt_starts = 0; ntt_inv_starts = 0; perm_starts = 0;
            end
            cyc = cyc + 1;
            if (tb_trustedge_spi.dut.shared_ntt_busy) ntt_busy = ntt_busy + 1;
            if (tb_trustedge_spi.dut.u_shared_mlkem_sponge.busy) sponge_busy = sponge_busy + 1;
            if (tb_trustedge_spi.dut.u_shared_mlkem_sponge.permutation_busy) perm_busy = perm_busy + 1;
            if (tb_trustedge_spi.dut.shared_ntt_busy && tb_trustedge_spi.dut.u_shared_mlkem_sponge.busy)
                ntt_and_sponge = ntt_and_sponge + 1;
            if (tb_trustedge_spi.dut.shared_ntt_start) begin
                ntt_starts = ntt_starts + 1;
                if (tb_trustedge_spi.dut.shared_ntt_inverse) ntt_inv_starts = ntt_inv_starts + 1;
            end
            if (tb_trustedge_spi.dut.u_shared_mlkem_sponge.permutation_start) perm_starts = perm_starts + 1;
        end else if (active) begin
            active = 1'b0;
            n_decaps = n_decaps + 1;
            $display("PROFILE decaps=%0d cycles=%0d ntt_busy=%0d sponge_busy=%0d perm_busy=%0d ntt_and_sponge=%0d ntt_starts=%0d ntt_inverse_starts=%0d perm_starts=%0d",
                     n_decaps, cyc, ntt_busy, sponge_busy, perm_busy, ntt_and_sponge, ntt_starts, ntt_inv_starts, perm_starts);
        end
    end
endmodule
