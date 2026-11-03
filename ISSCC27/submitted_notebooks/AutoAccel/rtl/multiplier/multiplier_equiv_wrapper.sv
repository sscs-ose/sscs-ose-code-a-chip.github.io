
module multiplier_equiv_wrapper #(
    parameter int N = 8
) (
    input  logic [N-1:0]   A,
    input  logic [N-1:0]   B,
    output logic [2*N-1:0] P_conventional,
    output logic [2*N-1:0] P_karatsuba
);

    conventional_multiplier #(.N(N)) u_conventional (
        .A(A),
        .B(B),
        .P(P_conventional)
    );

    karatsuba_multiplier #(.N(N)) u_karatsuba (
        .A(A),
        .B(B),
        .P(P_karatsuba)
    );

endmodule

