
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 22.06.2026 17:26:07
// Design Name: 
// Module Name: timer
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


module timer(
    input logic clk,
    input logic rst,
    input logic [31:0] data_word,
    input logic write,
    output logic master_ready,
    output logic wave1,
    output logic wave2
    );
    logic [15:0] bit_16;
    logic [7:0] counter_value;
    logic [5:0] control_word;
    logic ready;
    
    control_logic control_logic1(
                                .clk(clk),
                                .rst(rst),
                                .data_word(data_word),
                                .write(write),
                                .pready_p(ready),
                                .bit_16(bit_16),
                                .counter_value(counter_value),
                                .control_word(control_word),
                                .master_ready(master_ready)
                            );
                            
    
    decoder_logic decoder_logic1(
                                 .clk(clk),
                                 .rst(rst),
                                 .bit_16(bit_16),
                                 .counter_value(counter_value),
                                 .control_word(control_word),
                                 .ready(ready),
                                 .wave1(wave1),
                                 .wave2(wave2)
                            );
                                                     
                            
endmodule:timer
