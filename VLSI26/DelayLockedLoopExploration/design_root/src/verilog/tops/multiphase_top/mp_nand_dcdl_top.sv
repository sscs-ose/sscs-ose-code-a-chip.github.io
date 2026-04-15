`timescale 1ps/1ps

// Outputs all phases instead of one clock

module nand_dcdl_top #(
    parameter integer STAGES = 8
)(
    input  logic clk,
    input  logic rst_n,
    input  logic shift_left,
    input  logic shift_right, 
    input  logic A, 
    output logic [STAGES-1:0] phases
);

    logic [STAGES-1:0] Q;

    dll_shift_register #(
        .WIDTH(STAGES)
    ) sr (
        .clk(clk),
        .rst_n(rst_n),
        .shift_left(shift_left),
        .shift_right(shift_right),
        .Q(Q)
    );

    nand_dcdl #(
        .STAGES(STAGES)
    ) dcdl (
        .A(A),
        .Q(Q),
        .taps(phases)
    );

endmodule