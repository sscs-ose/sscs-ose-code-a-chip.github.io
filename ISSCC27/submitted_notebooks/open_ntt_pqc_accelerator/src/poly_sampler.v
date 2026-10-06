// ---------------------------------------------------------------------------
// poly_sampler.v: Hardware Centered Binomial (CBD) & Rejection Sampler (N12)
//
// Accelerates full polynomial generation in silicon for ML-KEM and ML-DSA:
// 1. Rejection Sampler (SampleNTT):
//    Filters uniform random bytes from the Keccak-f[1600] XOF engine into
//    valid coefficients mod Q (rejecting candidates >= Q in 0 dead cycles).
// 2. Centered Binomial Distribution Sampler (CBD_eta):
//    Samples secret and noise polynomials according to CBD_eta (eta = 2 or 3)
//    using branch-free constant-time bitwise summation mod Q.
// ---------------------------------------------------------------------------
`timescale 1ns / 1ps

module poly_sampler #(
    parameter integer WIDTH = 24,
    parameter [WIDTH-1:0] Q = 24'd8380417
) (
    input  wire                 clk,
    input  wire                 rst_n,

    // Mode select: 0 = Rejection Sampling (Uniform in Z_q), 1 = CBD_eta (Noise)
    input  wire                 mode_cbd,
    input  wire [1:0]           eta_param,    // 2'd2 for eta=2, 2'd3 for eta=3

    // Stream input from Keccak XOF (src/keccak_xof.v)
    input  wire                 in_valid,
    input  wire [23:0]          in_data,
    output wire                 in_ready,

    // Output to Coeff RAM / NTT datapath
    output reg                  out_valid,
    output reg  [WIDTH-1:0]     out_coeff,
    output reg                  out_rejected   // Pulses high on rejected uniform candidate
);

    assign in_ready = 1'b1;

    // --- 1. Constant-Time Centered Binomial Generator ---
    // For eta=2: 4 bits -> a[0]+a[1] - (b[0]+b[1])
    // For eta=3: 6 bits -> a[0]+a[1]+a[2] - (b[0]+b[1]+b[2])
    function [WIDTH-1:0] sample_cbd;
        input [5:0] bits;
        input [1:0] eta;
        reg [2:0] sum_a, sum_b;
        begin
            if (eta == 2'd2) begin
                sum_a = bits[0] + bits[1];
                sum_b = bits[2] + bits[3];
            end else begin // eta == 3
                sum_a = bits[0] + bits[1] + bits[2];
                sum_b = bits[3] + bits[4] + bits[5];
            end
            
            if (sum_a >= sum_b)
                sample_cbd = sum_a - sum_b;
            else
                sample_cbd = Q - (sum_b - sum_a);
        end
    endfunction

    // --- 2. Sequential Sampling Logic ---
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid    <= 1'b0;
            out_coeff    <= {WIDTH{1'b0}};
            out_rejected <= 1'b0;
        end else begin
            out_valid    <= 1'b0;
            out_rejected <= 1'b0;

            if (in_valid) begin
                if (mode_cbd) begin
                    // CBD Noise Sampling Mode: always accepts in 1 cycle
                    out_coeff <= sample_cbd(in_data[5:0], eta_param);
                    out_valid <= 1'b1;
                end else begin
                    // Uniform Rejection Sampling Mode (SampleNTT)
                    if (in_data < Q) begin
                        out_coeff <= in_data[WIDTH-1:0];
                        out_valid <= 1'b1;
                    end else begin
                        // Candidate >= Q, reject and discard
                        out_rejected <= 1'b1;
                    end
                end
            end
        end
    end

endmodule
