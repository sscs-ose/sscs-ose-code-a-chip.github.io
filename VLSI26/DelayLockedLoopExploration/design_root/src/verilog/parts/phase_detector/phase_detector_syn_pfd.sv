`timescale 1ps/1ps

/*
|=======================================================================
| Module      : phase_frequency_detector
| Author      : Mythri Muralikannan
| Description : Two-flip-flop phase-frequency detector (PFD)
|
| Function:
|   Compares the rising edges of the reference clock (clk_in) and the
|   feedback clock (clk_out) and generates UP/DOWN control signals.
|
| Output meaning:
|   up   = 1 -> reference clock leads feedback clock -> speed up loop
|   down = 1 -> feedback clock leads reference clock -> slow down loop
|
| Operation:
|   - Rising edge of clk_in sets the UP flip-flop
|   - Rising edge of clk_out sets the DOWN flip-flop
|   - When both outputs become high, an internal clear resets both
|
| Behavior:
|   - Produces UP/DOWN pulses proportional to phase difference
|   - Detects both phase error and frequency mismatch
|
| Notes:
|   - Fully synthesizable
|   - Standard architecture used in many PLL/DLL implementations
|=======================================================================
*/

module phase_detector (
    input  wire clk_in,     // Reference clock
    input  wire clk_out,    // Feedback clock
    input  wire rst,        // Asynchronous active-high reset
    output wire up,         // Request to speed up
    output wire down        // Request to slow down
);

    reg up_ff;
    reg down_ff;

    // Internal reset: clears both flip-flops when both outputs are high
    wire clr;
    assign clr = rst | (up_ff & down_ff);

    // Set UP on reference clock edge
    always @(posedge clk_in or posedge rst) begin
        if (rst)
            up_ff <= 1'b0;
        else if (clr)
            up_ff <= 1'b0;
        else
            up_ff <= 1'b1;
    end

    // Set DOWN on feedback clock edge
    always @(posedge clk_out or posedge rst) begin
        if (rst)
            down_ff <= 1'b0;
        else if (clr)
            down_ff <= 1'b0;
        else
            down_ff <= 1'b1;
    end

    // Output assignments
    assign up   = up_ff;
    assign down = down_ff;

endmodule
