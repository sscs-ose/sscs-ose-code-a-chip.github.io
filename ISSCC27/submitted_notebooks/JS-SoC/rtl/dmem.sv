
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 23:25:24
// Design Name: 
// Module Name: dmem
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



//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 23:25:24
// Design Name: 
// Module Name: dmem
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


module dmem(
    input logic clk,
    input logic [31:0] a,
    input logic [31:0] write_data,
    input logic mem_write,
    output logic [31:0] out
    );
    logic [31:0] ram[10:0];
    assign out=ram[a[5:2]];
    always_comb begin
    if(|a[1:0]) begin
    end
    end
    always_comb begin
    if(|a[31:6]) begin
    end
    end
    always_ff @(posedge clk)
        if(mem_write)
            begin
            ram[a[5:2]]<=write_data;
            end
endmodule:dmem
