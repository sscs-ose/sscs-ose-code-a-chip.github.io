//**************************************************************************
Module      : dll_controller_acquire_track
Author      : Mythri Muralikannan
Description : Acquire/track DLL controller
//**************************************************************************

`timescale 1ps/1ps

module controller #(
    parameter integer CTRL_BITS        = 6,
    parameter integer INIT_CTRL        = 32,
    parameter integer ACQUIRE_STEP     = 4,
    parameter integer TRACK_STEP       = 1,
    parameter integer QUIET_CYCLES     = 8
)(
    input  wire                 clk_in,
    input  wire                 rst,
    input  wire                 up,
    input  wire                 down,
    output reg  [CTRL_BITS-1:0] ctrl
);

    localparam integer MAX_CTRL = (1 << CTRL_BITS) - 1;
    localparam [CTRL_BITS-1:0] ZERO_CTRL = {CTRL_BITS{1'b0}};
    localparam [CTRL_BITS-1:0] MAX_CTRL_VEC = MAX_CTRL[CTRL_BITS-1:0];

    localparam ACQUIRE = 1'b0;
    localparam TRACK   = 1'b1;

    reg mode;
    reg [$clog2(QUIET_CYCLES + 1)-1:0] quiet_count;

    integer step_size;
    integer next_ctrl;

    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            mode       <= ACQUIRE;
            quiet_count <= 0;

            if (INIT_CTRL < 0)
                ctrl <= ZERO_CTRL;
            else if (INIT_CTRL > MAX_CTRL)
                ctrl <= MAX_CTRL_VEC;
            else
                ctrl <= INIT_CTRL[CTRL_BITS-1:0];
        end else begin
            step_size = (mode == ACQUIRE) ? ACQUIRE_STEP : TRACK_STEP;

            case ({up, down})
                2'b10: begin
                    quiet_count <= 0;
                    next_ctrl   = ctrl + step_size;
                    if (next_ctrl > MAX_CTRL)
                        ctrl <= MAX_CTRL_VEC;
                    else
                        ctrl <= next_ctrl[CTRL_BITS-1:0];
                end

                2'b01: begin
                    quiet_count <= 0;
                    next_ctrl   = ctrl - step_size;
                    if (next_ctrl < 0)
                        ctrl <= ZERO_CTRL;
                    else
                        ctrl <= next_ctrl[CTRL_BITS-1:0];
                end

                default: begin
                    ctrl <= ctrl;
                    if (quiet_count < QUIET_CYCLES)
                        quiet_count <= quiet_count + 1'b1;
                end
            endcase

            if (quiet_count == QUIET_CYCLES - 1)
                mode <= TRACK;
        end
    end

endmodule