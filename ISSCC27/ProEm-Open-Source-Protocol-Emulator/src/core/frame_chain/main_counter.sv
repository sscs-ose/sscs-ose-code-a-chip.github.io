// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/frame_chain/main_counter.sv
// Module: main_counter
// Type: RTL, core (frame chain)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain > main_counter
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module main_counter (
	input logic clk,
	input logic rst_n,
	input logic tick,
	input logic configuration,
	input logic[15:0] clock_cycles,
	input logic wait_end,
	input logic write_config,
	input logic follow_config,
	input logic follow_write,
	input logic ack_config,
	input logic input_bit,
	input logic msb,
	input logic enable,
	input logic fifo_free,
	input logic end_success,
	input logic abort,
	input logic host_empty,
	input logic[7:0] host_data,
	input logic[3:0] host_len,

	output logic complete,
	output logic byte_done,
	output logic listening,
	output logic pending,
	output logic writing,
	output logic have_data,
	output logic waiting_end,
	output logic host_pop,
	output logic[7:0] data_out,
	output logic[3:0] data_len,
	output logic data_wire,
	output logic data_valid
);

logic[15:0] internal_clock;
logic[15:0] remaining;
logic[7:0] shift_data;
logic[7:0] next_shift;
logic[7:0] pending_data;
logic[7:0] carry_data;
logic[7:0] current_data;
logic[8:0] take_mask;
logic[8:0] len_mask;
logic[8:0] rest_mask;
logic[7:0] take_value;
logic[3:0] pending_len;
logic[3:0] carry_len;
logic[3:0] current_len;
logic[3:0] byte_room;
logic[3:0] limit;
logic[3:0] take;
logic[3:0] byte_bits;
logic[2:0] index;

logic internal_wait_end;
logic internal_write;
logic internal_follow;
logic write_mode;
logic internal_ack;
logic pending_valid;
logic carry_valid;
logic ack_pending;
logic ack_value;
logic ack_wait;
logic ack_last;
logic nack_pending;
logic read_tick;
logic finishing;
logic end_finish;
logic release_data;
logic ack_push;
logic nack_push;
logic write_push;
logic write_last;
logic write_byte_end;
logic write_finish;
logic ack_seen;

