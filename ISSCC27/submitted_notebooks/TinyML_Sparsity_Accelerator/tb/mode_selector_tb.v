`timescale 1ns / 1ps

module mode_selector_tb;
    reg [15:0] dense_cost, sparse_cost;
    wire use_sparse;

    integer pass_count, fail_count;

    mode_selector uut (
        .dense_cost(dense_cost),
        .sparse_cost(sparse_cost),
        .use_sparse(use_sparse)
    );

    task check_ms;
        input expected;
        input [8*24-1:0] label;
        begin
            #1;
            if (use_sparse === expected) begin
                $display("[PASS] %0s: use_sparse=%b", label, use_sparse);
                pass_count = pass_count + 1;
            end else begin
                $display("[FAIL] %0s: use_sparse=%b (expected %b)", label, use_sparse, expected);
                fail_count = fail_count + 1;
            end
        end
    endtask

    initial begin
        $dumpfile("mode_selector_tb.vcd");
        $dumpvars(0, mode_selector_tb);
        pass_count = 0; fail_count = 0;

        // Sparse cheaper → use sparse
        dense_cost = 160; sparse_cost = 97;  check_ms(1'b1, "Sparse cheaper");
        // Dense cheaper → use dense
        dense_cost = 160; sparse_cost = 217; check_ms(1'b0, "Dense cheaper");
        // Equal → use dense (not strictly less)
        dense_cost = 160; sparse_cost = 160; check_ms(1'b0, "Equal cost");
        // Edge: sparse=0
        dense_cost = 160; sparse_cost = 0;   check_ms(1'b1, "Sparse=0");

        $display("MS TEST: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $finish;
    end
endmodule
