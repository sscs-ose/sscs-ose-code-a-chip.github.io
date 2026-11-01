module hullcirq_npu2_post (
    input wire clk,
    input wire rst,
    input wire [64:0] post_config,
    input wire post_config_valid,
    output wire post_config_ready,
    input wire signed [31:0] acc_data,
    input wire acc_data_valid,
    output wire acc_data_ready,
    output wire signed [31:0] result_data,
    output wire result_data_valid,
    input wire result_data_ready
);

reg [64:0] config_reg;
reg configured;
reg [1:0] result_index;
reg [31:0] result_reg;
reg pending;

wire signed [31:0] bias;
wire [31:0] wrapped;

assign bias = result_index[0] ? $signed(config_reg[64:33]) : $signed(config_reg[32:1]);
assign wrapped = $signed(acc_data) + bias;

assign post_config_ready = !rst && !configured && !pending && (result_index == 2'b00);
assign acc_data_ready = !rst && configured && !post_config_valid && (!pending || result_data_ready);
assign result_data_valid = pending && !rst;
assign result_data = pending ? result_reg : 32'b0;

always @(posedge clk) begin
    if (rst) begin
        config_reg <= 65'b0;
        configured <= 0;
        result_index <= 2'b00;
        result_reg <= 32'b0;
        pending <= 0;
    end else begin
        if (post_config_valid && post_config_ready) begin
            config_reg <= post_config;
            configured <= 1;
            result_index <= 2'b00;
            pending <= 0;
        end else if (acc_data_valid && acc_data_ready) begin
            if (config_reg[0] && (wrapped[31] == 1'b1)) begin
                result_reg <= 32'b0;
            end else begin
                result_reg <= wrapped;
            end
            pending <= 1;
            if (result_index == 2'b11) begin
                configured <= 1'b0;
                result_index <= 2'b00;
            end else begin
                result_index <= result_index + 2'd1;
            end
        end else if (result_data_valid && result_data_ready && pending) begin
            pending <= 0;
        end
    end
end

endmodule
