/// sta-blackbox
(* blackbox *) module automx_mha_ip (
    input wire clk_i, rst_ni,
    input wire cfg_valid_i, output wire cfg_ready_o,
    input wire [1:0] cfg_stage_i, cfg_row_i,
    input wire [3:0] cfg_wpos_i, cfg_wneg_i,
    input wire req_valid_i, output wire req_ready_o,
    input wire [39:0] req_act_x2_i,
    output wire rsp_valid_o, input wire rsp_ready_i,
    output wire rsp_row_o, output wire [47:0] rsp_result_x2_o,
    output wire busy_o, fault_o,
    input wire core_available_i, core_fault_i,
    output wire core_cfg_valid_o, input wire core_cfg_ready_i,
    output wire [1:0] core_cfg_row_o,
    output wire [3:0] core_cfg_wpos_o, core_cfg_wneg_o,
    output wire core_eval_valid_o, input wire core_eval_ready_i,
    output wire [19:0] core_act_x2_o,
    input wire core_result_valid_i, output wire core_result_ready_o,
    input wire [47:0] core_result_x2_i,
    input wire core_result_calibrated_i,
    inout wire VPWR, VGND
);
endmodule

(* blackbox *) module automx_cim_readout_seq (
    input wire clk_i, rst_ni,
    input wire cfg_valid_i, output wire cfg_ready_o,
    input wire [1:0] cfg_row_i,
    input wire [3:0] cfg_wpos_i, cfg_wneg_i,
    input wire cal_valid_i, output wire cal_ready_o,
    input wire [8:0] cal_address_i, input wire [11:0] cal_threshold_i,
    output wire calibrated_o,
    input wire eval_valid_i, output wire eval_ready_o,
    input wire signed [19:0] act_x2_i, input wire raw_mode_i,
    output wire result_valid_o, input wire result_ready_i,
    output reg signed [47:0] result_acc_o,
    output reg [95:0] raw_codes_o,
    output reg result_calibrated_o, output wire fault_o,
    output reg [15:0] weight_pos_o, weight_neg_o,
    output reg [3:0] wlp_o, wln_o,
    output wire pre_b_o, track_o, output reg [3:0] select_o,
    output wire adc_rst_no, adc_start_o, output reg clk_vcm_o,
    input wire adc_eoc_i, input wire [15:0] adc_word_i,
    inout wire VPWR, VGND
);
endmodule
