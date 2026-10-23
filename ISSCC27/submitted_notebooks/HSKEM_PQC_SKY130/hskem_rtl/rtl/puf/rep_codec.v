// ============================================================================
// rep_codec.v  -  Ma lap (repetition 3x) + giai ma majority vote
// ----------------------------------------------------------------------------
// Encode: moi bit -> 3 bit giong nhau.
// Decode: 3 bit -> 1 bit (da so).
// ============================================================================
module rep_codec #(
    parameter integer DATA_BITS = 32
) (
    input  wire [DATA_BITS-1:0]          data_in,
    output wire [DATA_BITS*3-1:0]        encoded,
    input  wire [DATA_BITS*3-1:0]        noisy_in,
    output wire [DATA_BITS-1:0]          decoded
);
    genvar gi;
    generate
        for (gi = 0; gi < DATA_BITS; gi = gi + 1) begin : enc
            assign encoded[gi*3+0] = data_in[gi];
            assign encoded[gi*3+1] = data_in[gi];
            assign encoded[gi*3+2] = data_in[gi];
        end
    endgenerate

    generate
        for (gi = 0; gi < DATA_BITS; gi = gi + 1) begin : dec
            wire [2:0] triple = noisy_in[gi*3 +: 3];
            wire [1:0] sum = triple[0] + triple[1] + triple[2];
            assign decoded[gi] = (sum >= 2'd2);
        end
    endgenerate
endmodule
