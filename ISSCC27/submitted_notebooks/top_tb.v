`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// Self-checking top-level testbench for Sparsity-Aware Zero-Skipping MAC
// Pure Verilog-2001 compliant (Compatible with Vivado, ModelSim, Icarus)
//////////////////////////////////////////////////////////////////////////////

module top_tb;

    parameter TILE_SIZE  = 16;
    parameter DATA_WIDTH = 8;
    parameter ACC_WIDTH  = 32;

    reg clk;
    reg rst_n;
    reg wr_en;
    reg [$clog2(TILE_SIZE)-1:0] wr_addr;
    reg signed [DATA_WIDTH-1:0] act_in;
    reg signed [DATA_WIDTH-1:0] wt_in;
    reg tile_valid;

    wire done;
    wire selected_mode;
    wire signed [ACC_WIDTH-1:0] result;

    integer pass_count, fail_count;
    integer i;

    top #(
        .TILE_SIZE(TILE_SIZE),
        .DATA_WIDTH(DATA_WIDTH),
        .ACC_WIDTH(ACC_WIDTH)
    ) uut (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(wr_en),
        .wr_addr(wr_addr),
        .act_in(act_in),
        .wt_in(wt_in),
        .tile_valid(tile_valid),
        .done(done),
        .selected_mode(selected_mode),
        .result(result)
    );

    // Clock generation (50 MHz)
    always #10 clk = ~clk;

    // Task: trigger computation and wait for done
    task run_tile;
        begin
            @(posedge clk);
            tile_valid = 1;
            @(posedge clk);
            tile_valid = 0;
            @(posedge done);
            @(posedge clk); // Pipeline settle cycle
        end
    endtask

    initial begin
        // Waveform dump
        $dumpfile("top_tb.vcd");
        $dumpvars(0, top_tb);

        clk        = 0;
        rst_n      = 0;
        wr_en      = 0;
        wr_addr    = 0;
        act_in     = 0;
        wt_in      = 0;
        tile_valid = 0;
        pass_count = 0;
        fail_count = 0;

        // Apply Reset
        #40 rst_n = 1;
        #20;

        // ===========================================================
        // Test 1: Sparse Mode — 50% sparsity (8 zeros out of 16)
        // Even indices: act=0, Odd indices: act=3, all wt=4
        // Expected MACs: 8 non-zero pairs -> 8 * (3 * 4) = 96
        // Zero count = 8 -> sparse_cost = (16-8)*12 + 25 = 121 < 160 -> Sparse
        // ===========================================================
        $display("\n--- Starting Test 1: Sparse Mode (50%% sparsity) ---");
        for (i = 0; i < TILE_SIZE; i = i + 1) begin
            @(posedge clk);
            wr_en   = 1;
            wr_addr = i[3:0];
            act_in  = (i % 2 == 0) ? 8'sd0 : 8'sd3;
            wt_in   = 8'sd4;
        end
        @(posedge clk);
        wr_en = 0;

        run_tile();

        #1;
        if (result === 32'sd96 && selected_mode === 1'b1) begin
            $display("[PASS] Test 1: Result = %0d (Expected 96), Mode = Sparse", result);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test 1: Result = %0d (Expected 96), Mode = %b (Expected 1)", result, selected_mode);
            fail_count = fail_count + 1;
        end

        // ===========================================================
        // Test 2: Dense Mode — 0% sparsity (no zeros)
        // All act = 2, all wt = 3
        // Expected: 16 * (2 * 3) = 96
        // Zero count = 0 -> sparse_cost = 16*12 + 25 = 217 > 160 -> Dense
        // ===========================================================
        #40;
        $display("\n--- Starting Test 2: Dense Mode (0%% sparsity) ---");
        for (i = 0; i < TILE_SIZE; i = i + 1) begin
            @(posedge clk);
            wr_en   = 1;
            wr_addr = i[3:0];
            act_in  = 8'sd2;
            wt_in   = 8'sd3;
        end
        @(posedge clk);
        wr_en = 0;

        run_tile();

        #1;
        if (result === 32'sd96 && selected_mode === 1'b0) begin
            $display("[PASS] Test 2: Result = %0d (Expected 96), Mode = Dense", result);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test 2: Result = %0d (Expected 96), Mode = %b (Expected 0)", result, selected_mode);
            fail_count = fail_count + 1;
        end

        // ===========================================================
        // Test 3: All zeros — 100% sparsity
        // All act = 0, all wt = 5 -> Expected: 0
        // ===========================================================
        #40;
        $display("\n--- Starting Test 3: All Zeros (100%% sparsity) ---");
        for (i = 0; i < TILE_SIZE; i = i + 1) begin
            @(posedge clk);
            wr_en   = 1;
            wr_addr = i[3:0];
            act_in  = 8'sd0;
            wt_in   = 8'sd5;
        end
        @(posedge clk);
        wr_en = 0;

        run_tile();

        #1;
        if (result === 32'sd0 && selected_mode === 1'b1) begin
            $display("[PASS] Test 3: Result = %0d (Expected 0), Mode = Sparse", result);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test 3: Result = %0d (Expected 0), Mode = %b (Expected 1)", result, selected_mode);
            fail_count = fail_count + 1;
        end

        // ===========================================================
        // Test 4: Mixed negative values
        // Non-zero products sum to: -1 + 2 - 3 + 4 - 5 + 6 - 7 + 8 = 4
        // ===========================================================
        #40;
        $display("\n--- Starting Test 4: Negative Values ---");
        for (i = 0; i < TILE_SIZE; i = i + 1) begin
            @(posedge clk);
            wr_en   = 1;
            wr_addr = i[3:0];
            case (i)
                0: act_in = -8'sd1;
                1: act_in =  8'sd2;
                2: act_in = -8'sd3;
                3: act_in =  8'sd4;
                4: act_in = -8'sd5;
                5: act_in =  8'sd6;
                6: act_in = -8'sd7;
                7: act_in =  8'sd8;
                default: act_in = 8'sd0;
            endcase
            wt_in = 8'sd1;
        end
        @(posedge clk);
        wr_en = 0;

        run_tile();

        #1;
        if (result === 32'sd4 && selected_mode === 1'b1) begin
            $display("[PASS] Test 4: Result = %0d (Expected 4), Mode = Sparse", result);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test 4: Result = %0d (Expected 4), Mode = %b (Expected 1)", result, selected_mode);
            fail_count = fail_count + 1;
        end

        // ===========================================================
        // Test Summary
        // ===========================================================
        #40;
        $display("\n===========================================");
        $display("  TEST SUMMARY: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $display("===========================================");
        if (fail_count == 0)
            $display("  >>> ALL TESTS PASSED <<<\n");
        else
            $display("  >>> SOME TESTS FAILED <<<\n");

        $finish;
    end

endmodule
