
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 17:46:42
// Design Name: 
// Module Name: alu
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


module alu(
    input logic [3:0] alu_con,
    input logic [31:0] a,//rd1
    input logic [31:0] b,//rd2
    output logic zero,
    output logic [31:0] result
    );
    always_comb
    begin
        case(alu_con)
        4'b0000:result=a+b;
        4'b0001:result=a-b;
        4'b0010:result=a<<b[4:0];
        4'b0011: if($signed(a)<$signed(b)) begin
                    result=32'b1;
                    end
                 else  begin
                    result='0;
                    end
        4'b0100: if(a<b) begin
                    result=32'b1;
                    end
                    else begin
                    result='0;
                    end  
        4'b0101:result=a^b;
        4'b0110:result=$signed(a)>>>b[4:0];
        4'b0111:result=a>>b[4:0];
        4'b1000:result=a|b;
        4'b1001:result=a&b;
        default:result=32'bx;
        endcase   
    end   
    assign zero=(result==32'b0); 
endmodule:alu
