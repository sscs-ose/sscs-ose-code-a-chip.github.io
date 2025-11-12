// This testbench simulates the core_rc module and verifies its functionality
// in both pass-through (recompute_needed = 0) and recomputation (recompute_needed = 1) modes.

`timescale 1ns/1ps

module core_rc_tb;

    // Parameters for the DUT (Device Under Test)
    // These must match the parameters of the core_rc module.
    parameter IN_DATA_WIDTH = 24;
    parameter OUT_DATA_WIDTH = 24;
    parameter RECOMPUTE_FIFO_DEPTH = 16;
    parameter RETIMING_REG_NUM = 4;
    parameter RECOMPUTE_SCALE_WIDTH = 24;
    parameter RECOMPUTE_SHIFT_WIDTH = 5;

    // Testbench signals (reg) and wires
    reg clk;
    reg rst_n;
    reg recompute_needed;
    reg [RECOMPUTE_SCALE_WIDTH - 1:0] rc_scale;
    reg rc_scale_vld;
    reg rc_scale_clear;
    reg [RECOMPUTE_SHIFT_WIDTH - 1:0] rms_rc_shift;
    reg [IN_DATA_WIDTH - 1:0] in_data;
    reg in_data_vld;

    wire [OUT_DATA_WIDTH - 1:0] out_data;
    wire out_data_vld;
    wire error;

    // Instantiate the Device Under Test (DUT)
    core_rc #(
        .IN_DATA_WIDTH(IN_DATA_WIDTH),
        .OUT_DATA_WIDTH(OUT_DATA_WIDTH),
        .RECOMPUTE_FIFO_DEPTH(RECOMPUTE_FIFO_DEPTH),
        .RETIMING_REG_NUM(RETIMING_REG_NUM)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .recompute_needed(recompute_needed),
        .rc_scale(rc_scale),
        .rc_scale_vld(rc_scale_vld),
        .rc_scale_clear(rc_scale_clear),
        .rms_rc_shift(rms_rc_shift),
        .in_data(in_data),
        .in_data_vld(in_data_vld),
        .out_data(out_data),
        .out_data_vld(out_data_vld),
        .error(error)
    );

    // Clock generation
    initial begin
        clk = 0;
        forever #5 clk = ~clk; // 10 ns period
    end

    // VCD (Value Change Dump) extraction for waveform viewing
    initial begin
        $dumpfile("core_rc.vcd");
        $dumpvars(0, core_rc_tb);
    end

    task automatic wait_for_out(
    output logic [OUT_DATA_WIDTH-1:0] val,
    input  integer timeout
    );
    integer t;
    begin
        t = timeout;
        while (t > 0 && !out_data_vld) begin
        @(posedge clk);
        t = t - 1;
        end
        if (!out_data_vld) $display("Timeout waiting for out_data_vld");
        val = out_data;
    end
    endtask

    // Storage for captured outputs
    logic [OUT_DATA_WIDTH-1:0] got [0:3];

    // Main test scenario
    initial begin
        // 1. Initial Reset
        $display("Starting simulation...");
        rst_n = 1'b0;
        recompute_needed = 1'b0;
        rc_scale_vld = 1'b0;
        rc_scale_clear = 1'b0;
        in_data_vld = 1'b0;
        #10;
        rst_n = 1'b1;
        $display("Reset released.");

        // 2. Test Scenario: No Recompute (Pass-through)
        $display("\n--- Testing No Recompute (Pass-through) Mode ---");
        recompute_needed = 1'b0;
        
        // Pass a few data points and check for 1-cycle latency
        @(posedge clk);
        in_data = 24'hA5A5A5;
        in_data_vld = 1'b1;
        $display("Time %0t: Sending data: %h, Expecting output after 1 cycle", $time, in_data);

        @(posedge clk); // Wait one cycle for latency
        in_data_vld = 1'b1;
        in_data = 24'hFFFFFE; // Next data
        $display("Time %0t: Checking output for previous data", $time);
        if (out_data_vld == 1'b1 && out_data == 24'hA5A5A5) begin
            $display("Time %0t: Pass-through success for A5A5A5", $time);
        end else begin
            $display("Time %0t: Pass-through FAILED for A5A5A5. Got %h, Expected A5A5A5", $time, out_data);
        end

        @(posedge clk);
        in_data_vld = 1'b1;
        in_data = 24'h0001FF; // Next data
        $display("Time %0t: Checking output for previous data", $time);
        if (out_data_vld == 1'b1 && out_data == 24'hFFFFFE) begin
            $display("Time %0t: Pass-through success for FFFFFE", $time);
        end else begin
            $display("Time %0t: Pass-through FAILED for FFFFFE. Got %h, Expected FFFFFE", $time, out_data);
        end
        
        @(posedge clk);
        in_data_vld = 1'b0; // End of this sequence
        $display("Time %0t: Checking output for previous data", $time);
        if (out_data_vld == 1'b1 && out_data == 24'h0001FF) begin
            $display("Time %0t: Pass-through success for 0001FF", $time);
        end else begin
            $display("Time %0t: Pass-through FAILED for 0001FF. Got %h, Expected 0001FF", $time, out_data);
        end
        @(posedge clk); // Give some idle time
        

        // After pass-through
        @(posedge clk);
        rst_n = 0; @(posedge clk); @(posedge clk);
        rst_n = 1; @(posedge clk);

        // 3. Test Scenario: With Recompute
        $display("\n--- Testing With Recompute Mode ---");
        recompute_needed = 1'b1;
        rc_scale = 24'd12345;
        rms_rc_shift = 5'd3;
        
        // Load the scale factor
        rc_scale_vld = 1'b1;
        @(posedge clk);
        rc_scale_vld = 1'b0;
        $display("Time %0t: Scale factor %d and shift %d are being loaded.", $time, rc_scale, rms_rc_shift);
        
        // Let the FIFO fill with some data
        @(posedge clk);
        in_data = 24'h100000; // Data point 1
        in_data_vld = 1'b1;
        
        @(posedge clk);
        in_data = 24'h200000; // Data point 2
        
        @(posedge clk);
        in_data = 24'h300000; // Data point 3
        
        @(posedge clk);
        in_data = 24'h400000; // Data point 4
        @(posedge clk);
        in_data_vld = 1'b0;

        wait_for_out(got[0], 100);
        @(posedge clk);
        wait_for_out(got[1], 100);
        @(posedge clk);
        wait_for_out(got[2], 100);
        @(posedge clk);
        wait_for_out(got[3], 100);

        $display("Recompute outs: %h %h %h %h", got[0], got[1], got[2], got[3]);

        // Wait to make sure the recomputation pipeline drains
        repeat(10) @(posedge clk);

        $display("\nSimulation finished.");
        $finish;
    end
endmodule
