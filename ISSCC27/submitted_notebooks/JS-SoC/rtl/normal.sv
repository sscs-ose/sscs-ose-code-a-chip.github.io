
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 16.06.2026 23:45:40
// Design Name: 
// Module Name: normal
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


module normal #(parameter N=16)(
    input logic clk,
    input logic rst,
    input logic write,
    input logic [N-1:0] data_in,
    input logic [7:0] count,
    output logic wave,
    output logic pready_p
    );
    
    logic [N-1:0] mem;
    logic [N-1:0] counter;
    logic [7:0] mem_1;
    logic [7:0] counter_1;
    //logic write_pending;
    //logic busy;
    assign pready_p=1'b1;
    typedef enum logic [1:0] {idle,counting,pulse} state_t;
    state_t state;
    always_ff @ (posedge clk)
        begin
        if(rst)
            begin
            wave<=1'b0;
            //busy<=1'b0;
            mem<='0;
            counter<='0;
            mem_1<='0;
            counter_1<='0;
            //write_pending<=0;
            state<=idle;
            end
        else
            begin
            if(write)
                begin
                    mem<=data_in;
                    mem_1<=count;
//                    if(data_in !='0 && ~busy)
//                        begin
//                        write_pending<=1'b1;
//                        end
                end
            case(state)
                idle:
                begin
                    wave<=1'b0;
                    if(mem !=0)
                        begin
                        counter<='0;
                        counter_1<='0;
                        //busy<=1'b1;
                        //write_pending<=1'b0;
                        state<=counting;
                        end
                end
                
                counting:
                begin
                    //busy<=1'b1;
                    if(counter==mem)
                        begin
                        counter<='0;
                        wave<=1'b1;
                        
                        if(mem_1==8'b0)
                            begin
                            state<=idle;
                            end
                        else
                            state<=pulse;
                        end
                    else 
                        begin
                            counter<=counter+1'b1;
                        end
                    end
                pulse:
                begin
                    wave<=1'b1;
                    //busy<=1'b1;
                    if(counter_1==mem_1)
                        begin
                        counter_1<='0;
                        wave<=1'b0;
                        //busy<=1'b0;
                        state<=idle;
//                        mem<='0;
//                        mem_1<='0;
                        end
                    else
                        begin
                        counter_1<=counter_1+1'b1;
                        end
                end
                
                default:state<=idle;
            endcase
        end
    end              
                        
                        
                    
endmodule:normal
