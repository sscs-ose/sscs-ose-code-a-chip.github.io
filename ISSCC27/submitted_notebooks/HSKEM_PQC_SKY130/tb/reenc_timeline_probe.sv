// Simulation-only debug probe: a timeline of the first two re-encryptions inside a decapsulation, in cycles
// from the re-encryption's start. It lists the encryption controller's major state changes, the noise
// sampler's polynomial steps, the decapsulation's hash sequencer (J) and the shared sponge's done pulses.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module reenc_timeline_probe;
    wire [31:0] es  = tb_trustedge_spi.dut.u_mlkem512_encaps_partial.state;
    wire [2:0]  pp  = tb_trustedge_spi.dut.u_mlkem512_encaps_partial.u_encrypt_prf.poly_index;
    wire [5:0]  ps  = tb_trustedge_spi.dut.u_mlkem512_encaps_partial.u_encrypt_prf.state;
    wire [5:0]  ds  = tb_trustedge_spi.dut.u_mlkem512_decaps_partial.state;
    wire [5:0]  hs  = tb_trustedge_spi.dut.u_mlkem512_decaps_partial.hstate;
    wire        sd  = tb_trustedge_spi.dut.shared_sponge_done;
    localparam [5:0] ST_REENC_WAIT = 6'd42;
    integer t = 0, runs = 0;
    reg active = 1'b0;
    reg [31:0] es_q;
    reg [2:0]  pp_q;
    reg [5:0]  ps_q, hs_q;
    always @(posedge tb_trustedge_spi.clk) begin
        if (ds == ST_REENC_WAIT && runs < 8) begin
            if (!active) begin active = 1'b1; t = 0; es_q = es; pp_q = pp; ps_q = ps; hs_q = hs;
                $display("TL start run=%0d es=%h pp=%0d", runs, es, pp); end
            t = t + 1;
            if (es != es_q && (es[12] || es_q[12] || es[5] || es_q[5] || es[26] || es_q[20] || es[16]))
                $display("TL %0d enc %h -> %h", t, es_q, es);
            if (pp != pp_q) $display("TL %0d prf poly %0d", t, pp);
            if (ps != ps_q && (ps == 6'b010000 || ps_q == 6'b010000)) $display("TL %0d prf state %b -> %b", t, ps_q, ps);
            if (hs != hs_q) $display("TL %0d hstate %0d -> %0d", t, hs_q, hs);
            if (sd) $display("TL %0d sponge done", t);
            es_q = es; pp_q = pp; ps_q = ps; hs_q = hs;
        end else if (active) begin
            active = 1'b0; runs = runs + 1;
            $display("TL end %0d", t);
        end
    end
endmodule
