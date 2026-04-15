`timescale 1ps/1ps

/*
|=======================================================================
| Module      : sampled_xor_phase_detector
| Author      : Mythri Muralikannan
| Description : XOR-based sampled bang-bang phase detector
|
| Function:
|   Uses an XOR gate to detect phase mismatch between the reference
|   clock (clk_in) and feedback clock (clk_out). The feedback clock is
|   sampled on the rising edge of the reference clock to determine
|   which clock is leading.
|
| Output meaning:
|   up   = 1 -> reference clock leads feedback clock -> speed up loop
|   down = 1 -> feedback clock leads reference clock -> slow down loop
|
| Operation:
|   - phase_error = clk_in XOR clk_out
|   - On each rising edge of clk_in:
|       * If clocks differ (phase_error = 1), determine which clock
|         leads by sampling clk_out
|       * If clk_out is low -> reference leads -> up = 1
|       * If clk_out is high -> feedback leads -> down = 1
|   - If clocks match, both outputs are cleared
|
| Notes:
|   - Fully synthesizable
|   - XOR detects phase difference but not direction
|   - Direction is inferred by sampling clk_out
|   - Accuracy depends on duty cycle and timing alignment
|
| Issues:
|   - Case 3 & 5: When clk_out leads clk_in, the XOR term is often 0 at the clk_in sampling edge, so the detector clears/holds instead of asserting DOWN; this design only samples on clk_in, so it misses true lead information.
|   s- Overall: XOR only indicates mismatch, not direction; direction is inferred from clk_out level, making the detector duty-cycle/timing dependent and biased toward lag detection (UP) while weak for lead detection near lock.
|=======================================================================
*/

module phase_detector (
    input  wire clk_in,    // Reference clock
    input  wire clk_out,   // Feedback clock
    input  wire rst,       // Asynchronous active-high reset
    output reg  up,        // Request to speed up
    output reg  down       // Request to slow down
);

    // Phase mismatch indicator
    wire phase_error;
    assign phase_error = clk_in ^ clk_out;

    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            up   <= 1'b0;
            down <= 1'b0;
        end
        else begin
            if (phase_error) begin
                // Determine which clock leads by sampling clk_out
                if (clk_out == 1'b0) begin
                    // Reference edge arrived first
                    up   <= 1'b1;
                    down <= 1'b0;
                end
                else begin
                    // Feedback already high -> feedback leads
                    up   <= 1'b0;
                    down <= 1'b1;
                end
            end
            else begin
                // No detectable phase difference
                up   <= 1'b0;
                down <= 1'b0;
            end
        end
    end

endmodule