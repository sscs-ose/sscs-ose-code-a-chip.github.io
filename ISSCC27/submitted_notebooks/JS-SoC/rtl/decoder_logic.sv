
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 22.06.2026 10:20:05
// Design Name: 
// Module Name: decoder_logic
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


module decoder_logic(
    input logic clk,
    input logic rst,
    input logic [15:0] bit_16,
    input logic [7:0] counter_value,
    input logic [5:0] control_word,
    output logic ready,
    output logic wave1,
    output logic wave2
    );
    logic write_normal,write_square;
    logic pready_1,pready_2;
    always_comb
    begin
        write_normal=0;
        write_square=0;
        case(control_word)
            6'b000_001: write_normal=1;
            6'b010_000:write_square=1;
            default:
                    begin
                        write_normal=0;
                        write_square=0;
                    end
        endcase        
    end
    
    normal #(.N(16)) normal_time(.clk(clk),.rst(rst),
                                 .write(write_normal),
                                 .data_in(bit_16),
                                 .count(counter_value),
                                 .wave(wave1),
                                 .pready_p(pready_1)
                                 );
                    
    square #(.N(16)) square_time(.clk(clk),.rst(rst),
                                 .write(write_square),
                                 .data_in(bit_16),
                                 .wave(wave2),
                                 .pready_p(pready_2)
                                 );
   
   assign ready=pready_1 && pready_2;
        
    
endmodule:decoder_logic
