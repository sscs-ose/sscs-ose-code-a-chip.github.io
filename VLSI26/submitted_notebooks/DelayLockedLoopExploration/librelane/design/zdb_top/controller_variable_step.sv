//**************************************************************************
// Module      : dll_controller_varstep
// Author      : Mythri Muralikannan
// Description : Variable-step DLL controller
//**************************************************************************


`timescale 1ps/1ps

module controller #(
    parameter integer CTRL_BITS   = 6,
    parameter integer INIT_CTRL   = 32,
    parameter integer BIG_STEP    = 4,
    parameter integer MED_STEP    = 2,
    parameter integer BIG_THRESH  = 8,
    parameter integer MED_THRESH  = 4
)(
    input  wire                 clk_in,
    input  wire                 rst,
    input  wire                 up,
    input  wire                 down,
    output reg  [CTRL_BITS-1:0] ctrl
);

    localparam integer MAX_CTRL = (1 << CTRL_BITS) - 1;
    localparam [CTRL_BITS-1:0] MAX_CTRL_VEC = MAX_CTRL[CTRL_BITS-1:0];
    localparam [CTRL_BITS-1:0] ZERO_CTRL    = {CTRL_BITS{1'b0}};

    reg [3:0] same_dir_count;
    reg       last_dir_up;  // 1 = up, 0 = down

    integer step_size;
    integer next_ctrl;

    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            same_dir_count <= 4'd0;
            last_dir_up    <= 1'b0;

            if (INIT_CTRL < 0)
                ctrl <= ZERO_CTRL;
            else if (INIT_CTRL > MAX_CTRL)
                ctrl <= MAX_CTRL_VEC;
            else
                ctrl <= INIT_CTRL[CTRL_BITS-1:0];
        end else begin
            if (up && !down) begin
                if (last_dir_up)
                    same_dir_count <= same_dir_count + 1'b1;
                else begin
                    same_dir_count <= 4'd1;
                    last_dir_up    <= 1'b1;
                end

                if (same_dir_count >= BIG_THRESH)
                    step_size = BIG_STEP;
                else if (same_dir_count >= MED_THRESH)
                    step_size = MED_STEP;
                else
                    step_size = 1;

                next_ctrl = ctrl + step_size;
                if (next_ctrl > MAX_CTRL)
                    ctrl <= MAX_CTRL_VEC;
                else
                    ctrl <= next_ctrl[CTRL_BITS-1:0];

            end else if (!up && down) begin
                if (!last_dir_up)
                    same_dir_count <= same_dir_count + 1'b1;
                else begin
                    same_dir_count <= 4'd1;
                    last_dir_up    <= 1'b0;
                end

                if (same_dir_count >= BIG_THRESH)
                    step_size = BIG_STEP;
                else if (same_dir_count >= MED_THRESH)
                    step_size = MED_STEP;
                else
                    step_size = 1;

                next_ctrl = ctrl - step_size;
                if (next_ctrl < 0)
                    ctrl <= ZERO_CTRL;
                else
                    ctrl <= next_ctrl[CTRL_BITS-1:0];

            end else begin
                same_dir_count <= 4'd0;
                ctrl           <= ctrl;
            end
        end
    end

endmodule