module vernier_dcdl_top (
    input logic clk,
    input logic rst_n,
    input logic shift_left,
    input logic shift_right, 
    input logic A, 
    output logic Y
);
logic [3:0] Q;
dll_shift_register sr (
    .clk(clk),
    .rst_n(rst_n),
    .shift_left(shift_left),
    .shift_right(shift_right),
    .Q(Q)
);
vernier_dcdl #(.STAGES(4)) dcdl (
    .A(A),
    .Q(Q),
    .Y(Y)
);
endmodule