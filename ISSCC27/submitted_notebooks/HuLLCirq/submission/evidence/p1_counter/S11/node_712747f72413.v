module release_counter (
    input wire clk_ctr,
    input wire rst_ctr,
    input wire [3:0] data_in,
    input wire data_in_valid,
    output wire data_in_ready,
    output wire [3:0] data_out,
    output wire data_out_valid,
    input wire data_out_ready
);

reg [3:0] accumulator;
reg valid_register;

assign data_out = accumulator;
assign data_out_valid = valid_register;
assign data_in_ready = (!valid_register) || data_out_ready;

always @(posedge clk_ctr) begin
    if (rst_ctr) begin
        accumulator <= 4'b0000;
        valid_register <= 1'b0;
    end else begin
        if ((!valid_register) || data_out_ready) begin
            valid_register <= data_in_valid;
            if (data_in_valid) begin
                accumulator <= accumulator + data_in;
            end
        end
    end
end

endmodule
