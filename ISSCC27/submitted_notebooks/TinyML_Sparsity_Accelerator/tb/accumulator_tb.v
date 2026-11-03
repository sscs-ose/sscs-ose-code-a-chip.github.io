`timescale 1ns / 1ps

module accumulator_tb;
    parameter IN_WIDTH  = 16;
    parameter ACC_WIDTH = 32;

    reg clk, rst_n, clear, enable;
    reg signed [IN_WIDTH-1:0] din;
    wire signed [ACC_WIDTH-1:0] acc_out;

    integer pass_count, fail_count;

    accumulator #(.IN_WIDTH(IN_WIDTH), .ACC_WIDTH(ACC_WIDTH)) uut (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .enable(enable), .din(din), .acc_out(acc_out)
    );

    always #10 clk = ~clk;

    task check_acc;
        input signed [ACC_WIDTH-1:0] expected;
        input [8*24-1:0] label;
        begin
            @(posedge clk); #1;
            if (acc_out === expected) begin
                $display("[PASS] %0s: acc=%0d", label, acc_out);
                pass_count = pass_count + 1;
            end else begin
                $display("[FAIL] %0s: acc=%0d (expected %0d)", label, acc_out, expected);
                fail_count = fail_count + 1;
            end
        end
    endtask

    initial begin
        $dumpfile("accumulator_tb.vcd");
        $dumpvars(0, accumulator_tb);

        clk = 0; rst_n = 0; clear = 0; enable = 0; din = 0;
        pass_count = 0; fail_count = 0;
        #40 rst_n = 1;

        // Accumulate 10
        @(posedge clk); enable = 1; din = 16'sd10;
        check_acc(32'sd10, "Acc += 10");

        // Accumulate 20 → 30
        din = 16'sd20;
        check_acc(32'sd30, "Acc += 20 = 30");

        // Disable — hold at 30
        enable = 0; din = 16'sd99;
        check_acc(32'sd30, "Hold on disable");

        // Clear
        enable = 0; clear = 1;
        check_acc(32'sd0, "Clear");
        clear = 0;

        // Accumulate negative: -15
        enable = 1; din = -16'sd15;
        check_acc(-32'sd15, "Acc += -15");

        // Accumulate 15 → 0
        din = 16'sd15;
        check_acc(32'sd0, "Acc += 15 = 0");

        #20;
        $display("ACC TEST: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $finish;
    end
endmodule
