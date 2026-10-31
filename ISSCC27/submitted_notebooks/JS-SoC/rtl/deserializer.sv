
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 02.06.2026 18:42:46
// Design Name: 
// Module Name: deserializer
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
 
module deserializer(
    input  logic        clk,
    input  logic        rst,
    input  logic        ready,
    input  logic [7:0]  data_in,

    output logic        rdy_clear,
    output logic [31:0] data_out,
    output logic        master_ready
);

    logic [1:0]  counter;
    logic [31:0] mem;

    logic ready_d;
    logic ready_pulse;

    assign ready_pulse = ready & ~ready_d;

    always_ff @(posedge clk) begin
        if(rst)
            ready_d <= 1'b0;
        else
            ready_d <= ready;
    end
    	
    always_comb begin
    if(|mem[7:0])begin
    end
    end
    always_ff @(posedge clk) begin
        if(rst) begin
            master_ready <= 1'b0;
            rdy_clear    <= 1'b0;
            data_out     <= 32'b0;
            counter      <= 2'b00;
            mem          <= 32'b0;
        end
        else begin

            rdy_clear    <= 1'b0;
            master_ready <= 1'b0;

            if(ready_pulse) begin

                rdy_clear <= 1'b1;

                case(counter)
                    2'b00: mem[31:24] <= data_in;
                    2'b01: mem[23:16] <= data_in;
                    2'b10: mem[15:8]  <= data_in;

                    2'b11: begin
                        mem[7:0] <= data_in;
                        data_out <= {mem[31:8], data_in};
                        master_ready <= 1'b1;
                    end
                endcase

                if(counter == 2'b11)
                    counter <= 2'b00;
                else
                    counter <= counter + 1'b1;

            end
        end
    end
    

endmodule:deserializer
