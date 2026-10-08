//**************************************************************************
// Author: Alfi Misha Antony Selvin Raj
// Description: Sanity check for top (INCLUDED IN INCLUDE)
//**************************************************************************
`timescale 1ns/1ps

module tb_nand_dcdl_top;

logic clk;
logic rst_n;
logic shift_left;
logic shift_right;
logic A;
logic Y;

int errors;

nand_dcdl_top dut (
    .clk(clk),
    .rst_n(rst_n),
    .shift_left(shift_left),
    .shift_right(shift_right),
    .A(A),
    .Y(Y)
);

//
// clock generation
//
initial clk = 0;
always #5 clk = ~clk;

// -------------------------------------------------------
// Self-check: verify Q and Y match expectations.
// Q is accessed via dut.Q (internal signal).
// Behaviorally: Y = (|Q) ? A : 0
// -------------------------------------------------------
task automatic check_state(
    input logic [3:0] exp_Q,
    input logic       exp_Y,
    input string      label
);
    begin
        #1;
        if (dut.Q !== exp_Q) begin
            $display("[%0t] ERROR: %s | expected Q=%04b, got Q=%04b",
                     $time, label, exp_Q, dut.Q);
            errors++;
        end else
            $display("[%0t] PASS : %s | Q=%04b", $time, label, dut.Q);

        if (Y !== exp_Y) begin
            $display("[%0t] ERROR: %s | expected Y=%b, got Y=%b",
                     $time, label, exp_Y, Y);
            errors++;
        end else
            $display("[%0t] PASS : %s | Y=%b (A=%b)", $time, label, Y, A);
    end
endtask

task automatic check_no_x(input string label);
    begin
        #1;
        if (Y === 1'bx || Y === 1'bz) begin
            $display("[%0t] ERROR: X/Z on Y @ %s", $time, label);
            errors++;
        end
    end
endtask

// Apply shift_left for one cycle (change on negedge to avoid setup issues)
task automatic do_shift_left;
    begin
        @(negedge clk);
        shift_left  = 1'b1;
        shift_right = 1'b0;
        @(posedge clk);
        @(negedge clk);
        shift_left  = 1'b0;
    end
endtask

task automatic do_shift_right;
    begin
        @(negedge clk);
        shift_right = 1'b1;
        shift_left  = 1'b0;
        @(posedge clk);
        @(negedge clk);
        shift_right = 1'b0;
    end
endtask

//
// stimulus
//
initial begin
    $display("====== nand_dcdl_top testbench ======");
    errors      = 0;
    rst_n       = 0;
    shift_left  = 0;
    shift_right = 0;
    A           = 0;

    // --------------------------------------------------
    // TEST 1: Reset — Q must start at 4'b0001, Y=0 (A=0)
    // --------------------------------------------------
    $display("\n=== TEST 1: Reset initializes Q=4'b0001 ===");
    #20;
    rst_n = 1;
    @(posedge clk); #1;
    if (dut.Q !== 4'b0001) begin
        $display("[%0t] ERROR: after reset Q=%04b, expected 4'b0001", $time, dut.Q);
        errors++;
    end else
        $display("[%0t] PASS : after reset Q=%04b", $time, dut.Q);
    check_no_x("after reset");

    // --------------------------------------------------
    // TEST 2: A=0, any Q — Y must be 0
    // --------------------------------------------------
    $display("\n=== TEST 2: A=0 forces Y=0 ===");
    A = 1'b0;
    check_state(4'b0001, 1'b0, "A=0 Q=0001 -> Y=0");
    do_shift_left;
    check_state(4'b0010, 1'b0, "A=0 Q=0010 -> Y=0");
    do_shift_left;
    check_state(4'b0100, 1'b0, "A=0 Q=0100 -> Y=0");
    do_shift_left;
    check_state(4'b1000, 1'b0, "A=0 Q=1000 -> Y=0");

    // --------------------------------------------------
    // TEST 3: A=1, valid Q — Y must be 1
    // --------------------------------------------------
    $display("\n=== TEST 3: A=1 with valid Q -> Y=1 ===");
    A = 1'b1;
    // Q is currently 4'b1000 from previous test
    check_state(4'b1000, 1'b1, "A=1 Q=1000 -> Y=1");
    do_shift_left;   // 1000->0001 (wrap)
    check_state(4'b0001, 1'b1, "A=1 Q=0001 -> Y=1");
    do_shift_left;
    check_state(4'b0010, 1'b1, "A=1 Q=0010 -> Y=1");
    do_shift_left;
    check_state(4'b0100, 1'b1, "A=1 Q=0100 -> Y=1");
    do_shift_left;
    check_state(4'b1000, 1'b1, "A=1 Q=1000 -> Y=1");

    // --------------------------------------------------
    // TEST 4: Full left rotation (4 shifts) returns Q to start
    // --------------------------------------------------
    $display("\n=== TEST 4: Full left rotation via shift_left ===");
    // Reset to known state
    @(negedge clk); rst_n = 0; @(posedge clk); #1; rst_n = 1;
    A = 1'b1;
    do_shift_left; check_state(4'b0010, 1'b1, "L1: 0001->0010");
    do_shift_left; check_state(4'b0100, 1'b1, "L2: 0010->0100");
    do_shift_left; check_state(4'b1000, 1'b1, "L3: 0100->1000");
    do_shift_left; check_state(4'b0001, 1'b1, "L4: 1000->0001 (wrap)");

    // --------------------------------------------------
    // TEST 5: Full right rotation (4 shifts) returns Q to start
    // --------------------------------------------------
    $display("\n=== TEST 5: Full right rotation via shift_right ===");
    do_shift_right; check_state(4'b1000, 1'b1, "R1: 0001->1000");
    do_shift_right; check_state(4'b0100, 1'b1, "R2: 1000->0100");
    do_shift_right; check_state(4'b0010, 1'b1, "R3: 0100->0010");
    do_shift_right; check_state(4'b0001, 1'b1, "R4: 0010->0001 (wrap)");

    // --------------------------------------------------
    // TEST 6: Reset mid-operation restores Q=4'b0001
    // --------------------------------------------------
    $display("\n=== TEST 6: Reset mid-operation ===");
    do_shift_left;
    do_shift_left;  // Q=0100
    @(posedge clk); #1;
    $display("[%0t] INFO: Q before mid-reset = %04b", $time, dut.Q);
    @(negedge clk); rst_n = 0; @(posedge clk); #1; rst_n = 1;
    check_state(4'b0001, 1'b1, "mid-reset restores Q=0001, Y=A=1");

    // --------------------------------------------------
    // TEST 7: A toggles with fixed Q — Y tracks A
    // --------------------------------------------------
    $display("\n=== TEST 7: A toggle with fixed Q ===");
    begin : test7
        logic [3:0] qvals [0:3];
        int k;
        qvals[0] = 4'b0001;
        qvals[1] = 4'b0010;
        qvals[2] = 4'b0100;
        qvals[3] = 4'b1000;
        @(negedge clk); rst_n = 0; @(posedge clk); #1; rst_n = 1;
        for (k = 0; k < 4; k++) begin
            // Shift to desired position
            begin : inner_shift
                int s;
                for (s = 0; s < k; s++) begin
                    do_shift_left;
                end
            end
            A = 1'b0; check_state(qvals[k], 1'b0, $sformatf("Q=%04b A=0->Y=0", qvals[k]));
            A = 1'b1; check_state(qvals[k], 1'b1, $sformatf("Q=%04b A=1->Y=1", qvals[k]));
            A = 1'b0; check_state(qvals[k], 1'b0, $sformatf("Q=%04b A=0 again->Y=0", qvals[k]));
            // Reset back to 0001 for next iteration
            @(negedge clk); rst_n = 0; @(posedge clk); #1; rst_n = 1;
        end
    end

    // --------------------------------------------------
    // TEST 8: Original stimulus (shift left/right sequences)
    // --------------------------------------------------
    $display("\n=== TEST 8: Original shift sequences (forward/backward) ===");
    @(negedge clk); rst_n = 0; @(posedge clk); #1; rst_n = 1;
    A = 1;

    // move delay forward
    repeat (4) begin
        @(posedge clk);
        shift_left = 1;
        @(posedge clk);
        shift_left = 0;
    end

    // move delay backward
    repeat (4) begin
        @(posedge clk);
        shift_right = 1;
        @(posedge clk);
        shift_right = 0;
    end

    // Q should be back to 4'b0001 after 4L then 4R
    @(posedge clk); #1;
    if (dut.Q !== 4'b0001) begin
        $display("[%0t] ERROR: 4L+4R should return to Q=0001, got %04b", $time, dut.Q);
        errors++;
    end else
        $display("[%0t] PASS : 4L+4R returned to Q=0001", $time);

    // --------------------------------------------------
    // Summary
    // --------------------------------------------------
    #40;
    $display("\n============================");
    if (errors == 0)
        $display("TESTBENCH PASSED: 0 errors");
    else
        $display("TESTBENCH FAILED: %0d error(s)", errors);
    $display("============================");
    $finish;
end

//
// monitor behavior
//
always @(posedge clk) begin
    $display("t=%0t  A=%b  Q=%b  Y=%b",
        $time, A, dut.Q, Y);
end

endmodule
