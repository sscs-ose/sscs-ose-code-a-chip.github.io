// SKY130 hard-macro synthesis contract.  The physical implementation supplies
// the matching GDS/LEF/Liberty/SPICE/SPEF views described in docs/macro_contract.md.
`default_nettype none
(* blackbox *)
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
endmodule
`default_nettype wire
