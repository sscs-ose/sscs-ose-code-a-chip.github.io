`timescale 1ns / 1ps

module rgb_output (
    input  wire        clk,
    input  wire        rst,              // Active-high reset
    input  wire        video_on,         // Undelayed active-video signal from vga_timing
    input  wire [31:0] vga_data,         // 32-bit pixel data (00RRGGBB) from axi_framebuffer

    output wire [7:0]  red,
    output wire [7:0]  green,
    output wire [7:0]  blue
);

    // 1-cycle delay register to align with synchronous framebuffer read latency
    reg video_on_delayed;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            video_on_delayed <= 1'b0;
        end else begin
            video_on_delayed <= video_on;
        end
    end

    // Combinational RGB extraction gated by delayed active video
    assign red   = video_on_delayed ? vga_data[23:16] : 8'h00;
    assign green = video_on_delayed ? vga_data[15:8]  : 8'h00;
    assign blue  = video_on_delayed ? vga_data[7:0]   : 8'h00;

endmodule
