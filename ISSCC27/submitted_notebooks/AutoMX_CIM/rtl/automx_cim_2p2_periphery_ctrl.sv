// Candidate digital control for a physical two-phase CIM wrapper.
// A local analog sequencer must perform precharge, signed PWM and sample/hold
// within one phase request. This clocked controller cannot generate 50 ps PWM
// units or guarantee the 1.9--2.1 ns sampling aperture.
`timescale 1ns/1ps
`default_nettype none
module automx_cim_2p2_periphery_ctrl (
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

    // Four rows x four columns, bit 4*row+column. Drive the passive core's
    // WPOS/WNEG pins from physical weight storage using this fixed mapping.
    output logic [15:0]        weight_pos_o,
    output logic [15:0]        weight_neg_o,
    output logic signed [19:0] act_x2_o,
    output logic               phase_b_o,
    output logic               phase_req_o,
    input  logic               phase_done_i,
    output logic               adc_req_o,
    input  logic               adc_done_i,
    // Four signed 12-bit partial codes, lane 0 in bits [11:0]. Stable when
    // adc_done_i is asserted. The converter/decoder owns their validity.
    input  logic signed [47:0] adc_partials_i
);
    typedef enum logic [4:0] {
        READY,
        PH_A_REQ, PH_A_WAIT, ADC_A_REQ, ADC_A_WAIT,
        PH_B_REQ, PH_B_WAIT, ADC_B_REQ, ADC_B_WAIT,
        HOLD_RESULT
    } state_t;
    state_t state_q;
    logic signed [47:0] partial_a_q;

    // Configuration is forbidden during an accepted evaluation. A malformed
    // ternary row (positive and negative bits both set) is not acknowledged.
    assign cfg_ready_o = (state_q == READY) && !eval_valid_i &&
                         !(|(cfg_wpos_i & cfg_wneg_i));
    assign eval_ready_o = (state_q == READY) && !cfg_valid_i;
    assign result_valid_o = (state_q == HOLD_RESULT);
    assign phase_b_o = (state_q == PH_B_REQ || state_q == PH_B_WAIT ||
                        state_q == ADC_B_REQ || state_q == ADC_B_WAIT);
    assign phase_req_o = (state_q == PH_A_REQ || state_q == PH_B_REQ);
    assign adc_req_o = (state_q == ADC_A_REQ || state_q == ADC_B_REQ);

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state_q <= READY;
            weight_pos_o <= '0;
            weight_neg_o <= '0;
            act_x2_o <= '0;
            partial_a_q <= '0;
            result_acc_o <= '0;
        end else begin
            case (state_q)
                READY: begin
                    if (cfg_valid_i && cfg_ready_o) begin
                        case (cfg_row_i)
                            2'd0: begin weight_pos_o[3:0] <= cfg_wpos_i;
                                         weight_neg_o[3:0] <= cfg_wneg_i; end
                            2'd1: begin weight_pos_o[7:4] <= cfg_wpos_i;
                                         weight_neg_o[7:4] <= cfg_wneg_i; end
                            2'd2: begin weight_pos_o[11:8] <= cfg_wpos_i;
                                         weight_neg_o[11:8] <= cfg_wneg_i; end
                            2'd3: begin weight_pos_o[15:12] <= cfg_wpos_i;
                                         weight_neg_o[15:12] <= cfg_wneg_i; end
                            default: ;
                        endcase
                    end
                    if (eval_valid_i && eval_ready_o) begin
                        act_x2_o <= act_x2_i;
                        state_q <= PH_A_REQ;
                    end
                end
                PH_A_REQ: state_q <= PH_A_WAIT;
                PH_A_WAIT: if (phase_done_i) state_q <= ADC_A_REQ;
                ADC_A_REQ: state_q <= ADC_A_WAIT;
                ADC_A_WAIT: if (adc_done_i) begin
                    partial_a_q <= adc_partials_i;
                    state_q <= PH_B_REQ;
                end
                PH_B_REQ: state_q <= PH_B_WAIT;
                PH_B_WAIT: if (phase_done_i) state_q <= ADC_B_REQ;
                ADC_B_REQ: state_q <= ADC_B_WAIT;
                ADC_B_WAIT: if (adc_done_i) begin
                    for (integer col = 0; col < 4; col = col + 1)
                        result_acc_o[12*col +: 12] <=
                            12'($signed(partial_a_q[12*col +: 12]) +
                                $signed(adc_partials_i[12*col +: 12]));
                    state_q <= HOLD_RESULT;
                end
                HOLD_RESULT: if (result_ready_i) state_q <= READY;
                default: state_q <= READY;
            endcase
        end
    end
endmodule
`default_nettype wire
