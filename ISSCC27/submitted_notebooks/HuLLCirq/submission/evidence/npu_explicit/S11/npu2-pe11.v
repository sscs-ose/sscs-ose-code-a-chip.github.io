module hullcirq_npu2_pe11 (
    input wire clk,
    input wire rst,
    input wire [17:0] pair_data,
    input wire pair_data_valid,
    output wire pair_data_ready,
    output wire signed [31:0] sum_data,
    output wire sum_data_valid,
    input wire sum_data_ready
);

reg [31:0] accumulator;
reg [31:0] result;
reg result_pending;

wire signed [7:0] a;
wire signed [7:0] b;
wire signed [15:0] product;
wire signed [31:0] extended_product;
wire signed [31:0] updated_sum;

assign a = pair_data[7:0];
assign b = pair_data[15:8];
assign product = a * b;
assign extended_product = {{16{product[15]}}, product};
assign updated_sum = pair_data[16] ? extended_product : ($signed(accumulator) + extended_product);

assign pair_data_ready = !rst && !result_pending;
assign sum_data_valid = result_pending && !rst;
assign sum_data = result_pending ? result : 32'b0;

always @(posedge clk) begin
    if (rst) begin
        accumulator <= 32'b0;
        result <= 32'b0;
        result_pending <= 0;
    end else begin
        if (pair_data_valid && pair_data_ready) begin
            accumulator <= updated_sum;
            if (pair_data[17]) begin
                result <= updated_sum;
                result_pending <= 1;
            end
        end else if (sum_data_valid && sum_data_ready && result_pending) begin
            result_pending <= 0;
        end
    end
end

endmodule
