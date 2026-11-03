`default_nettype none
module automx_cim_mixed_signal_proto (
    input wire clk_i, rst_ni,
    input wire cfg_valid_i, output wire cfg_ready_o,
    input wire [1:0] cfg_row_i, input wire [3:0] cfg_wpos_i, cfg_wneg_i,
    input wire cal_valid_i, output wire cal_ready_o,
    input wire [8:0] cal_address_i, input wire [11:0] cal_threshold_i,
    output wire calibrated_o,
    input wire eval_valid_i, output wire eval_ready_o,
    input wire signed [19:0] act_x2_i, input wire raw_mode_i,
    output wire result_valid_o, input wire result_ready_i,
    output wire signed [47:0] result_acc_o, output wire [95:0] raw_codes_o,
    output wire result_calibrated_o, fault_o,
    output wire BIAS_MON,
    input wire mha_mode_i,
    input wire mha_cfg_valid_i, output wire mha_cfg_ready_o,
    input wire [1:0] mha_cfg_stage_i, mha_cfg_row_i,
    input wire [3:0] mha_cfg_wpos_i, mha_cfg_wneg_i,
    input wire mha_req_valid_i, output wire mha_req_ready_o,
    input wire [39:0] mha_req_act_x2_i,
    output wire mha_rsp_valid_o, input wire mha_rsp_ready_i,
    output wire mha_rsp_row_o, output wire [47:0] mha_rsp_result_x2_o,
    output wire mha_busy_o, mha_fault_o,
    inout wire VPWR, VGND
);
wire [15:0] wp, wn, adc_word; wire [3:0] wlp, wln, sel;
wire pre_b, track, adc_rst_n, adc_start, clk_vcm, eoc, eoc_osr;
wire BLP0, BLN0, BLP1, BLN1, BLP2, BLN2, BLP3, BLN3, HP0, HN0, HP1, HN1, HP2, HN2, HP3, HN3, TRACK_B, TRACK_N;
wire AINP, AINN;
wire seq_cfg_valid, seq_cfg_ready, seq_cal_ready, seq_eval_valid, seq_eval_ready;
wire [1:0] seq_cfg_row;
wire [3:0] seq_cfg_wpos, seq_cfg_wneg;
wire [19:0] seq_act;
wire seq_result_valid, seq_result_ready;
wire mha_core_cfg_valid, mha_core_eval_valid, mha_core_result_ready;
wire [1:0] mha_core_cfg_row;
wire [3:0] mha_core_cfg_wpos, mha_core_cfg_wneg;
wire [19:0] mha_core_act;
wire mha_reserve = mha_mode_i || mha_busy_o;
assign seq_cfg_valid=mha_reserve ? mha_core_cfg_valid : cfg_valid_i;
assign seq_cfg_row=mha_reserve ? mha_core_cfg_row : cfg_row_i;
assign seq_cfg_wpos=mha_reserve ? mha_core_cfg_wpos : cfg_wpos_i;
assign seq_cfg_wneg=mha_reserve ? mha_core_cfg_wneg : cfg_wneg_i;
assign seq_eval_valid=mha_reserve ? mha_core_eval_valid : eval_valid_i;
assign seq_act=mha_reserve ? mha_core_act : act_x2_i;
assign seq_result_ready=mha_busy_o ? mha_core_result_ready : (!mha_mode_i && result_ready_i);
assign cfg_ready_o=!mha_reserve && seq_cfg_ready;
assign cal_ready_o=!mha_busy_o && seq_cal_ready;
assign eval_ready_o=!mha_reserve && seq_eval_ready;
assign result_valid_o=!mha_reserve && seq_result_valid;
automx_mha_ip mha_i (
    .clk_i(clk_i), .rst_ni(rst_ni),
    .cfg_valid_i(mha_cfg_valid_i), .cfg_ready_o(mha_cfg_ready_o),
    .cfg_stage_i(mha_cfg_stage_i), .cfg_row_i(mha_cfg_row_i),
    .cfg_wpos_i(mha_cfg_wpos_i), .cfg_wneg_i(mha_cfg_wneg_i),
    .req_valid_i(mha_req_valid_i && mha_mode_i), .req_ready_o(mha_req_ready_o),
    .req_act_x2_i(mha_req_act_x2_i),
    .rsp_valid_o(mha_rsp_valid_o), .rsp_ready_i(mha_rsp_ready_i),
    .rsp_row_o(mha_rsp_row_o), .rsp_result_x2_o(mha_rsp_result_x2_o),
    .busy_o(mha_busy_o), .fault_o(mha_fault_o),
    .core_available_i(mha_mode_i && calibrated_o && seq_eval_ready && !cal_valid_i),
    .core_fault_i(fault_o),
    .core_cfg_valid_o(mha_core_cfg_valid), .core_cfg_ready_i(seq_cfg_ready),
    .core_cfg_row_o(mha_core_cfg_row), .core_cfg_wpos_o(mha_core_cfg_wpos), .core_cfg_wneg_o(mha_core_cfg_wneg),
    .core_eval_valid_o(mha_core_eval_valid), .core_eval_ready_i(seq_eval_ready), .core_act_x2_o(mha_core_act),
    .core_result_valid_i(seq_result_valid), .core_result_ready_o(mha_core_result_ready),
    .core_result_x2_i(result_acc_o), .core_result_calibrated_i(result_calibrated_o)
);
automx_cim_readout_seq seq_i (
.clk_i(clk_i),
.rst_ni(rst_ni),
.cfg_valid_i(seq_cfg_valid),
.cfg_ready_o(seq_cfg_ready),
.cfg_row_i(seq_cfg_row),
.cfg_wpos_i(seq_cfg_wpos),
.cfg_wneg_i(seq_cfg_wneg),
.cal_valid_i(cal_valid_i && !mha_busy_o),
.cal_ready_o(seq_cal_ready),
.cal_address_i(cal_address_i),
.cal_threshold_i(cal_threshold_i),
.calibrated_o(calibrated_o),
.eval_valid_i(seq_eval_valid),
.eval_ready_o(seq_eval_ready),
.act_x2_i(seq_act),
.raw_mode_i(mha_reserve ? 1'b0 : raw_mode_i),
.result_valid_o(seq_result_valid),
.result_ready_i(seq_result_ready),
.result_acc_o(result_acc_o),
.raw_codes_o(raw_codes_o),
.result_calibrated_o(result_calibrated_o),
.fault_o(fault_o),
.weight_pos_o(wp), .weight_neg_o(wn), .wlp_o(wlp), .wln_o(wln), .pre_b_o(pre_b), .track_o(track),
.select_o(sel), .adc_rst_no(adc_rst_n), .adc_start_o(adc_start), .clk_vcm_o(clk_vcm),
.adc_eoc_i(eoc_osr), .adc_word_i(adc_word));
automx_cim_core_acquisition_proto core_i (.BLP0(BLP0), .BLN0(BLN0), .BLP1(BLP1), .BLN1(BLN1), .BLP2(BLP2), .BLN2(BLN2), .BLP3(BLP3), .BLN3(BLN3), .HP0(HP0), .HN0(HN0), .HP1(HP1), .HN1(HN1), .HP2(HP2), .HN2(HN2), .HP3(HP3), .HN3(HN3), .PRE_B(pre_b), .TRACK(track), .VPWR(VPWR), .VGND(VGND), .TRACK_B(TRACK_B), .TRACK_N(TRACK_N), .WLP0(wlp[0]), .WLN0(wln[0]), .WLP1(wlp[1]), .WLN1(wln[1]), .WLP2(wlp[2]), .WLN2(wln[2]), .WLP3(wlp[3]), .WLN3(wln[3]), .WPOS_0_0(wp[0]), .WNEG_0_0(wn[0]), .WPOS_0_1(wp[1]), .WNEG_0_1(wn[1]), .WPOS_0_2(wp[2]), .WNEG_0_2(wn[2]), .WPOS_0_3(wp[3]), .WNEG_0_3(wn[3]), .WPOS_1_0(wp[4]), .WNEG_1_0(wn[4]), .WPOS_1_1(wp[5]), .WNEG_1_1(wn[5]), .WPOS_1_2(wp[6]), .WNEG_1_2(wn[6]), .WPOS_1_3(wp[7]), .WNEG_1_3(wn[7]), .WPOS_2_0(wp[8]), .WNEG_2_0(wn[8]), .WPOS_2_1(wp[9]), .WNEG_2_1(wn[9]), .WPOS_2_2(wp[10]), .WNEG_2_2(wn[10]), .WPOS_2_3(wp[11]), .WNEG_2_3(wn[11]), .WPOS_3_0(wp[12]), .WNEG_3_0(wn[12]), .WPOS_3_1(wp[13]), .WNEG_3_1(wn[13]), .WPOS_3_2(wp[14]), .WNEG_3_2(wn[14]), .WPOS_3_3(wp[15]), .WNEG_3_3(wn[15]));
automx_cim_condition_mux_proto condition_i (.HP0(HP0), .HN0(HN0), .HP1(HP1), .HN1(HN1), .HP2(HP2), .HN2(HN2), .HP3(HP3), .HN3(HN3), .SEL0(sel[0]), .SEL1(sel[1]), .SEL2(sel[2]), .SEL3(sel[3]), .AINP(AINP), .AINN(AINN), .BIAS_MON(BIAS_MON), .VPWR(VPWR), .VGND(VGND));
adc_top adc_i (.VDD(VPWR), .VSS(VGND), .clk_vcm(clk_vcm), .conversion_finished_osr_out(eoc_osr), .conversion_finished_out(eoc), .inn_analog(AINP), .inp_analog(AINN), .rst_n(adc_rst_n), .start_conversion_in(adc_start), .config_1_in({1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0}), .config_2_in({1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1}), .result_out({adc_word[15], adc_word[14], adc_word[13], adc_word[12], adc_word[11], adc_word[10], adc_word[9], adc_word[8], adc_word[7], adc_word[6], adc_word[5], adc_word[4], adc_word[3], adc_word[2], adc_word[1], adc_word[0]}));
endmodule
`default_nettype wire
