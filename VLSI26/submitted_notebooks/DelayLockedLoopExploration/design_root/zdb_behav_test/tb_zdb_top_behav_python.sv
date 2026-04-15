`timescale 1ns/1ps

module tb_zdb;

    // ===============================
    // Default parameters (overridable)
    // ===============================

`ifndef CLK_PERIOD
`define CLK_PERIOD 4
`endif

`ifndef CTRL_BITS
`define CTRL_BITS 6
`endif

`ifndef INIT_CTRL
`define INIT_CTRL 32
`endif

`ifndef DELAY_PS
`define DELAY_PS 700
`endif

`ifndef UPDATE_DIV_BITS
`define UPDATE_DIV_BITS 2
`endif

`ifndef RESET_DELAY_PS
`define RESET_DELAY_PS 20
`endif

`ifndef LOCK_COUNT_MAX
`define LOCK_COUNT_MAX 32
`endif

    // Convert macros → localparams
    localparam CLK_PERIOD        = `CLK_PERIOD;
    localparam CTRL_BITS         = `CTRL_BITS;

    localparam INIT_CTRL         = `INIT_CTRL;
    localparam DELAY_PS          = `DELAY_PS;
    localparam UPDATE_DIV_BITS   = `UPDATE_DIV_BITS;
    localparam RESET_DELAY_PS    = `RESET_DELAY_PS;
    localparam LOCK_COUNT_MAX    = `LOCK_COUNT_MAX;

    // ===============================
    // DUT signals
    // ===============================
    reg clk_in;
    reg rst;

    wire clk_out;
    wire locked;

    zdb_top #(
        .CTRL_BITS       (CTRL_BITS),
        .INIT_CTRL       (INIT_CTRL),
        .DELAY_PS        (DELAY_PS),
        .UPDATE_DIV_BITS (UPDATE_DIV_BITS),
        .RESET_DELAY_PS  (RESET_DELAY_PS),
        .LOCK_COUNT_MAX  (LOCK_COUNT_MAX)
    ) dut (
        .clk_in (clk_in),
        .rst    (rst),
        .clk_out(clk_out),
        .locked (locked),
        .ctrl_dbg()
    );

    task print_config;
        $display("====================================");
        $display("SIMULATION CONFIGURATION");
        $display("CLK_PERIOD        = %0d", CLK_PERIOD);
        $display("CTRL_BITS         = %0d", CTRL_BITS);
        $display("INIT_CTRL         = %0d", INIT_CTRL);
        $display("DELAY_PS          = %0d", DELAY_PS);
        $display("UPDATE_DIV_BITS   = %0d", UPDATE_DIV_BITS);
        $display("RESET_DELAY_PS    = %0d", RESET_DELAY_PS);
        $display("LOCK_COUNT_MAX    = %0d", LOCK_COUNT_MAX);
    `ifdef SIM_TIMEOUT
        $display("SIM_TIMEOUT       = %0d", `SIM_TIMEOUT);
    `else
        $display("SIM_TIMEOUT       = default");
    `endif
        $display("====================================");
    endtask

    // ===============================
    // Clock generation
    // ===============================
    initial begin
        clk_in = 0;
        #1.3;
        forever #(CLK_PERIOD/2.0) clk_in = ~clk_in;
    end

    // ===============================
    // Reset
    // ===============================
    initial begin
        rst = 1;
        #50;
        rst = 0;
    end

    // ===============================
    // Wave dump
    // ===============================
    initial begin
        $dumpfile("zdb.vcd");
        $dumpvars(0, tb_zdb);
        $dumpvars(0, phase_error);
    end

    // ===============================
    // Phase measurement
    // ===============================
    real t_ref_last;
    real phase_error;

    function real abs_real(input real x);
        abs_real = (x < 0) ? -x : x;
    endfunction

    always @(posedge clk_in)
        t_ref_last = $realtime;

    always @(posedge clk_out) begin
        real t_fb;
        t_fb = $realtime;

        phase_error = t_fb - t_ref_last;

        if (phase_error > CLK_PERIOD/2.0)
            phase_error -= CLK_PERIOD;

        if (phase_error < -CLK_PERIOD/2.0)
            phase_error += CLK_PERIOD;
    end

    // ===============================
    // Lock detection
    // ===============================
    integer stable_count = 0;
    integer print_div    = 0;

    real delay_ns = DELAY_PS * 1e-3;
    real tol = 1.5 * (delay_ns);  // 1.5 × delay step 

    always @(posedge clk_in) begin
        print_div = print_div + 1;

        if (print_div % 10 == 0) begin
            $display("t=%0t ctrl=%0d phase_err=%0.3f",
                     $time, dut.ctrl_dbg, phase_error);
        end

        if (abs_real(phase_error) <  tol) begin  // Minimum possible delay
            stable_count = stable_count + 1;
        end else begin
            stable_count = 0;
        end

        if (stable_count > LOCK_COUNT_MAX) begin
            $display("====================================");
            $display("LOCK ACHIEVED at t=%0t", $time);
            $display("Final phase error = %0.3f ns", phase_error);
            $display("Final ctrl = %0d", dut.ctrl_dbg);
            print_config();   // Prints chosen config
            $display("====================================");
            #20;
            $finish;
        end
    end

    // ===============================
    // Timeout
    // ===============================
`ifndef SIM_TIMEOUT
`define SIM_TIMEOUT 100000
`endif

    initial begin
        #(`SIM_TIMEOUT);
        $display("====================================");
        $display("FAIL: Did not lock");
        print_config();  
        $display("====================================");
        $finish;
    end

endmodule