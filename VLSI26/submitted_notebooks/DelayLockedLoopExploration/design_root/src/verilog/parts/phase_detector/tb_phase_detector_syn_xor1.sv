`timescale 1ps/1ps

module tb_phase_detector;

    reg clk_in;
    reg clk_out;
    reg rst;
    wire up;
    wire down;

    phase_detector dut (
        .clk_in(clk_in),
        .clk_out(clk_out),
        .rst(rst),
        .up(up),
        .down(down)
    );


    initial begin
        rst = 1'b1;
        #20000; // 20ns in picoseconds
        rst = 1'b0;
    end

    initial begin
        clk_in = 1'b0;
        #22000; // 22ns initial delay
        clk_in = 1'b1;
        forever #5000 clk_in = ~clk_in;
    end

    initial begin
        clk_out = 1'b0;
        #20000; // 20ns initial delay
        clk_in = 1'b1;
        forever #5000 clk_out = ~clk_out;
    end

    initial begin
        $dumpfile("tb_phase_detector_syn_xor1.vcd");
        $dumpvars(0, tb_phase_detector);

        #100000; // 100ns total simulation time
        $display("Simulation complete.");
        $finish;
    end

endmodule