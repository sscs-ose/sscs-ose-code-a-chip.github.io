`timescale 1ps/1ps

/*
|=======================================================================
| Module      : edge_order_phase_detector
| Author      : Mythri Muralikannan
| Description : First-edge-wins binary phase detector
|
| Function:
|   Determines which clock edge arrives first and holds that decision
|   until the opposite clock edge arrives, at which point the outputs
|   are cleared.
|
| Output meaning:
|   up   = 1 -> reference clock leads feedback clock -> speed up loop
|   down = 1 -> feedback clock leads reference clock -> slow down loop
|
| Notes:
|   - Fully synthesizable
|   - Simpler than a PFD, but less robust for close/simultaneous edges
| 
| Issues:
| - Case 3 & 5: When clk_out leads clk_in, the detector still asserts UP because the "first-edge-wins" logic lets clk_in set UP before DOWN can capture the earlier feedback edge.
| - Case 1 & 6: Aligned edges occasionally trigger both signals (UP=1, DOWN=1) due to simultaneous events on the two clocks, showing ambiguity in edge ordering without a proper reset/arbiter.|=======================================================================
|*/

module phase_detector (
    input  wire clk_in,
    input  wire clk_out,
    input  wire rst,
    output reg  up,
    output reg  down
);

    // Reference edge arrived first
    always @(posedge clk_in or posedge rst) begin
        if (rst) begin
            up <= 1'b0;
        end
        else if (!down) begin
            // Only assert UP if feedback has not already won
            up <= 1'b1;
        end
        else begin
            // Feedback edge already occurred; clear after pair completes
            up <= 1'b0;
        end
    end

    // Feedback edge arrived first
    always @(posedge clk_out or posedge rst) begin
        if (rst) begin
            down <= 1'b0;
        end
        else if (!up) begin
            // Only assert DOWN if reference has not already won
            down <= 1'b1;
        end
        else begin
            // Reference edge already occurred; clear after pair completes
            down <= 1'b0;
        end
    end

endmodule