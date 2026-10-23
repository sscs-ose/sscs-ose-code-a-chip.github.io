// Records a VCD of the whole design over the first ML-KEM decapsulation of the full-system testbench
// (the first busy interval of u_mlkem512_decaps_partial longer than one cycle; the unit also raises
// one-cycle busy pulses), for the activity-based power estimate of the chip (scripts/fullchip_power.sh).
// Dumping starts in the second busy cycle, so the window misses only the first cycle of the interval.
// +skip=<n> skips the first n such intervals (the testbench's first long busy interval is not a full
// decapsulation; the profiled ones are the next three, all of identical length).
// Compiled as a second top level next to tb_trustedge_spi; it only reads signals through hierarchical
// references. The file name comes from +vcd=<path>, which may be a named pipe. With DUMP_SHADOW defined it
// dumps the shadow of the routed netlist instead of the RTL.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module decaps_vcd_window;
    reg [1023:0] path;
    reg          started = 1'b0, busy_q = 1'b0;
    integer      cycles = 0, skip = 0, seen = 0;
    reg          in_long = 1'b0;
    initial if (!$value$plusargs("skip=%d", skip)) skip = 0;

    always @(posedge tb_trustedge_spi.clk) begin
        if (!started && busy_q && tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy && !in_long) begin
            in_long = 1'b1;
            seen = seen + 1;
        end
        if (!tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy) in_long = 1'b0;
        if (!started && in_long && seen == skip + 1) begin
            started = 1'b1;
            if (!$value$plusargs("vcd=%s", path)) path = "decaps.vcd";
            $dumpfile(path);
`ifdef DUMP_SHADOW
            $dumpvars(0, shadow_chip);          // the routed logic (scripts/shadow_netlist.py)
`else
            $dumpvars(0, tb_trustedge_spi.dut);
`endif
            $display("DECAPS_VCD start t=%0t", $time);
        end else if (started) begin
            if (tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy) begin
                cycles = cycles + 1;
            end else begin
                $dumpflush;
                $display("DECAPS_VCD end t=%0t cycles_in_window=%0d", $time, cycles + 1);
                $finish;
            end
        end
        busy_q = tb_trustedge_spi.dut.u_mlkem512_decaps_partial.busy;
    end
endmodule
