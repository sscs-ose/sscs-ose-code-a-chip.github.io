// ============================================================================
// crc16_ccitt.v  -  CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)
// ============================================================================
module crc16_ccitt (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        crc_reset,
    input  wire        byte_valid,
    input  wire [7:0]  byte_in,
    output reg  [15:0] crc_out
);
    function [15:0] crc16_byte;
        input [15:0] c;
        input [7:0]  d;
        integer i;
        reg [15:0] x;
        begin
            x = c ^ {d, 8'h00};
            for (i = 0; i < 8; i = i + 1) begin
                if (x[15])
                    x = {x[14:0], 1'b0} ^ 16'h1021;
                else
                    x = {x[14:0], 1'b0};
            end
            crc16_byte = x;
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            crc_out <= 16'hFFFF;
        else if (crc_reset)
            crc_out <= 16'hFFFF;
        else if (byte_valid)
            crc_out <= crc16_byte(crc_out, byte_in);
    end
endmodule
