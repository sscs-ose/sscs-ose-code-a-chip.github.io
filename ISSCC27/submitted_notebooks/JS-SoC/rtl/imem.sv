
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 23:12:53
// Design Name: 
// Module Name: imem
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


module imem(
    input logic clk,
    input logic rst,
    input  logic [31:0] a, //boot_data _in or address for PC
    input logic [4:0] boot_address,
    input logic imem_write,
    input logic hold,
    output logic [31:0] out
);

    logic [31:0] ram [31:0];

//    initial begin
//        ram[0]  = 32'h40000537;
//        ram[1]  = 32'h486925B7;
//        ram[2]  = 32'h12158593;
//        ram[3]  = 32'h00B52023;
//        ram[4]  = 32'h00850513;
//        ram[5]  = 32'h000A05B7;
//        ram[6]  = 32'h00358593;
//        ram[7]  = 32'h00B52023;
//        ram[8]  = 32'h00450513;
//        ram[9]  = 32'h0C0A05B7;
//        ram[10] = 32'h00658593;
//        ram[11] = 32'h00B52023;
//        ram[12] = 32'h0E0005B7;
//        ram[13] = 32'h00A58593;
//        ram[14] = 32'h00B52023;
//        ram[15] = 32'h00F00093;
//        ram[16] = 32'h01400113;
//        ram[17] = 32'h002081B3;
//        ram[18] = 32'h40118233;
//        ram[19] = 32'h004182B3;
//        ram[20] = 32'hFF628313;
//        ram[21] = 32'h00000063;
//    end
    integer i;
    always_ff @(posedge clk)
    begin
        if(rst)
        begin
            for(i=0;i<32;i=i+1)
            begin
                ram[i]<='0;
            end
        end
        else
        begin
            if(imem_write)
            begin
                ram[boot_address]<=a;
            end
        end
    end    
    
    
    //assign out = ram[a[6:2]]
    always_comb
    begin
        if(hold)
        begin
            out='0;
        end
        else
        begin
            out = ram[a[6:2]];
        end
    end
    
    always_comb begin
    if((|a[31:7]) & (|a[1:0]))begin
    end
    end
endmodule:imem
