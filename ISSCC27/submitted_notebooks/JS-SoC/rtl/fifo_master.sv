
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.06.2026 12:41:42
// Design Name: 
// Module Name: fifo_master
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module fifo_master(
    input logic clk,
    input logic rst,
    input logic w_en,
    input logic [63:0] data_in,
    output logic full,
    output logic [31:0] pr_data,
    output logic tx,
    output logic wave,
    output logic wave1,
    output logic wave2
    );
    
    logic [63:0] data_out;
    logic r_en;
    logic empty;
    fifo #(.depth(4),.width(64)) fifo1(
                                     .clk(clk),
                                     .rst(rst),
                                     .w_en(w_en),
                                     .r_en(r_en),
                                     .data_in(data_in),
                                     .data_out(data_out),
                                     .full(full),
                                     .empty(empty)
                                );
    master master1 (
                    .clk(clk),
                    .rst(rst),
                    .fifo_data(data_out),
                    .fifo_empty(empty),
                    .r_en(r_en),
                    .pr_data(pr_data),
                    .tx(tx),
                    .wave(wave),
                    .wave1(wave1),
                    .wave2(wave2)
                    );
                    
                    
endmodule
