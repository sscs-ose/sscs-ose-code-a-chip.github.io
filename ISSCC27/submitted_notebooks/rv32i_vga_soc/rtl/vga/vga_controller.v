`timescale 1ns / 1ps

module vga_controller #(
    parameter PIXEL_SCALE = 1,
    parameter H_VISIBLE = 640,
    parameter H_FRONT   = 16,
    parameter H_SYNC    = 96,
    parameter H_BACK    = 48,
    parameter V_VISIBLE = 480,
    parameter V_FRONT   = 10,
    parameter V_SYNC    = 2,
    parameter V_BACK    = 33
)(
    input  wire        clk,
    input  wire        rst,

    // Interface to/from vga_registers
    input  wire        display_enable,
    output wire        vga_fb_req,
    output wire [20:0] vga_fb_addr,
    output wire        vga_video_on,

    // Pixel data input from Framebuffer SRAM
    input  wire [31:0] vga_data,

    // VGA Physical Pins (1-cycle delayed to align with SRAM read latency)
    output wire        Hsync,
    output wire        Vsync,
    output wire [7:0]  red,
    output wire [7:0]  green,
    output wire [7:0]  blue
);

    wire [15:0] H_count;
    wire [15:0] V_count;
    wire        raw_video_on;
    wire        raw_hsync;
    wire        raw_vsync;

    assign vga_video_on = raw_video_on;
    assign vga_fb_req   = raw_video_on && display_enable;

    // 1. VGA Timing Generator
    vga_timing #(
        .H_VISIBLE(H_VISIBLE),
        .H_FRONT(H_FRONT),
        .H_SYNC(H_SYNC),
        .H_BACK(H_BACK),
        .V_VISIBLE(V_VISIBLE),
        .V_FRONT(V_FRONT),
        .V_SYNC(V_SYNC),
        .V_BACK(V_BACK)
    ) u_vga_timing (
        .clk      (clk),
        .rst      (rst),
        .H_count  (H_count),
        .V_count  (V_count),
        .Hsync    (raw_hsync),
        .Vsync    (raw_vsync),
        .video_on (raw_video_on)
    );

    // 2. Pixel Address Generator
    pixel_addr_gen #(
        .PIXEL_SCALE(PIXEL_SCALE)
    ) u_pixel_addr_gen (
        .H_count    (H_count),
        .V_count    (V_count),
        .video_on   (raw_video_on),
        .pixel_addr (vga_fb_addr)
    );

    // 3. Pipeline Register: Delay HSYNC & VSYNC by 1 clock cycle to match SRAM synchronous read latency
    reg hsync_d1;
    reg vsync_d1;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            hsync_d1 <= 1'b1;
            vsync_d1 <= 1'b1;
        end else begin
            hsync_d1 <= raw_hsync;
            vsync_d1 <= raw_vsync;
        end
    end

    assign Hsync = hsync_d1;
    assign Vsync = vsync_d1;

    // 4. RGB Output Stage (uses internal 1-cycle delayed video_on, blanks when display_enable = 0)
    rgb_output u_rgb_output (
        .clk      (clk),
        .rst      (rst),
        .video_on (raw_video_on && display_enable),
        .vga_data (vga_data),
        .red      (red),
        .green    (green),
        .blue     (blue)
    );

endmodule
