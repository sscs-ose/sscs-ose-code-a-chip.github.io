module release_saturating_lane (
    input wire clk_array,
    input wire rst_array_n,
    input wire [7:0] data_i,
    input wire data_i_valid,
    output wire data_i_ready,
    output wire [3:0] data_o,
    output wire data_o_valid,
    input wire data_o_ready
);
    wire signed [4:0] operand_a = {data_i[7], data_i[7:4]};
    wire signed [4:0] operand_b = {data_i[3], data_i[3:0]};
    wire signed [4:0] sum = operand_a + operand_b;
    wire [3:0] clipped = (sum > 5'sd7) ? 4'd7 : ((sum < -5'sd8) ? 4'h8 : sum[3:0]);
    reg [3:0] slot_data;
    reg slot_valid;
    assign data_i_ready = (!slot_valid) || data_o_ready;
    assign data_o = slot_data;
    assign data_o_valid = slot_valid;
    always @(posedge clk_array) begin
        if (!rst_array_n) begin
            slot_data <= 4'd0;
            slot_valid <= 1'b0;
        end else if (data_i_ready) begin
            slot_valid <= data_i_valid;
            if (data_i_valid) slot_data <= clipped;
        end
    end
endmodule
