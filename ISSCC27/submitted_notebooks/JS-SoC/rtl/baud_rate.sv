
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 25.05.2026 18:07:07
// Design Name: 
// Module Name: baud_rate
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


module baud_rate(
    input  logic clk,
    input  logic rst,
    output logic tx_en,
    output logic rx_en
);

logic [12:0] transmitter;
logic [8:0]  receiver;

always_ff @(posedge clk) begin
    if(rst) begin
        transmitter <= 13'd0;
        tx_en <= 1'b0;
    end
    else if(transmitter == 13'd31) begin
        transmitter <= 13'd0;
        tx_en <= 1'b1;
    end
    else begin
        transmitter <= transmitter + 1'b1;
        tx_en <= 1'b0;
    end
end

always_ff @(posedge clk) begin
    if(rst) begin
        receiver <= 9'd0;
        rx_en <= 1'b0;
    end
    else if(receiver == 9'd1) begin
        receiver <= 9'd0;
        rx_en <= 1'b1;
    end
    else begin
        receiver <= receiver + 1'b1;
        rx_en <= 1'b0;
    end
end

endmodule
