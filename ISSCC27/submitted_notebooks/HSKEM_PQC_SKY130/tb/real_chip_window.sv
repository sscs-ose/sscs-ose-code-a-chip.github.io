// Controller of the gate-level run of the routed chip netlist next to the RTL testbench (scripts/real_netlist.py).
// Detects the first ML-KEM decapsulation like decaps_vcd_window.sv (+skip=<n> skips n busy intervals), then at the
// next falling clock edge loads the routed netlist's flip-flops from the shadow's registers (the RTL state; a register the
// RTL simulation leaves unknown is loaded as 0) and releases its clock. From the following rising edge the routed netlist
// runs on its own. At every falling edge until the end of the window its flip-flops, outputs and macro inputs are compared
// with the shadow's, where the shadow's value is known (the RTL simulation leaves never-written registers unknown, and
// those are don't-care). With +vcd=<path> the activity of real_chip over the window is recorded; +dbg=<n> dumps both
// netlists and stops after n cycles; +list=<n> prints the first n flip-flop and the first n pin mismatch events (index, cycle,
// real and shadow values; names in real_flops.txt and real_flops.txt.pins). Compiled as a further top level; simulation only.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module real_chip_window;
    reg [1023:0] path;
    reg          started = 1'b0, armed = 1'b0, busy_q = 1'b0, in_long = 1'b0, dump = 1'b0, dbg = 1'b0;
    integer      cycles = 0, skip = 0, seen = 0, k, nbad, nbadx, npin, nunk;
    integer      bad_cycles = 0, bad_flops = 0, bad_flops_x = 0, bad_pin_cycles = 0, bad_pins = 0, dbg_cycles = 0;
    integer      first_bad = -1, first_bad_cycle = -1, first_pin_cycle = -1, unknown_sum = 0;
    integer      list_n = 0, listed_ff = 0, listed_pin = 0;
    initial begin
        if (!$value$plusargs("skip=%d", skip)) skip = 0;
        dump = $value$plusargs("vcd=%s", path);
        dbg = $value$plusargs("dbg=%d", dbg_cycles);
        if (!$value$plusargs("list=%d", list_n)) list_n = 0;
    end

    always @(posedge tb_trustedge_spi.clk) begin
        if (!started && !armed && busy_q && tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy && !in_long) begin
            in_long = 1'b1;
            seen = seen + 1;
        end
        if (!tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy) in_long = 1'b0;
        if (!started && !armed && in_long && seen == skip + 1) armed = 1'b1;
        busy_q = tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy;
    end

    always @(negedge tb_trustedge_spi.clk) begin
        if (armed && !started) begin
            started = 1'b1;
            real_chip.load = 1'b1; #1; real_chip.load = 1'b0;
            if (dump) begin $dumpfile(path); if (dbg) $dumpvars(0, real_chip, shadow_chip); else $dumpvars(0, real_chip); end
            real_chip.run = 1'b1;
            $display("REAL_CHIP load at t=%0t, %0d flip-flops, %0d compared pins", $time, real_chip.NFF, real_chip.NPIN);
        end else if (started) begin
            cycles = cycles + 1;
            nbad = 0; nbadx = 0; nunk = 0;
            for (k = 0; k < real_chip.NFF; k = k + 1) begin
                if (real_chip.q_shadow[k] === 1'b0 || real_chip.q_shadow[k] === 1'b1) begin
                    if (real_chip.q_real[k] !== real_chip.q_shadow[k]) begin
                        nbad = nbad + 1;
                        if (real_chip.q_real[k] === 1'bx || real_chip.q_real[k] === 1'bz) nbadx = nbadx + 1;
                        if (listed_ff < list_n) begin
                            listed_ff = listed_ff + 1;
                            $display("REAL_CHIP ff_mismatch idx=%0d cycle=%0d real=%b shadow=%b", k, cycles, real_chip.q_real[k], real_chip.q_shadow[k]);
                        end
                        if (first_bad < 0) begin
                            first_bad = k; first_bad_cycle = cycles;
                            $display("REAL_CHIP first flip-flop mismatch: index %0d at cycle %0d t=%0t real=%b shadow=%b",
                                     k, cycles, $time, real_chip.q_real[k], real_chip.q_shadow[k]);
                        end
                    end
                end else nunk = nunk + 1;
            end
            unknown_sum = unknown_sum + nunk;
            if (nbad > 0) begin bad_cycles = bad_cycles + 1; bad_flops = bad_flops + nbad; bad_flops_x = bad_flops_x + nbadx; end
            npin = 0;
            for (k = 0; k < real_chip.NPIN; k = k + 1)
                if ((real_chip.p_shadow[k] === 1'b0 || real_chip.p_shadow[k] === 1'b1) && real_chip.p_real[k] !== real_chip.p_shadow[k]) begin
                    npin = npin + 1;
                    if (listed_pin < list_n) begin
                        listed_pin = listed_pin + 1;
                        $display("REAL_CHIP pin_mismatch idx=%0d cycle=%0d real=%b shadow=%b", k, cycles, real_chip.p_real[k], real_chip.p_shadow[k]);
                    end
                    if (first_pin_cycle < 0) begin
                        first_pin_cycle = cycles;
                        $display("REAL_CHIP first pin mismatch: index %0d at cycle %0d t=%0t real=%b shadow=%b",
                                 k, cycles, $time, real_chip.p_real[k], real_chip.p_shadow[k]);
                    end
                end
            if (npin > 0) begin bad_pin_cycles = bad_pin_cycles + 1; bad_pins = bad_pins + npin; end
            if (cycles % 500 == 0)
                $display("REAL_CHIP cycle %0d: flip-flop mismatches %0d (real x: %0d), shadow-unknown flip-flops %0d, pin mismatches %0d",
                         cycles, nbad, nbadx, nunk, npin);
            if (dbg && cycles >= dbg_cycles) begin $dumpflush; $display("REAL_CHIP debug stop after %0d cycles", cycles); $finish; end
            if (!tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy) begin
                if (dump) $dumpflush;
                $display("REAL_CHIP end t=%0t cycles_compared=%0d cycles_with_flop_mismatch=%0d flop_mismatches=%0d (real x: %0d) first_flop_mismatch_cycle=%0d cycles_with_pin_mismatch=%0d pin_mismatches=%0d first_pin_mismatch_cycle=%0d mean_shadow_unknown_flops=%0d",
                         $time, cycles, bad_cycles, bad_flops, bad_flops_x, first_bad_cycle, bad_pin_cycles, bad_pins, first_pin_cycle, unknown_sum / cycles);
                $finish;
            end
        end
    end
endmodule
