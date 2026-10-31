
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 26.05.2026 10:51:23
// Design Name: 
// Module Name: uart_rx
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


module uart_rx(
    input  logic       clk,
    input  logic       rst,
    input  logic       rdy_clr,
    input  logic       en, // 16x oversampling clock tick
    input  logic       rx, 
    output logic       rdy,
    output logic [7:0] data_out
    );

    typedef enum logic [1:0] {S0, S1, S2} state_t;
    state_t state;
    logic [2:0] index;
    logic [7:0] temp;
    logic [3:0] sample; 

    always_ff @(posedge clk) begin
        if(rst) begin
            rdy      <= 1'b0;
            data_out <= 8'h0;
            sample   <= 4'd0;
            state    <= S0;
            temp     <= 8'h0;
            index    <= 3'd0;
        end else begin
            // Handshake clear
            if(rdy_clr) rdy <= 1'b0;

            else if(en) begin
                case(state)
                    S0: begin // Idle: Look for falling edge of Start Bit
                        if(rx == 1'b0) begin
                            // Sample at tick 8 (center of start bit)
                            if(sample == 4'd7) begin 
                                state  <= S1;
                                sample <= 4'd0;
                                index  <= 3'd0;
                                temp   <= 8'h0;
                            end else begin
                                sample <= sample + 1'b1;
                            end
                        end else begin
                            sample <= 4'd0;
                        end
                    end
                    
                    S1: begin // Data Bits: Sample at middle of every 16-tick period
                        if(sample == 4'd15) begin 
                            sample      <= 4'd0;
                            temp[index] <= rx; // Sample at the center
                            if(index == 3'b111) begin
                                state <= S2;
                                index <= 3'd0;
                            end else begin
                                index <= index + 1'b1;
                            end
                        end else begin
                            sample <= sample + 1'b1;
                        end
                    end
                    
                    S2: begin // Stop Bit: Verify and finish
                        if(sample == 4'd15) begin
                            if(rx == 1'b1) begin
                                data_out <= temp;
                                rdy      <= 1'b1;
                            end
                            state  <= S0;
                            sample <= 4'd0;
                        end else begin
                            sample <= sample + 1'b1;
                        end
                    end
                    default: state <= S0;
                endcase
            end
        end
    end

endmodule: uart_rx
