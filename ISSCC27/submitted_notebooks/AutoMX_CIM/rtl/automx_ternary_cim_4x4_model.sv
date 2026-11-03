// Exact digital simulation model of the SKY130 ternary 4x4 macro contract.
// It is not the physical macro and must never be used to claim analog results.
`timescale 1ns/1ps
`default_nettype none
module automx_ternary_cim_4x4_model (
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
    logic [3:0] wpos_mem [0:3];
    logic [3:0] wneg_mem [0:3];
    integer row, col;
    integer signed sum;
    integer signed act_value;

    assign cfg_ready_o = !eval_valid_i && (!result_valid_o || result_ready_i);
    assign eval_ready_o = !cfg_valid_i && (!result_valid_o || result_ready_i);

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            result_valid_o <= 1'b0;
            result_acc_o <= '0;
        end else begin
            if (result_valid_o && result_ready_i)
                result_valid_o <= 1'b0;
            if (cfg_valid_i && cfg_ready_o) begin
                wpos_mem[cfg_row_i] <= cfg_wpos_i;
                wneg_mem[cfg_row_i] <= cfg_wneg_i;
            end
            if (eval_valid_i && eval_ready_o) begin
                for (col = 0; col < 4; col = col + 1) begin
                    sum = 0;
                    for (row = 0; row < 4; row = row + 1) begin
                        act_value = 32'($signed(act_x2_i[5*row +: 5]));
                        if (wpos_mem[row][col]) sum = sum + act_value;
                        if (wneg_mem[row][col]) sum = sum - act_value;
                    end
                    // Four signed E2M1 inputs are bounded by +/-48, so the
                    // 12-bit result lane cannot overflow for valid inputs.
                    result_acc_o[12*col +: 12] <= 12'(sum);
                end
                result_valid_o <= 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
