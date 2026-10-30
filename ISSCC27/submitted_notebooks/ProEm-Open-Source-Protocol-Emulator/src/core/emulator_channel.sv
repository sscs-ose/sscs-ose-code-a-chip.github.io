// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/emulator_channel.sv
// Module: emulator_channel
// Type: RTL, core
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel
// Submodules: host_fifo, line_codec, frame_chain, entry_dispatch
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module emulator_channel #(
	parameter int blocks = 7,
	parameter int buffer_depth = 16,
	parameter int host_depth = 8
) (
	input logic clk,
	input logic rst_n,
	input logic [7:0] pins,
	input logic cfg_we,
	input logic [3:0] cfg_sel,
	input logic [7:0] cfg_compare,
	input logic [7:0] cfg_cycles,
	input logic [2:0] cfg_pin,
	input logic cfg_capture,
	input logic cfg_write,
	input logic [1:0] cfg_group,
	input logic cfg_sr,
	input logic cfg_any,
	input logic cfg_seek,
	input logic cfg_follow,
	input logic [15:0] cfg_main_cycles,
	input logic cfg_wait_end,
	input logic cfg_ack,
	input logic [15:0] cfg_end_pattern,
	input logic [2:0] cfg_pin_b,
	input logic cfg_pair,
	input logic cfg_invert,
	input logic cfg_error,
	input logic run,
	input logic [1:0] run_mode,
	input logic halt,
	input logic host_we,
	input logic [11:0] host_wdata,
	input logic [15:0] line_config,
	input logic [31:0] clock_config,
	input logic [7:0] out_config,
	input logic host_ready,

	output logic host_valid,
	output logic [3:0] host_len,
	output logic [7:0] host_data,
	output logic host_full,
	output logic armed,
	output logic data_out,
	output logic data_oe,
	output logic pair_out,
	output logic pair_oe,
	output logic clock_out,
	output logic clock_oe,
	output logic select_out
);

logic [11:0] host_head;
logic [7:0] view;
logic [7:0] out_data;
logic [3:0] out_len;
logic [7:0] tx_data;
logic [3:0] tx_len;
logic host_empty;
logic host_pop;
logic tick;
logic end_tick;
logic code_error;
logic tx_done;
logic tx_ready;
logic tx_valid;
logic send_valid;
logic send_ready;
logic [7:0] send_data;
logic [3:0] send_len;
logic tail_valid;
logic [7:0] tail_data;
logic [3:0] tail_len;
logic tx_take;
logic out_rd_en;
logic out_wire;
logic out_empty;
logic out_full;
logic complete;
logic abort;
logic timeout;
logic line_error;
logic byte_done;
logic line_free;
logic listen;
logic in_frame;
logic frame_mark;
logic discard;
logic strict_tx;
logic tx_mismatch;
logic i2c_target;
logic i2c_start;
logic i2c_stop;
logic tx_cancel;

host_fifo #(
	.depth(host_depth),
	.width(12)
) host (
	.clk(clk),
	.rst_n(rst_n),
	.flush(halt),
	.wr_en(host_we),
	.din(host_wdata),
	.rd_en(host_pop),
	.full(host_full),
	.empty(host_empty),
	.dout(host_head)
);

line_codec codec (
	.clk(clk),
	.rst_n(rst_n),
	.pins(pins),
	.line_config(line_config),
	.clock_config(clock_config),
	.out_config(out_config),
	.listen(listen),
	.line_free(line_free),
	.in_frame(in_frame),
	.frame_mark(frame_mark),
	.halt(halt),
	.tx_cancel(tx_cancel),
	.tx_valid(send_valid),
	.tx_len(send_len),
	.tx_data(send_data),
	.tx_ready(send_ready),
	.tx_done(tx_done),
	.view(view),
	.tick(tick),
	.end_tick(end_tick),
	.code_error(code_error),
	.strict_tx(strict_tx),
	.tx_mismatch(tx_mismatch),
	.i2c_target(i2c_target),
	.i2c_start(i2c_start),
	.i2c_stop(i2c_stop),
	.data_out(data_out),
	.data_oe(data_oe),
	.pair_out(pair_out),
	.pair_oe(pair_oe),
	.clock_out(clock_out),
	.clock_oe(clock_oe),
	.select_out(select_out)
);

frame_chain #(
	.blocks(blocks),
	.buffer_depth(buffer_depth)
) chain (
	.clk(clk),
	.rst_n(rst_n),
	.tick(tick),
	.end_tick(end_tick),
	.pins(view),
	.raw_pins(pins),
	.code_error(code_error),
	.run(run),
	.run_mode(run_mode),
	.halt(halt),
	.host_empty(host_empty),
	.host_data(host_head[7:0]),
	.host_len(host_head[11:8]),
	.cfg_we(cfg_we),
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
	.tx_done(tx_done),
	.discard(discard),
	.tx_take(tx_take),
	.tail_ready(send_ready),
	.strict_tx(strict_tx),
	.tx_mismatch(tx_mismatch),
	.i2c_target(i2c_target),
	.i2c_start(i2c_start),
	.i2c_stop(i2c_stop),
	.out_rd_en(out_rd_en),
	.host_pop(host_pop),
	.out_data(out_data),
	.out_len(out_len),
	.out_wire(out_wire),
	.out_empty(out_empty),
	.out_full(out_full),
	.complete(complete),
	.abort(abort),
	.timeout(timeout),
	.line_error(line_error),
	.byte_done(byte_done),
	.line_free(line_free),
	.listen(listen),
	.armed(armed),
	.in_frame(in_frame),
	.tx_cancel(tx_cancel),
	.tail_valid(tail_valid),
	.tail_len(tail_len),
	.tail_data(tail_data)
);

entry_dispatch dispatch (
	.clk(clk),
	.rst_n(rst_n),
	.out_empty(out_empty),
	.out_data(out_data),
	.out_len(out_len),
	.out_wire(out_wire),
	.tx_ready(tx_ready),
	.host_ready(host_ready),
	.flush(tx_cancel),
	.out_rd_en(out_rd_en),
	.tx_valid(tx_valid),
	.tx_len(tx_len),
	.tx_data(tx_data),
	.host_valid(host_valid),
	.host_len(host_len),
	.host_data(host_data),
	.frame_mark(frame_mark),
	.discard(discard)
);

assign tx_ready = send_ready && !tail_valid;
assign tx_take = tx_valid && tx_ready;
assign send_valid = tx_valid || tail_valid;
assign send_len = tx_valid ? tx_len : tail_len;
assign send_data = tx_valid ? tx_data : tail_data;

endmodule
