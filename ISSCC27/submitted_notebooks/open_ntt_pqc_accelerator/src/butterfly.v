// ---------------------------------------------------------------------------
// butterfly : NTT butterfly, Cooley-Tukey (forward) or Gentleman-Sande (inverse)
//
// mode_gs = 0  (Cooley-Tukey, forward NTT):
//     t     = mod_mul(zeta, b_in)     = (zeta * b_in) mod Q
//     a_out = (a_in + t) mod Q
//     b_out = (a_in - t) mod Q
//
// mode_gs = 1  (Gentleman-Sande, inverse NTT):
//     u     = (a_in + b_in) mod Q
//     v     = (a_in - b_in) mod Q
//     a_out = u
//     b_out = mod_mul(zeta, v)        = (zeta * v) mod Q
//
// A multiply-only operation (point-wise product, scaling) uses mode_gs = 0 with
// a_in = 0: then a_out = mod_mul(zeta, b_in).
//
// Latency is 2 clocks. One input pair may be accepted every clock (streaming).
// ---------------------------------------------------------------------------
module butterfly #(
    parameter integer WIDTH  = 24,
    parameter [WIDTH-1:0] Q      = 24'd8380417,
    parameter [31:0]      QPRIME = 32'd4236238847
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             in_valid,
    input  wire             mode_gs,
    input  wire [WIDTH-1:0] a_in,
    input  wire [WIDTH-1:0] b_in,
    input  wire [WIDTH-1:0] zeta,
    output reg  [WIDTH-1:0] a_out,
    output reg  [WIDTH-1:0] b_out,
    output reg              out_valid
);

    // Pre-add/sub (used by the Gentleman-Sande path)
    wire [WIDTH:0]   pre_sum = a_in + b_in;
    wire [WIDTH-1:0] u_now   = (pre_sum >= Q) ? (pre_sum - Q) : pre_sum[WIDTH-1:0];
    wire [WIDTH-1:0] v_now   = (a_in >= b_in) ? (a_in - b_in) : (a_in + Q - b_in);

    // Operand fed to the multiplier: v for GS, b_in for CT.
    wire [WIDTH-1:0] mul_b = mode_gs ? v_now : b_in;

    // Stage 1: t = mod_mul(zeta, mul_b), 1-clock latency.
    wire [WIDTH-1:0] t;
    wire             t_valid;
    mod_mul #(.WIDTH(WIDTH), .Q(Q), .QPRIME(QPRIME)) u_mm (
        .clk      (clk),
        .rst_n    (rst_n),
        .in_valid (in_valid),
        .a        (zeta),
        .b        (mul_b),
        .result   (t),
        .out_valid(t_valid)
    );

    // Align a_in and u by one clock with t.
    reg [WIDTH-1:0] a_del, u_del;
    reg             gs_del;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_del  <= {WIDTH{1'b0}};
            u_del  <= {WIDTH{1'b0}};
            gs_del <= 1'b0;
        end else begin
            a_del  <= a_in;
            u_del  <= u_now;
            gs_del <= mode_gs;
        end
    end

    // Stage 2: modular add / subtract for CT, or pass-through for GS.
    wire [WIDTH:0]   sum  = a_del + t;
    wire [WIDTH-1:0] ct_a = (sum >= Q) ? (sum - Q) : sum[WIDTH-1:0];
    wire [WIDTH-1:0] ct_b = (a_del >= t) ? (a_del - t) : (a_del + Q - t);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_out     <= {WIDTH{1'b0}};
            b_out     <= {WIDTH{1'b0}};
            out_valid <= 1'b0;
        end else begin
            a_out     <= gs_del ? u_del : ct_a;
            b_out     <= gs_del ? t     : ct_b;
            out_valid <= t_valid;
        end
    end

endmodule
