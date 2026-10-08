import mlkem512_pkg::*;

module mlkem512_byte_pack_block #(
    parameter int D = 10,
    parameter int COEFFS = 4,
    parameter int BYTES = 5
) (
    input  wire [15:0] coeff [0:COEFFS-1],
    output logic [(8*BYTES)-1:0] bytes_le
);
    integer i;

    always_comb begin
        bytes_le = '0;
        for (i = 0; i < COEFFS; i = i + 1)
            bytes_le[i * D +: D] = coeff[i][D-1:0];
    end
endmodule

module mlkem512_byte_unpack_block #(
    parameter int D = 10,
    parameter int COEFFS = 4,
    parameter int BYTES = 5
) (
    input  wire [(8*BYTES)-1:0] bytes_le,
    output logic [15:0] coeff [0:COEFFS-1]
);
    integer i;

    always_comb begin
        for (i = 0; i < COEFFS; i = i + 1)
            coeff[i] = {{(16-D){1'b0}}, bytes_le[i * D +: D]};
    end
endmodule

