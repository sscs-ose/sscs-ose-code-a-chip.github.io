`timescale 1ns/1ps

module tb_phase_detector;

    reg  clk_in;
    reg  clk_out;
    reg  rst;
    wire up;
    wire down;

    integer error_count;
    integer sample_count;
    integer up_count;
    integer down_count;
    integer both_count;
    integer idle_count;

    reg [8*64-1:0] case_name;
    reg sampling_enable;

    // DUT: compile this testbench with exactly one phase_detector implementation
    phase_detector dut (
        .clk_in  (clk_in),
        .clk_out (clk_out),
        .rst     (rst),
        .up      (up),
        .down    (down)
    );

    // ------------------------------------------------------------
    // Scoreboard control
    // ------------------------------------------------------------
    task start_scoreboard;
        input [8*64-1:0] name;
        begin
            case_name       = name;
            sample_count    = 0;
            up_count        = 0;
            down_count      = 0;
            both_count      = 0;
            idle_count      = 0;
            sampling_enable = 1'b1;
            $display("\n=== %0s ===", name);
        end
    endtask

    task stop_scoreboard;
        begin
            sampling_enable = 1'b0;
            $display("SUMMARY %0s: samples=%0d up=%0d down=%0d both=%0d idle=%0d",
                     case_name, sample_count, up_count, down_count, both_count, idle_count);
        end
    endtask

    // ------------------------------------------------------------
    // Background sampler
    // ------------------------------------------------------------
    always begin
        #1;
        if (sampling_enable) begin
            sample_count = sample_count + 1;

            if (up && down)
                both_count = both_count + 1;
            else if (up)
                up_count = up_count + 1;
            else if (down)
                down_count = down_count + 1;
            else
                idle_count = idle_count + 1;
        end
    end

    // ------------------------------------------------------------
    // Checks
    // ------------------------------------------------------------
    task check_reset_clears_outputs;
        begin
            #0.1;
            if (up !== 1'b0 || down !== 1'b0) begin
                $display("ERROR @ %0t: reset did not clear outputs: up=%b down=%b",
                         $time, up, down);
                error_count = error_count + 1;
            end
        end
    endtask

    task check_aligned_behavior;
        begin
            stop_scoreboard();

            // Aligned clocks should not show strong one-sided bias.
            if (up_count > (sample_count/2)) begin
                $display("ERROR: aligned clocks showed excessive UP activity");
                error_count = error_count + 1;
            end

            if (down_count > (sample_count/2)) begin
                $display("ERROR: aligned clocks showed excessive DOWN activity");
                error_count = error_count + 1;
            end
        end
    endtask

    task check_lag_behavior;
        begin
            stop_scoreboard();

            // clk_out lags clk_in => UP should dominate
            if (up_count <= down_count) begin
                $display("ERROR: lag case did not show UP dominance");
                error_count = error_count + 1;
            end
        end
    endtask

    task check_lead_behavior;
        begin
            stop_scoreboard();

            // clk_out leads clk_in => DOWN should dominate
            if (down_count <= up_count) begin
                $display("ERROR: lead case did not show DOWN dominance");
                error_count = error_count + 1;
            end
        end
    endtask

    // ------------------------------------------------------------
    // Utility: generate N cycles with phase offset
    // Positive phase_ns => clk_out lags clk_in
    // Negative phase_ns => clk_out leads clk_in
    // ------------------------------------------------------------
    task run_cycles;
        input integer cycles;
        input integer phase_ns;
        input integer period_ns;
        integer i;
        integer half;
        integer abs_phase;
        begin
            half = period_ns / 2;
            abs_phase = (phase_ns < 0) ? -phase_ns : phase_ns;

            for (i = 0; i < cycles; i = i + 1) begin
                if (phase_ns >= 0) begin
                    // clk_in leads, clk_out lags
                    clk_in = 1'b1;
                    #(abs_phase);
                    clk_out = 1'b1;
                    #(half - abs_phase);

                    clk_in = 1'b0;
                    #(abs_phase);
                    clk_out = 1'b0;
                    #(half - abs_phase);
                end
                else begin
                    // clk_out leads, clk_in lags
                    clk_out = 1'b1;
                    #(abs_phase);
                    clk_in = 1'b1;
                    #(half - abs_phase);

                    clk_out = 1'b0;
                    #(abs_phase);
                    clk_in = 1'b0;
                    #(half - abs_phase);
                end
            end
        end
    endtask

    // ------------------------------------------------------------
    // Utility: perfectly aligned clocks
    // ------------------------------------------------------------
    task run_aligned_cycles;
        input integer cycles;
        input integer period_ns;
        integer i;
        integer half;
        begin
            half = period_ns / 2;
            for (i = 0; i < cycles; i = i + 1) begin
                clk_in  = 1'b1;
                clk_out = 1'b1;
                #(half);
                clk_in  = 1'b0;
                clk_out = 1'b0;
                #(half);
            end
        end
    endtask

    // ------------------------------------------------------------
    // Optional monitor
    // ------------------------------------------------------------
    initial begin
        $display(" time   rst clk_in clk_out | up down ");
        $display("--------------------------------------");
        $monitor("%5t   %b     %b      %b    |  %b    %b",
                 $time, rst, clk_in, clk_out, up, down);
    end

    // ------------------------------------------------------------
    // Stimulus
    // ------------------------------------------------------------
    initial begin
        error_count    = 0;
        sample_count   = 0;
        up_count       = 0;
        down_count     = 0;
        both_count     = 0;
        idle_count     = 0;
        sampling_enable= 1'b0;

        clk_in  = 1'b0;
        clk_out = 1'b0;
        rst     = 1'b1;

        // Initial reset
        #1;
        check_reset_clears_outputs();

        #9;
        rst = 1'b0;

        // Case 1: aligned clocks
        start_scoreboard("CASE 1: aligned clocks");
        run_aligned_cycles(6, 10);
        check_aligned_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 2: clk_out lags clk_in by 2ns
        start_scoreboard("CASE 2: clk_out lags clk_in by 2 ns");
        run_cycles(8, 2, 10);
        check_lag_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 3: clk_out leads clk_in by 2ns
        start_scoreboard("CASE 3: clk_out leads clk_in by 2 ns");
        run_cycles(8, -2, 10);
        check_lead_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 4: small lag near lock
        start_scoreboard("CASE 4: small lag near lock (1 ns)");
        run_cycles(8, 1, 10);
        check_lag_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 5: small lead near lock
        start_scoreboard("CASE 5: small lead near lock (1 ns)");
        run_cycles(8, -1, 10);
        check_lead_behavior();

        // Case 6: asynchronous reset
        start_scoreboard("CASE 6: asynchronous reset");
        #7;
        rst = 1'b1;
        check_reset_clears_outputs();
        #8;
        rst = 1'b0;
        run_aligned_cycles(4, 10);
        check_aligned_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 7: large lag (4 ns in 10 ns period — near half-cycle)
        start_scoreboard("CASE 7: large lag (4 ns, near half-period)");
        run_cycles(8, 4, 10);
        check_lag_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 8: large lead (4 ns in 10 ns period)
        start_scoreboard("CASE 8: large lead (4 ns, near half-period)");
        run_cycles(8, -4, 10);
        check_lead_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 9: lag with longer period (20 ns clock, 3 ns offset)
        start_scoreboard("CASE 9: lag 3 ns, period 20 ns");
        run_cycles(8, 3, 20);
        check_lag_behavior();

        // Idle gap
        #20;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 10: lead with longer period (20 ns clock, 3 ns offset)
        start_scoreboard("CASE 10: lead 3 ns, period 20 ns");
        run_cycles(8, -3, 20);
        check_lead_behavior();

        // Idle gap
        #20;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 11: reset during active lag run, then resume
        start_scoreboard("CASE 11: reset mid-lag then resume");
        run_cycles(4, 2, 10);
        rst = 1'b1;
        check_reset_clears_outputs();
        #5;
        rst = 1'b0;
        run_cycles(4, 2, 10);
        check_lag_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 12: extended run with consistent lag (16 cycles) — checks sustained behavior
        start_scoreboard("CASE 12: sustained lag 2 ns, 16 cycles");
        run_cycles(16, 2, 10);
        check_lag_behavior();

        // Idle gap
        #10;
        clk_in  = 1'b0;
        clk_out = 1'b0;

        // Case 13: extended run with consistent lead (16 cycles)
        start_scoreboard("CASE 13: sustained lead 2 ns, 16 cycles");
        run_cycles(16, -2, 10);
        check_lead_behavior();

        if (error_count == 0) begin
            $display("\n======================================");
            $display("TEST PASSED");
            $display("======================================");
        end
        else begin
            $display("\n======================================");
            $display("TEST FAILED: %0d error(s)", error_count);
            $display("======================================");
        end

        #10;
        $finish;
    end

endmodule
