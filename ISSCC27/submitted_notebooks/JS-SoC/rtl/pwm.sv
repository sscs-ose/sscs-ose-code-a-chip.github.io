
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 11.06.2026 17:09:35
// Design Name: 
// Module Name: pwm
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


module pwm(
    input logic clk,
    input logic [31:0] data,
    input logic rst,
    //input logic psel,
    //input logic penable,
    input logic write,
    output logic wave,
    //output logic busy,
    output logic pready_p
    );
    assign pready_p=1'b1;
    logic [31:0] pwm_data;
    always_ff @ (posedge clk)
        begin
        if(rst)
            pwm_data<=32'b0;
        else if(write)
            pwm_data<=data;
        end
        
    logic [15:0] period;
    assign period= pwm_data[31:16];
    
    logic [15:0] duty;
    assign duty=pwm_data[15:0];
    
    logic enable;
    assign enable= (pwm_data!=32'b0);
    
    logic [15:0] counter;
    
    always_ff @(posedge clk)
    begin
        if(rst)
        begin
            counter <= 16'd0;
            //busy    <= 1'b0;
        end
        else if(enable && period != 0)
        begin
            if(counter == period-1)
                counter <= 16'd0;
            else
                counter <= counter + 16'd1;

            //busy <= 1'b1;
        end
        else
        begin
            counter <= 16'd0;
            //busy    <= 1'b0;
        end
    end
    assign wave=(counter<duty) && enable;         
endmodule:pwm
