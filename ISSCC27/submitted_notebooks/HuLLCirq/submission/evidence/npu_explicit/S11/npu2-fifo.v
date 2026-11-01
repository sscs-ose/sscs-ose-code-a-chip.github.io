module hullcirq_npu2_fifo (
    input wire clk,
    input wire rst,
    input wire signed [31:0] result_data,
    input wire result_data_valid,
    output wire result_data_ready,
    output wire signed [31:0] output_data,
    output wire output_data_valid,
    input wire output_data_ready,
    output wire output_transfer
);

reg [31:0] storage [1:0];
reg read_ptr;
reg write_ptr;
reg [1:0] count;

assign output_data_valid = count != 2'd00 && !rst;
assign output_data = count != 2'd00 ? storage[read_ptr] : 32'b0;
assign output_transfer = output_data_valid && output_data_ready;
assign result_data_ready = !rst && ((count < 2'd2) || (output_data_valid && output_data_ready));

always @(posedge clk) begin
    if (rst) begin
        read_ptr <= 1'b0;
        write_ptr <= 1'b0;
        count <= 2'd00;
    end else begin
        if (result_data_valid && result_data_ready) begin
            storage[write_ptr] <= result_data;
            write_ptr <= ~write_ptr;
        end
        if (output_data_valid && output_data_ready) read_ptr <= ~read_ptr;
        case ({result_data_valid && result_data_ready, output_data_valid && output_data_ready})
            2'b10: count <= count + 2'd1;
            2'b01: count <= count - 2'd1;
            default: count <= count;
        endcase
    end
end

endmodule
