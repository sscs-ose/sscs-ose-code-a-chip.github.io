module hullcirq_npu2_top(input clk, input rst, input [68:0] config_data, input config_data_valid, output config_data_ready, input [12:0] load_data, input load_data_valid, output load_data_ready, output signed [31:0] output_data, output output_data_valid, input output_data_ready, output busy, output job_done);

  wire [3:0] schedule_config;
  wire schedule_config_valid, schedule_config_ready;
  wire [64:0] post_config;
  wire post_config_valid, post_config_ready;
  wire [2:0] read_index;
  wire read_index_valid, read_index_ready;
  wire [31:0] operands;
  wire operands_valid, operands_ready;
  wire [33:0] batch_data;
  wire batch_data_valid, batch_data_ready;
  wire [17:0] pair00, pair01, pair10, pair11;
  wire pair00_valid, pair00_ready, pair01_valid, pair01_ready, pair10_valid, pair10_ready, pair11_valid, pair11_ready;
  wire signed [31:0] sum00, sum01, sum10, sum11;
  wire sum00_valid, sum00_ready, sum01_valid, sum01_ready, sum10_valid, sum10_ready, sum11_valid, sum11_ready;
  wire signed [31:0] acc_data;
  wire acc_data_valid, acc_data_ready;
  wire signed [31:0] result_data;
  wire result_data_valid, result_data_ready;
  wire output_transfer;
  wire buffer_load_data_ready;
  wire gated_load_data_valid;

  assign gated_load_data_valid = load_data_valid && !busy;
  assign load_data_ready = buffer_load_data_ready && !busy;

  hullcirq_npu2_control control(.clk(clk), .rst(rst), .config_data(config_data), .config_data_valid(config_data_valid), .config_data_ready(config_data_ready), .schedule_config(schedule_config), .schedule_config_valid(schedule_config_valid), .schedule_config_ready(schedule_config_ready), .post_config(post_config), .post_config_valid(post_config_valid), .post_config_ready(post_config_ready), .output_transfer(output_transfer), .busy(busy), .job_done(job_done));
  hullcirq_npu2_buffer buffer(.clk(clk), .rst(rst), .load_data(load_data), .load_data_valid(gated_load_data_valid), .load_data_ready(buffer_load_data_ready), .read_index(read_index), .read_index_valid(read_index_valid), .read_index_ready(read_index_ready), .operands(operands), .operands_valid(operands_valid), .operands_ready(operands_ready));
  hullcirq_npu2_scheduler scheduler(.clk(clk), .rst(rst), .schedule_config(schedule_config), .schedule_config_valid(schedule_config_valid), .schedule_config_ready(schedule_config_ready), .read_index(read_index), .read_index_valid(read_index_valid), .read_index_ready(read_index_ready), .operands(operands), .operands_valid(operands_valid), .operands_ready(operands_ready), .batch_data(batch_data), .batch_data_valid(batch_data_valid), .batch_data_ready(batch_data_ready));
  hullcirq_npu2_dispatcher dispatcher(.clk(clk), .rst(rst), .batch_data(batch_data), .batch_data_valid(batch_data_valid), .batch_data_ready(batch_data_ready), .pair00(pair00), .pair00_valid(pair00_valid), .pair00_ready(pair00_ready), .pair01(pair01), .pair01_valid(pair01_valid), .pair01_ready(pair01_ready), .pair10(pair10), .pair10_valid(pair10_valid), .pair10_ready(pair10_ready), .pair11(pair11), .pair11_valid(pair11_valid), .pair11_ready(pair11_ready));
  hullcirq_npu2_pe00 pe00(.clk(clk), .rst(rst), .pair_data(pair00), .pair_data_valid(pair00_valid), .pair_data_ready(pair00_ready), .sum_data(sum00), .sum_data_valid(sum00_valid), .sum_data_ready(sum00_ready));
  hullcirq_npu2_pe01 pe01(.clk(clk), .rst(rst), .pair_data(pair01), .pair_data_valid(pair01_valid), .pair_data_ready(pair01_ready), .sum_data(sum01), .sum_data_valid(sum01_valid), .sum_data_ready(sum01_ready));
  hullcirq_npu2_pe10 pe10(.clk(clk), .rst(rst), .pair_data(pair10), .pair_data_valid(pair10_valid), .pair_data_ready(pair10_ready), .sum_data(sum10), .sum_data_valid(sum10_valid), .sum_data_ready(sum10_ready));
  hullcirq_npu2_pe11 pe11(.clk(clk), .rst(rst), .pair_data(pair11), .pair_data_valid(pair11_valid), .pair_data_ready(pair11_ready), .sum_data(sum11), .sum_data_valid(sum11_valid), .sum_data_ready(sum11_ready));
  hullcirq_npu2_collector collector(.clk(clk), .rst(rst), .sum00(sum00), .sum00_valid(sum00_valid), .sum00_ready(sum00_ready), .sum01(sum01), .sum01_valid(sum01_valid), .sum01_ready(sum01_ready), .sum10(sum10), .sum10_valid(sum10_valid), .sum10_ready(sum10_ready), .sum11(sum11), .sum11_valid(sum11_valid), .sum11_ready(sum11_ready), .acc_data(acc_data), .acc_data_valid(acc_data_valid), .acc_data_ready(acc_data_ready));
  hullcirq_npu2_post post(.clk(clk), .rst(rst), .post_config(post_config), .post_config_valid(post_config_valid), .post_config_ready(post_config_ready), .acc_data(acc_data), .acc_data_valid(acc_data_valid), .acc_data_ready(acc_data_ready), .result_data(result_data), .result_data_valid(result_data_valid), .result_data_ready(result_data_ready));
  hullcirq_npu2_fifo fifo(.clk(clk), .rst(rst), .result_data(result_data), .result_data_valid(result_data_valid), .result_data_ready(result_data_ready), .output_data(output_data), .output_data_valid(output_data_valid), .output_data_ready(output_data_ready), .output_transfer(output_transfer));

endmodule
