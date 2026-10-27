`timescale 1ns / 1ps

module zero_detector_tb;
    parameter DATA_WIDTH = 8;

    reg [DATA_WIDTH-1:0] act, wt;
    wire is_zero;

    integer pass_count, fail_count;

    zero_detector #(.DATA_WIDTH(DATA_WIDTH)) uut (
        .act(act), .wt(wt), .is_zero(is_zero)
    );

    task check_zd;
        input expected;
        input [8*24-1:0] label;
        begin
            #1;
            if (is_zero === expected) begin
                $display("[PASS] %0s: is_zero=%b", label, is_zero);
                pass_count = pass_count + 1;
            end else begin
                $display("[FAIL] %0s: is_zero=%b (expected %b)", label, is_zero, expected);
                fail_count = fail_count + 1;
            end
        end
    endtask

    initial begin
        $dumpfile("zero_detector_tb.vcd");
        $dumpvars(0, zero_detector_tb);
        pass_count = 0; fail_count = 0;

        act = 8'd5;  wt = 8'd3;  check_zd(1'b0, "Both non-zero");
        act = 8'd0;  wt = 8'd3;  check_zd(1'b1, "Act zero");
        act = 8'd5;  wt = 8'd0;  check_zd(1'b1, "Wt zero");
        act = 8'd0;  wt = 8'd0;  check_zd(1'b1, "Both zero");
        act = 8'hFF; wt = 8'hFF; check_zd(1'b0, "Both 0xFF (-1)");
        act = 8'h80; wt = 8'd1;  check_zd(1'b0, "-128 and 1");

        $display("ZD TEST: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $finish;
    end
endmodule
