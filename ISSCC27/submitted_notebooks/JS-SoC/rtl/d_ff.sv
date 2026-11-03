
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 09:38:54
// Design Name: 
// Module Name: d_ff
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


module d_ff(
    input logic [31:0] d,
    input logic clk,
    input logic rst,
    input logic stall,
    output logic [31:0] out
    );
    always_ff @( posedge clk)
        begin
            if(rst | stall)
                out<='0;
            else
                out<=  d;
        end
endmodule:d_ff
