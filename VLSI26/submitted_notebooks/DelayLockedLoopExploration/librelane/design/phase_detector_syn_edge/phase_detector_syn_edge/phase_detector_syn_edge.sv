`timescale 1ps/1ps

//**************************************************************************
// Module      : edge_order_phase_detector
// Author      : Mythri Muralikannan
// Description : First-edge-wins binary phase detector
//**************************************************************************

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