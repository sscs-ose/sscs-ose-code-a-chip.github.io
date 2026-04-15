module inv_dcdl (
    input  logic A,
    input  logic [1:0] Q,
    output logic Y
);

logic tap0, tap1, tap2, tap3;
logic d0, d1, d2, d3;

// inverter chain

inverter inv0 (.in(A),     .out(d0));
inverter inv1 (.in(d0),    .out(tap0));

inverter inv2 (.in(tap0),  .out(d1));
inverter inv3 (.in(d1),    .out(tap1));

inverter inv4 (.in(tap1),  .out(d2));
inverter inv5 (.in(d2),    .out(tap2));

inverter inv6 (.in(tap2),  .out(d3));
inverter inv7 (.in(d3),    .out(tap3));


// mux stage

logic mux0, mux1;

// first level muxes
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

// final mux
mux m2 (
    .x0(mux0),
    .x1(mux1),
    .s(Q[1]),
    .Y(Y)
);

endmodule