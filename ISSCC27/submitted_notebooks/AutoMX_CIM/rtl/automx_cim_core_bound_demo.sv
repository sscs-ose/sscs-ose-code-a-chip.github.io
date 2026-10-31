// Physical integration bridge for the measured passive CIM core.
// The analog phase engine, precharge, sample/hold and ADC are external at
// this boundary. This module is not the clocked CIM wrapper blackbox.
`default_nettype none
module automx_cim_core_bound_demo (
    input  logic               clk_i,
    input  logic               rst_ni,
    input  logic               cfg_valid_i,
    output logic               cfg_ready_o,
    input  logic [1:0]         cfg_row_i,
    input  logic [3:0]         cfg_wpos_i,
    input  logic [3:0]         cfg_wneg_i,
    input  logic               eval_valid_i,
    output logic               eval_ready_o,
    input  logic signed [19:0] act_x2_i,
    output logic               result_valid_o,
    input  logic               result_ready_i,
    output logic signed [47:0] result_acc_o,
    output logic signed [19:0] phase_act_x2_o,
    output logic               phase_b_o,
    output logic               phase_req_o,
    input  logic               phase_done_i,
    output logic               adc_req_o,
    input  logic               adc_done_i,
    input  logic signed [47:0] adc_partials_i,
    // An external analog phase engine drives the 50 ps PWM row pulses.
    input  wire [3:0]          wl_pos_i,
    input  wire [3:0]          wl_neg_i,
    // Differential bitlines terminate at the physical top-level boundary.
    inout  wire                BLP0, BLN0, BLP1, BLN1,
    inout  wire                BLP2, BLN2, BLP3, BLN3,
    inout  wire                VPWR, VGND
);
    logic [15:0] weight_pos, weight_neg;

    automx_cim_2p2_periphery_ctrl ctrl_i (
        .clk_i, .rst_ni, .cfg_valid_i, .cfg_ready_o,
        .cfg_row_i, .cfg_wpos_i, .cfg_wneg_i,
        .eval_valid_i, .eval_ready_o, .act_x2_i,
        .result_valid_o, .result_ready_i, .result_acc_o,
        .weight_pos_o(weight_pos), .weight_neg_o(weight_neg),
        .act_x2_o(phase_act_x2_o), .phase_b_o, .phase_req_o,
        .phase_done_i, .adc_req_o, .adc_done_i, .adc_partials_i
    );

    // Bit index = 4*row + column. The grounded core substrate is explicit.
    automx_ternary_cim_4x4_core core_i (
        .BLP0(BLP0), .BLN0(BLN0), .BLP1(BLP1), .BLN1(BLN1),
        .BLP2(BLP2), .BLN2(BLN2), .BLP3(BLP3), .BLN3(BLN3),
        .WLP0(wl_pos_i[0]), .WLN0(wl_neg_i[0]),
        .WLP1(wl_pos_i[1]), .WLN1(wl_neg_i[1]),
        .WLP2(wl_pos_i[2]), .WLN2(wl_neg_i[2]),
        .WLP3(wl_pos_i[3]), .WLN3(wl_neg_i[3]),
        .WPOS_0_0(weight_pos[0]),  .WNEG_0_0(weight_neg[0]),
        .WPOS_0_1(weight_pos[1]),  .WNEG_0_1(weight_neg[1]),
        .WPOS_0_2(weight_pos[2]),  .WNEG_0_2(weight_neg[2]),
        .WPOS_0_3(weight_pos[3]),  .WNEG_0_3(weight_neg[3]),
        .WPOS_1_0(weight_pos[4]),  .WNEG_1_0(weight_neg[4]),
        .WPOS_1_1(weight_pos[5]),  .WNEG_1_1(weight_neg[5]),
        .WPOS_1_2(weight_pos[6]),  .WNEG_1_2(weight_neg[6]),
        .WPOS_1_3(weight_pos[7]),  .WNEG_1_3(weight_neg[7]),
        .WPOS_2_0(weight_pos[8]),  .WNEG_2_0(weight_neg[8]),
        .WPOS_2_1(weight_pos[9]),  .WNEG_2_1(weight_neg[9]),
        .WPOS_2_2(weight_pos[10]), .WNEG_2_2(weight_neg[10]),
        .WPOS_2_3(weight_pos[11]), .WNEG_2_3(weight_neg[11]),
        .WPOS_3_0(weight_pos[12]), .WNEG_3_0(weight_neg[12]),
        .WPOS_3_1(weight_pos[13]), .WNEG_3_1(weight_neg[13]),
        .WPOS_3_2(weight_pos[14]), .WNEG_3_2(weight_neg[14]),
        .WPOS_3_3(weight_pos[15]), .WNEG_3_3(weight_neg[15]),
        .VGND(VGND)
    );
endmodule
`default_nettype wire
