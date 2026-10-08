`timescale 1ps/1ps

/*
|=======================================================================
| Module      : single_ff_phase_detector
| Author      : Mythri Muralikannan
| Description : Single-flip-flop bang-bang phase detector
|
| Function:
|   Samples the feedback clock (clk_out) on the rising edge of the
|   reference clock (clk_in) and generates a 1-bit phase decision.
|
| Output meaning:
|   up   = 1 -> reference clock leads feedback clock -> speed up
|   down = 1 -> feedback clock leads reference clock -> slow down
|
| Operation:
|   - On each rising edge of clk_in, clk_out is sampled
|   - If clk_out is low, feedback has not risen yet -> up = 1
|   - If clk_out is high, feedback is assumed to be ahead -> down = 1
|
| Notes:
|   - Fully synthesizable
|   - Simple and low-cost implementation
|   - Does not measure phase magnitude, only lead/lag
|   - Zero phase error can be biased toward down depending on timing
| 
| Issues:
|   - Case 1: Aligned clocks failed due to "excesive DOWN activity". There is not special "equal case"
|   - Case 6: Asynch results in same biased behavior (no equal clock stage).
|=======================================================================
*/

module phase_detector (
    input  wire clk_in,    // Reference input clock
    input  wire clk_out,   // Feedback clock
    input  wire rst,       // Asynchronous active-high reset
    output reg  up,        // Assert to speed up
    output reg  down       // Assert to slow down
);

    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            up   <= 1'b0;
            down <= 1'b0;
        end else begin
            // Sample feedback clock at the reference edge
            if (clk_out == 1'b0) begin
                // Feedback edge has not arrived yet: clk_in is leading
                up   <= 1'b1;
                down <= 1'b0;
            end else begin
                // Feedback is already high: clk_out is leading
                up   <= 1'b0;
                down <= 1'b1;
            end 
        end
    end

endmodule