`timescale 1ps/1ps

//**************************************************************************
// Module      : controller
// Author      : Mythri Muralikannan
// Description : Saturating up/down DLL controller
//**************************************************************************

module controller #(
    parameter integer CTRL_BITS = 6,
    parameter integer INIT_CTRL = 32
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

    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            if (INIT_CTRL < 0)
                ctrl <= ZERO_CTRL;
            else if (INIT_CTRL > MAX_CTRL)
                ctrl <= MAX_CTRL_VEC;
            else
                ctrl <= INIT_CTRL[CTRL_BITS-1:0];
        end
        else begin
            case ({up, down})
                2'b10: begin
                    if (ctrl < MAX_CTRL_VEC)
                        ctrl <= ctrl + 1'b1;
                end

                2'b01: begin
                    if (ctrl > ZERO_CTRL)
                        ctrl <= ctrl - 1'b1;
                end

                default: begin
                    ctrl <= ctrl;
                end
            endcase
        end
    end

endmodule