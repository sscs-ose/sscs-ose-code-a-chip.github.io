// AutoAccel: recursive Karatsuba multiplier with conventional base case.
//
// For N <= THRESHOLD the design defers to the shift-and-add
// conventional_multiplier. Above the threshold it applies one Karatsuba
// split: the two half-width products recurse; the (HALF+1)-bit middle
// product is computed exactly by a conventional multiplier instance.
//
// Width rule: N must be even. For N > THRESHOLD the halving chain must
// remain even until it reaches the threshold, i.e. N must be a multiple
// of 2^k where 2^k is the smallest power of two <= THRESHOLD... in
// practice: verified and measured for N in {8, 16, 32, 64} with
// THRESHOLD = 8.
module karatsuba_recursive_multiplier #(
    parameter int N = 8,          // must be even, >= 2
    parameter int THRESHOLD = 8   // base-case width
)(
    input  logic [N-1:0]   A,
    input  logic [N-1:0]   B,
    output logic [2*N-1:0] P
);

    initial begin
        if (N < 2 || N % 2 != 0)
            $fatal(1, "karatsuba_recursive_multiplier: N must be even and >= 2, got %0d", N);
    end

    generate
        if (N <= THRESHOLD) begin : gen_base_case
            // Base case: shift-and-add multiplier.
            conventional_multiplier #(.N(N)) u_base (
                .A(A),
                .B(B),
                .P(P)
            );
        end else begin : gen_karatsuba_step
            localparam int HALF = N / 2;

            logic [HALF-1:0] A_lo, A_hi, B_lo, B_hi;
            logic [N-1:0]    Z0, Z2;
            logic [HALF:0]   A_sum, B_sum;
            logic [N+1:0]    Z1;      // (HALF+1)-bit x (HALF+1)-bit product
            logic [N+1:0]    middle;  // cross term, always non-negative

            assign A_lo = A[HALF-1:0];
            assign A_hi = A[N-1:HALF];
            assign B_lo = B[HALF-1:0];
            assign B_hi = B[N-1:HALF];

            // Recursive half products (HALF is even whenever this branch
            // is instantiated with a power-of-two N above the threshold).
            karatsuba_recursive_multiplier #(.N(HALF), .THRESHOLD(THRESHOLD)) u_lo (
                .A(A_lo), .B(B_lo), .P(Z0)
            );
            karatsuba_recursive_multiplier #(.N(HALF), .THRESHOLD(THRESHOLD)) u_hi (
                .A(A_hi), .B(B_hi), .P(Z2)
            );

            // Middle product computed exactly at width HALF+1.
            assign A_sum = A_lo + A_hi;
            assign B_sum = B_lo + B_hi;
            conventional_multiplier #(.N(HALF + 1)) u_mid (
                .A(A_sum),
                .B(B_sum),
                .P(Z1)      // 2*(HALF+1) = N+2 bits
            );

            assign middle = Z1 - Z2 - Z0;   // unsigned wrap, mathematically >= 0

            assign P = ({{N{1'b0}}, Z2}     << N)
                     + ({{N{1'b0}}, middle} << HALF)
                     +  {{N{1'b0}}, Z0};
        end
    endgenerate

endmodule
