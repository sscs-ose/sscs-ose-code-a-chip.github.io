// Non-intrusive state profiler for ML-KEM decapsulation, a companion of decaps_profiler.sv. It is
// compiled as another top-level module and reads signals through hierarchical references only.
//
// For every decapsulation it bins each cycle by the FSM state of the decapsulation controller and, while
// that controller waits for the re-encryption, by the state of the re-encryption controller. Each bin
// counts all its cycles and, separately, those in which neither the NTT engine nor the Keccak sponge is
// busy (the profile's "everything else").
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module decaps_state_profiler;
    localparam [5:0] ST_REENC_WAIT = 6'd42;
    integer n_decaps = 0;
    integer dec_all[0:63], dec_other[0:63], enc_all[0:31], enc_other[0:31];
    integer i, e;
    reg active = 1'b0;
    reg other;
    reg [5:0]  ds;
    reg [31:0] es;

    always @(posedge tb_trustedge_spi.clk) begin
        if (tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy) begin
            if (!active) begin
                active = 1'b1;
                for (i = 0; i < 64; i = i + 1) begin dec_all[i] = 0; dec_other[i] = 0; end
                for (i = 0; i < 32; i = i + 1) begin enc_all[i] = 0; enc_other[i] = 0; end
            end
            other = !tb_trustedge_spi.dut.shared_ntt_busy && !tb_trustedge_spi.dut.u_shared_mlkem_sponge.busy;
            ds = tb_trustedge_spi.dut.u_mlkem512_decaps_partial.state;
            dec_all[ds] = dec_all[ds] + 1;
            if (other) dec_other[ds] = dec_other[ds] + 1;
            if (ds == ST_REENC_WAIT) begin
                es = tb_trustedge_spi.dut.u_mlkem512_encaps_partial.state;
                e = 31;
                for (i = 0; i < 32; i = i + 1) if (es[i]) e = i;
                enc_all[e] = enc_all[e] + 1;
                if (other) enc_other[e] = enc_other[e] + 1;
            end
        end else if (active) begin
            active = 1'b0;
            n_decaps = n_decaps + 1;
            for (i = 0; i < 64; i = i + 1)
                if (dec_all[i] != 0)
                    $display("STATEPROF decaps=%0d dec_state=%0d all=%0d other=%0d", n_decaps, i, dec_all[i], dec_other[i]);
            for (i = 0; i < 32; i = i + 1)
                if (enc_all[i] != 0)
                    $display("STATEPROF decaps=%0d enc_state_bit=%0d all=%0d other=%0d", n_decaps, i, enc_all[i], enc_other[i]);
        end
    end
endmodule
