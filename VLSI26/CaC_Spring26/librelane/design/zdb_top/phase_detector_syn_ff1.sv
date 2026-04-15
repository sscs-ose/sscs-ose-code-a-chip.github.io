`timescale 1ps/1ps

//**************************************************************************
// Module      : single_ff_phase_detector
// Author      : Mythri Muralikannan
// Description : Single-flip-flop bang-bang phase detector
//**************************************************************************

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