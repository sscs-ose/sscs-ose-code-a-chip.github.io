module hullcirq_npu2_collector (
    input wire clk,
    input wire rst,
    input wire signed [31:0] sum00,
    input wire sum00_valid,
    output wire sum00_ready,
    input wire signed [31:0] sum01,
    input wire sum01_valid,
    output wire sum01_ready,
    input wire signed [31:0] sum10,
    input wire sum10_valid,
    output wire sum10_ready,
    input wire signed [31:0] sum11,
    input wire sum11_valid,
    output wire sum11_ready,
    output wire signed [31:0] acc_data,
    output wire acc_data_valid,
    input wire acc_data_ready
);

reg [1:0] selected_lane;

assign sum00_ready = !rst && (selected_lane == 2'b00) && acc_data_ready;
assign sum01_ready = !rst && (selected_lane == 2'b01) && acc_data_ready;
assign sum10_ready = !rst && (selected_lane == 2'b10) && acc_data_ready;
assign sum11_ready = !rst && (selected_lane == 2'b11) && acc_data_ready;

assign acc_data = selected_lane == 2'b00 ? sum00 :
                 selected_lane == 2'b01 ? sum01 :
                 selected_lane == 2'b10 ? sum10 :
                 sum11;

assign acc_data_valid = !rst && ((selected_lane == 2'b00) ? sum00_valid : 
                                 (selected_lane == 2'b01) ? sum01_valid : 
                                 (selected_lane == 2'b10) ? sum10_valid : 
                                 sum11_valid);

always @(posedge clk) begin
    if (rst) begin
        selected_lane <= 2'b00;
    end else if (acc_data_valid && acc_data_ready) begin
        selected_lane <= selected_lane == 2'b11 ? 2'b00 : selected_lane + 1;
    end
end

endmodule
