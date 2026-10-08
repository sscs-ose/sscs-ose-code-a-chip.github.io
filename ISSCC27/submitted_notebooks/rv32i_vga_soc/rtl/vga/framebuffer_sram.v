`timescale 1ns / 1ps

module framebuffer_sram #(
    parameter FB_WIDTH  = 640,
    parameter FB_HEIGHT = 480
)(
    input  wire        clk,
    input  wire        en,
    input  wire [3:0]  we,
    input  wire [18:0] addr,     // 307,200 words (19-bit word index)
    input  wire [31:0] wdata,
    output reg  [31:0] rdata
);

    localparam FB_DEPTH = FB_WIDTH * FB_HEIGHT; // 307,200 pixels
    reg [31:0] memory [0:FB_DEPTH-1];

    always @(posedge clk) begin
        if (en) begin
            if (we[0]) memory[addr][7:0]   <= wdata[7:0];
            if (we[1]) memory[addr][15:8]  <= wdata[15:8];
            if (we[2]) memory[addr][23:16] <= wdata[23:16];
            if (we[3]) memory[addr][31:24] <= wdata[31:24];
            rdata <= memory[addr];
        end
    end

endmodule
