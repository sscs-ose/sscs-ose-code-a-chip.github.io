// Counts, for each of the chip's 18 SRAM macros, the write cycles and the "useful" cycles (a write, or a
// read at a new address) over the same decapsulation window as tb/decaps_vcd_window.sv (+skip=<n>).
// On the chip every macro's chip select is tied active, so each macro performs one access in every clock
// cycle; the useful cycles are the accesses that a chip-select gate would have to keep. Compiled as an
// extra top level next to tb_trustedge_spi (CAC_SRAM_COUNT=1); it only reads signals through
// hierarchical references.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
`define TE_DUT tb_trustedge_spi.dut

module sram_access_mon (input wire clk, input wire on, input wire we, input wire [9:0] addr);
    integer writes = 0, useful = 0;
    reg [9:0] addr_q = 10'h3ff;
    always @(posedge clk) begin
        if (on) begin
            if (we) writes = writes + 1;
            if (we || addr !== addr_q) useful = useful + 1;
        end
        addr_q = addr;
    end
endmodule

module sram_access_counter;
    integer skip = 0, seen = 0, cycles = 0;
    reg     busy_q = 1'b0, in_long = 1'b0, active = 1'b0, done = 1'b0;
    wire    clk = tb_trustedge_spi.clk;
    initial if (!$value$plusargs("skip=%d", skip)) skip = 0;

`define MON(n, p) sram_access_mon n (.clk(clk), .on(active), .we(`TE_DUT.p.we), .addr({1'b0, `TE_DUT.p.addr}));
    `MON(m00, u_c3_pk_pair_sram)
    `MON(m01, u_mlkem512_decaps_partial.u_ciphertext_ref_sram)
    `MON(m02, u_mlkem512_decaps_partial.u_product_pair_sram)
    `MON(m03, u_mlkem512_encaps_partial.u_codec.u_ciphertext_sram)
    `MON(m04, u_mlkem512_encaps_partial.u_codec.u_coeff_sram)
    `MON(m05, u_mlkem512_encaps_partial.u_codec.u_decoded_coeff_sram)
    `MON(m06, u_mlkem512_encaps_partial.u_noise_even_sram)
    `MON(m07, u_mlkem512_encaps_partial.u_noise_odd_sram)
    `MON(m08, u_mlkem512_kpke_partial.u_matrix_mac.u_dkpke_pair_sram)
    `MON(m09, u_mlkem512_kpke_partial.u_matrix_mac.u_ekpke_pair_sram)
    `MON(m10, u_mlkem512_kpke_partial.u_matrix_mac.u_error_even_sram)
    `MON(m11, u_mlkem512_kpke_partial.u_matrix_mac.u_error_odd_sram)
    `MON(m12, u_mlkem512_kpke_partial.u_matrix_mac.u_matrix_even_sram)
    `MON(m13, u_mlkem512_kpke_partial.u_matrix_mac.u_matrix_odd_sram)
    `MON(m14, u_mlkem512_kpke_partial.u_matrix_mac.u_noise_byte_sram)
    `MON(m15, u_mlkem512_kpke_partial.u_matrix_mac.u_secret_even_sram)
    `MON(m16, u_mlkem512_kpke_partial.u_matrix_mac.u_secret_odd_sram)
    `MON(m17, u_shared_ntt.u_coeff_ram)

`define SHOW(n, p) $display("SRAM_ACCESS %0s writes=%0d useful=%0d", `"p`", n.writes, n.useful);
    always @(posedge clk) begin
        if (!done) begin
            if (busy_q && `TE_DUT.u_mlkem512_decaps_partial.busy && !in_long) begin
                in_long = 1'b1;
                seen = seen + 1;
                if (seen == skip + 1) active = 1'b1;
            end
            if (active) begin
                if (`TE_DUT.u_mlkem512_decaps_partial.busy) begin
                    cycles = cycles + 1;
                end else begin
                    active = 1'b0; done = 1'b1;
                    `SHOW(m00, u_c3_pk_pair_sram)
                    `SHOW(m01, u_mlkem512_decaps_partial.u_ciphertext_ref_sram)
                    `SHOW(m02, u_mlkem512_decaps_partial.u_product_pair_sram)
                    `SHOW(m03, u_mlkem512_encaps_partial.u_codec.u_ciphertext_sram)
                    `SHOW(m04, u_mlkem512_encaps_partial.u_codec.u_coeff_sram)
                    `SHOW(m05, u_mlkem512_encaps_partial.u_codec.u_decoded_coeff_sram)
                    `SHOW(m06, u_mlkem512_encaps_partial.u_noise_even_sram)
                    `SHOW(m07, u_mlkem512_encaps_partial.u_noise_odd_sram)
                    `SHOW(m08, u_mlkem512_kpke_partial.u_matrix_mac.u_dkpke_pair_sram)
                    `SHOW(m09, u_mlkem512_kpke_partial.u_matrix_mac.u_ekpke_pair_sram)
                    `SHOW(m10, u_mlkem512_kpke_partial.u_matrix_mac.u_error_even_sram)
                    `SHOW(m11, u_mlkem512_kpke_partial.u_matrix_mac.u_error_odd_sram)
                    `SHOW(m12, u_mlkem512_kpke_partial.u_matrix_mac.u_matrix_even_sram)
                    `SHOW(m13, u_mlkem512_kpke_partial.u_matrix_mac.u_matrix_odd_sram)
                    `SHOW(m14, u_mlkem512_kpke_partial.u_matrix_mac.u_noise_byte_sram)
                    `SHOW(m15, u_mlkem512_kpke_partial.u_matrix_mac.u_secret_even_sram)
                    `SHOW(m16, u_mlkem512_kpke_partial.u_matrix_mac.u_secret_odd_sram)
                    `SHOW(m17, u_shared_ntt.u_coeff_ram)
                    $display("SRAM_WINDOW cycles=%0d", cycles);
                end
            end
            if (!`TE_DUT.u_mlkem512_decaps_partial.busy) in_long = 1'b0;
            busy_q = `TE_DUT.u_mlkem512_decaps_partial.busy;
        end
    end
endmodule
