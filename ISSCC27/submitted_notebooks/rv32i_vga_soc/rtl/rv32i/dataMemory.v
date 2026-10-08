module dataMemory (
    input             clk,
    input             load,
    input             write,
    input      [31:0] address,
    input      [31:0] data_in,
    output reg [31:0] data_out
);


    reg [7:0] memory [0:255];

    always @(posedge clk) begin
        if (write) begin
            memory[address]     <= data_in[7:0];   
            memory[address + 1] <= data_in[15:8];  
            memory[address + 2] <= data_in[23:16]; 
            memory[address + 3] <= data_in[31:24]; 
        end

        if (load) begin
            data_out <= {
                memory[address + 3], 
                memory[address + 2], 
                memory[address + 1], 
                memory[address]     
            };
        end
    end

endmodule
