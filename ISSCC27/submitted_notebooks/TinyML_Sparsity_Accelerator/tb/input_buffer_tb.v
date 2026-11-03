`timescale 1ns / 1ps

module input_buffer_tb;
    parameter TILE_SIZE  = 16;
    parameter DATA_WIDTH = 8;

    reg clk, wr_en;
    reg [$clog2(TILE_SIZE)-1:0] wr_addr, rd_addr;
    reg [DATA_WIDTH-1:0] act_in, wt_in;
    wire [DATA_WIDTH-1:0] act_out, wt_out;

    integer pass_count, fail_count, i;

    input_buffer #(.TILE_SIZE(TILE_SIZE), .DATA_WIDTH(DATA_WIDTH)) uut (
        .clk(clk), .wr_en(wr_en), .wr_addr(wr_addr),
        .act_in(act_in), .wt_in(wt_in),
        .rd_addr(rd_addr), .act_out(act_out), .wt_out(wt_out)
    );

    always #10 clk = ~clk;

    initial begin
        $dumpfile("input_buffer_tb.vcd");
        $dumpvars(0, input_buffer_tb);

        clk = 0; wr_en = 0; wr_addr = 0; rd_addr = 0;
        act_in = 0; wt_in = 0;
        pass_count = 0; fail_count = 0;

        #40;

        // Write all 16 entries: act[i] = i+1, wt[i] = 16-i
        for (i = 0; i < TILE_SIZE; i = i + 1) begin
            @(posedge clk);
            wr_en   = 1;
            wr_addr = i[$clog2(TILE_SIZE)-1:0];
            act_in  = i[DATA_WIDTH-1:0] + 1;
            wt_in   = (TILE_SIZE - i);
        end
        @(posedge clk); wr_en = 0;

        // Read back all 16 entries and check (combinational read)
        for (i = 0; i < TILE_SIZE; i = i + 1) begin
            rd_addr = i[$clog2(TILE_SIZE)-1:0];
            #1;
            if (act_out === (i[DATA_WIDTH-1:0] + 1) && wt_out === (TILE_SIZE - i)) begin
                pass_count = pass_count + 1;
            end else begin
                $display("[FAIL] addr=%0d: act=%0d (exp %0d), wt=%0d (exp %0d)",
                         i, act_out, i+1, wt_out, TILE_SIZE-i);
                fail_count = fail_count + 1;
            end
        end

        if (fail_count == 0)
            $display("[PASS] All 16 buffer entries read correctly");

        $display("BUF TEST: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $finish;
    end
endmodule
