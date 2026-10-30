// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/top/protocol_emulator.sv
// Module: protocol_emulator
// Type: Top level (chip core)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator
// Submodules: uart_rx, control_unit, emulator_channel (x2), return_path
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module protocol_emulator #(
	parameter int RATIO_WIDTH = 16,
	parameter int blocks = 7,
	parameter int buffer_depth = 16,
	parameter int host_depth = 8
) (
	input logic clk,
	input logic rst_n,
	input logic rx_serial,
	input logic [7:0] pin_in,

	output logic tx_serial,
	output logic data_out_a,
	output logic data_oe_a,
	output logic pair_out_a,
	output logic pair_oe_a,
	output logic clock_out_a,
	output logic clock_oe_a,
	output logic select_out_a,
	output logic armed_a,
	output logic host_full_a,
	output logic data_out_b,
	output logic data_oe_b,
	output logic pair_out_b,
	output logic pair_oe_b,
	output logic clock_out_b,
	output logic clock_oe_b,
	output logic select_out_b,
	output logic armed_b,
	output logic host_full_b,
	output logic baud_locked
);

logic [7:0] pinSync;
logic [7:0] pinStable;
logic [7:0] pins;
logic [RATIO_WIDTH-1:0] rx_ratio;
logic [RATIO_WIDTH-1:0] tx_ratio;
logic [7:0] rx_data;
logic [3:0] cfg_sel;
logic [7:0] cfg_compare;
logic [7:0] cfg_cycles;
logic [2:0] cfg_pin;
logic [1:0] cfg_group;
logic [15:0] cfg_main_cycles;
logic [15:0] cfg_end_pattern;
logic [2:0] cfg_pin_b;
logic [1:0] run_mode;
logic [11:0] host_wdata;
logic [15:0] line_a;
logic [15:0] line_b;
logic [31:0] clock_a;
logic [31:0] clock_b;
logic [7:0] out_a;
logic [7:0] out_b;
logic [15:0] link_div;
logic [3:0] host_len_a;
logic [7:0] host_data_a;
logic [3:0] host_len_b;
logic [7:0] host_data_b;
logic [3:0] events;
logic rx_valid;
logic rx_error;
logic cmd_error;
logic cfg_we_a;
logic cfg_we_b;
logic cfg_capture;
logic cfg_write;
logic cfg_sr;
logic cfg_any;
logic cfg_seek;
logic cfg_follow;
logic cfg_wait_end;
logic cfg_ack;
logic cfg_pair;
logic cfg_invert;
logic cfg_error;
logic run_a;
logic run_b;
logic halt_a;
logic halt_b;
logic clear_a;
logic clear_b;
logic host_we_a;
logic host_we_b;
logic host_valid_a;
logic host_valid_b;
logic host_ready_a;
logic host_ready_b;
logic rst_a;
logic rst_b;

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		pinSync <= '0;
		pinStable <= '0;
		pins <= '0;
	end else begin
		pinSync <= pin_in;
		pinStable <= pinSync;
		pins <= pinStable;
	end
end

assign rst_a = rst_n && !clear_a;
assign rst_b = rst_n && !clear_b;
assign tx_ratio = (link_div != 16'd0) ? link_div : rx_ratio;
assign events = {host_we_b && host_full_b, host_we_a && host_full_a, cmd_error, rx_error};

uart_rx #(
	.RATIO_WIDTH(RATIO_WIDTH)
) receiver (
	.clk(clk),
	.rst_n(rst_n),
	.rx_serial(rx_serial),
	.clk_ratio(rx_ratio),
	.locked(baud_locked),
	.rx_data(rx_data),
	.rx_valid(rx_valid),
	.frame_error(rx_error)
);

control_unit control (
	.clk(clk),
	.rst_n(rst_n),
	.rx_data(rx_data),
	.rx_valid(rx_valid),
	.cfg_we_a(cfg_we_a),
	.cfg_we_b(cfg_we_b),
	.cfg_sel(cfg_sel),
	.cfg_compare(cfg_compare),
	.cfg_cycles(cfg_cycles),
	.cfg_pin(cfg_pin),
	.cfg_capture(cfg_capture),
	.cfg_write(cfg_write),
	.cfg_group(cfg_group),
	.cfg_sr(cfg_sr),
	.cfg_any(cfg_any),
	.cfg_seek(cfg_seek),
	.cfg_follow(cfg_follow),
	.cfg_main_cycles(cfg_main_cycles),
	.cfg_wait_end(cfg_wait_end),
	.cfg_ack(cfg_ack),
	.cfg_end_pattern(cfg_end_pattern),
	.cfg_pin_b(cfg_pin_b),
	.cfg_pair(cfg_pair),
	.cfg_invert(cfg_invert),
	.cfg_error(cfg_error),
	.run_a(run_a),
	.run_b(run_b),
	.run_mode(run_mode),
	.halt_a(halt_a),
	.halt_b(halt_b),
	.clear_a(clear_a),
	.clear_b(clear_b),
	.host_we_a(host_we_a),
	.host_we_b(host_we_b),
	.host_wdata(host_wdata),
	.line_a(line_a),
	.line_b(line_b),
	.clock_a(clock_a),
	.clock_b(clock_b),
	.out_a(out_a),
	.out_b(out_b),
	.link_div(link_div),
	.cmd_error(cmd_error)
);

