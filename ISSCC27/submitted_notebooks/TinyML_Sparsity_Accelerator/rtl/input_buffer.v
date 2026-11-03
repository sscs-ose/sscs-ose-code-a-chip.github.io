`timescale 1ns / 1ps

module input_buffer #(
    parameter TILE_SIZE  = 16,
    parameter DATA_WIDTH = 8
)(
    input  wire clk,
    input  wire wr_en,
    input  wire [$clog2(TILE_SIZE)-1:0] wr_addr,
    input  wire [DATA_WIDTH-1:0] act_in,
    input  wire [DATA_WIDTH-1:0] wt_in,
    
    input  wire [$clog2(TILE_SIZE)-1:0] rd_addr,
    output wire [DATA_WIDTH-1:0] act_out,
    output wire [DATA_WIDTH-1:0] wt_out
);

    reg [DATA_WIDTH-1:0] act_mem [0:TILE_SIZE-1];
    reg [DATA_WIDTH-1:0] wt_mem  [0:TILE_SIZE-1];

    integer i;
    initial begin
        for (i = 0; i < TILE_SIZE; i = i + 1) begin
            act_mem[i] = {DATA_WIDTH{1'b0}};
            wt_mem[i]  = {DATA_WIDTH{1'b0}};
        end
    end

    always @(posedge clk) begin
        if (wr_en) begin
            act_mem[wr_addr] <= act_in;
            wt_mem[wr_addr]  <= wt_in;
        end
    end

    assign act_out = act_mem[rd_addr];
    assign wt_out  = wt_mem[rd_addr];

endmodule
