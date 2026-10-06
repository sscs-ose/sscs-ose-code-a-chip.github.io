// ---------------------------------------------------------------------------
// mask : First-order side-channel masking unit (N5)
//
// Provides first-order share splitting and recombination for side-channel
// mitigation. In masked mode, sensitive polynomial coefficients are split
// into two random shares (x0, x1) such that (x0 + x1) mod Q = x.
// Linear operations (addition, subtraction, scaling by public twiddles)
// execute independently across shares without leaking the secret value.
// ---------------------------------------------------------------------------
module mask #(
    parameter integer WIDTH = 24,
    parameter [WIDTH-1:0] Q = 24'd8380417
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             enable,        // 1 = active masking, 0 = pass-through
    input  wire             split_valid,   // Pulse to split a coefficient
    input  wire [WIDTH-1:0] coeff_in,      // Unmasked input coefficient
    input  wire [WIDTH-1:0] rand_mask,     // Randomness source (PRNG / TRNG share)
    output reg  [WIDTH-1:0] share0_out,    // Share 0: (coeff_in - rand_mask) mod Q
    output reg  [WIDTH-1:0] share1_out,    // Share 1: rand_mask mod Q
    output reg              split_done,

    input  wire             combine_valid, // Pulse to recombine shares
    input  wire [WIDTH-1:0] share0_in,
    input  wire [WIDTH-1:0] share1_in,
    output reg  [WIDTH-1:0] coeff_out,     // Recombined: (share0_in + share1_in) mod Q
    output reg              combine_done
);

    // Modular addition: (a + b) mod Q
    function [WIDTH-1:0] mod_add;
        input [WIDTH-1:0] a, b;
        reg [WIDTH:0] sum;
        begin
            sum = a + b;
            mod_add = (sum >= Q) ? (sum - Q) : sum[WIDTH-1:0];
        end
    endfunction

    // Modular subtraction: (a - b) mod Q
    function [WIDTH-1:0] mod_sub;
        input [WIDTH-1:0] a, b;
        reg signed [WIDTH:0] diff;
        begin
            diff = a - b;
            mod_sub = (diff < 0) ? (diff + Q) : diff[WIDTH-1:0];
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            share0_out   <= {WIDTH{1'b0}};
            share1_out   <= {WIDTH{1'b0}};
            split_done   <= 1'b0;
            coeff_out    <= {WIDTH{1'b0}};
            combine_done <= 1'b0;
        end else begin
            split_done   <= 1'b0;
            combine_done <= 1'b0;

            if (split_valid) begin
                if (enable) begin
                    share0_out <= mod_sub(coeff_in, rand_mask % Q);
                    share1_out <= rand_mask % Q;
                end else begin
                    share0_out <= coeff_in;
                    share1_out <= {WIDTH{1'b0}};
                end
                split_done <= 1'b1;
            end

            if (combine_valid) begin
                if (enable) begin
                    coeff_out <= mod_add(share0_in, share1_in);
                end else begin
                    coeff_out <= share0_in;
                end
                combine_done <= 1'b1;
            end
        end
    end

endmodule
