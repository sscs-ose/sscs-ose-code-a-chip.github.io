`timescale 1ps/1ps

//**************************************************************************
// Module      : tb_zdb_top
// Description : Functional testbench for zero-delay buffer top-level
//**************************************************************************

module tb_zdb_top;

    parameter integer CTRL_BITS = 6;
    parameter integer INIT_CTRL = 32;
    localparam integer MAX_CTRL = (1 << CTRL_BITS) - 1;

    reg clk_in;
    reg rst;

    wire clk_out;
    wire [CTRL_BITS-1:0] ctrl_dbg;
    wire up_dbg;
    wire down_dbg;
    wire shift_left_dbg;
    wire shift_right_dbg;

    integer errors;
    integer clk_in_edges;
    integer clk_out_edges;
    integer up_events;
    integer down_events;
    integer shift_left_events;
    integer shift_right_events;

    // DUT
    zdb_top #(
        .CTRL_BITS (CTRL_BITS),
        .INIT_CTRL (INIT_CTRL)
    ) dut (
        .clk_in          (clk_in),
        .rst             (rst),
        .clk_out         (clk_out),
        .ctrl_dbg        (ctrl_dbg),
        .up_dbg          (up_dbg),
        .down_dbg        (down_dbg),
        .shift_left_dbg  (shift_left_dbg),
        .shift_right_dbg (shift_right_dbg)
    );

    // Reference clock: 10 ns period

    initial begin
        clk_in = 1'b0;
        forever #5000 clk_in = ~clk_in;
    end

    // Edge/event counters

    always @(posedge clk_in)
        clk_in_edges = clk_in_edges + 1;

    always @(posedge clk_out)
        clk_out_edges = clk_out_edges + 1;

    always @(posedge up_dbg)
        up_events = up_events + 1;

    always @(posedge down_dbg)
        down_events = down_events + 1;

    always @(posedge shift_left_dbg)
        shift_left_events = shift_left_events + 1;

    always @(posedge shift_right_dbg)
        shift_right_events = shift_right_events + 1;

    // Monitor
    initial begin
        $display(" time   rst clk_in clk_out | up down shiftL shiftR | ctrl");
        $display("-------------------------------------------------------------");
        $monitor("%6t   %b    %b      %b    |  %b    %b     %b      %b   | %0d",
                 $time, rst, clk_in, clk_out,
                 up_dbg, down_dbg, shift_left_dbg, shift_right_dbg, ctrl_dbg);
    end

    // Helpers
    task expect_ctrl_exact;
        input integer expected;
        begin
            if (ctrl_dbg !== expected[CTRL_BITS-1:0]) begin
                $display("ERROR @ %0t: expected ctrl=%0d, got %0d",
                         $time, expected, ctrl_dbg);
                errors = errors + 1;
            end
        end
    endtask

    task expect_ctrl_in_range;
        begin
            if (ctrl_dbg > MAX_CTRL[CTRL_BITS-1:0]) begin
                $display("ERROR @ %0t: ctrl out of range, ctrl=%0d", $time, ctrl_dbg);
                errors = errors + 1;
            end
        end
    endtask

    task expect_known_outputs;
        begin
            if ((^clk_out === 1'bx) ||
                (^up_dbg === 1'bx) ||
                (^down_dbg === 1'bx) ||
                (^shift_left_dbg === 1'bx) ||
                (^shift_right_dbg === 1'bx) ||
                (^ctrl_dbg === 1'bx)) begin
                $display("ERROR @ %0t: unknown (X/Z) detected on outputs", $time);
                errors = errors + 1;
            end
        end
    endtask

    task wait_cycles;
        input integer n;
        integer k;
        begin
            for (k = 0; k < n; k = k + 1) begin
                @(posedge clk_in);
                #1;
                expect_ctrl_in_range();
                expect_known_outputs();
            end
        end
    endtask

    // Test sequence
    initial begin
        errors = 0;
        clk_in_edges      = 0;
        clk_out_edges     = 0;
        up_events         = 0;
        down_events       = 0;
        shift_left_events = 0;
        shift_right_events= 0;

        rst = 1'b1;

        // Check reset state
        #1;
        expect_ctrl_exact(INIT_CTRL);

        // Hold reset for a bit, then release
        #12000;
        rst = 1'b0;

        $display("\n=== TEST 1: Post-reset initialization ===");
        @(posedge clk_in);
        #1;
        expect_ctrl_exact(INIT_CTRL);

        $display("\n=== TEST 2: Functional run ===");
        wait_cycles(40);

        // Clock out should toggle during operation
        if (clk_out_edges == 0) begin
            $display("ERROR: clk_out did not toggle after reset release");
            errors = errors + 1;
        end

        $display("\n=== TEST 3: Observe loop activity ===");
        $display("clk_in edges       = %0d", clk_in_edges);
        $display("clk_out edges      = %0d", clk_out_edges);
        $display("UP events          = %0d", up_events);
        $display("DOWN events        = %0d", down_events);
        $display("shift_left events  = %0d", shift_left_events);
        $display("shift_right events = %0d", shift_right_events);

        // This is a soft functional expectation: at least some internal
        // activity should be visible in a working loop.
        if ((up_events + down_events) == 0) begin
            $display("WARNING: no phase-detector activity observed");
        end

        if ((shift_left_events + shift_right_events) == 0) begin
            $display("WARNING: no DCDL shift activity observed");
        end

        $display("\n=== TEST 4: Asynchronous reset ===");
        #3000;
        rst = 1'b1;
        #1;
        expect_ctrl_exact(INIT_CTRL);

        #7000;
        rst = 1'b0;
        wait_cycles(10);

        $display("\n======================================");
        if (errors == 0)
            $display("TEST PASSED");
        else
            $display("TEST FAILED: %0d error(s)", errors);
        $display("======================================");

        $finish;
    end

endmodule