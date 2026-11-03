//**************************************************************************
// Author: Oliver Lee
// Description: Wrapper for SKY130 PDK Cells
//**************************************************************************

module nand2 (
    input   logic a,
    input   logic b,
    output  logic out
);
    (* dont_touch = "true" *) sky130_fd_sc_hd__nand2_1 core_nand (
        .A(a), .B(b), .Y(out)
    );
endmodule

module inverter (
    input   logic in,
    output  logic out
);
    (* dont_touch = "true" *) sky130_fd_sc_hd__inv_1 core_inv (
        .A(in), .Y(out)
    );
endmodule

module mux (
    input   logic x0,
    input   logic x1,
    input   logic s,
    output  logic Y
);
    (* dont_touch = "true" *) sky130_fd_sc_hd__mux2_1 core_mux (
        .A0(x0), .A1(x1), .S(s), .X(Y)
    );
endmodule

module xnor2 (
    input   logic a,
    input   logic b,
    output  logic y   
);
    (* dont_touch = "true" *) sky130_fd_sc_hd__xnor2_1 core_xnor (
        .A(a), .B(b), .Y(y)
    );
endmodule