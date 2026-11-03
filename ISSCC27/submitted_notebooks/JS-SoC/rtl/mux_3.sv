
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 09:35:17
// Design Name: 
// Module Name: mux_3
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


module mux_3(
    input logic [31:0] a,
    input logic [31:0] b,
    input logic [31:0] c,
    input logic [1:0] sel,
    output logic [31:0] y
    );
    always_comb
    begin
        case(sel)
        2'b00:y=a;
        2'b01:y=b;
        2'b10:y=c;
        default:y=32'bx;
    endcase
    end
endmodule:mux_3
