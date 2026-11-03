
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 02.06.2026 10:42:20
// Design Name: 
// Module Name: serializer
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


module serializer(
    input  logic        clk,
    input  logic        rst,
    input  logic [31:0] data_in,
    input  logic        wr_en,
    input  logic        busy,
    //input  logic        tx,

    output logic [7:0]  data_out,
    output logic        master_busy,
    output logic        master_write
);

    logic [31:0] mem;
    logic [1:0]  counter;
    logic        waiting_for_busy;

    always_ff @(posedge clk) begin
        if(rst) begin
            mem              <= 32'b0;
            counter          <= 2'b00;
            data_out         <= 8'b0;
            master_busy      <= 1'b0;
            master_write     <= 1'b0;
            waiting_for_busy <= 1'b0;
        end
        else begin

            master_write <= 1'b0;

            // Load a new 32-bit word
            if(wr_en) begin
                mem              <= data_in;
                counter          <= 2'b00;
                master_busy      <= 1'b1;
                waiting_for_busy <= 1'b0;
            end

            else if(master_busy) begin

                // Issue a byte only when UART is idle
                if(!waiting_for_busy && !busy) begin

                    case(counter)
                        2'd0: data_out <= mem[31:24];
                        2'd1: data_out <= mem[23:16];
                        2'd2: data_out <= mem[15:8];
                        2'd3: data_out <= mem[7:0];
                    endcase

                    master_write     <= 1'b1;
                    waiting_for_busy <= 1'b1;
                end

                // Wait until UART actually becomes busy
                else if(waiting_for_busy && busy) begin

                    waiting_for_busy <= 1'b0;

                    if(counter == 2'd3) begin
                        counter     <= 2'b00;
                        master_busy <= 1'b0;
                    end
                    else begin
                        counter <= counter + 1'b1;
                    end
                end
            end
        end
    end


endmodule
