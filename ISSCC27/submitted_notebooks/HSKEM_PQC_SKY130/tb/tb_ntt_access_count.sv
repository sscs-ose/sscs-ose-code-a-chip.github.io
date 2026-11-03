// Counts SRAM word reads and writes of kyber_ntt_engine_packed2 during one forward and one inverse transform.
// The window runs from the start pulse until done; the coefficient load and read-back outside it are not counted.
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module tb_ntt_access_count;
    reg clk = 0, rst_n = 0, start = 0, inverse = 0, we = 0;
    reg  [7:0]  waddr = 0, raddr = 0;
    reg  [15:0] wdata = 0;
    wire [15:0] rdata;
    wire busy, done;
    always #5 clk = ~clk;

    kyber_ntt_engine_packed2 #(.EXTRA_STAGE(`XSTAGE)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .inverse(inverse),
        .busy(busy), .done(done), .waddr(waddr), .wdata(wdata), .we(we),
        .we_pair(1'b0), .wdata_odd(12'd0), .rdata_pair(), .stream(1'b0), .re(1'b0),
        .rdata(rdata), .raddr(raddr));

    reg active = 0;
    integer rd = 0, rd_idle = 0, wr = 0, i, cycles;
    always @(posedge clk) if (active && dut.u_sram.ce) begin
        if (dut.u_sram.we) wr = wr + 1;
        else if (busy) rd = rd + 1;
        else rd_idle = rd_idle + 1;   // idle read port (!busy && !we) serves the external raddr read-back, not the transform
    end

    task automatic run_one(input integer inv);
        begin
            for (i = 0; i < 256; i = i + 1) begin
                @(negedge clk); we = 1; waddr = i; wdata = (i * 37 + 11) % 3329;
            end
            @(negedge clk); we = 0;
            @(negedge clk); inverse = inv; start = 1; active = 1; rd = 0; rd_idle = 0; wr = 0;
            @(negedge clk); start = 0;
            cycles = 1;
            while (!done) begin @(negedge clk); cycles = cycles + 1; end
            @(posedge clk); #1 active = 0;
            $display("ACCESS_COUNT dir=%0s sram_reads=%0d sram_writes=%0d idle_port_reads=%0d cycles=%0d", inv ? "inverse" : "forward", rd, wr, rd_idle, cycles);
        end
    endtask

    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1;
        run_one(0);
        run_one(1);
        $finish;
    end
endmodule
