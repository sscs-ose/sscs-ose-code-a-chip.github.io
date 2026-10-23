// Simulation-only probe for TRUSTEDGE_DEFER_J: measures how long the decapsulation's hash sequencer runs
// J(z||c) (states ST_J_START..ST_J_OUT, 46..50) during each re-encryption, independently of the cycle model.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module j_phase_probe;
    wire [5:0] hs = tb_trustedge_spi.dut.u_mlkem512_decaps_partial.hstate;
    wire       re = tb_trustedge_spi.dut.u_mlkem512_decaps_partial.reencrypt_active;
    integer n = 0;
    reg in_j = 1'b0;
    always @(posedge tb_trustedge_spi.clk) begin
        if (re && (hs >= 6'd46) && (hs <= 6'd50)) begin n = n + 1; in_j = 1'b1; end
        else if (in_j) begin $display("J_PHASE cycles=%0d", n); n = 0; in_j = 1'b0; end
    end
endmodule
