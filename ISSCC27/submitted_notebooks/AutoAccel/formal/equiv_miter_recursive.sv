// Combinational equivalence miter: conventional vs recursive Karatsuba.
// Outputs are exposed as ports so the proof can use
//   yosys "sat -verify -prove P_conv P_rec"
// ($check/assert cells are avoided because Yosys 0.70's SAT core has no
// model for them inside a miter).

module equiv_miter_recursive #(
    parameter int N = 8,
    parameter int THRESHOLD = 8
)(
    input  logic [N-1:0] A,
    input  logic [N-1:0] B,
    output logic [2*N-1:0] P_conv,
    output logic [2*N-1:0] P_rec
);
    conventional_multiplier #(.N(N)) u_conv (.A(A), .B(B), .P(P_conv));
    karatsuba_recursive_multiplier #(.N(N), .THRESHOLD(THRESHOLD)) u_rec (.A(A), .B(B), .P(P_rec));
endmodule
