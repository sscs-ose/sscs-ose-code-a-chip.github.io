`timescale 1ns / 1ps

module cost_estimator_tb;
    parameter TILE_SIZE = 16;

    reg [$clog2(TILE_SIZE+1)-1:0] zero_count;
    wire [15:0] dense_cost, sparse_cost;

    integer pass_count, fail_count;

    cost_estimator #(.TILE_SIZE(TILE_SIZE)) uut (
        .zero_count(zero_count),
        .dense_cost(dense_cost),
        .sparse_cost(sparse_cost)
    );

    task check_cost;
        input [15:0] exp_dense, exp_sparse;
        input [8*24-1:0] label;
        begin
            #1;
            if (dense_cost === exp_dense && sparse_cost === exp_sparse) begin
                $display("[PASS] %0s: dense=%0d, sparse=%0d", label, dense_cost, sparse_cost);
                pass_count = pass_count + 1;
            end else begin
                $display("[FAIL] %0s: dense=%0d (exp %0d), sparse=%0d (exp %0d)",
                         label, dense_cost, exp_dense, sparse_cost, exp_sparse);
                fail_count = fail_count + 1;
            end
        end
    endtask

    initial begin
        $dumpfile("cost_estimator_tb.vcd");
        $dumpvars(0, cost_estimator_tb);
        pass_count = 0; fail_count = 0;

        // zc=0: dense=160, sparse=16*12+25=217 → Dense wins
        zero_count = 0;  check_cost(160, 217, "zc=0");
        // zc=4: sparse=(16-4)*12+25=169 → Dense wins
        zero_count = 4;  check_cost(160, 169, "zc=4");
        // zc=5: sparse=(16-5)*12+25=157 → Sparse wins (breakeven)
        zero_count = 5;  check_cost(160, 157, "zc=5 (breakeven)");
        // zc=10: sparse=(16-10)*12+25=97 → Sparse wins
        zero_count = 10; check_cost(160, 97,  "zc=10");
        // zc=16: sparse=0*12+25=25 → Sparse wins
        zero_count = 16; check_cost(160, 25,  "zc=16");

        $display("CE TEST: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $finish;
    end
endmodule
