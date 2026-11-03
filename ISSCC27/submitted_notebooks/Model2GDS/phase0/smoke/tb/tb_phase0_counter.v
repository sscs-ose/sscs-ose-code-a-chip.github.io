`timescale 1ns/1ps

module tb_phase0_counter;
    reg clk = 0;
    reg rst_n = 0;
    reg en = 0;
    wire [7:0] count;

    phase0_counter dut (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .count(count)
    );

    always #5 clk = ~clk;

    task expect_count(input [7:0] expected);
        begin
            #1;
            if (count !== expected) begin
                $display("PHASE0_SIM_FAIL expected=%0d got=%0d", expected, count);
                $fatal(1);
            end
        end
    endtask

    initial begin
        repeat (2) @(posedge clk);
        rst_n = 1;
        expect_count(0);

        en = 1;
        @(posedge clk); expect_count(1);
        @(posedge clk); expect_count(2);
        @(posedge clk); expect_count(3);

        en = 0;
        @(posedge clk); expect_count(3);

        en = 1;
        @(posedge clk); expect_count(4);

        $display("PHASE0_SIM_PASS");
        $finish;
    end
endmodule
