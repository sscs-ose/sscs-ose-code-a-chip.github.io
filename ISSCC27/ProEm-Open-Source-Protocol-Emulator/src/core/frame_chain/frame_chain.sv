// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/frame_chain/frame_chain.sv
// Module: frame_chain
// Type: RTL, core (frame chain)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain
// Submodules: first_counter, header_counter (x6), start_router, branch_unit, main_counter, end_counter, watchdog, crc_unit, frame_buffer
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module frame_chain #(
	parameter int blocks = 7,
	parameter int buffer_depth = 16
) (
	input logic clk,
	input logic rst_n,
	input logic tick,
	input logic end_tick,
	input logic[7:0] pins,
	input logic[7:0] raw_pins,
	input logic code_error,
	input logic run,
	input logic[1:0] run_mode,
	input logic halt,
	input logic host_empty,
	input logic[7:0] host_data,
	input logic[3:0] host_len,
	input logic cfg_we,
	input logic[3:0] cfg_sel,
	input logic[7:0] cfg_compare,
	input logic[7:0] cfg_cycles,
	input logic[2:0] cfg_pin,
	input logic cfg_capture,
	input logic cfg_write,
	input logic[1:0] cfg_group,
	input logic cfg_sr,
	input logic cfg_any,
	input logic cfg_seek,
	input logic cfg_follow,
	input logic[15:0] cfg_main_cycles,
	input logic cfg_wait_end,
	input logic cfg_ack,
	input logic[15:0] cfg_end_pattern,
	input logic[2:0] cfg_pin_b,
	input logic cfg_pair,
	input logic cfg_invert,
	input logic cfg_error,
	input logic tx_done,
	input logic discard,
	input logic tx_take,
	input logic tail_ready,
	input logic strict_tx,
	input logic tx_mismatch,
	input logic i2c_target,
	input logic i2c_start,
	input logic i2c_stop,
	input logic out_rd_en,

	output logic host_pop,
	output logic[7:0] out_data,
	output logic[3:0] out_len,
	output logic out_wire,
	output logic out_empty,
	output logic out_full,
	output logic complete,
	output logic abort,
	output logic timeout,
	output logic line_error,
	output logic byte_done,
	output logic line_free,
	output logic listen,
	output logic armed,
	output logic in_frame,
	output logic tx_cancel,
	output logic tail_valid,
	output logic[3:0] tail_len,
	output logic[7:0] tail_data
);

logic[blocks-1:0] block_success;
logic[blocks-1:0] block_fail;
logic[blocks-1:0] block_configured;
logic[blocks-1:0] block_active;
logic[blocks-1:0] block_ready;
logic[blocks-1:0] block_enable;
logic[blocks-1:0] block_push;
logic[blocks-1:0] block_writing;
logic[blocks-1:0] block_sr;
logic[blocks-1:0] sr_sent;
logic[blocks-1:0] sr_need;
logic[7:0] block_value [0:blocks-1];
logic[3:0] block_len [0:blocks-1];
logic[1:0] block_group [0:blocks-1];
logic[1:0] mode;
logic[1:0] base_mode;
logic[1:0] new_mode;
logic set_mode;
logic branch_stall;
logic[blocks*8-1:0] block_values;
logic[2:0] data_pin;
logic[2:0] end_pin;
logic[2:0] end_pin_b;
logic[7:0] main_data;
logic[3:0] main_len;
logic[12:0] fifo_din;
logic[12:0] fifo_raw;
logic[7:0] reversed;
logic[7:0] flipped;
logic[12:0] tx_raw;
logic[7:0] tx_flipped;
logic[7:0] tx_data;
logic tx_covered;
logic[4:0] outstanding;
logic[4:0] queued;
logic[7:0] status_flags;

