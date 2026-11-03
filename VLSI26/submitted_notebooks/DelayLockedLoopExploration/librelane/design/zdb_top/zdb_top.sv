`timescale 1ps/1ps

//**************************************************************************
// Module      : zdb_top
// Author      : Mythri Muralikannan
// Description : Zero-Delay Buffer (ZDB) top-level wrapper
//**************************************************************************

module zdb_top #(
    parameter integer CTRL_BITS = 6,
    parameter integer INIT_CTRL = 32
)(
    input  wire                 clk_in,
    input  wire                 rst,
    output wire                 clk_out,

    // Debug / visibility signals
    output wire [CTRL_BITS-1:0] ctrl_dbg,
    output wire                 up_dbg,
    output wire                 down_dbg,
    output wire                 shift_left_dbg,
    output wire                 shift_right_dbg
);


    // Internal Signals
    wire [CTRL_BITS-1:0] ctrl;
    wire up;
    wire down;

    reg  [CTRL_BITS-1:0] ctrl_d;
    wire shift_left;
    wire shift_right;

    wire dcdl_clk;

    // Phase detector
    phase_detector u_pd (
        .clk_in  (clk_in),
        .clk_out (clk_out),
        .rst     (rst),
        .up      (up),
        .down    (down)
    );

    // Controller
    controller #(
        .CTRL_BITS (CTRL_BITS),
        .INIT_CTRL (INIT_CTRL)
    ) u_controller (
        .clk_in (clk_in),
        .rst    (rst),
        .up     (up),
        .down   (down),
        .ctrl   (ctrl)
    );

    // If ctrl increased relative to previous cycle, generate shift_left.
    // If ctrl decreased, generate shift_right.
    always @(posedge clk_in or posedge rst) begin
        if (rst)
            ctrl_d <= INIT_CTRL[CTRL_BITS-1:0];
        else
            ctrl_d <= ctrl;
    end

    assign shift_left  = (ctrl > ctrl_d);
    assign shift_right = (ctrl < ctrl_d);

    // Declare DCDL
    nand_dcdl_top u_dcdl_top (
        .clk         (clk_in),
        .rst_n       (~rst),
        .shift_left  (shift_left),
        .shift_right (shift_right),
        .A           (clk_in),
        .Y           (dcdl_clk)
    );

    assign clk_out = dcdl_clk;

    // Debug outputs
    assign ctrl_dbg        = ctrl;
    assign up_dbg          = up;
    assign down_dbg        = down;
    assign shift_left_dbg  = shift_left;
    assign shift_right_dbg = shift_right;

endmodule