emulator_channel #(
	.blocks(blocks),
	.buffer_depth(buffer_depth),
	.host_depth(host_depth)
) channel_a (
	.clk(clk),
	.rst_n(rst_a),
	.pins(pins),
	.cfg_we(cfg_we_a),
	.cfg_sel(cfg_sel),
	.cfg_compare(cfg_compare),
	.cfg_cycles(cfg_cycles),
	.cfg_pin(cfg_pin),
	.cfg_capture(cfg_capture),
	.cfg_write(cfg_write),
	.cfg_group(cfg_group),
	.cfg_sr(cfg_sr),
	.cfg_any(cfg_any),
	.cfg_seek(cfg_seek),
	.cfg_follow(cfg_follow),
	.cfg_main_cycles(cfg_main_cycles),
	.cfg_wait_end(cfg_wait_end),
	.cfg_ack(cfg_ack),
	.cfg_end_pattern(cfg_end_pattern),
	.cfg_pin_b(cfg_pin_b),
	.cfg_pair(cfg_pair),
	.cfg_invert(cfg_invert),
	.cfg_error(cfg_error),
	.run(run_a),
	.run_mode(run_mode),
	.halt(halt_a),
	.host_we(host_we_a),
	.host_wdata(host_wdata),
	.line_config(line_a),
	.clock_config(clock_a),
	.out_config(out_a),
	.host_ready(host_ready_a),
	.host_valid(host_valid_a),
	.host_len(host_len_a),
	.host_data(host_data_a),
	.host_full(host_full_a),
	.armed(armed_a),
	.data_out(data_out_a),
	.data_oe(data_oe_a),
	.pair_out(pair_out_a),
	.pair_oe(pair_oe_a),
	.clock_out(clock_out_a),
	.clock_oe(clock_oe_a),
	.select_out(select_out_a)
);

emulator_channel #(
	.blocks(blocks),
	.buffer_depth(buffer_depth),
	.host_depth(host_depth)
) channel_b (
	.clk(clk),
	.rst_n(rst_b),
	.pins(pins),
	.cfg_we(cfg_we_b),
	.cfg_sel(cfg_sel),
	.cfg_compare(cfg_compare),
	.cfg_cycles(cfg_cycles),
	.cfg_pin(cfg_pin),
	.cfg_capture(cfg_capture),
	.cfg_write(cfg_write),
	.cfg_group(cfg_group),
	.cfg_sr(cfg_sr),
	.cfg_any(cfg_any),
	.cfg_seek(cfg_seek),
	.cfg_follow(cfg_follow),
	.cfg_main_cycles(cfg_main_cycles),
	.cfg_wait_end(cfg_wait_end),
	.cfg_ack(cfg_ack),
	.cfg_end_pattern(cfg_end_pattern),
	.cfg_pin_b(cfg_pin_b),
	.cfg_pair(cfg_pair),
	.cfg_invert(cfg_invert),
	.cfg_error(cfg_error),
	.run(run_b),
	.run_mode(run_mode),
	.halt(halt_b),
	.host_we(host_we_b),
	.host_wdata(host_wdata),
	.line_config(line_b),
	.clock_config(clock_b),
	.out_config(out_b),
	.host_ready(host_ready_b),
	.host_valid(host_valid_b),
	.host_len(host_len_b),
	.host_data(host_data_b),
	.host_full(host_full_b),
	.armed(armed_b),
	.data_out(data_out_b),
	.data_oe(data_oe_b),
	.pair_out(pair_out_b),
	.pair_oe(pair_oe_b),
	.clock_out(clock_out_b),
	.clock_oe(clock_oe_b),
	.select_out(select_out_b)
);

return_path #(
	.RATIO_WIDTH(RATIO_WIDTH)
) returner (
	.clk(clk),
	.rst_n(rst_n),
	.clk_ratio(tx_ratio),
	.a_valid(host_valid_a),
	.a_len(host_len_a),
	.a_data(host_data_a),
	.b_valid(host_valid_b),
	.b_len(host_len_b),
	.b_data(host_data_b),
	.events(events),
	.a_ready(host_ready_a),
	.b_ready(host_ready_b),
	.tx_serial(tx_serial)
);

endmodule
