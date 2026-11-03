`timescale 1ns/1ps
module phase_generator_tb;
    reg clk=0;
    reg reset_n=0;
    wire a,b,valid;
    integer i;
    phase_generator #(.DIVIDER_BITS(4)) dut (
        .clk(clk), .reset_n(reset_n), .phase_a(a), .phase_b(b), .phase_valid(valid)
    );
    always #5 clk=~clk;
    initial begin
        #1 reset_n=1;
        #1 reset_n=0;
        #1;
        if (a !== 0 || b !== 0 || valid !== 0) $fatal(1,"reset outputs");
        @(negedge clk); reset_n=1;
        for (i=0;i<96;i=i+1) begin
            @(negedge clk);
            $display("SAMPLE %0d %0d %0d %0d",i,a,b,valid);
        end
        // Assert reset in the middle of a clock cycle; require immediate neutral validity.
        #2 reset_n=0;
        #1;
        if (a !== 0 || b !== 0 || valid !== 0) $fatal(1,"asynchronous brownout reset");
        @(negedge clk); reset_n=1;
        #1;
        if (a !== 1 || b !== 0 || valid !== 1) $fatal(1,"restart phase");
        $display("PASS");
        $finish;
    end
endmodule
