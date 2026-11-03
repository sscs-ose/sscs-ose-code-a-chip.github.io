// Stage-7 base-only logical 32x8 tile. Sixteen sequential transactions use
// the clocked 4x4 macro interface; no dense residual/reference datapath is
// synthesized into this controller. The macro model is for simulation only.
`timescale 1ns/1ps
`default_nettype none
module automx_cim_tile_controller (
    input  logic                 clk_i,
    input  logic                 rst_ni,
    input  logic                 cfg_valid_i,
    output logic                 cfg_ready_o,
    input  logic [4:0]           cfg_row_i,
    input  logic [7:0]           cfg_wpos_i,
    input  logic [7:0]           cfg_wneg_i,
    input  logic                 cfg_alpha_valid_i,
    output logic                 cfg_alpha_ready_o,
    input  logic [2:0]           cfg_alpha_col_i,
    input  logic [15:0]          cfg_alpha_q_i,
    input  logic                 req_valid_i,
    output logic                 req_ready_o,
    input  logic signed [159:0]  req_act_x2_i,
    input  logic [7:0]           req_scale_e8m0_i,
    output logic                 rsp_valid_o,
    input  logic                 rsp_ready_i,
    output logic signed [383:0]  rsp_group_acc_q_o,
    output logic signed [383:0]  rsp_scaled_acc_q_o
);
    typedef enum logic [2:0] {IDLE, CONFIGURE, EVALUATE, COLLECT, RESPOND} state_t;
    state_t state;
    logic [7:0] wpos_mem [0:31];
    logic [7:0] wneg_mem [0:31];
    logic [15:0] alpha_mem [0:7];
    logic [31:0] weight_loaded;
    logic [7:0] alpha_loaded;
    logic signed [159:0] act_latched;
    logic [7:0] scale_latched;
    logic signed [15:0] base_sum [0:7];
    logic [2:0] row_group;
    logic col_group;
    logic [1:0] local_row;
    logic macro_cfg_valid, macro_cfg_ready;
    logic macro_eval_valid, macro_eval_ready;
    logic macro_result_valid, macro_result_ready;
    logic signed [47:0] macro_result;
    logic signed [19:0] macro_acts;
    logic [4:0] global_row;
    logic [3:0] macro_wpos, macro_wneg;
    logic signed [47:0] q24_value;

    assign cfg_ready_o = (state == IDLE) && !(|(cfg_wpos_i & cfg_wneg_i));
    assign cfg_alpha_ready_o = (state == IDLE);
    assign req_ready_o = (state == IDLE) && (&weight_loaded) && (&alpha_loaded)
                       && !cfg_valid_i && !cfg_alpha_valid_i;
    assign rsp_valid_o = (state == RESPOND);
    assign global_row = {row_group, local_row};
    assign macro_wpos = col_group ? wpos_mem[global_row][7:4] : wpos_mem[global_row][3:0];
    assign macro_wneg = col_group ? wneg_mem[global_row][7:4] : wneg_mem[global_row][3:0];
    assign macro_cfg_valid = (state == CONFIGURE);
    assign macro_eval_valid = (state == EVALUATE);
    assign macro_result_ready = (state == COLLECT);

    genvar row;
    generate for (row = 0; row < 4; row = row + 1) begin : gen_activation
        wire [4:0] activation_row = {row_group, 2'(row)};
        assign macro_acts[5*row +: 5] = act_latched[5*activation_row +: 5];
    end endgenerate

    automx_ternary_cim_4x4 macro_i (
        .clk_i(clk_i), .rst_ni(rst_ni),
        .cfg_valid_i(macro_cfg_valid), .cfg_ready_o(macro_cfg_ready),
        .cfg_row_i(local_row), .cfg_wpos_i(macro_wpos), .cfg_wneg_i(macro_wneg),
        .eval_valid_i(macro_eval_valid), .eval_ready_o(macro_eval_ready),
        .act_x2_i(macro_acts), .result_valid_o(macro_result_valid),
        .result_ready_i(macro_result_ready), .result_acc_o(macro_result),
        .VPWR(), .VGND()
    );

    // Exact Q24-domain result for the frozen base-only mode (col_v=1,
    // beta=0, residual=0). Right E8M0 shifts round toward negative infinity;
    // left shifts saturate rather than wrap. This convention is a digital RTL
    // contract, not an analog sensing specification.
    function automatic logic signed [47:0] scale_q24(
        input logic signed [47:0] value,
        input logic [7:0] scale_code
    );
        logic signed [95:0] wide, shifted;
        integer amount;
        begin
            wide = {{48{value[47]}}, value};
            if (scale_code < 8'd128) begin
                amount = 32'd128 - {24'd0, scale_code};
                scale_q24 = value >>> amount;
            end else begin
                amount = {24'd0, scale_code} - 32'd128;
                shifted = wide <<< amount;
                if (amount > 47 && value != 0)
                    scale_q24 = value[47] ? 48'sh800000000000 : 48'sh7fffffffffff;
                else if (shifted > 96'sd140737488355327)
                    scale_q24 = 48'sh7fffffffffff;
                else if (shifted < -96'sd140737488355328)
                    scale_q24 = 48'sh800000000000;
                else
                    scale_q24 = shifted[47:0];
            end
        end
    endfunction

    always_comb begin
        rsp_group_acc_q_o = '0;
        rsp_scaled_acc_q_o = '0;
        for (integer col = 0; col < 8; col = col + 1) begin
            q24_value = ($signed(base_sum[col]) * $signed({1'b0, alpha_mem[col]})) <<< 12;
            rsp_group_acc_q_o[48*col +: 48] = q24_value;
            rsp_scaled_acc_q_o[48*col +: 48] = scale_q24(q24_value, scale_latched);
        end
    end

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state <= IDLE;
            weight_loaded <= '0;
            alpha_loaded <= '0;
            act_latched <= '0;
            scale_latched <= 8'd128;
            row_group <= '0;
            col_group <= '0;
            local_row <= '0;
            for (integer i = 0; i < 8; i = i + 1) begin
                base_sum[i] <= '0;
                alpha_mem[i] <= '0;
            end
        end else begin
            case (state)
                IDLE: begin
                    if (cfg_valid_i && cfg_ready_o) begin
                        wpos_mem[cfg_row_i] <= cfg_wpos_i;
                        wneg_mem[cfg_row_i] <= cfg_wneg_i;
                        weight_loaded[cfg_row_i] <= 1'b1;
                    end
                    if (cfg_alpha_valid_i && cfg_alpha_ready_o) begin
                        alpha_mem[cfg_alpha_col_i] <= cfg_alpha_q_i;
                        alpha_loaded[cfg_alpha_col_i] <= 1'b1;
                    end
                    if (req_valid_i && req_ready_o) begin
                        act_latched <= req_act_x2_i;
                        scale_latched <= req_scale_e8m0_i;
                        row_group <= '0;
                        col_group <= '0;
                        local_row <= '0;
                        for (integer i = 0; i < 8; i = i + 1)
                            base_sum[i] <= '0;
                        state <= CONFIGURE;
                    end
                end
                CONFIGURE: if (macro_cfg_ready) begin
                    if (local_row == 2'd3) begin
                        local_row <= '0;
                        state <= EVALUATE;
                    end else
                        local_row <= local_row + 1'b1;
                end
                EVALUATE: if (macro_eval_ready) state <= COLLECT;
                COLLECT: if (macro_result_valid) begin
                    for (integer i = 0; i < 4; i = i + 1)
                        base_sum[4*col_group+i] <=
                            base_sum[4*col_group+i] + 16'($signed(macro_result[12*i +: 12]));
                    if (row_group == 3'd7 && col_group) begin
                        state <= RESPOND;
                    end else begin
                        if (col_group)
                            row_group <= row_group + 1'b1;
                        col_group <= !col_group;
                        state <= CONFIGURE;
                    end
                end
                RESPOND: if (rsp_ready_i) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