logic input_bit;
logic end_a;
logic end_b;
logic end_input;
logic end_pair;
logic end_invert;
logic end_error;
logic msb;
logic read_tick;
logic main_wire;
logic wire_accept;
logic main_listening;
logic[blocks-1:0] block_listening;
logic start_tick;
logic main_ready;
logic main_enable;
logic main_sr;
logic main_sr_sent;
logic main_sr_need;
logic sr_accept;
logic main_valid;
logic main_pending;
logic main_writing;
logic main_have_data;
logic end_success;
logic fifo_wr;
logic write_end;
logic frame_reset;
logic commit_wait;
logic commit;
logic end_configured;
logic rearm_wait;
logic rearm_done;
logic internal_armed;
logic internal_line_error;
logic mode_read;
logic mode_write;
logic armed_now;
logic status_pending;
logic status_accept;
logic overflow_seen;
logic frame_event;
logic space;
logic out_almost_full;
logic branch_hit;
logic branch_abort;
logic hit_seen;
logic underrun;
logic i2c_break;
logic i2c_abort;
logic start_pending;
logic start_prev;
logic main_end;
logic main_run;
logic line_watch;
logic finish_wait;
logic main_waiting_end;
logic cancel_now;
logic internal_cancel;
logic main_done_raw;
logic main_done_eff;
logic crc_on;
logic crc_check;
logic crc_append;
logic crc_good;
logic crc_restart;
logic crc_feed;
logic tx_select;
logic crc_feed_q;
logic crc_restart_q;
logic[7:0] crc_bits_q;
logic[3:0] crc_len_q;
logic crc_busy;
logic crc_event;
logic[2:0] crc_from;
logic[4:0] crc_width;
logic[15:0] crc_out;
logic[7:0] crc_bits;
logic[3:0] crc_len;
logic[7:0] covered;
logic[7:0] start_wire;
logic rx_bit_feed;
logic start_feed;
logic tx_feed;
logic[1:0] reply_when;
logic[3:0] reply_less;
logic[1:0] reply_gap;
logic[15:0] reply_pattern;
logic reply_fire;
logic[4:0] reply_len;
logic[7:0] reply_first;
logic[15:0] reply_upper;
logic[15:0] reply_lower;
logic[7:0] reply_second;
logic[3:0] reply_first_len;
logic[3:0] reply_second_len;
logic[7:0] crc_first;
logic[7:0] crc_second;
logic[3:0] crc_first_len;
logic[3:0] crc_second_len;
logic[5:0] tail_need;
logic[5:0] tail_remaining;
logic[5:0] tail_step;
logic tail_active;
logic tail_start;
logic tail_push;
logic crc_byte;
logic crc_span;
logic main_short;
logic[blocks-1:0] field_ok;
logic tail_take;
logic tail_wire;
logic tail_advance;
logic[7:0] tail_flipped;
logic[7:0] tail_reversed;
logic tail_done;
logic tail_bypass;
logic tail_skip;
logic reply_armed;
logic[12:0] tail_entry;

