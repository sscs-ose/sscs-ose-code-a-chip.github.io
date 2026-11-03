`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// Self-checking testbench for controller module
//////////////////////////////////////////////////////////////////////////////

module controller_tb;

    parameter TILE_SIZE = 16;

    reg clk, rst_n, tile_valid, is_zero, use_sparse;
    wire [$clog2(TILE_SIZE)-1:0] rd_addr;
    wire [$clog2(TILE_SIZE+1)-1:0] zero_count;
    wire mode_latched, mac_en, acc_en, acc_clr, done;

    integer pass_count, fail_count;

    controller #(.TILE_SIZE(TILE_SIZE)) uut (
        .clk(clk), .rst_n(rst_n), .tile_valid(tile_valid),
        .is_zero(is_zero), .use_sparse(use_sparse),
        .rd_addr(rd_addr), .zero_count(zero_count),
        .mode_latched(mode_latched), .mac_en(mac_en),
        .acc_en(acc_en), .acc_clr(acc_clr), .done(done)
    );

    always #10 clk = ~clk;

    initial begin
        $dumpfile("controller_tb.vcd");
        $dumpvars(0, controller_tb);

        clk = 0; rst_n = 0; tile_valid = 0;
        is_zero = 0; use_sparse = 0;
        pass_count = 0; fail_count = 0;

        #40 rst_n = 1; #20;

        // -------------------------------------------------------
        // Test 1: Dense mode (use_sparse=0, no zeros in SCAN)
        // -------------------------------------------------------
        $display("--- Test 1: Dense mode FSM ---");
        tile_valid = 1;
        @(posedge clk); tile_valid = 0;
        is_zero = 0; use_sparse = 0;

        // Wait through SCAN (16 cycles) + EVAL (1 cycle)
        repeat(17) @(posedge clk);

        // Should be in S_COMP now, mode_latched should be 0 (dense)
        if (mode_latched === 1'b0) begin
            $display("[PASS] Dense mode selected (mode_latched=0)");
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Expected mode_latched=0, got %b", mode_latched);
            fail_count = fail_count + 1;
        end

        // Wait for done
        @(posedge done);
        $display("[PASS] Done asserted in dense mode");
        pass_count = pass_count + 1;

        // Check zero_count = 0
        if (zero_count === 0) begin
            $display("[PASS] zero_count = 0");
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Expected zero_count=0, got %0d", zero_count);
            fail_count = fail_count + 1;
        end

        #60;

        // -------------------------------------------------------
        // Test 2: Sparse mode (is_zero=1 for 10 of 16 SCAN cycles)
        // -------------------------------------------------------
        $display("--- Test 2: Sparse mode FSM ---");
        tile_valid = 1;
        @(posedge clk); tile_valid = 0;

        // SCAN phase: first 10 cycles with is_zero=1, last 6 with is_zero=0
        is_zero = 1;
        repeat(10) @(posedge clk);
        is_zero = 0;
        repeat(6) @(posedge clk);

        // Now in EVAL — use_sparse should be asserted (10 zeros → sparse is cheaper)
        use_sparse = 1;
        @(posedge clk); // EVAL cycle
        use_sparse = 0;

        // Should be in S_COMP, mode_latched should be 1 (sparse)
        @(posedge clk);
        if (mode_latched === 1'b1) begin
            $display("[PASS] Sparse mode selected (mode_latched=1)");
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Expected mode_latched=1, got %b", mode_latched);
            fail_count = fail_count + 1;
        end

        @(posedge done);
        $display("[PASS] Done asserted in sparse mode");
        pass_count = pass_count + 1;

        #40;
        $display("===========================================");
        $display("  CTRL TEST: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $display("===========================================");
        $finish;
    end

endmodule
