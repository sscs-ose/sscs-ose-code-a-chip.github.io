import mlkem512_pkg::*;

module mlkem512_cbd2_block (
    input  wire [31:0] word_le,
    output logic [15:0] coeff [0:7]
);
    logic [31:0] d;
    logic [31:0] shifted_a;
    logic [31:0] shifted_b;
    logic [2:0] a;
    logic [2:0] b;
    integer j;

    always_comb begin
        d = (word_le & 32'h55555555) + ((word_le >> 1) & 32'h55555555);
        for (j = 0; j < 8; j = j + 1) begin
            shifted_a = d >> (4 * j);
            shifted_b = d >> ((4 * j) + 2);
            a = shifted_a[2:0] & 3'h3;
            b = shifted_b[2:0] & 3'h3;
            coeff[j] = (a >= b) ? {13'd0, (a - b)} :
                       (16'd3329 + {13'd0, a} - {13'd0, b});
        end
    end
endmodule

module mlkem512_cbd3_block (
    input  wire [23:0] word_le,
    output logic [15:0] coeff [0:3]
);
    logic [23:0] d;
    logic [23:0] shifted_a;
    logic [23:0] shifted_b;
    logic [3:0] a;
    logic [3:0] b;
    integer j;

    always_comb begin
        d = (word_le & 24'h249249) +
            ((word_le >> 1) & 24'h249249) +
            ((word_le >> 2) & 24'h249249);
        for (j = 0; j < 4; j = j + 1) begin
            shifted_a = d >> (6 * j);
            shifted_b = d >> ((6 * j) + 3);
            a = shifted_a[3:0] & 4'h7;
            b = shifted_b[3:0] & 4'h7;
            coeff[j] = (a >= b) ? {12'd0, (a - b)} :
                       (16'd3329 + {12'd0, a} - {12'd0, b});
        end
    end
endmodule
