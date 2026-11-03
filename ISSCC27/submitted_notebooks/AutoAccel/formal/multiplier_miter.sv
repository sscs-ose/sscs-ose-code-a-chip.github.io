module multiplier_miter #(
    parameter int N = 8
) (
    input logic [N-1:0] A,
    input logic [N-1:0] B
);
    logic [2*N-1:0] conventional_P;
    logic [2*N-1:0] karatsuba_P;

    conventional_multiplier #(.N(N)) conventional (
        .A(A), .B(B), .P(conventional_P)
    );

    karatsuba_multiplier #(.N(N)) karatsuba (
        .A(A), .B(B), .P(karatsuba_P)
    );

    for (genvar i = 0; i < 2*N; i++) begin : gen_output_checks
        always_comb begin
            assert (conventional_P[i] == karatsuba_P[i]);
        end
    end
endmodule
