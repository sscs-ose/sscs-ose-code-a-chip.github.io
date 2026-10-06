// ---------------------------------------------------------------------------
// perf_counters : Hardware Performance Monitoring & Side-Channel Telemetry Unit
//
// Cycle-accurate profiling unit capturing:
//   - Compute cycles vs Stall/Bus-wait cycles
//   - Real-time arithmetic bus toggle count (Hamming distance transitions)
//     serving as an on-chip side-channel leakage and dynamic power estimator.
// ---------------------------------------------------------------------------
module perf_counters #(
    parameter integer WIDTH = 24
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             sample_en,
    input  wire             is_busy,
    input  wire             is_stall,
    input  wire [WIDTH-1:0] coeff_bus,

    output reg  [31:0]      total_cycles,
    output reg  [31:0]      compute_cycles,
    output reg  [31:0]      stall_cycles,
    output reg  [31:0]      toggle_count
);

    reg [WIDTH-1:0] prev_coeff;

    // Bit-level popcount of bit transitions (Hamming distance)
    function [4:0] count_toggles;
        input [WIDTH-1:0] curr, prev;
        reg [WIDTH-1:0] diff;
        integer i;
        reg [4:0] cnt;
        begin
            diff = curr ^ prev;
            cnt = 5'd0;
            for (i = 0; i < WIDTH; i = i + 1) begin
                if (diff[i]) cnt = cnt + 1'b1;
            end
            count_toggles = cnt;
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            total_cycles   <= 32'd0;
            compute_cycles <= 32'd0;
            stall_cycles   <= 32'd0;
            toggle_count   <= 32'd0;
            prev_coeff     <= {WIDTH{1'b0}};
        end else if (sample_en) begin
            total_cycles <= total_cycles + 1'b1;
            if (is_busy && !is_stall)
                compute_cycles <= compute_cycles + 1'b1;
            if (is_stall)
                stall_cycles <= stall_cycles + 1'b1;

            toggle_count <= toggle_count + count_toggles(coeff_bus, prev_coeff);
            prev_coeff   <= coeff_bus;
        end
    end

endmodule
