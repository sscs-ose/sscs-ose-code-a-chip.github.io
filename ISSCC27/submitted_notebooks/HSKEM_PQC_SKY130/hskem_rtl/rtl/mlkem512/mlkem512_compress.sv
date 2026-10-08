import mlkem512_pkg::*;

module mlkem512_compress #(
    parameter int D = MLKEM512_DU
) (
    input  wire [15:0] coeff,
    output wire [D-1:0] compressed
);
    wire [31:0] rounded = (({16'd0, coeff} << D) + (MLKEM_Q / 2)) / MLKEM_Q;
    assign compressed = rounded[D-1:0];
endmodule

module mlkem512_decompress #(
    parameter int D = MLKEM512_DU
) (
    input  wire [D-1:0] compressed,
    output wire [15:0] coeff
);
    wire [31:0] scaled = ({16'd0, compressed} * MLKEM_Q) + (32'd1 << (D - 1));
    wire [31:0] rounded = scaled >> D;
    assign coeff = rounded[15:0];
endmodule
