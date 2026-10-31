// Code your design here
module karatsuba_multiplier #(
    parameter int N = 8      // must be even, >= 2
)(
    input  logic [N-1:0]   A,
    input  logic [N-1:0]   B,
    output logic [2*N-1:0] P
);

    initial begin
        if (N < 2 || N % 2 != 0)
            $fatal(1, "karatsuba_multiplier: N must be even and >= 2, got %0d", N);
    end

    localparam int HALF = N / 2;

    logic [HALF-1:0] A_low,  A_high, B_low, B_high;
    logic [N-1:0]    P0, P2;
    logic [HALF:0]   A_sum, B_sum;
    logic [N+1:0]    P1;      // N+2 bits: product of two (HALF+1)-bit values
    logic [N+1:0]    middle;  // max 2*(2^HALF-1)^2, fits in N+1 bits

    assign A_low  = A[HALF-1:0];
    assign A_high = A[N-1:HALF];
    assign B_low  = B[HALF-1:0];
    assign B_high = B[N-1:HALF];

    assign P0    = A_low  * B_low;
    assign P2    = A_high * B_high;
    assign A_sum = A_low  + A_high;
    assign B_sum = B_low  + B_high;
    assign P1    = A_sum  * B_sum;

    assign middle = P1 - P2 - P0;   // always non-negative for unsigned inputs

    assign P = ({{N{1'b0}}, P2}     << N)
             + ({{N{1'b0}}, middle} << HALF)
             +  {{N{1'b0}}, P0};

endmodule
