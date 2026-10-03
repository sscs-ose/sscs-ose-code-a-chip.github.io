// Simulation-only contract checker for the packed NTT in the full system (TRUSTEDGE_PACKED_NTT). It is a
// further top-level module and reads the shared engine's ports through hierarchical references only.
// The packed engine stores a coefficient pair per word, so external writes must arrive as the even
// coefficient followed by its odd partner, every value must be canonical (below q), and no transform may
// start while a pair is half written. Any violation is printed at once; a summary follows at the end.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module ntt_packed_checker;
    integer n_wr = 0, n_start = 0, n_err = 0;
    reg       pend = 1'b0;
    reg [7:0] pend_addr = 8'd0;
    wire       busy  = tb_trustedge_spi.dut.u_shared_ntt.busy;
    wire       we    = tb_trustedge_spi.dut.u_shared_ntt.we;
    wire       start = tb_trustedge_spi.dut.u_shared_ntt.start;
    wire [7:0] waddr = tb_trustedge_spi.dut.u_shared_ntt.waddr;
    wire [15:0] wdata = tb_trustedge_spi.dut.u_shared_ntt.wdata;

    always @(posedge tb_trustedge_spi.clk) begin
        if (!busy && we) begin
            n_wr = n_wr + 1;
            if (wdata >= 16'd3329) begin
                n_err = n_err + 1;
                $display("NTT_PACKED_VIOLATION t=%0t non-canonical write addr=%0d data=%0d", $time, waddr, wdata);
            end
            if (!waddr[0]) begin
                if (pend) begin
                    n_err = n_err + 1;
                    $display("NTT_PACKED_VIOLATION t=%0t even write %0d while %0d is pending", $time, waddr, pend_addr);
                end
                pend = 1'b1; pend_addr = waddr;
            end else begin
                if (!pend || pend_addr != {waddr[7:1], 1'b0}) begin
                    n_err = n_err + 1;
                    $display("NTT_PACKED_VIOLATION t=%0t odd write %0d without its even partner (pending=%0d %0d)",
                             $time, waddr, pend, pend_addr);
                end
                pend = 1'b0;
            end
        end
        if (start && !busy) begin
            n_start = n_start + 1;
            if (pend) begin
                n_err = n_err + 1;
                $display("NTT_PACKED_VIOLATION t=%0t start with pair %0d half written", $time, pend_addr);
            end
        end
    end

    final $display("NTT_PACKED_CHECK writes=%0d starts=%0d violations=%0d", n_wr, n_start, n_err);
endmodule
