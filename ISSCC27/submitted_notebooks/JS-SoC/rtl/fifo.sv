
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.06.2026 12:03:12
// Design Name: 
// Module Name: fifo
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


module fifo #(parameter depth=4,
              parameter width=64)(
    input logic clk,
    input logic rst,
    input logic w_en,//apb_write from the bridge side
    input logic r_en,//from the master side
    input logic [width-1:0] data_in,
    output logic [width-1:0] data_out,
    output logic full,
    output logic empty
);
localparam ptr_width=$clog2(depth);
logic [ptr_width:0] w_ptr,r_ptr;
logic [width-1:0] array[depth-1:0];


always_ff @(posedge clk)
    begin 
        if(rst)
            begin
                w_ptr<=0;
            end
        else if(w_en && !full)
            begin
                array[w_ptr[ptr_width-1:0]]<=data_in;
                w_ptr<=w_ptr+1;
            end
    end
always_ff @(posedge clk)
    begin
        if(rst)
            begin
                r_ptr<=0;
                //data_out<=0;
            end
        else if(r_en && !empty)
            begin
                r_ptr<=r_ptr+1;
                //data_out<=array[r_ptr[ptr_width-1:0]];
            end
    end
assign data_out=array[r_ptr[ptr_width-1:0]];

assign empty=(r_ptr==w_ptr);
assign full=(r_ptr[ptr_width]!=w_ptr[ptr_width])&(r_ptr[ptr_width-1:0]==w_ptr[ptr_width-1:0]);
endmodule:fifo
