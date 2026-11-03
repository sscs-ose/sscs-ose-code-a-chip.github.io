// Development-assistant software QA fixture only. Never imported as generated user RTL.
// Finite checker qualification; not evidence that the active NPU passes.
module hullcirq_npu2_pe00(
 input wire clk,
 input wire rst,
 input wire [17:0] pair_data,
 input wire pair_data_valid,
 output wire pair_data_ready,
 output wire signed [31:0] sum_data,
 output wire sum_data_valid,
 input wire sum_data_ready);
reg signed [31:0] accumulator, out_data;
reg out_valid;
wire signed [7:0] a = pair_data[7:0];
wire signed [7:0] b = pair_data[15:8];
wire signed [15:0] product = a * b;
wire signed [31:0] extended_product = {{16{product[15]}},product};
wire signed [31:0] next_accumulator = pair_data[16] ? extended_product : accumulator + extended_product;
assign pair_data_ready = !out_valid;
assign sum_data_valid = out_valid;
assign sum_data = out_data;
always @(posedge clk) begin
 if (rst) begin accumulator<=0; out_data<=0; out_valid<=0; end
 else if (pair_data_valid && pair_data_ready) begin
  accumulator <= next_accumulator;
  if (pair_data[17]) begin out_data<=next_accumulator; out_valid<=1; end
 end else if (sum_data_valid && sum_data_ready) out_valid<=0;
end
endmodule

// Development-assistant software QA fixture only. Never imported as generated user RTL.
// Finite checker qualification; not evidence that the active NPU passes.
module hullcirq_npu2_collector(
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
 input wire acc_data_ready);
reg [1:0] selected;
assign sum00_ready = !rst && selected==0 && acc_data_ready;
assign sum01_ready = !rst && selected==1 && acc_data_ready;
assign sum10_ready = !rst && selected==2 && acc_data_ready;
assign sum11_ready = !rst && selected==3 && acc_data_ready;
assign acc_data_valid = !rst && (selected==0 ? sum00_valid : selected==1 ? sum01_valid : selected==2 ? sum10_valid : sum11_valid);
assign acc_data = selected==0 ? sum00 : selected==1 ? sum01 : selected==2 ? sum10 : sum11;
always @(posedge clk) begin
 if (rst) selected<=0;
 else if (acc_data_valid && acc_data_ready) selected<=selected+1'b1;
end
endmodule

// Development-assistant software QA fixture only. Never imported as generated user RTL.
// Finite checker qualification; not evidence that the active NPU passes.
module hullcirq_npu2_post(
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
 input wire result_data_ready);
reg configured;
reg [1:0] result_index;
reg [64:0] saved_config;
reg out_valid;
reg [31:0] out_data;
wire [31:0] bias = result_index[0] ? saved_config[64:33] : saved_config[32:1];
wire [31:0] wrapped = acc_data + bias;
assign post_config_ready = !configured && !out_valid && result_index==0;
assign acc_data_ready = configured && (!out_valid || result_data_ready) && !post_config_valid;
assign result_data = out_data;
assign result_data_valid = out_valid;
always @(posedge clk) begin
 if (rst) begin configured<=0; result_index<=0; saved_config<=0; out_valid<=0; out_data<=0; end
 else begin
  if (post_config_valid && post_config_ready) begin saved_config<=post_config; configured<=1; result_index<=0; end
  if (acc_data_valid && acc_data_ready) begin
   out_data <= saved_config[0] && wrapped[31] ? 32'b0 : wrapped;
   out_valid<=1;
   result_index<=result_index+1'b1;
   if (result_index==3) configured<=0;
  end else if (result_data_valid && result_data_ready) out_valid<=0;
 end
end
endmodule
