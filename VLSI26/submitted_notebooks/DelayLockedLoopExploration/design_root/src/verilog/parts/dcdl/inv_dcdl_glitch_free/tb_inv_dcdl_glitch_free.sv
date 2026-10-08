`timescale 1ns/1ps

module tb_inv_dcdl_glitch_free;

    logic clk;
    logic rst_n;
    logic A;
    logic [1:0] Q;
    logic Y;

    // DUT
    inv_dcdl_glitch_free dut (
        .clk(clk),
        .rst_n(rst_n),
        .A(A),
        .Q(Q),
        .Y(Y)
    );

    // Clock: 10ns period
    initial clk = 0;
    always #5 clk = ~clk;

    // Print signal changes only
    always @(A)
        $display("[%0t] A changed to %b | Q=%b", $time, A, Q);

    always @(Y)
        $display("[%0t] Y changed to %b | Q=%b", $time, Y, Q);

    // Apply one test case
    task run_case(input [1:0] q_val);
    begin
        $display("\n=======================");
        $display("Testing Q = %b", q_val);
        $display("=======================");

        Q = q_val;

        // Wait for select register
        @(posedge clk);

        // Toggle input high
        A = 1;
        @(posedge clk);

        // Toggle input low
        A = 0;
        @(posedge clk);
    end
    endtask

    // Main stimulus
    initial begin
        rst_n = 0;
        A     = 0;
        Q     = 2'b00;

        $dumpfile("inv_dcdl_glitch_free.vcd");
        $dumpvars(0, tb_inv_dcdl_glitch_free);

        // Reset
        repeat (2) @(posedge clk);
        rst_n = 1;
        @(posedge clk);

        // Run all select values
        run_case(2'b00);
        run_case(2'b01);
        run_case(2'b10);
        run_case(2'b11);

        $display("\nSimulation Done.");
        #10;
        $finish;
    end

endmodule