assign write_mode = internal_follow ? follow_write : internal_write;
assign next_shift = msb ? {shift_data[6:0], input_bit} : {input_bit, shift_data[7:1]};
assign read_tick = !write_mode && enable && tick && !ack_pending;
assign finishing = read_tick && !internal_wait_end && (remaining == 16'd1);
assign end_finish = !write_mode && enable && internal_wait_end && end_success;
assign release_data = pending_valid && fifo_free;
assign ack_push = ack_pending && !pending_valid && fifo_free;

assign current_data = carry_valid ? carry_data : host_data;
assign current_len = carry_valid ? carry_len : host_len;
assign byte_room = 4'd8 - byte_bits;
assign limit = (!internal_ack || {12'd0, byte_room} > remaining) ? ((remaining > 16'd8) ? 4'd8 : remaining[3:0]) : byte_room;
assign take = (current_len > limit) ? limit : current_len;
assign take_mask = (9'd1 << take) - 1'b1;
assign len_mask = (9'd1 << (current_len - take)) - 1'b1;
assign rest_mask = (9'd1 << ({1'b0, index} + 4'd1)) - 1'b1;
assign take_value = msb ? ((current_data >> (current_len - take)) & take_mask[7:0]) : (current_data & take_mask[7:0]);
assign have_data = carry_valid || !host_empty;
assign waiting_end = !write_mode && enable && internal_wait_end;
assign write_push = write_mode && enable && have_data && fifo_free && !ack_wait && !nack_pending;
assign write_last = write_push && ({12'd0, take} == remaining);
assign write_byte_end = write_push && (byte_bits + take == 4'd8);
assign write_finish = write_last && !internal_ack;
assign ack_seen = write_mode && enable && ack_wait && tick;
assign nack_push = nack_pending && fifo_free;

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		internal_clock <= '0;
		internal_wait_end <= 1'b0;
		internal_write <= 1'b0;
		internal_follow <= 1'b0;
		internal_ack <= 1'b0;
		remaining <= '0;
		shift_data <= '0;
		pending_data <= '0;
		pending_len <= '0;
		carry_data <= '0;
		carry_len <= '0;
		byte_bits <= '0;
		index <= '0;
		pending_valid <= 1'b0;
		carry_valid <= 1'b0;
		ack_pending <= 1'b0;
		ack_value <= 1'b0;
		ack_wait <= 1'b0;
		ack_last <= 1'b0;
		nack_pending <= 1'b0;
	end else begin
		if (release_data) begin
			pending_valid <= 1'b0;
		end
		if (ack_push) begin
			ack_pending <= 1'b0;
		end
		if (nack_push) begin
			nack_pending <= 1'b0;
		end
		if (configuration) begin
			internal_clock <= clock_cycles;
			internal_wait_end <= wait_end;
			internal_write <= write_config;
			internal_follow <= follow_config;
			internal_ack <= ack_config;
			remaining <= clock_cycles;
			shift_data <= '0;
			byte_bits <= '0;
			index <= '0;
			pending_valid <= 1'b0;
			carry_valid <= 1'b0;
			ack_pending <= 1'b0;
			ack_wait <= 1'b0;
			nack_pending <= 1'b0;
		end else if (abort || end_finish || !enable) begin
			if (abort) begin
				pending_valid <= 1'b0;
				ack_pending <= 1'b0;
				nack_pending <= 1'b0;
			end
			remaining <= internal_clock;
			shift_data <= '0;
			byte_bits <= '0;
			index <= '0;
			ack_wait <= 1'b0;
		end else if (write_mode) begin
			if (write_push) begin
				if (current_len > take) begin
					carry_data <= msb ? (current_data & len_mask[7:0]) : (current_data >> take);
					carry_len <= current_len - take;
					carry_valid <= 1'b1;
				end else begin
					carry_valid <= 1'b0;
				end
				remaining <= write_last ? internal_clock : remaining - {12'd0, take};
				byte_bits <= (write_byte_end || write_last) ? 4'd0 : byte_bits + take;
				if (internal_ack && (write_byte_end || write_last)) begin
					ack_wait <= 1'b1;
					ack_last <= write_last;
				end
			end else if (ack_seen) begin
				ack_wait <= 1'b0;
				if (input_bit) begin
					nack_pending <= 1'b1;
				end
			end
		end else if (read_tick) begin
			if (index == 3'd7 || finishing) begin
				pending_data <= msb ? (next_shift & rest_mask[7:0]) : (next_shift >> (3'd7 - index));
				pending_len <= {1'b0, index} + 1'b1;
				pending_valid <= 1'b1;
				if (internal_ack) begin
					ack_pending <= 1'b1;
					ack_value <= finishing;
				end
			end
			if (finishing) begin
				remaining <= internal_clock;
				shift_data <= '0;
				index <= '0;
			end else begin
				shift_data <= next_shift;
				index <= index + 1'b1;
				remaining <= remaining - 1'b1;
			end
		end
	end
end

assign complete = (finishing && !internal_ack) || end_finish || write_finish || (ack_push && ack_value) || (ack_seen && ack_last && !input_bit) || nack_push;
assign byte_done = (read_tick && (index == 3'd7 || finishing)) || write_byte_end || (write_last && internal_ack);
assign pending = pending_valid || ack_pending || nack_pending;
assign listening = enable && ((!write_mode && !ack_pending) || (write_mode && ack_wait));
assign writing = write_mode;
assign host_pop = write_push && !carry_valid;

always_comb begin
	data_valid = 1'b0;
	data_out = '0;
	data_len = '0;
	data_wire = 1'b0;
	if (nack_push) begin
		data_valid = 1'b1;
		data_out = 8'h02;
	end else if (write_mode) begin
		data_valid = write_push;
		data_out = take_value;
		data_len = take;
		data_wire = 1'b1;
	end else if (release_data) begin
		data_valid = 1'b1;
		data_out = pending_data;
		data_len = pending_len;
	end else if (ack_push) begin
		data_valid = 1'b1;
		data_out = {7'd0, ack_value};
		data_len = 4'd1;
		data_wire = 1'b1;
	end
end

endmodule
