
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 18.06.2026 18:03:16
// Design Name: 
// Module Name: control_logic
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


module control_logic(
    input logic clk,
    input logic rst,
    input logic [31:0] data_word,
    input logic write,
    input logic pready_p,
    output logic [15:0] bit_16,
    output logic [7:0] counter_value,
    output logic [5:0] control_word,
    //(data_word[26],mode)
    //output logic [1:0] size_sel
    output logic master_ready
    );
    //control word 6-square back 5-square 4-auto back 3-auto 2-normal back 1-normal
    //data_word [31:0]
    //in that [15:0] is the data or counter value
    //next counter value for normal mode [23:16]
    //[25:24] is the selection of the mode 3 mode<=> normal,auto,quare(00,01,10)
    //[26] is for the forward or backword, 1 for forward 0 for backword
    //[28:27] is for selection of size//00-
    //rest bits for the time being no use
    assign master_ready=pready_p;
    always_ff @(posedge clk)  
        begin
            if(write)
            begin
            case(data_word[25:24])
                2'b00: 
                begin
                //normal mode
                if(data_word[26])
                    begin
                        control_word<=6'b000_001;//normal mode forward direction 
                        bit_16<=data_word[15:0];
                        counter_value<=data_word[23:16];
                    end
                else
                    begin
                        control_word<=6'b000_010;//normal mode reverse direction 
                        bit_16<=data_word[15:0];
                        counter_value<=data_word[23:16];
                    end
                end
                2'b01:
                begin
                    if(data_word[26])
                    begin
                        control_word<=6'b000_100;//auto mode forward direction 
                        bit_16<=data_word[15:0];
                        counter_value<=data_word[23:16];
                    end
                else
                    begin
                        control_word<=6'b001_000;//auto mode reverse direction 
                        bit_16<=data_word[15:0];
                        counter_value<=data_word[23:16];
                    end
                end
                2'b10:
                begin
                    if(data_word[26])
                    begin
                        control_word<=6'b010_000;//square mode forward direction 
                        bit_16<=data_word[15:0];
                        counter_value<=data_word[23:16];
                    end
                else
                    begin
                        control_word<=6'b100_000;//square mode reverse direction 
                        bit_16<=data_word[15:0];
                        counter_value<=data_word[23:16];
                    end
                end
                default:
                    begin
                        control_word<='0;//
                        bit_16<='0;
                        counter_value<='0;
                    end
            endcase
            end
            else if (rst) 
            begin
                bit_16<='0;
                control_word<='0;
                counter_value<='0;
            end
        end     
        always_comb
        begin
            if(|data_word[31:27])
            begin
            end
        end
endmodule:control_logic
