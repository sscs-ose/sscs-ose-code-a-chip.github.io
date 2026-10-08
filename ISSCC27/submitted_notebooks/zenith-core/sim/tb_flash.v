`default_nettype none
`timescale 1ns / 1ps

module tb_flash;
    localparam CLK_FREQ  = 27_000_000;
    localparam BAUD_RATE = 115_200;
    localparam real CLK_HALF_NS = 1.0e9 / CLK_FREQ / 2.0;
    localparam real BIT_NS      = 1.0e9 / BAUD_RATE;

    reg clk = 0, rst_n = 0, rx = 1;
    wire [7:0] gpio_out, gpio_dir, debug_pc, debug_state;
    wire [15:0] debug_instr;
    wire uart_tx_pin, pwm_pin, loader_active;

    microrv8_system #(.CLK_FREQ(CLK_FREQ), .BAUD_RATE(BAUD_RATE)) dut (
        .clk(clk), .rst_n(rst_n), .gpio_in(8'hA5),
        .gpio_out(gpio_out), .gpio_dir(gpio_dir),
        .uart_rx_pin(rx), .uart_tx_pin(uart_tx_pin), .pwm_pin(pwm_pin),
        .debug_pc(debug_pc), .debug_state(debug_state),
        .debug_instr(debug_instr), .loader_active(loader_active)
    );

    always #(CLK_HALF_NS) clk = ~clk;

    task send_byte(input [7:0] b);
        integer i;
        begin
            rx = 0; #(BIT_NS);
            for (i = 0; i < 8; i = i + 1) begin
                rx = b[i]; #(BIT_NS);
            end
            rx = 1; #(BIT_NS);
        end
    endtask

    reg [7:0] mem [0:1023];
    integer nbytes, run_us, k, dump_n;
    reg [1023:0] fname, vcdname;

    initial begin
        if (!$value$plusargs("BYTES=%s", fname))  fname = "prog.hex";
        if (!$value$plusargs("NBYTES=%d", nbytes)) nbytes = 0;
        if (!$value$plusargs("RUN_US=%d", run_us)) run_us = 200;
        if (!$value$plusargs("VCD=%s", vcdname))  vcdname = "tb_flash.vcd";
        $timeformat(-9, 1, " ns", 14);
        for (k = 0; k < 1024; k = k + 1) mem[k] = 8'h00;
        $readmemh(fname, mem, 0, nbytes - 1);

        $dumpfile(vcdname);
        $dumpvars(1, tb_flash);

        #200 rst_n = 1;
        #(2 * BIT_NS);
        $display("[%0t] Sending %0d bytes over UART at %0d baud", $time, nbytes, BAUD_RATE);
        for (k = 0; k < nbytes; k = k + 1) send_byte(mem[k]);
        $display("[%0t] Transfer done, loader_active=%b", $time, loader_active);
        if ($value$plusargs("DUMP_ROM=%d", dump_n))
            for (k = 0; k < dump_n; k = k + 1)
                $display("ROM[%0d] = %04h", k, dut.imem.rom[k]);
        #(run_us * 1000.0);
        $display("[%0t] End. gpio_out=0x%02h pc=%0d", $time, gpio_out, debug_pc);
        $finish;
    end

    always @(gpio_out)
        $display("[%0t] GPIO = 0x%02h (%0d)  pc=%0d", $time, gpio_out, gpio_out, debug_pc);
endmodule
`default_nettype wire
