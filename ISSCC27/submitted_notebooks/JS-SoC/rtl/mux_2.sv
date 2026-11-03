
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 09:27:30
// Design Name: 
// Module Name: mux_2
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


module mux_2(
    input logic [31:0] a,
    input logic [31:0] b,
    input logic sel,
    output logic [31:0] y
    );
    always_comb
    begin
    case(sel)
        1'b0:y=a;
        1'b1:y=b;
        default:y=32'bx;
    endcase
    end
endmodule:mux_2
