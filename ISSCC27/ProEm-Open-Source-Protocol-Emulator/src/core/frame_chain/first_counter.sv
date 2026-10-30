// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/frame_chain/first_counter.sv
// Module: first_counter
// Type: RTL, core (frame chain)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain > first_counter
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module first_counter (
	input logic clk,
	input logic rst_n,
	input logic tick,
	input logic configuration,
	input logic[7:0] compare_bit,
	input logic[7:0] clock_cycles,
	input logic[2:0] pin_select,
	input logic capture,
	input logic write_config,
	input logic[7:0] pins,
	input logic msb,
	input logic enable,
	input logic event_mode,
	input logic start_event,
	input logic complete,
	input logic abort,

	output logic success,
	output logic writing,
	output logic[7:0] compare_out,
	output logic push,
	output logic[3:0] push_len
);

logic[7:0] compare_data;
logic[7:0] compare_mask;
logic[7:0] internal_clock;
logic[7:0] window;
logic[7:0] next_window;
logic[7:0] counter;
logic[3:0] length;
logic[2:0] internal_pin;

logic internal_capture;
logic internal_write;
logic internal_configured;
logic internal_success;
logic internal_push;
logic input_bit;
logic match;

assign input_bit = pins[internal_pin];
assign next_window = msb ? {window[6:0], input_bit} : {input_bit, window[7:1]};
assign match = ((next_window ^ compare_data) & compare_mask) == 8'd0;
assign length = (internal_clock >= 8'd8) ? 4'd8 : internal_clock[3:0];

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		compare_data <= '0;
		compare_mask <= '1;
		internal_clock <= 8'd8;
		window <= '0;
		counter <= '0;
		internal_pin <= '0;
		internal_capture <= 1'b0;
		internal_write <= 1'b0;
		internal_configured <= 1'b0;
		internal_success <= 1'b0;
		internal_push <= 1'b0;
	end else begin
		internal_push <= 1'b0;
		if (configuration) begin
			internal_clock <= clock_cycles;
			compare_data <= compare_bit;
			compare_mask <= (clock_cycles >= 8'd8) ? 8'hFF : (msb ? ~(8'hFF << clock_cycles) : ~(8'hFF >> clock_cycles));
			internal_pin <= pin_select;
			internal_capture <= capture;
			internal_write <= write_config;
			internal_configured <= 1'b1;
			window <= '0;
			counter <= '0;
			internal_success <= 1'b0;
		end else if (complete || abort) begin
			window <= '0;
			counter <= '0;
			internal_success <= 1'b0;
		end else if (internal_write) begin
			if (internal_configured && tick && !internal_success) begin
				internal_success <= 1'b1;
				internal_push <= (length != 4'd0);
			end
		end else if (internal_clock == 8'd0) begin
			if (enable && internal_configured && !internal_success && (event_mode ? start_event : (input_bit == compare_data[0]))) begin
				internal_success <= 1'b1;
			end
		end else if (tick && !internal_success) begin
			window <= next_window;
			if (counter != internal_clock) begin
				counter <= counter + 1'b1;
			end
			if ((counter + 1'b1 >= internal_clock) && match) begin
				internal_success <= 1'b1;
				internal_push <= internal_capture;
			end
		end
	end
end

assign success = internal_success;
assign writing = internal_write;
assign compare_out = msb ? (compare_data & ~(8'hFF << length)) : (compare_data >> (4'd8 - length));
assign push = internal_push;
assign push_len = length;

endmodule
