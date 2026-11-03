// ---------------------------------------------------------------------------
// mod_mul : Montgomery modular multiplier
//
// Computes  result = a * b * R^{-1} mod Q,  with R = 2^32.
//
// This is the critical arithmetic cell of the NTT butterfly. Twiddle factors
// are stored in the Montgomery domain (pre-multiplied by R), so that
// mod_mul(zeta_mont, x) == (zeta * x) mod Q.
//
// Reduction (unsigned Montgomery / REDC):
//     T = a * b                      (product, up to 2*WIDTH bits)
//     m = (T[31:0] * QPRIME) mod 2^32
//     u = (T + m*Q) >> 32
//     if (u >= Q) u = u - Q
//
// One clock of latency: inputs registered on in_valid, result on out_valid.
// Parameterised by modulus so the same cell serves Dilithium (q=8380417) and
// Kyber (q=3329) by changing Q / QPRIME.
// ---------------------------------------------------------------------------
module mod_mul #(
    parameter integer WIDTH  = 24,                 // coefficient width (bits)
    parameter [WIDTH-1:0] Q      = 24'd8380417,    // modulus
    parameter [31:0]      QPRIME = 32'd4236238847  // (-Q^{-1}) mod 2^32
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             in_valid,
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output reg  [WIDTH-1:0] result,
    output reg              out_valid
);

    // Full product T = a * b  (self-determined 2*WIDTH-bit multiply)
    wire [2*WIDTH-1:0] T = a * b;

    // m = low 32 bits of (T[31:0] * QPRIME)
    wire [31:0] m = T[31:0] * QPRIME;

    // m * Q  (32 + WIDTH bits) and the running sum T + m*Q
    localparam integer SUMW = (2*WIDTH > 32 + WIDTH ? 2*WIDTH : 32 + WIDTH) + 1;
    wire [SUMW-1:0] mq  = m * Q;
    wire [SUMW-1:0] sum = T + mq;

    // u = (T + m*Q) / R  = right shift by 32; result fits in WIDTH+1 bits
    wire [WIDTH:0] u = sum[SUMW-1:32];

    // Conditional final subtraction to bring u into [0, Q)
    wire [WIDTH-1:0] u_reduced = (u >= Q) ? (u - Q) : u[WIDTH-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result    <= {WIDTH{1'b0}};
            out_valid <= 1'b0;
        end else begin
            result    <= u_reduced;
            out_valid <= in_valid;
        end
    end

endmodule
