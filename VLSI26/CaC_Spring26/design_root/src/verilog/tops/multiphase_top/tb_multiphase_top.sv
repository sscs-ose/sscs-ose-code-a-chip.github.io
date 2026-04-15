`timescale 1ps/1ps

module tb_multiphase_top;

    // Parameters
    parameter CTRL_BITS = 6;
    parameter STAGES    = 8;

    parameter LOCK_STABLE_CYCLES = 50;
    parameter TIMEOUT_CYCLES     = 2000;

    // DUT signals
    reg clk_in;
    reg rst;

    wire clk_out;
    wire [STAGES-1:0] clk_phases;

    wire [CTRL_BITS-1:0] ctrl_dbg;
    wire up_dbg;
    wire down_dbg;
    wire shift_left_dbg;
    wire shift_right_dbg;

    // Instantiate DUT
    multiphase_top #(
        .CTRL_BITS (CTRL_BITS),
        .INIT_CTRL (32),
        .STAGES    (STAGES),
        .FB_INDEX  (STAGES/2)
    ) dut (
        .clk_in(clk_in),
        .rst(rst),

        .clk_out(clk_out),
        .clk_phases(clk_phases),

        .ctrl_dbg(ctrl_dbg),
        .up_dbg(up_dbg),
        .down_dbg(down_dbg),
        .shift_left_dbg(shift_left_dbg),
        .shift_right_dbg(shift_right_dbg)
    );

    // Clock generation (10ns period)
    initial clk_in = 0;
    always #5000 clk_in = ~clk_in;

    // Reset
    initial begin
        rst = 1;
        #20000;
        rst = 0;
    end

    // Wave dump
    initial begin
        $dumpfile("dll_selfcheck.vcd");
        $dumpvars(0, tb_multiphase_top);
    end

    // Lock detection logic
    integer cycle_count = 0;
    integer stable_count = 0;

    reg [CTRL_BITS-1:0] ctrl_prev;

    reg locked = 0;
    reg fail   = 0;

    always @(posedge clk_in) begin
        if (rst) begin
            cycle_count  <= 0;
            stable_count <= 0;
            ctrl_prev    <= 0;
            locked       <= 0;
            fail         <= 0;
        end
        else begin
            cycle_count <= cycle_count + 1;

            // Check stability condition
            if ((ctrl_dbg == ctrl_prev) && (up_dbg == 0) && (down_dbg == 0)) begin
                stable_count <= stable_count + 1;
            end
            else begin
                stable_count <= 0;
            end

            ctrl_prev <= ctrl_dbg;

            // Declare LOCK
            if (!locked && stable_count > LOCK_STABLE_CYCLES) begin
                locked <= 1;
                $display("========================================");
                $display(" DLL LOCKED at time %0t ps", $time);
                $display("   Cycles to lock: %0d", cycle_count);
                $display("   Final ctrl: %0d", ctrl_dbg);
                $display("========================================");
            end

            // Timeout FAIL
            if (!locked && cycle_count > TIMEOUT_CYCLES) begin
                fail <= 1;
                $display("========================================");
                $display(" DLL FAILED TO LOCK");
                $display("   Timeout cycles: %0d", TIMEOUT_CYCLES);
                $display("   Last ctrl: %0d", ctrl_dbg);
                $display("========================================");
                $finish;
            end
        end
    end

    // Phase sanity check
    integer toggle_count [0:STAGES-1];

    integer i;

    initial begin
        for (i = 0; i < STAGES; i = i + 1)
            toggle_count[i] = 0;
    end

    // Count toggles on each phase (event-based, no undersampling)
    reg [STAGES-1:0] prev_phases;

    always @(clk_phases) begin
        if (!rst) begin
            for (int j = 0; j < STAGES; j++) begin
                if (clk_phases[j] != prev_phases[j])
                    toggle_count[j]++;
            end
        end
        prev_phases = clk_phases;  // blocking is correct here
    end

    initial begin
        wait(locked || fail);

        #10000; // let it run a bit after lock

        if (locked) begin
            $display("\n Phase Activity Check:");

            for (i = 0; i < STAGES; i = i + 1) begin
                if (toggle_count[i] == 0) begin
                    $display("Phase %0d is NOT toggling!", i);
                    fail = 1;
                end
                else begin
                    $display("Phase %0d toggles (%0d times)", i, toggle_count[i]);
                end
            end

            if (!fail) begin
                $display("\nALL CHECKS PASSED");
            end
            else begin
                $display("\nSOME CHECKS FAILED");
            end
        end

        #10000;
        $finish;
    end

endmodule