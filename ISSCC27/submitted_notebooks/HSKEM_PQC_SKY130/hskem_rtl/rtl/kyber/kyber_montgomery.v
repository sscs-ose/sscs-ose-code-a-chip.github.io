// Montgomery reduction mod q=3329, R=2^16 (theo crystals-kyber ref)
// out = montgomery_reduce(a) where a in [0, 2^16*q)
module kyber_montgomery (
    input  wire [31:0] a,
    output wire [15:0] out
);
    localparam [15:0] KYBER_Q    = 16'd3329;
    localparam [15:0] KYBER_QINV = 16'd62209; // -1/q mod 2^16

    wire [31:0] t_full = a[15:0] * KYBER_QINV;
    wire [15:0] t = t_full[15:0];
    wire [31:0] qprod = {16'd0, t} * {16'd0, KYBER_Q};
    wire [31:0] diff = a - qprod;
    assign out = diff[31:16];
endmodule

// fqmul: Montgomery multiply mod q
module kyber_fqmul (
    input  wire [15:0] a,
    input  wire [15:0] b,
    output wire [15:0] out
);
    wire [31:0] prod = a * b;
    kyber_montgomery u_red (.a(prod), .out(out));
endmodule

// Conditional subtract q
module kyber_csubq (
    input  wire [15:0] a,
    output wire [15:0] out
);
    localparam KYBER_Q = 3329;

    wire [16:0] t = a - KYBER_Q;
    assign out = t[16] ? a : t[15:0];
endmodule