assign input_bit = pins[data_pin];
assign end_a = raw_pins[end_pin];
assign end_b = raw_pins[end_pin_b] ^ end_invert;
assign end_input = end_pair ? (!end_a && !end_b) : end_a;
assign mode_read = (mode == 2'd1);
assign mode_write = (mode == 2'd2);
assign armed_now = internal_armed || run;
assign line_free = (outstanding == 5'd0) && !(|(block_push & block_writing));
assign read_tick = tick && line_free;
assign rearm_done = rearm_wait && end_success;
assign space = !out_almost_full;
assign start_tick = armed_now && (block_writing[0] ? ((run || (main_have_data && mode == 2'd0)) && space) : (read_tick && !rearm_wait));

always_comb begin
	block_active[0] = 1'b1;
	for (int k = 1; k < blocks; k++) begin
		block_active[k] = block_configured[k] && ((block_group[k] == 2'd0) || (block_group[k] == 2'd1 && mode_read) || (block_group[k] == 2'd2 && mode_write));
	end
end

always_comb begin
	block_enable[0] = 1'b1;
	sr_need[0] = 1'b0;
	for (int k = 1; k < blocks; k++) begin
		block_enable[k] = block_ready[k] && (!block_sr[k] || sr_sent[k]) && (!block_writing[k] || space) && !branch_stall;
		sr_need[k] = block_ready[k] && block_sr[k] && !sr_sent[k];
	end
end

assign main_enable = main_ready && (!main_sr || main_sr_sent) && !branch_stall;
assign main_sr_need = main_ready && main_sr && !main_sr_sent;
assign sr_accept = ((|sr_need) || main_sr_need) && !(|block_push) && !main_valid && !out_full && !abort && !halt;
assign frame_event = complete || abort || write_end;
assign status_accept = status_pending && !frame_event && !(|block_push) && !main_valid && !sr_accept && !out_full && !main_pending && !tail_active && !halt;

always_comb begin
	block_listening[0] = internal_armed && !block_writing[0] && !block_success[0];
	for (int k = 1; k < blocks; k++) begin
		block_listening[k] = block_enable[k] && !block_writing[k] && !block_success[k] && !block_fail[k];
	end
end

assign listen = line_free && ((|block_listening) || main_listening);
assign wire_accept = fifo_wr && fifo_din[12] && !out_full && !abort && !halt;
assign main_run = main_enable && !finish_wait && !tail_active;
assign complete = (main_done_eff && !(line_watch && main_writing)) || (finish_wait && line_free);
assign write_end = timeout && main_writing && main_run;
assign underrun = strict_tx && main_run && main_writing && !main_have_data && line_free && !main_pending && !main_listening && !write_end;
assign i2c_break = i2c_target && (i2c_start || i2c_stop) && block_success[0];
assign i2c_abort = i2c_break && !main_waiting_end;
assign main_end = end_success || i2c_break;
assign abort = (|block_fail) || (timeout && !write_end) || internal_line_error || branch_abort || underrun || i2c_abort;
assign frame_reset = complete || abort || write_end || halt;
assign commit = (commit_wait && !main_pending) || main_enable || branch_abort;

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		data_pin <= '0;
		end_pin <= '0;
		end_pin_b <= '0;
		end_pair <= 1'b0;
		end_invert <= 1'b0;
		end_error <= 1'b0;
		msb <= 1'b0;
		mode <= '0;
		base_mode <= '0;
		hit_seen <= 1'b0;
		start_pending <= 1'b0;
		start_prev <= 1'b0;
		finish_wait <= 1'b0;
		internal_cancel <= 1'b0;
		commit_wait <= 1'b0;
		outstanding <= '0;
		queued <= '0;
		main_short <= 1'b0;
		end_configured <= 1'b0;
		rearm_wait <= 1'b0;
		internal_armed <= 1'b0;
		internal_line_error <= 1'b0;
		status_pending <= 1'b0;
		status_flags <= '0;
		overflow_seen <= 1'b0;
		main_sr <= 1'b0;
		main_sr_sent <= 1'b0;
		block_sr <= '0;
		sr_sent <= '0;
		reply_when <= '0;
		reply_less <= '0;
		reply_gap <= '0;
		reply_pattern <= '0;
		tail_remaining <= '0;
		crc_feed_q <= 1'b0;
		crc_restart_q <= 1'b1;
		crc_bits_q <= '0;
		crc_len_q <= '0;
		for (int k = 0; k < blocks; k++) begin
			block_group[k] <= '0;
		end
	end else begin
		crc_feed_q <= crc_feed;
		crc_restart_q <= crc_restart;
		crc_bits_q <= crc_bits;
		crc_len_q <= crc_len;
		outstanding <= outstanding + {4'd0, wire_accept} + {4'd0, tail_take} - {4'd0, tx_done} - {4'd0, discard};
		queued <= queued + {4'd0, wire_accept} - {4'd0, tx_take} - {4'd0, discard};
		start_prev <= block_success[0];
		internal_cancel <= cancel_now;
		if (frame_reset) begin
			finish_wait <= 1'b0;
		end else if (main_done_eff && line_watch && main_writing) begin
			finish_wait <= 1'b1;
		end
		if (i2c_target && i2c_start) begin
			start_pending <= 1'b1;
		end else if (!i2c_target || (block_success[0] && !start_prev)) begin
			start_pending <= 1'b0;
		end
		if (frame_event || halt) begin
			hit_seen <= 1'b0;
		end else if (branch_hit) begin
			hit_seen <= 1'b1;
		end
		internal_line_error <= ((end_error && end_pair && end_tick && end_a && end_b && main_enable && !main_writing) || (code_error && block_success[0])) && !internal_line_error;
		if (frame_event) begin
			status_pending <= 1'b1;
			status_flags <= status_flags | {branch_abort, hit_seen || branch_hit, underrun, overflow_seen || (fifo_wr && out_full), internal_line_error, timeout, abort, complete || write_end};
			overflow_seen <= 1'b0;
		end else if (status_accept) begin
			status_pending <= 1'b0;
			status_flags <= '0;
		end else if (fifo_wr && out_full) begin
			overflow_seen <= 1'b1;
		end
		if (halt) begin
			status_pending <= 1'b0;
			status_flags <= '0;
		end
		if (halt) begin
			internal_armed <= 1'b0;
		end else if (run) begin
			internal_armed <= 1'b1;
		end
		if (run && !halt) begin
			mode <= run_mode;
			base_mode <= run_mode;
		end else if (frame_reset) begin
			mode <= base_mode;
		end else if (set_mode) begin
			mode <= new_mode;
		end
		for (int k = 1; k < blocks; k++) begin
			if (cfg_we && cfg_sel == k) begin
				block_group[k] <= cfg_group;
				block_sr[k] <= cfg_sr;
			end
		end
		if (cfg_we && cfg_sel == 4'd14) begin
			main_short <= (cfg_main_cycles < 16'd8);
			data_pin <= cfg_pin;
			main_sr <= cfg_sr;
		end
		if (cfg_we && cfg_sel == 4'd15) begin
			end_pin <= cfg_pin;
			end_pin_b <= cfg_pin_b;
			end_pair <= cfg_pair;
			end_invert <= cfg_invert;
			end_error <= cfg_error;
			end_configured <= 1'b1;
		end
		if (frame_reset) begin
			sr_sent <= '0;
			main_sr_sent <= 1'b0;
		end else if (sr_accept) begin
			sr_sent <= sr_sent | sr_need;
			main_sr_sent <= main_sr_sent || main_sr_need;
		end
		if (halt) begin
			rearm_wait <= 1'b0;
		end else if (abort && end_configured && !block_writing[0]) begin
			rearm_wait <= 1'b1;
		end else if (rearm_done) begin
			rearm_wait <= 1'b0;
		end
		if (cfg_we && cfg_sel == 4'd12) begin
			msb <= cfg_compare[0];
		end
		if (cfg_we && cfg_sel == 4'd7) begin
			reply_when <= cfg_main_cycles[7:6];
			reply_less <= cfg_main_cycles[5:2];
			reply_gap <= cfg_main_cycles[1:0];
			reply_pattern <= {cfg_cycles, cfg_compare};
		end
		if (frame_reset) begin
			tail_remaining <= '0;
		end else if (tail_start) begin
			tail_remaining <= tail_need;
		end else if (tail_skip) begin
			tail_remaining <= '0;
		end else if (tail_advance) begin
			tail_remaining <= tail_remaining & ~tail_step;
		end
		if (halt) begin
			commit_wait <= 1'b0;
		end else if (complete || write_end) begin
			commit_wait <= 1'b1;
		end else if (commit || abort) begin
			commit_wait <= 1'b0;
		end
	end
end

first_counter start (
	.clk(clk),
	.rst_n(rst_n),
	.tick(start_tick),
	.configuration(cfg_we && cfg_sel == 4'd0),
	.compare_bit(cfg_compare),
	.clock_cycles(cfg_cycles),
	.pin_select(cfg_pin),
	.capture(cfg_capture),
	.write_config(cfg_write),
	.pins(pins),
	.msb(msb),
	.enable(internal_armed && !rearm_wait),
	.event_mode(i2c_target),
	.start_event(start_pending),
	.complete(frame_reset),
	.abort(1'b0),
	.success(block_success[0]),
	.writing(block_writing[0]),
	.compare_out(block_value[0]),
	.push(block_push[0]),
	.push_len(block_len[0])
);

assign block_fail[0] = 1'b0;
assign block_configured[0] = 1'b1;

genvar i;
generate
	for (i = 1; i < blocks; i++) begin : g_header
		header_counter header (
			.clk(clk),
			.rst_n(rst_n),
			.tick(read_tick),
			.configuration(cfg_we && cfg_sel == i),
			.compare_bit(cfg_compare),
			.clock_cycles(cfg_cycles),
			.capture(cfg_capture),
			.write_config(cfg_write),
			.any_config(cfg_any),
			.seek_config(cfg_seek),
			.input_bit(input_bit),
			.msb(msb),
			.enable(block_enable[i]),
			.complete(frame_reset),
			.abort(1'b0),
			.success(block_success[i]),
			.fail(block_fail[i]),
			.configured(block_configured[i]),
			.writing(block_writing[i]),
			.compare_out(block_value[i]),
			.push(block_push[i]),
			.push_len(block_len[i])
		);
	end
endgenerate

always_comb begin
	for (int k = 0; k < blocks; k++) begin
		block_values[k*8 +: 8] = block_value[k];
	end
end

branch_unit #(
	.blocks(blocks)
) brancher (
	.clk(clk),
	.rst_n(rst_n),
	.cfg_we(cfg_we),
	.cfg_sel(cfg_sel),
	.cfg_rule(cfg_main_cycles[7:0]),
	.cfg_mask(cfg_cycles),
	.cfg_value(cfg_compare),
	.block_success(block_success),
	.block_values(block_values),
	.mismatch(tx_mismatch),
	.crc_event(crc_event),
	.crc_good(crc_good),
	.in_frame(block_success[0]),
	.frame_reset(frame_reset),
	.stall(branch_stall),
	.set_mode(set_mode),
	.new_mode(new_mode),
	.hit(branch_hit),
	.branch_abort(branch_abort),
	.line_watch(line_watch)
);

start_router #(
	.blocks(blocks)
) router (
	.block_success(block_success),
	.block_configured(block_configured),
	.block_active(block_active),
	.block_enable(block_ready),
	.main_enable(main_ready)
);

main_counter main_block (
	.clk(clk),
	.rst_n(rst_n),
	.tick(read_tick),
	.configuration(cfg_we && cfg_sel == 4'd14),
	.clock_cycles(cfg_main_cycles),
	.wait_end(cfg_wait_end),
	.write_config(cfg_write),
	.follow_config(cfg_follow),
	.follow_write(mode_write),
	.ack_config(cfg_ack),
	.input_bit(input_bit),
	.msb(msb),
	.enable(main_run),
	.fifo_free(!(|block_push) && (!main_writing || space)),
	.end_success(main_end),
	.abort(abort || halt),
	.host_empty(host_empty),
	.host_data(host_data),
	.host_len(host_len),
	.complete(main_done_raw),
	.byte_done(byte_done),
	.listening(main_listening),
	.pending(main_pending),
	.writing(main_writing),
	.have_data(main_have_data),
	.waiting_end(main_waiting_end),
	.host_pop(host_pop),
	.data_out(main_data),
	.data_len(main_len),
	.data_wire(main_wire),
	.data_valid(main_valid)
);

end_counter #(
	.width(16)
) end_block (
	.clk(clk),
	.rst_n(rst_n),
	.tick(end_tick),
	.configuration(cfg_we && cfg_sel == 4'd15),
	.compare_bit(cfg_end_pattern),
	.clock_cycles(cfg_cycles),
	.input_bit(end_input),
	.msb(msb),
	.enable((main_enable && !main_writing) || rearm_wait),
	.complete(frame_reset || rearm_done),
	.abort(1'b0),
	.success(end_success)
);

always_comb begin
	for (int k = 0; k < 8; k++) begin
		covered[k] = crc_on && (k >= crc_from);
	end
	for (int k = 0; k < blocks; k++) begin
		field_ok[k] = !crc_byte || (block_len[k] == 4'd8);
	end
	for (int r = 0; r < 8; r++) begin
		start_wire[r] = (r < block_len[0]) ? block_value[0][block_len[0] - 1 - r] : 1'b0;
	end
	if (!msb) begin
		start_wire = block_value[0];
	end
end

assign rx_bit_feed = read_tick && ((|(block_listening[blocks-1:1] & covered[blocks-1:1] & field_ok[blocks-1:1])) || (main_listening && !main_writing && covered[7] && !(crc_byte && main_short)));
assign start_feed = block_success[0] && !start_prev && !block_writing[0] && covered[0] && (block_len[0] != 4'd0) && field_ok[0];
assign tx_select = ((|block_push) || main_valid) && tx_raw[12] && (tx_raw[11:8] != 4'd0) && tx_covered && (!crc_byte || (tx_raw[11:8] == 4'd8));
assign tx_feed = tx_select && wire_accept;
assign crc_feed = tx_feed || start_feed || rx_bit_feed;
assign crc_busy = crc_feed_q || crc_restart_q;
assign crc_restart = !block_success[0] && !crc_span;

always_comb begin
	if (tx_select) begin
		crc_bits = tx_data;
		crc_len = tx_raw[11:8];
	end else if (start_feed) begin
		crc_bits = start_wire;
		crc_len = block_len[0];
	end else begin
		crc_bits = {7'd0, input_bit};
		crc_len = 4'd1;
	end
end

crc_unit crc_block (
	.clk(clk),
	.rst_n(rst_n),
	.cfg_we(cfg_we),
	.cfg_sel(cfg_sel),
	.cfg_rule(cfg_main_cycles[7:0]),
	.cfg_high(cfg_cycles),
	.cfg_low(cfg_compare),
	.restart(crc_restart_q),
	.feed(crc_feed_q),
	.feed_bits(crc_bits_q),
	.feed_len(crc_len_q),
	.enabled(crc_on),
	.check(crc_check),
	.append(crc_append),
	.byte_only(crc_byte),
	.span(crc_span),
	.cover_from(crc_from),
	.width(crc_width),
	.good(crc_good),
	.crc_out(crc_out)
);

always_comb begin
	for (int r = 0; r < 8; r++) begin
		crc_first[r] = crc_out[15 - r];
		crc_second[r] = crc_out[7 - r];
	end
end

assign crc_first_len = (crc_width > 5'd8) ? 4'd8 : crc_width[3:0];
assign crc_second_len = (crc_width > 5'd8) ? (crc_width[3:0] - 4'd8) : 4'd0;
assign reply_len = {1'b0, reply_less} + 5'd1;
assign reply_first_len = (reply_len > 5'd8) ? 4'd8 : reply_len[3:0];
assign reply_second_len = (reply_len > 5'd8) ? (reply_len[3:0] - 4'd8) : 4'd0;
assign reply_upper = reply_pattern >> (reply_len - 5'd8);
assign reply_lower = reply_pattern & ~(16'hFFFF << (reply_len - 5'd8));
assign reply_first = (msb && reply_len > 5'd8) ? reply_upper[7:0] : reply_pattern[7:0];
assign reply_second = msb ? reply_lower[7:0] : reply_pattern[15:8];
assign reply_fire = (reply_when == 2'd3) || (reply_when == 2'd1 && crc_good) || (reply_when == 2'd2 && crc_on && !crc_good);
assign reply_armed = (reply_when != 2'd0);
assign tail_need = {reply_armed && (reply_len > 5'd8), reply_armed, reply_armed, crc_append && main_writing && (crc_width > 5'd8), crc_append && main_writing, crc_check && !main_writing};
assign main_done_eff = (main_done_raw && !(|tail_need)) || tail_done;
assign tail_active = |tail_remaining;
assign tail_start = main_done_raw && (|tail_need) && !tail_active;
assign tail_step = tail_remaining & (~tail_remaining + 6'd1);
assign tail_wire = (tail_step != 6'b000001);
assign tail_push = tail_active && !crc_busy && !tail_wire && !(|block_push) && !main_valid && !sr_accept && !out_full && space && !(abort && !branch_abort) && !halt;
assign tail_valid = tail_active && !crc_busy && tail_wire && !tail_skip && (queued == 5'd0) && !(|block_push) && !main_valid && !sr_accept && !abort && !halt && !internal_cancel;
assign tail_take = tail_valid && tail_ready;
assign tail_advance = tail_push || tail_take;
assign tail_skip = tail_active && !crc_busy && (tail_step == 6'b001000) && !reply_fire && !abort && !halt;
assign tail_done = (tail_advance && ((tail_remaining & ~tail_step) == 6'd0)) || tail_skip;
assign crc_event = tail_push && (tail_step == 6'b000001);

always_comb begin
	tail_bypass = 1'b0;
	tail_entry = '0;
	case (tail_step)
		6'b000001: tail_entry = {1'b0, 4'hE, 6'd0, 1'b1, crc_good};
		6'b000010: begin
			tail_entry = {1'b1, crc_first_len, crc_first};
			tail_bypass = 1'b1;
		end
		6'b000100: begin
			tail_entry = {1'b1, crc_second_len, crc_second};
			tail_bypass = 1'b1;
		end
		6'b001000: begin
			tail_entry = {1'b1, 4'd0, 1'b1, 5'd0, reply_gap};
			tail_bypass = 1'b1;
		end
		6'b010000: tail_entry = {1'b1, reply_first_len, reply_first};
		6'b100000: tail_entry = {1'b1, reply_second_len, reply_second};
		default: tail_entry = '0;
	endcase
end

watchdog dog (
	.clk(clk),
	.rst_n(rst_n),
	.configuration(cfg_we && cfg_sel == 4'd13),
	.clock_limit(cfg_main_cycles),
	.busy(block_success[0]),
	.tick(tick || host_pop || tx_done),
	.frame_reset(frame_reset),
	.timeout(timeout)
);

always_comb begin
	fifo_wr = 1'b0;
	fifo_raw = '0;
	if (tail_push) begin
		fifo_wr = 1'b1;
		fifo_raw = tail_entry;
	end
	if (status_accept) begin
		fifo_wr = 1'b1;
		fifo_raw = {1'b0, 4'hF, status_flags};
	end
	if (sr_accept) begin
		fifo_wr = 1'b1;
		fifo_raw = {1'b1, 4'd0, 8'd0};
	end
	if (main_valid) begin
		fifo_wr = 1'b1;
		fifo_raw = {main_wire, main_len, main_data};
	end
	for (int j = blocks - 1; j >= 0; j--) begin
		if (block_push[j]) begin
			fifo_wr = 1'b1;
			fifo_raw = {block_writing[j], block_len[j], block_value[j]};
		end
	end
end

always_comb begin
	tx_raw = {main_wire, main_len, main_data};
	tx_covered = covered[7];
	for (int j = blocks - 1; j >= 0; j--) begin
		if (block_push[j]) begin
			tx_raw = {block_writing[j], block_len[j], block_value[j]};
			tx_covered = covered[j];
		end
	end
	for (int r = 0; r < 8; r++) begin
		tx_flipped[r] = tx_raw[7 - r];
	end
	tx_data = msb ? (tx_flipped >> (4'd8 - tx_raw[11:8])) : tx_raw[7:0];
end

always_comb begin
	for (int r = 0; r < 8; r++) begin
		flipped[r] = fifo_raw[7 - r];
	end
	reversed = flipped >> (4'd8 - fifo_raw[11:8]);
	fifo_din = (msb && fifo_raw[12]) ? {fifo_raw[12:8], reversed} : fifo_raw;
end

always_comb begin
	for (int r = 0; r < 8; r++) begin
		tail_flipped[r] = tail_entry[7 - r];
	end
	tail_reversed = tail_flipped >> (4'd8 - tail_entry[11:8]);
end

assign tail_len = tail_entry[11:8];
assign tail_data = (msb && !tail_bypass) ? tail_reversed : tail_entry[7:0];

frame_buffer #(
	.depth(buffer_depth),
	.width(13)
) out_buffer (
	.clk(clk),
	.rst_n(rst_n),
	.wr_en(fifo_wr),
	.din(fifo_din),
	.commit(commit),
	.commit_all(wire_accept || status_accept),
	.rollback((abort && !branch_abort) || halt),
	.rd_en(out_rd_en),
	.full(out_full),
	.almost_full(out_almost_full),
	.empty(out_empty),
	.dout({out_wire, out_len, out_data})
);

assign line_error = internal_line_error;
assign armed = internal_armed;
assign in_frame = block_success[0];
assign cancel_now = branch_abort || underrun || i2c_abort;
assign tx_cancel = internal_cancel;

endmodule
