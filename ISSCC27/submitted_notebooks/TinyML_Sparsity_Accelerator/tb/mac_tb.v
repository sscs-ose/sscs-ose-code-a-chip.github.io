`timescale 1ns / 1ps

module mac_tb;
    parameter DATA_WIDTH = 8;

    reg clk, rst_n, enable;
    reg signed [DATA_WIDTH-1:0] act, wt;
    wire signed [2*DATA_WIDTH-1:0] prod;

    integer pass_count, fail_count;

    mac #(.DATA_WIDTH(DATA_WIDTH)) uut (
        .clk(clk), .rst_n(rst_n), .enable(enable),
        .act(act), .wt(wt), .prod(prod)
    );

    always #10 clk = ~clk;

    task check_prod;
        input signed [2*DATA_WIDTH-1:0] expected;
        input [8*24-1:0] label;
        begin
            @(posedge clk); #1;
            if (prod === expected) begin
                $display("[PASS] %0s: prod=%0d", label, prod);
                pass_count = pass_count + 1;
            end else begin
                $display("[FAIL] %0s: prod=%0d (expected %0d)", label, prod, expected);
                fail_count = fail_count + 1;
            end
        end
    endtask

    initial begin
        $dumpfile("mac_tb.vcd");
        $dumpvars(0, mac_tb);

        clk = 0; rst_n = 0; enable = 0; act = 0; wt = 0;
        pass_count = 0; fail_count = 0;
        #40 rst_n = 1;

        // Test 1: 5 × (-4) = -20
        @(posedge clk); enable = 1; act = 8'sd5; wt = -8'sd4;
        check_prod(-16'sd20, "5 * -4");

        // Test 2: 10 × 3 = 30
        act = 8'sd10; wt = 8'sd3;
        check_prod(16'sd30, "10 * 3");

        // Test 3: Disable — should hold last value (30)
        enable = 0; act = 8'sd8; wt = 8'sd8;
        check_prod(16'sd30, "Hold on disable");

        // Test 4: -128 × 1 = -128
        enable = 1; act = -8'sd128; wt = 8'sd1;
        check_prod(-16'sd128, "-128 * 1");

        // Test 5: 127 × 127 = 16129
        act = 8'sd127; wt = 8'sd127;
        check_prod(16'sd16129, "127 * 127");

        // Test 6: -128 × -128 = 16384
        act = -8'sd128; wt = -8'sd128;
        check_prod(16'sd16384, "-128 * -128");

        #20;
        $display("MAC TEST: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $finish;
    end
endmodule
