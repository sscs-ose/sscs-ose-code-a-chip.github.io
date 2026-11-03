module conventional_multiplier #(
    parameter int N = 8
)(
    input logic [N-1:0] A,
    input logic [N-1:0] B,
    output logic [2*N-1:0] P
);

    logic [N-1:0] partial_prod [N];
    logic [2*N-1:0] shifted_prod [N];

    genvar i;

    generate
        for (i = 0; i < N; i++) begin : gen_pp

            assign partial_prod[i] = B[i] ? A : '0;

            assign shifted_prod[i] =
                {{N{1'b0}}, partial_prod[i]} << i;

        end
    endgenerate

    always_comb begin

        P = '0;

        for (int k = 0; k < N; k++) begin
            P = P + shifted_prod[k];
        end

    end

endmodule
