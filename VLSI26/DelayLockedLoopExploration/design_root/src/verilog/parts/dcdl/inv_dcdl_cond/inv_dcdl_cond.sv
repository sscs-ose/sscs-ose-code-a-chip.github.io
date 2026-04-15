//**************************************************************************
// Author: Alfi Misha Antony Selvin Raj
// Description: Conditional inv dcdl (gate-level)
//**************************************************************************
(* dont_touch = "true" *)
module inv_dcdl_cond (
    input  logic A,
    input  logic [1:0] Q,
    output logic Y
);

    // delay chain
    logic tap0, tap1, tap2, tap3;

    inverter inv1 (.in(A),     .out(tap0));
    inverter inv2 (.in(tap0),  .out(tap1));
    inverter inv3 (.in(tap1),  .out(tap2));
    inverter inv4 (.in(tap2),  .out(tap3));

    // mux tree
    logic mux0, mux1, mux2;

    mux m0 (
        .x0(tap0),
        .x1(tap1),
        .s(Q[0]),
        .Y(mux0)
    );

    mux m1 (
        .x0(tap2),
        .x1(tap3),
        .s(Q[0]),
        .Y(mux1)
    );

    mux m2 (
        .x0(mux0),
        .x1(mux1),
        .s(Q[1]),
        .Y(mux2)
    );

    // XNOR stage 
    xnor2 x1 (
        .a(mux2),
        .b(Q[1]),
        .y(Y)
    );

endmodule