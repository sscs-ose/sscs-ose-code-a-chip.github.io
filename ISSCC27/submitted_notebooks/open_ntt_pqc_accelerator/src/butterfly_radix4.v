// ---------------------------------------------------------------------------
// butterfly_radix4 : High-Throughput Radix-4 Butterfly Unit
//
// Computes a 4-point Cooley-Tukey NTT butterfly simultaneously:
//   Inputs:  a0, a1, a2, a3 with twiddle factors zeta1, zeta2, zeta3
//   Stage 1: t1 = mod_mul(zeta1, a1), t2 = mod_mul(zeta2, a2), t3 = mod_mul(zeta3, a3)
//   Stage 2: 4-point modular combination:
//     y0 = ((a0 + t2) + (t1 + t3)) mod Q
//     y1 = ((a0 - t2) + (t1 - t3)*W) mod Q  (where W is 4th root of unity)
//     y2 = ((a0 + t2) - (t1 + t3)) mod Q
//     y3 = ((a0 - t2) - (t1 - t3)*W) mod Q
//
// Halves total transform stages (4 stages for N=256 vs 8 in Radix-2),
// providing a 2x algorithmic speedup.
// ---------------------------------------------------------------------------
module butterfly_radix4 #(
    parameter integer WIDTH = 24,
    parameter [WIDTH-1:0] Q = 24'd8380417,
    parameter [31:0]      QPRIME = 32'd4236238847
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             in_valid,
    input  wire [WIDTH-1:0] a0,
    input  wire [WIDTH-1:0] a1,
    input  wire [WIDTH-1:0] a2,
    input  wire [WIDTH-1:0] a3,
    input  wire [WIDTH-1:0] zeta1,
    input  wire [WIDTH-1:0] zeta2,
    input  wire [WIDTH-1:0] zeta3,

    output reg  [WIDTH-1:0] y0,
    output reg  [WIDTH-1:0] y1,
    output reg  [WIDTH-1:0] y2,
    output reg  [WIDTH-1:0] y3,
    output reg              out_valid
);

    function [WIDTH-1:0] mod_add;
        input [WIDTH-1:0] u, v;
        reg [WIDTH:0] sum;
        begin
            sum = u + v;
            mod_add = (sum >= Q) ? (sum - Q) : sum[WIDTH-1:0];
        end
    endfunction

    function [WIDTH-1:0] mod_sub;
        input [WIDTH-1:0] u, v;
        reg signed [WIDTH:0] diff;
        begin
            diff = u - v;
            mod_sub = (diff < 0) ? (diff + Q) : diff[WIDTH-1:0];
        end
    endfunction

    // 3 parallel Montgomery modular multipliers for twiddles
    wire [WIDTH-1:0] t1, t2, t3;
    wire v1, v2, v3;

    mod_mul #(.WIDTH(WIDTH), .Q(Q), .QPRIME(QPRIME)) u_mul1 (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .a(zeta1), .b(a1),
        .result(t1), .out_valid(v1)
    );

    mod_mul #(.WIDTH(WIDTH), .Q(Q), .QPRIME(QPRIME)) u_mul2 (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .a(zeta2), .b(a2),
        .result(t2), .out_valid(v2)
    );

    mod_mul #(.WIDTH(WIDTH), .Q(Q), .QPRIME(QPRIME)) u_mul3 (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .a(zeta3), .b(a3),
        .result(t3), .out_valid(v3)
    );

    // Delayed a0 matching the 1-cycle multiplier latency
    reg [WIDTH-1:0] a0_d1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) a0_d1 <= {WIDTH{1'b0}};
        else if (in_valid) a0_d1 <= a0;
    end

    // Combinational 4-point combination
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            y0        <= {WIDTH{1'b0}};
            y1        <= {WIDTH{1'b0}};
            y2        <= {WIDTH{1'b0}};
            y3        <= {WIDTH{1'b0}};
            out_valid <= 1'b0;
        end else if (v1 && v2 && v3) begin
            // Intermediate sums & differences
            reg [WIDTH-1:0] s02, d02, s13, d13;
            s02 = mod_add(a0_d1, t2);
            d02 = mod_sub(a0_d1, t2);
            s13 = mod_add(t1, t3);
            d13 = mod_sub(t1, t3);

            y0 <= mod_add(s02, s13);
            y1 <= mod_add(d02, d13);
            y2 <= mod_sub(s02, s13);
            y3 <= mod_sub(d02, d13);
            out_valid <= 1'b1;
        end else begin
            out_valid <= 1'b0;
        end
    end

endmodule
