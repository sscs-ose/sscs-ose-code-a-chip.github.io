`timescale 1ps/1ps

module tb_tdc_top;

    // Parameters
    parameter STAGES = 8;
    parameter CLK_PERIOD = 10000; // 10ns

    // DUT signals
    reg clk_in;
    reg rst;
    reg event_in;  

    wire [$clog2(STAGES)-1:0] tdc_out;

    // DUT
    tdc_top #(
        .STAGES(STAGES)
    ) dut (
        .clk_in(clk_in),
        .rst(rst),
        .event_in(event_in), 
        .tdc_out(tdc_out)
    );

    // Clock generation
    initial clk_in = 0;
    always #(CLK_PERIOD/2) clk_in = ~clk_in;

    // Reset
    initial begin
        rst = 1;
        event_in = 0;
        #20000;
        rst = 0;
    end

    // Wave dump
    initial begin
        $dumpfile("tdc.vcd");
        $dumpvars(0, tb_tdc_top);
    end

    integer i;
    integer errors = 0;

    reg [$clog2(STAGES)-1:0] prev_code;

    initial begin
        wait(!rst);

        $display("\n========================================");
        $display("Starting TDC sweep test");
        $display("========================================");

        prev_code = 0;

        // Sweep event across full clock period
        for (i = 0; i < CLK_PERIOD; i += (CLK_PERIOD / (STAGES*4))) begin

            @(posedge clk_in);

            // Generate event at controlled offset
            #(i);
            event_in = 1;
            #1;
            event_in = 0;

            // Wait for sampling to settle
            #100;

            $display("Offset = %0d ps → TDC = %0d", i, tdc_out);

            // ---------------------------------
            // CHECK: Monotonic increase
            // ---------------------------------
            if (tdc_out < prev_code) begin
                $display("ERROR: Non-monotonic output!");
                $display("   prev = %0d, curr = %0d", prev_code, tdc_out);
                errors++;
            end

            prev_code = tdc_out;
        end

        // -----------------------------------------
        // Final result
        // -----------------------------------------
        $display("\n========================================");

        if (errors == 0) begin
            $display("ALL TDC CHECKS PASSED");
        end else begin
            $display("TDC FAILED with %0d errors", errors);
        end

        $display("========================================");

        #10000;
        $finish;
    end

endmodule