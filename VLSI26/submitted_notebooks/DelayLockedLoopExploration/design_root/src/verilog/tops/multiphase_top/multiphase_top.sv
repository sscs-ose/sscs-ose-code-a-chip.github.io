
`timescale 1ps/1ps

module multiphase_top #(
    parameter integer CTRL_BITS = 6,
    parameter integer INIT_CTRL = 32,
    parameter integer STAGES    = 8,
    parameter integer FB_INDEX  = STAGES/2   // feedback phase
)(
    input  wire clk_in,
    input  wire rst,

    output wire clk_out,
    output wire [STAGES-1:0] clk_phases,

    // Debug
    output wire [CTRL_BITS-1:0] ctrl_dbg,
    output wire up_dbg,
    output wire down_dbg,
    output wire shift_left_dbg,
    output wire shift_right_dbg
);

    wire [CTRL_BITS-1:0] ctrl;
    wire up, down;

    reg  [CTRL_BITS-1:0] ctrl_d;
    wire shift_left, shift_right;

    wire [STAGES-1:0] phases;

    // -------------------------
    // Phase detector
    // -------------------------
    phase_detector u_pd (
        .clk_in  (clk_in),
        .clk_out (clk_out),
        .rst     (rst),
        .up      (up),
        .down    (down)
    );

    // -------------------------
    // Controller
    // -------------------------
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

    // -------------------------
    // ctrl → shift pulses
    // -------------------------
    always @(posedge clk_in or posedge rst) begin
        if (rst)
            ctrl_d <= INIT_CTRL[CTRL_BITS-1:0];
        else
            ctrl_d <= ctrl;
    end

    assign shift_left  = (ctrl > ctrl_d);
    assign shift_right = (ctrl < ctrl_d);

    // -------------------------
    // Multiphase DCDL
    // -------------------------
    nand_dcdl_top #(
        .STAGES(STAGES)
    ) u_dcdl_top (
        .clk(clk_in),
        .rst_n(~rst),
        .shift_left(shift_left),
        .shift_right(shift_right),
        .A(clk_in),
        .phases(phases)
    );

    // -------------------------
    // Feedback phase selection
    // -------------------------
    assign clk_out = phases[FB_INDEX];

    // Export all phases
    assign clk_phases = phases;

    // -------------------------
    // Debug
    // -------------------------
    assign ctrl_dbg        = ctrl;
    assign up_dbg          = up;
    assign down_dbg        = down;
    assign shift_left_dbg  = shift_left;
    assign shift_right_dbg = shift_right;

endmodule