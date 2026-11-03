// Ideal *digital* two-read model of the proposed 2+2-row clocked wrapper.
// PRECHARGE/SAMPLE states model sequencing only: no bitline, ADC or PVT proof.
`timescale 1ns/1ps
`default_nettype none
module automx_ternary_cim_4x4_2p2_model (
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
    typedef enum logic [2:0] {
        READY, PRECHARGE_A, SAMPLE_A, PRECHARGE_B, SAMPLE_B, HOLD_RESULT
    } state_t;
    state_t state;
    logic [3:0] wpos_mem [0:3];
    logic [3:0] wneg_mem [0:3];
    logic signed [19:0] acts_latched;
    logic signed [11:0] partial_a [0:3];
    // Observable from the dedicated testbench; not wrapper interface pins.
    logic [7:0] phase_a_count;
    logic [7:0] phase_b_count;

    assign cfg_ready_o = (state == READY) && !eval_valid_i &&
                         !(|(cfg_wpos_i & cfg_wneg_i));
    assign eval_ready_o = (state == READY) && !cfg_valid_i;
    assign result_valid_o = (state == HOLD_RESULT);

    function automatic logic signed [11:0] pair_sum(
        input integer first_row, input integer column
    );
        integer signed total;
        integer signed activation;
        integer row;
        begin
            total = 0;
            for (integer offset = 0; offset < 2; offset = offset + 1) begin
                row = first_row + offset;
                activation = 32'($signed(acts_latched[5*row +: 5]));
                if (wpos_mem[row][column]) total = total + activation;
                if (wneg_mem[row][column]) total = total - activation;
            end
            pair_sum = 12'(total);
        end
    endfunction

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state <= READY;
            acts_latched <= '0;
            result_acc_o <= '0;
            phase_a_count <= '0;
            phase_b_count <= '0;
            for (integer i = 0; i < 4; i = i + 1) begin
                wpos_mem[i] <= '0;
                wneg_mem[i] <= '0;
                partial_a[i] <= '0;
            end
        end else begin
            case (state)
                READY: begin
                    if (cfg_valid_i && cfg_ready_o) begin
                        wpos_mem[cfg_row_i] <= cfg_wpos_i;
                        wneg_mem[cfg_row_i] <= cfg_wneg_i;
                    end
                    if (eval_valid_i && eval_ready_o) begin
                        acts_latched <= act_x2_i;
                        state <= PRECHARGE_A;
                    end
                end
                PRECHARGE_A: state <= SAMPLE_A;
                SAMPLE_A: begin
                    for (integer col = 0; col < 4; col = col + 1)
                        partial_a[col] <= pair_sum(0, col);
                    phase_a_count <= phase_a_count + 1'b1;
                    state <= PRECHARGE_B;
                end
                PRECHARGE_B: state <= SAMPLE_B;
                SAMPLE_B: begin
                    for (integer col = 0; col < 4; col = col + 1)
                        result_acc_o[12*col +: 12] <=
                            12'($signed(partial_a[col]) + $signed(pair_sum(2, col)));
                    phase_b_count <= phase_b_count + 1'b1;
                    state <= HOLD_RESULT;
                end
                HOLD_RESULT: if (result_ready_i) state <= READY;
                default: state <= READY;
            endcase
        end
    end
endmodule
`default_nettype wire
