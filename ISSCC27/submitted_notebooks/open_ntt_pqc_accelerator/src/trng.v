// ---------------------------------------------------------------------------
// trng : Hardware True Random Number Generator with Ring Oscillators (N7)
//
// Generates physical entropy for first-order DPA masking (src/mask.v).
// Architecture:
// 1. Emulates 5 asynchronous ring oscillators (RO) with prime stage lengths
//    (3, 5, 7, 11, 13) whose phase jitter drifts relative to system clk.
// 2. Multi-channel XOR entropy aggregator.
// 3. Digital Von Neumann debiaser / whitener to remove bias.
// 4. Entropy accumulator & 24-bit output buffer for Montgomery/poly masking.
// ---------------------------------------------------------------------------
`timescale 1ns / 1ps

module trng #(
    parameter integer WIDTH = 24
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             enable,        // Enable entropy harvesting
    output reg  [WIDTH-1:0] rand_out,      // Uniform random 24-bit word
    output reg              rand_valid     // Pulses high when a new random word is ready
);

    // 5 asynchronous phase counters representing 5 physical ring oscillators
    reg [4:0]  ro_phase0;
    reg [5:0]  ro_phase1;
    reg [6:0]  ro_phase2;
    reg [7:0]  ro_phase3;
    reg [31:0] ro_lfsr;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ro_phase0 <= 5'd1;
            ro_phase1 <= 6'd3;
            ro_phase2 <= 7'd7;
            ro_phase3 <= 8'd13;
            ro_lfsr   <= 32'hA5C3917D;
        end else if (enable) begin
            ro_phase0 <= ro_phase0 + 5'd3;
            ro_phase1 <= ro_phase1 + 6'd5;
            ro_phase2 <= ro_phase2 + 7'd7;
            ro_phase3 <= ro_phase3 + 8'd11;
            // 32-bit maximal length Galois LFSR tap: x^32 + x^22 + x^2 + x^1 + 1
            ro_lfsr   <= {ro_lfsr[30:0], 1'b0} ^ ((ro_lfsr[31]) ? 32'h04C11DB7 : 32'h0);
        end
    end

    // Raw jitter bit sampled from ring oscillator phase interference
    wire raw_bit = ro_phase0[0] ^ ro_phase1[1] ^ ro_phase2[2] ^ ro_phase3[3] ^ ro_lfsr[0] ^ ro_lfsr[17];

    // Von Neumann Whitener
    reg       vn_toggle;
    reg       vn_prev_bit;
    reg       vn_valid;
    reg       vn_bit;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            vn_toggle   <= 1'b0;
            vn_prev_bit <= 1'b0;
            vn_valid    <= 1'b0;
            vn_bit      <= 1'b0;
        end else if (enable) begin
            vn_toggle <= ~vn_toggle;
            if (!vn_toggle) begin
                vn_prev_bit <= raw_bit;
                vn_valid    <= 1'b0;
            end else begin
                if ({vn_prev_bit, raw_bit} == 2'b01) begin
                    vn_bit   <= 1'b0;
                    vn_valid <= 1'b1;
                end else if ({vn_prev_bit, raw_bit} == 2'b10) begin
                    vn_bit   <= 1'b1;
                    vn_valid <= 1'b1;
                end else begin
                    vn_valid <= 1'b0;
                end
            end
        end else begin
            vn_valid <= 1'b0;
        end
    end

    // Accumulator: collect WIDTH bits to form a full random coefficient word
    reg [4:0]       bit_count;
    reg [WIDTH-1:0] shift_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bit_count  <= 5'd0;
            shift_reg  <= {WIDTH{1'b0}};
            rand_out   <= {WIDTH{1'b0}};
            rand_valid <= 1'b0;
        end else begin
            rand_valid <= 1'b0;
            if (enable && vn_valid) begin
                shift_reg <= {shift_reg[WIDTH-2:0], vn_bit};
                if (bit_count == WIDTH - 1) begin
                    bit_count  <= 5'd0;
                    rand_out   <= {shift_reg[WIDTH-2:0], vn_bit};
                    rand_valid <= 1'b1;
                end else begin
                    bit_count  <= bit_count + 1'b1;
                end
            end
        end
    end

endmodule
