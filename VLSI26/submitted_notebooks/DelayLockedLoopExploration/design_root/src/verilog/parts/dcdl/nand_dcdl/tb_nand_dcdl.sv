//**************************************************************************
// Author: Alfi Misha Antony Selvin Raj
// Description: Sanity check for delay line (NOT INCLUDED IN TOP)
//**************************************************************************
//not in the include this is just for my debug purpose.
`timescale 1ns/1ps

module tb_nand_dcdl;

logic A;
logic [3:0] Q;
logic Y;

int errors;

nand_dcdl dut (
    .A(A),
    .Q(Q),
    .Y(Y)
);

// -------------------------------------------------------
// Self-check: for any Q with at least one bit set, Y must
// follow A.  For Q=4'b0000, Y must be 0 regardless of A.
//
// Behavioral derivation:
//   Each nand_dcdl_cell is a 2:1 mux: out = ctl ? in0 : in1
//   The chain feeds A into the first active cell (lowest
//   Q bit that is 1), so Y = A when |Q != 0, Y = 0 when Q=0.
// -------------------------------------------------------
task automatic check_Y(
    input logic exp_Y,
    input string label
);
    begin
        #1;  // allow combinational settling
        if (Y !== exp_Y) begin
            $display("[%0t] ERROR: %s | A=%b Q=%04b -> expected Y=%b, got Y=%b",
                     $time, label, A, Q, exp_Y, Y);
            errors++;
        end else begin
            $display("[%0t] PASS : %s | A=%b Q=%04b -> Y=%b",
                     $time, label, A, Q, Y);
        end
    end
endtask

// Check Y is not X or Z
task automatic check_no_x(input string label);
    begin
        #1;
        if (Y === 1'bx || Y === 1'bz) begin
            $display("[%0t] ERROR: X/Z on Y @ %s | A=%b Q=%04b Y=%b",
                     $time, label, A, Q, Y);
            errors++;
        end
    end
endtask

initial begin
    $display("====== nand_dcdl testbench ======");
    errors = 0;

    A = 0;
    Q = 4'b0001;

    // --------------------------------------------------
    // TEST 1: Original sanity sweep (A=1, sweep one-hot Q)
    // --------------------------------------------------
    $display("\n=== TEST 1: Original sanity sweep ===");
    #5 A = 1;
    #10 Q = 4'b0001;  check_Y(1'b1, "A=1 Q=0001");
    #10 Q = 4'b0010;  check_Y(1'b1, "A=1 Q=0010");
    #10 Q = 4'b0100;  check_Y(1'b1, "A=1 Q=0100");
    #10 Q = 4'b1000;  check_Y(1'b1, "A=1 Q=1000");

    // Toggle A
    #10 A = 0;  #10 A = 1;

    // --------------------------------------------------
    // TEST 2: All one-hot Q patterns, A=1 -> Y must be 1
    // --------------------------------------------------
    $display("\n=== TEST 2: One-hot Q patterns, A=1 -> Y=1 ===");
    A = 1'b1;
    #2;
    Q = 4'b0001; check_Y(1'b1, "A=1 one-hot Q=0001");
    Q = 4'b0010; check_Y(1'b1, "A=1 one-hot Q=0010");
    Q = 4'b0100; check_Y(1'b1, "A=1 one-hot Q=0100");
    Q = 4'b1000; check_Y(1'b1, "A=1 one-hot Q=1000");

    // --------------------------------------------------
    // TEST 3: All one-hot Q patterns, A=0 -> Y must be 0
    // --------------------------------------------------
    $display("\n=== TEST 3: One-hot Q patterns, A=0 -> Y=0 ===");
    A = 1'b0;
    #2;
    Q = 4'b0001; check_Y(1'b0, "A=0 one-hot Q=0001");
    Q = 4'b0010; check_Y(1'b0, "A=0 one-hot Q=0010");
    Q = 4'b0100; check_Y(1'b0, "A=0 one-hot Q=0100");
    Q = 4'b1000; check_Y(1'b0, "A=0 one-hot Q=1000");

    // --------------------------------------------------
    // TEST 4: Q=0 -> Y must be 0 regardless of A
    // (no active mux selection: all cells pass 0 up the chain)
    // --------------------------------------------------
    $display("\n=== TEST 4: Q=0 forces Y=0 regardless of A ===");
    Q = 4'b0000;
    A = 1'b1; check_Y(1'b0, "Q=0000 A=1 -> Y=0");
    A = 1'b0; check_Y(1'b0, "Q=0000 A=0 -> Y=0");

    // --------------------------------------------------
    // TEST 5: Multi-hot Q patterns — Y should still follow A
    // (any active bit in the chain routes A through)
    // --------------------------------------------------
    $display("\n=== TEST 5: Multi-hot Q patterns, A=1 -> Y=1 ===");
    A = 1'b1;
    Q = 4'b0011; check_Y(1'b1, "A=1 Q=0011 (multi-hot)");
    Q = 4'b0101; check_Y(1'b1, "A=1 Q=0101 (multi-hot)");
    Q = 4'b1010; check_Y(1'b1, "A=1 Q=1010 (multi-hot)");
    Q = 4'b1111; check_Y(1'b1, "A=1 Q=1111 (all bits set)");

    $display("\n=== TEST 5b: Multi-hot Q patterns, A=0 -> Y=0 ===");
    A = 1'b0;
    Q = 4'b0011; check_Y(1'b0, "A=0 Q=0011 (multi-hot)");
    Q = 4'b1100; check_Y(1'b0, "A=0 Q=1100 (multi-hot)");
    Q = 4'b1111; check_Y(1'b0, "A=0 Q=1111 (all bits set)");

    // --------------------------------------------------
    // TEST 6: A toggles while Q is fixed — Y must track A
    // (for each one-hot position)
    // --------------------------------------------------
    $display("\n=== TEST 6: A toggle with fixed Q ===");
    begin : test6
        logic [3:0] qvals [0:3];
        int k;
        qvals[0] = 4'b0001;
        qvals[1] = 4'b0010;
        qvals[2] = 4'b0100;
        qvals[3] = 4'b1000;
        for (k = 0; k < 4; k++) begin
            Q = qvals[k];
            A = 1'b0; check_Y(1'b0, $sformatf("Q=%04b A=0->Y=0", Q));
            A = 1'b1; check_Y(1'b1, $sformatf("Q=%04b A=1->Y=1", Q));
            A = 1'b0; check_Y(1'b0, $sformatf("Q=%04b A=0 again->Y=0", Q));
            A = 1'b1; check_Y(1'b1, $sformatf("Q=%04b A=1 again->Y=1", Q));
        end
    end

    // --------------------------------------------------
    // TEST 7: No X/Z on Y for all 16 Q values with A=0 and A=1
    // --------------------------------------------------
    $display("\n=== TEST 7: No X/Z on Y for all Q in [0,15] ===");
    begin : test7
        int q;
        for (q = 0; q < 16; q++) begin
            Q = q[3:0];
            A = 1'b0; check_no_x($sformatf("A=0 Q=%04b", Q));
            A = 1'b1; check_no_x($sformatf("A=1 Q=%04b", Q));
        end
    end

    // --------------------------------------------------
    // Summary
    // --------------------------------------------------
    #20 $display("\n============================");
    if (errors == 0)
        $display("TESTBENCH PASSED: 0 errors");
    else
        $display("TESTBENCH FAILED: %0d error(s)", errors);
    $display("============================");
    $finish;
end

endmodule
