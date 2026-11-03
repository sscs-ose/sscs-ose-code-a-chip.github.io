
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 18.06.2026 00:01:59
// Design Name: 
// Module Name: square
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


module square #(parameter N=16)(
    input logic clk,
    input logic rst,
    input logic write,
    input logic [N-1:0] data_in,
    output logic wave,
    output logic pready_p
    );
    assign pready_p=1'b1;
    logic write_pending;
    logic running;
    logic [N-1:0] mem;
    logic [N-1:0] counter;
    typedef enum logic [1:0] {idle,counting} state_t;
    state_t state;
    always_ff @ (posedge clk)
        begin
        if(rst)
            begin
            wave<=1'b0;
            mem<='0;
            counter<='0;
            state<=idle;
            write_pending<=1'b0;
            running<=1'b0;
            end
        else
            begin
                if(write)
                    begin
                    mem<=data_in;
                    if(data_in !='0)
                        begin
                        running<=1'b1;
                        write_pending<=1'b1;
                        end
                    else
                        begin
                        running<=1'b0;
                        write_pending<=1'b0;
                        end
                    end
                case(state)
                        idle:
                            begin
                                wave<=1'b0;
                                if(write_pending)
                                    begin
                                    counter<='0;
                                    write_pending<=1'b0;
                                    state<=counting;
                                    end
                                else
                                    begin
                                    end
                            end
                        counting:
                            begin
                                wave<=1'b0;
                                if(!running)
                                    begin
                                    state<=idle;
                                    wave<=1'b0;
                                    end
                                else if(counter==mem)
                                    begin
                                    counter<='0;
                                    wave<=~wave;
                                    end
                                else
                                    begin
                                    counter<=counter+1'b1;
                                    wave<=1'b0;
                                    end
                            end
                    default:state<=idle;
                    endcase
                end
        end                  
endmodule:square 
