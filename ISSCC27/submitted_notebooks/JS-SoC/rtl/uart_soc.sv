
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 03.06.2026 11:18:32
// Design Name: 
// Module Name: uart_soc
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


module uart_soc(
    input logic clk,
    input logic rst,
    input logic [31:0] data_in,
    input logic wr_en,
    output logic master_busy,
    output logic [31:0] data_out,
    output logic tx,
    output logic master_ready
    );
    //for baud rate generator
    logic tx_en;
    logic rx_en;
    //serializer
    logic master_write;
    logic [7:0] data_tx;
    //tx
    logic busy;
    //logic tx;
    //rx
    logic ready;
    logic [7:0] data_rx;
    //deserializer
    logic rdy_clear;
    
    baud_rate baud_rate1(
        .clk(clk),
        .rst(rst),
        .tx_en(tx_en),
        .rx_en(rx_en)
    );
    
    serializer serializer1(
        .clk(clk),
        .rst(rst),
        .data_in(data_in),
        .wr_en(wr_en),
        .busy(busy),//input from tx
        //.tx(tx),//from tx
        .data_out(data_tx),
        .master_busy(master_busy),
        .master_write(master_write)
    );
    
    uart_tx uart_tx1(
        .clk(clk),
        .wr_en(master_write),
        .en(tx_en),
        .rst(rst),
        .data_in(data_tx),
        .tx(tx),//output 
        .busy(busy)//output
    );
    
    
    uart_rx uart_rx1(
        .clk(clk),
        .rst(rst),
        .rdy_clr(rdy_clear),//input from deserializer
        .en(rx_en),
        .rx(tx),
        .rdy(ready),//output
        .data_out(data_rx)//output
    );
    
    
    deserializer deserializer1(
        .clk(clk),
        .rst(rst),
        .ready(ready),
        .data_in(data_rx),
        .rdy_clear(rdy_clear),
        .data_out(data_out),
        .master_ready(master_ready)
    );
    
endmodule:uart_soc
