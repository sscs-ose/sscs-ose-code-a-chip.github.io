`timescale 1ns/1ps

module tb_zdb;

    localparam CLK_PERIOD        = 4;
    localparam CTRL_BITS         = 6;

    localparam INIT_CTRL         = 32;
    localparam DELAY_PS          = 700;
    localparam UPDATE_DIV_BITS   = 2; //MIN 2
    localparam RESET_DELAY_PS    = 20;
    localparam LOCK_COUNT_MAX    = 32;

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

    // ================= CLOCK =================
    initial begin
        clk_in = 0;
        #1.3;
        forever #(CLK_PERIOD/2.0) clk_in = ~clk_in;
    end

    initial begin
        rst = 1;
        #50;
        rst = 0;
    end

    // ================= VCD =================
    initial begin
        $dumpfile("zdb.vcd");
        $dumpvars(0, tb_zdb);

        // Explicitly dump key debug signals
        $dumpvars(0, phase_error);
        $dumpvars(0, t_ref_last);
        $dumpvars(0, t_ref_prev);
        $dumpvars(0, t_fb);
        $dumpvars(0, stable_count);
    end

    // ================= PHASE MEASUREMENT =================

    real t_ref_last = 0;
    real t_ref_prev = 0;
    real t_fb       = 0;
    real phase_error = 0;

    function real abs_real(input real x);
        abs_real = (x < 0) ? -x : x;
    endfunction

    // Track last TWO reference edges
    always @(posedge clk_in) begin
        t_ref_prev = t_ref_last;
        t_ref_last = $realtime;
    end

    // Compute phase error robustly
    always @(posedge clk_out) begin
        real err1, err2;

        t_fb = $realtime;

        err1 = t_fb - t_ref_last;
        err2 = t_fb - t_ref_prev;

        // Pick closest edge
        if (abs_real(err1) < abs_real(err2))
            phase_error = err1;
        else
            phase_error = err2;

        // Wrap into [-T/2, +T/2]
        if (phase_error > CLK_PERIOD/2.0)
            phase_error -= CLK_PERIOD;

        if (phase_error < -CLK_PERIOD/2.0)
            phase_error += CLK_PERIOD;
    end

    // ================= LOCK DETECTION =================

    integer stable_count = 0;
    integer print_div    = 0;
    real delay_ns = DELAY_PS * 1e-3;
    real tol = (1.5 * delay_ns < CLK_PERIOD * 0.25) ? 1.5 * delay_ns :
CLK_PERIOD * 0.25;

    always @(posedge clk_in) begin
        print_div = print_div + 1;

        if (print_div % 10 == 0) begin
            $display("t=%0t ctrl=%0d phase_err=%0.4f ns",
                     $time, dut.ctrl_dbg, phase_error);
        end

        // Better lock condition (relative to clock)
        if (abs_real(phase_error) <  tol)  begin
            stable_count = stable_count + 1;
        end else begin
            stable_count = 0;
        end

        if (stable_count > LOCK_COUNT_MAX) begin
            $display("====================================");
            $display("LOCK ACHIEVED at t=%0t", $time);
            $display("Final phase error = %0.4f ns", phase_error);
            $display("Final ctrl = %0d", dut.ctrl_dbg);
            $display("====================================");
            #20;
            $finish;
        end
    end

    // ================= TIMEOUT =================

    initial begin
        #100000;
        $display("====================================");
        $display("FAIL: Did not lock");
        $display("====================================");
        $finish;
    end

endmodule