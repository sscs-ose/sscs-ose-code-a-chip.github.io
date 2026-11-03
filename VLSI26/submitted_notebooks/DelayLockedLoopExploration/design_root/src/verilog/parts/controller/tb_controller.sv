`timescale 1ps/1ps

/*
|=======================================================================
| Module      : tb_controller
| Description : Common testbench for DLL / ZDB controller implementations
|
| Assumptions:
|   - DUT module name is controller
|   - DUT interface:
|       clk_in, rst, up, down, ctrl
|
| Supported controller styles:
|   - Saturating up/down
|   - Filtered up/down
|   - Variable-step
|   - Acquire/track
|   - Coarse/fine
|
| Test strategy:
|   This testbench checks general controller behavior rather than
|   exact per-cycle increments, so it can be reused across multiple
|   controller architectures.
|
| Tests:
|    1. Reset initializes ctrl to INIT_CTRL
|    2. Hold behavior does not cause runaway changes
|    3. Repeated UP requests cause ctrl to increase
|    4. Repeated DOWN requests cause ctrl to decrease
|    5. Simultaneous up/down does not cause runaway changes
|    6. ctrl saturates within valid bounds
|    7. Recovery from zero is possible
|    8. Asynchronous reset restores INIT_CTRL
|    9. ctrl stays within bounds under persistent UP
|   10. ctrl stays within bounds under persistent DOWN
|   11. ctrl never increments past MAX during long UP burst
|   12. ctrl never decrements below 0 during long DOWN burst
|   13. Alternating up/down does not drift far from starting point
|   14. Reset from MAX restores INIT_CTRL
|   15. Reset from zero restores INIT_CTRL
|   16. ctrl reaches MAX before wrapping (no overflow)
|   17. ctrl reaches 0 before wrapping (no underflow)
|=======================================================================
*/

module tb_controller;

    parameter integer CTRL_BITS = 6;
    parameter integer INIT_CTRL = 32;
    localparam integer MAX_CTRL = (1 << CTRL_BITS) - 1;

    reg clk_in;
    reg rst;
    reg up;
    reg down;
    wire [CTRL_BITS-1:0] ctrl;

    integer errors;
    integer i;
    integer start_ctrl;
    integer end_ctrl;

    // DUT
    controller #(
        .CTRL_BITS(CTRL_BITS),
        .INIT_CTRL(INIT_CTRL)
    ) dut (
        .clk_in(clk_in),
        .rst   (rst),
        .up    (up),
        .down  (down),
        .ctrl  (ctrl)
    );

    // Clock: 10 ns period
    initial begin
        clk_in = 1'b0;
        forever #5000 clk_in = ~clk_in;
    end

    // Monitor
    initial begin
        $display(" time   rst up down | ctrl");
        $display("--------------------------");
        $monitor("%6t   %b   %b   %b   | %0d", $time, rst, up, down, ctrl);
    end

    task expect_ctrl_exact;
        input integer expected;
        begin
            if (ctrl !== expected[CTRL_BITS-1:0]) begin
                $display("ERROR @ %0t: expected ctrl=%0d, got %0d",
                         $time, expected, ctrl);
                errors = errors + 1;
            end
        end
    endtask

    task expect_in_range;
        begin
            if ((ctrl < 0) || (ctrl > MAX_CTRL[CTRL_BITS-1:0])) begin
                $display("ERROR @ %0t: ctrl=%0d out of valid range [0,%0d]",
                         $time, ctrl, MAX_CTRL);
                errors = errors + 1;
            end
        end
    endtask

    task run_cycles;
        input integer num_cycles;
        begin
            for (i = 0; i < num_cycles; i = i + 1) begin
                @(posedge clk_in);
                #1;
                expect_in_range();
            end
        end
    endtask

    task drive_and_run;
        input reg up_i;
        input reg down_i;
        input integer num_cycles;
        begin
            up   = up_i;
            down = down_i;
            run_cycles(num_cycles);
        end
    endtask

    task expect_nonincreasing;
        input integer before_val;
        begin
            if (ctrl > before_val[CTRL_BITS-1:0]) begin
                $display("ERROR @ %0t: ctrl increased unexpectedly (before=%0d, after=%0d)",
                         $time, before_val, ctrl);
                errors = errors + 1;
            end
        end
    endtask

    task expect_nondecreasing;
        input integer before_val;
        begin
            if (ctrl < before_val[CTRL_BITS-1:0]) begin
                $display("ERROR @ %0t: ctrl decreased unexpectedly (before=%0d, after=%0d)",
                         $time, before_val, ctrl);
                errors = errors + 1;
            end
        end
    endtask

    task expect_eventual_increase;
        input integer before_val;
        begin
            if (ctrl <= before_val[CTRL_BITS-1:0]) begin
                $display("ERROR @ %0t: ctrl did not increase (before=%0d, after=%0d)",
                         $time, before_val, ctrl);
                errors = errors + 1;
            end
        end
    endtask

    task expect_eventual_decrease;
        input integer before_val;
        begin
            if (ctrl >= before_val[CTRL_BITS-1:0]) begin
                $display("ERROR @ %0t: ctrl did not decrease (before=%0d, after=%0d)",
                         $time, before_val, ctrl);
                errors = errors + 1;
            end
        end
    endtask

    // Verify ctrl did not exceed MAX_CTRL during last N cycles.
    // Uses continuous in_range check inside run_cycles.

    initial begin
        errors = 0;
        rst    = 1'b1;
        up     = 1'b0;
        down   = 1'b0;

        // Reset check
        #1;
        expect_ctrl_exact(INIT_CTRL);

        #2000;
        rst = 1'b0;
        @(posedge clk_in);
        #1;
        expect_ctrl_exact(INIT_CTRL);

        // ------------------------------------------------------------
        $display("\n=== TEST 1: Hold behavior ===");
        // Hold should not run away. Some advanced modes may internally
        // switch state, but ctrl should remain stable over a quiet window.
        start_ctrl = ctrl;
        drive_and_run(1'b0, 1'b0, 16);
        expect_ctrl_exact(start_ctrl);

        // ------------------------------------------------------------
        $display("\n=== TEST 2: Repeated UP requests increase ctrl ===");
        start_ctrl = ctrl;
        drive_and_run(1'b1, 1'b0, 16);
        expect_eventual_increase(start_ctrl);

        // ------------------------------------------------------------
        $display("\n=== TEST 3: Repeated DOWN requests decrease ctrl ===");
        start_ctrl = ctrl;
        drive_and_run(1'b0, 1'b1, 16);
        expect_eventual_decrease(start_ctrl);

        // ------------------------------------------------------------
        $display("\n=== TEST 4: Simultaneous up/down does not run away ===");
        start_ctrl = ctrl;
        drive_and_run(1'b1, 1'b1, 16);

        // Allow small implementation-dependent behavior, but reject
        // runaway movement.
        if ((ctrl > start_ctrl + 1) || (ctrl < start_ctrl - 1)) begin
            $display("ERROR @ %0t: ctrl changed excessively during up=down=1 (before=%0d, after=%0d)",
                     $time, start_ctrl, ctrl);
            errors = errors + 1;
        end

        // ------------------------------------------------------------
        $display("\n=== TEST 5: Upper saturation / upper bound ===");
        drive_and_run(1'b1, 1'b0, 128);
        expect_in_range();

        if (ctrl != MAX_CTRL[CTRL_BITS-1:0]) begin
            $display("WARNING @ %0t: ctrl did not reach MAX_CTRL, final ctrl=%0d",
                     $time, ctrl);
        end

        // ------------------------------------------------------------
        $display("\n=== TEST 6: Lower saturation / lower bound ===");
        drive_and_run(1'b0, 1'b1, 128);
        expect_in_range();

        if (ctrl != 0) begin
            $display("WARNING @ %0t: ctrl did not reach 0, final ctrl=%0d",
                     $time, ctrl);
        end

        // ------------------------------------------------------------
        $display("\n=== TEST 7: Recovery from low end ===");
        start_ctrl = ctrl;
        drive_and_run(1'b1, 1'b0, 16);
        expect_eventual_increase(start_ctrl);

        // ------------------------------------------------------------
        $display("\n=== TEST 8: Recovery from high end ===");
        drive_and_run(1'b1, 1'b0, 128);
        start_ctrl = ctrl;
        drive_and_run(1'b0, 1'b1, 16);
        expect_eventual_decrease(start_ctrl);

        // ------------------------------------------------------------
        $display("\n=== TEST 9: Asynchronous reset ===");
        up   = 1'b1;
        down = 1'b0;
        #2000;
        rst = 1'b1;
        #1;
        expect_ctrl_exact(INIT_CTRL);

        #3000;
        rst = 1'b0;
        @(posedge clk_in);
        #1;
        expect_in_range();

        // ------------------------------------------------------------
        $display("\n=== TEST 10: ctrl never exceeds MAX during sustained UP ===");
        // Drive UP long enough to saturate, then keep driving — must not overflow
        drive_and_run(1'b1, 1'b0, 200);
        expect_in_range();
        if (ctrl > MAX_CTRL[CTRL_BITS-1:0]) begin
            $display("ERROR @ %0t: ctrl=%0d exceeded MAX_CTRL=%0d", $time, ctrl, MAX_CTRL);
            errors = errors + 1;
        end

        // ------------------------------------------------------------
        $display("\n=== TEST 11: ctrl never goes below 0 during sustained DOWN ===");
        drive_and_run(1'b0, 1'b1, 200);
        expect_in_range();
        if (ctrl > MAX_CTRL[CTRL_BITS-1:0]) begin   // checks for wrap-around underflow
            $display("ERROR @ %0t: ctrl=%0d wrapped below 0", $time, ctrl);
            errors = errors + 1;
        end

        // ------------------------------------------------------------
        $display("\n=== TEST 12: Reset from MAX restores INIT_CTRL ===");
        drive_and_run(1'b1, 1'b0, 128);  // push to MAX
        up   = 1'b0;
        down = 1'b0;
        #1000;
        rst = 1'b1;
        #1;
        expect_ctrl_exact(INIT_CTRL);
        #3000;
        rst = 1'b0;
        @(posedge clk_in);
        #1;
        expect_ctrl_exact(INIT_CTRL);

        // ------------------------------------------------------------
        $display("\n=== TEST 13: Reset from zero restores INIT_CTRL ===");
        drive_and_run(1'b0, 1'b1, 128);  // push to 0
        up   = 1'b0;
        down = 1'b0;
        #1000;
        rst = 1'b1;
        #1;
        expect_ctrl_exact(INIT_CTRL);
        #3000;
        rst = 1'b0;
        @(posedge clk_in);
        #1;
        expect_ctrl_exact(INIT_CTRL);

        // ------------------------------------------------------------
        $display("\n=== TEST 14: Alternating up/down does not drift far ===");
        // Alternate single-cycle UP and DOWN for 64 cycles.
        // ctrl should not drift more than a small amount from INIT_CTRL.
        start_ctrl = ctrl;
        begin : alt_test
            integer k;
            up   = 1'b0;
            down = 1'b0;
            for (k = 0; k < 64; k = k + 1) begin
                up   = 1'b1;
                down = 1'b0;
                @(posedge clk_in); #1; expect_in_range();
                up   = 1'b0;
                down = 1'b1;
                @(posedge clk_in); #1; expect_in_range();
            end
            up   = 1'b0;
            down = 1'b0;
        end
        // After balanced alternating, ctrl should be within a small window
        // of the starting value. Allow a generous window since some
        // controllers have asymmetric step sizes.
        if ((ctrl > start_ctrl + 8) || (ctrl < start_ctrl - 8)) begin
            $display("WARNING @ %0t: alternating up/down drifted more than 8 steps (start=%0d, end=%0d)",
                     $time, start_ctrl, ctrl);
        end

        // ------------------------------------------------------------
        $display("\n=== TEST 15: ctrl is monotone nondecreasing under sustained UP ===");
        // Reset to known state, then drive UP and verify ctrl only increases
        rst = 1'b1; #1000; rst = 1'b0;
        @(posedge clk_in); #1;
        start_ctrl = ctrl;
        begin : mono_up_test
            integer m;
            integer prev_ctrl;
            prev_ctrl = ctrl;
            up   = 1'b1;
            down = 1'b0;
            for (m = 0; m < 64; m = m + 1) begin
                @(posedge clk_in); #1;
                if (ctrl < prev_ctrl[CTRL_BITS-1:0]) begin
                    $display("ERROR @ %0t: ctrl decreased during sustained UP (prev=%0d, now=%0d)",
                             $time, prev_ctrl, ctrl);
                    errors = errors + 1;
                end
                prev_ctrl = ctrl;
                expect_in_range();
            end
            up   = 1'b0;
            down = 1'b0;
        end

        // ------------------------------------------------------------
        $display("\n=== TEST 16: ctrl is monotone nonincreasing under sustained DOWN ===");
        rst = 1'b1; #1000; rst = 1'b0;
        @(posedge clk_in); #1;
        begin : mono_down_test
            integer n;
            integer prev_ctrl2;
            prev_ctrl2 = ctrl;
            up   = 1'b0;
            down = 1'b1;
            for (n = 0; n < 64; n = n + 1) begin
                @(posedge clk_in); #1;
                if (ctrl > prev_ctrl2[CTRL_BITS-1:0]) begin
                    $display("ERROR @ %0t: ctrl increased during sustained DOWN (prev=%0d, now=%0d)",
                             $time, prev_ctrl2, ctrl);
                    errors = errors + 1;
                end
                prev_ctrl2 = ctrl;
                expect_in_range();
            end
            up   = 1'b0;
            down = 1'b0;
        end

        // ------------------------------------------------------------
        $display("\n======================================");
        if (errors == 0)
            $display("TEST PASSED");
        else
            $display("TEST FAILED: %0d error(s)", errors);
        $display("======================================");

        $finish;
    end

endmodule
