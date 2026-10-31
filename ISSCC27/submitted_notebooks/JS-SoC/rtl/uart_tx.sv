
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 26.05.2026 09:17:27
// Design Name: 
// Module Name: uart_tx
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


module uart_tx(
    input logic clk,
    input logic wr_en,
    input logic en, // baud rate enable (1 tick per bit)
    input logic rst,
    input logic [7:0] data_in,
    output logic tx, 
    output logic busy
    );
    typedef enum logic [1:0] {S0, S1, S2, S3} state_t;
    state_t state;
    logic [7:0] data;
    logic [2:0] index;

    always_ff @(posedge clk) begin
        if(rst) begin
            tx    <= 1'b1;
            state <= S0;
            data  <= 8'b0;
            index <= 3'b0;
        end else begin
            case(state)
                S0: begin // Idle state
                    tx <= 1'b1;
                    if(wr_en) begin
                        //$display("UART LATCH @%0t data_in=%h",$time,data_in);
                        state <= S1;
                        data  <= data_in;
                        index <= 3'b0;
                    end
                end
                S1: begin // Start bit state
                    if(en) begin
                        tx    <= 1'b0; // Drive line low
                        state <= S2;
                    end
                end
                S2: begin // Data bit transmission
                    if(en) begin
                        tx <= data[index];
                        if(index == 3'b111)
                            state <= S3;
                        else 
                            index <= index + 1'b1;
                    end
                end
                S3: begin // Stop bit state
                    if(en) begin
                        tx    <= 1'b1; // Drive line high
                        state <= S0;
                    end 
                end                  
                default: state <= S0;
            endcase
        end           
    end 
    assign busy = (state != S0);
    
//    always @(posedge clk)
//    begin
//    if(en)
//        $display(
//            "TX t=%0t state=%0d tx=%b index=%0d",
//            $time,state,tx,index
//        );
//    end

endmodule:uart_tx

