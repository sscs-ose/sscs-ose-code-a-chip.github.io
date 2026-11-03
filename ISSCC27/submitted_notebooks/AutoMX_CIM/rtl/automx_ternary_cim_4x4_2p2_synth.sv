// Digital-only implementation surrogate for OpenLane exploration.
// No passive CIM devices, bitlines, PWM, sample/hold, comparator or ADC exist here.
// Do not use this view for the clocked wrapper's physical GDS/LEF contract.
`timescale 1ns/1ps
`default_nettype none
module automx_ternary_cim_4x4 (
    input  logic        clk_i,
    input  logic        rst_ni,
    input  logic        cfg_valid_i,
    output logic        cfg_ready_o,
    input  logic [1:0]  cfg_row_i,
    input  logic [3:0]  cfg_wpos_i,
    input  logic [3:0]  cfg_wneg_i,
    input  logic        eval_valid_i,
    output logic        eval_ready_o,
    input  logic signed [19:0] act_x2_i,
    output logic        result_valid_o,
    input  logic        result_ready_i,
    output logic signed [47:0] result_acc_o,
    inout  wire         VPWR,
    inout  wire         VGND
);
    automx_ternary_cim_4x4_2p2_model digital_surrogate_i (
        .clk_i(clk_i), .rst_ni(rst_ni),
        .cfg_valid_i(cfg_valid_i), .cfg_ready_o(cfg_ready_o),
        .cfg_row_i(cfg_row_i), .cfg_wpos_i(cfg_wpos_i),
        .cfg_wneg_i(cfg_wneg_i), .eval_valid_i(eval_valid_i),
        .eval_ready_o(eval_ready_o), .act_x2_i(act_x2_i),
        .result_valid_o(result_valid_o), .result_ready_i(result_ready_i),
        .result_acc_o(result_acc_o), .VPWR(VPWR), .VGND(VGND)
    );
endmodule
`default_nettype wire
