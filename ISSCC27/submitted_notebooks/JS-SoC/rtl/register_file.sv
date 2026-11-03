
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 20:35:35
// Design Name: 
// Module Name: register_file
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


module register_file(
    input logic [4:0] a1,
    input logic [4:0] a2,
    input logic [4:0] a3,
    input logic [31:0] data,
    input logic reg_write,
    input logic clk,
    output logic [31:0] rd1,
    output logic [31:0] rd2
    );
    
    logic [31:0] register [31:0];
    
    // Clear array elements at start to prevent simulation floats
    initial begin
        integer i;
        for (i = 0; i < 32; i = i + 1) begin
            register[i] = 32'b0;
        end
    end
    
    // Enforce hardcoded zero lookups regardless of port input slicing vector indices
    assign rd1 = (a1 == 0) ? 32'b0 : register[a1];
    assign rd2 = (a2 == 0) ? 32'b0 : register[a2];
    
    // Synchronous write block
    always_ff @(posedge clk)
    begin
        if(reg_write && a3 != 0)
            begin
            register[a3] <= data;
            end
   end
endmodule:register_file

