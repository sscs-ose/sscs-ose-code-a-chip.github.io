`timescale 1ps/1ps


/* |======================================================================= */
/* | */
/* | Author             : Mythri Muralikannan */
/* | Description        : Bang-Bang Phase detector BEHAVIORAL testbench*/
/* | This detector does not measure the exact phase error but just outputs a 1-bit decision */
/* | UP = 1 --> the reference clock is ahead and there must be a speed up*/
/* | DOWN = 1 --> the feedback clock is ahead and there must be a slow down*/
/* |  This is a behavioral testbench for a behavioral DUT, the current design style.
/* |  Since the DUT uses $time, the testbench also uses scheduled delays in ps.
/* |======================================================================= */


module tb_phase_detector;

    reg  clk_in;
    reg  clk_out;
    reg  rst;
    wire up;
    wire down;

    // DUT
    phase_detector dut (
        .clk_in  (clk_in),
        .clk_out (clk_out),
        .rst     (rst),
        .up      (up),
        .down    (down)
    );

    integer errors;

    // ----------------------------------------
    // Self-check task
    // ----------------------------------------
    task check_outputs;
        input expected_up;
        input expected_down;
        input [8*80-1:0] test_name;
        begin
            #1; // allow combinational logic to settle
            if ((up !== expected_up) || (down !== expected_down)) begin
                $display("[%0t ps] ERROR: %0s | expected up=%0b down=%0b, got up=%0b down=%0b",
                         $time, test_name, expected_up, expected_down, up, down);
                errors = errors + 1;
            end else begin
                $display("[%0t ps] PASS : %0s | up=%0b down=%0b",
                         $time, test_name, up, down);
            end
        end
    endtask

    // ----------------------------------------
    // Stimulus
    // ----------------------------------------
    initial begin
        errors  = 0;
        clk_in  = 0;
        clk_out = 0;
        rst     = 1;

        $display("==========================================");
        $display("Starting self-checking testbench");
        $display("==========================================");

        // Reset check
        #5;
        check_outputs(1'b0, 1'b0, "reset active");

        // Release reset
        #5;
        rst = 0;
        #1;
        check_outputs(1'b0, 1'b0, "after reset release, no edges yet");

        // ------------------------------------
        // Test 1: clk_in edge happens last -> up=1
        // ------------------------------------
        #10 clk_out = 1;
        #1  check_outputs(1'b0, 1'b1, "clk_out edge more recent => down=1");
        #5  clk_out = 0;

        #10 clk_in = 1;
        #1  check_outputs(1'b1, 1'b0, "clk_in edge more recent => up=1");
        #5  clk_in = 0;

        // ------------------------------------
        // Test 2: clk_out edge happens last -> down=1
        // ------------------------------------
        #10 clk_in = 1;
        #1  check_outputs(1'b1, 1'b0, "clk_in edge more recent => up=1");
        #5  clk_in = 0;

        #10 clk_out = 1;
        #1  check_outputs(1'b0, 1'b1, "clk_out edge more recent => down=1");
        #5  clk_out = 0;

        // ------------------------------------
        // Test 3: multiple clk_in edges in a row
        // ------------------------------------
        #10 clk_in = 1;
        #1  check_outputs(1'b1, 1'b0, "clk_in still most recent");
        #5  clk_in = 0;

        #10 clk_in = 1;
        #1  check_outputs(1'b1, 1'b0, "clk_in updated again, still up=1");
        #5  clk_in = 0;

        // ------------------------------------
        // Test 4: multiple clk_out edges in a row
        // ------------------------------------
        #10 clk_out = 1;
        #1  check_outputs(1'b0, 1'b1, "clk_out updated, down=1");
        #5  clk_out = 0;

        #10 clk_out = 1;
        #1  check_outputs(1'b0, 1'b1, "clk_out updated again, still down=1");
        #5  clk_out = 0;

        // ------------------------------------
        // Test 5: reset in middle of operation
        // ------------------------------------
        #10 rst = 1;
        #1  check_outputs(1'b0, 1'b0, "mid-run reset clears outputs");

        #5 rst = 0;
        #1 check_outputs(1'b0, 1'b0, "after mid-run reset release");

        // ------------------------------------
        // Test 6: same-time edges after reset
        // If both timestamps are equal, expect up=0/down=0
        // ------------------------------------
        fork
            begin
                #10 clk_in = 1;
            end
            begin
                #10 clk_out = 1;
            end
        join

        #1 check_outputs(1'b0, 1'b0, "simultaneous edges => equal timestamps");

        #5 clk_in  = 0;
        #5 clk_out = 0;

        // ------------------------------------
        // Test 7: near-simultaneous edges (1ps apart)
        // clk_in 1ps before clk_out => up=1 briefly, then down=1
        // ------------------------------------
        #10 clk_in  = 1;
        #1  clk_out = 1;
        #1  check_outputs(1'b0, 1'b1, "clk_in 1ps before clk_out => down after clk_out");
        #5  clk_in  = 0;
        #5  clk_out = 0;

        // ------------------------------------
        // Test 8: alternating clk_in/clk_out edges (simulate running clocks)
        // 10 pairs with clk_in leading by 3ps each
        // ------------------------------------
        begin : test8
            integer i;
            $display("\n=== TEST 8: Alternating edges, clk_in leads by 3ps ===");
            for (i = 0; i < 10; i = i + 1) begin
                #20 clk_in  = 1;
                #3  clk_out = 1;
                #7  clk_in  = 0;
                #3  clk_out = 0;
                #7;
                // After each clk_in then clk_out: down should dominate
                // (clk_out was more recent each cycle)
            end
            check_outputs(1'b0, 1'b1, "after 10 cycles clk_in-lead-by-3ps => down=1");
        end

        // ------------------------------------
        // Test 9: alternating clk_in/clk_out edges, clk_out leads by 3ps
        // ------------------------------------
        begin : test9
            integer j;
            $display("\n=== TEST 9: Alternating edges, clk_out leads by 3ps ===");
            for (j = 0; j < 10; j = j + 1) begin
                #20 clk_out = 1;
                #3  clk_in  = 1;
                #7  clk_out = 0;
                #3  clk_in  = 0;
                #7;
            end
            check_outputs(1'b1, 1'b0, "after 10 cycles clk_out-lead-by-3ps => up=1");
        end

        // ------------------------------------
        // Test 10: reset clears state after alternating run
        // ------------------------------------
        #5 rst = 1;
        #1 check_outputs(1'b0, 1'b0, "reset after alternating run");
        #5 rst = 0;

        // ------------------------------------
        // Test 11: clk_in edges only (no clk_out activity)
        // last_clk_in > last_clk_out (which stays 0) => up=1
        // ------------------------------------
        #5 clk_in = 1;
        #1 check_outputs(1'b1, 1'b0, "only clk_in has fired => up=1");
        #5 clk_in = 0;
        #5 clk_in = 1;
        #1 check_outputs(1'b1, 1'b0, "second clk_in only => still up=1");
        #5 clk_in = 0;

        // ------------------------------------
        // Test 12: clk_out edges only (no clk_in activity after reset)
        // ------------------------------------
        #5 rst = 1; #5 rst = 0; // clear timestamps

        #5 clk_out = 1;
        #1 check_outputs(1'b0, 1'b1, "after reset, only clk_out fired => down=1");
        #5 clk_out = 0;
        #5 clk_out = 1;
        #1 check_outputs(1'b0, 1'b1, "second clk_out only => still down=1");
        #5 clk_out = 0;

        // ------------------------------------
        // Test 13: repeated reset-fire-check cycle (3 repetitions)
        // ------------------------------------
        begin : test13
            integer k;
            $display("\n=== TEST 13: Repeated reset-fire-check ===");
            for (k = 0; k < 3; k = k + 1) begin
                #5 rst = 1; #5 rst = 0;
                check_outputs(1'b0, 1'b0, "after reset, both 0");
                #5 clk_in = 1;
                #1 check_outputs(1'b1, 1'b0, "clk_in fired after reset => up=1");
                #5 clk_in = 0;
            end
        end

        // ------------------------------------
        // Final report
        // ------------------------------------
        $display("==========================================");
        if (errors == 0) begin
            $display("TESTBENCH PASSED: no errors");
        end else begin
            $display("TESTBENCH FAILED: %0d error(s)", errors);
        end
        $display("==========================================");

        $finish;
    end

endmodule
