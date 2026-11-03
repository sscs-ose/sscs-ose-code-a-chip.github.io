// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/frame_chain/header_counter.sv
// Module: header_counter
// Type: RTL, core (frame chain)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain > header_counter
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module header_counter (
	input logic clk,
	input logic rst_n,
	input logic tick,
	input logic configuration,
	input logic[7:0] compare_bit,
	input logic[7:0] clock_cycles,
	input logic capture,
	input logic write_config,
	input logic any_config,
	input logic seek_config,
	input logic input_bit,
	input logic msb,
	input logic enable,
	input logic complete,
	input logic abort,

	output logic success,
	output logic fail,
	output logic configured,
	output logic writing,
	output logic[7:0] compare_out,
	output logic push,
	output logic[3:0] push_len
);

logic[7:0] compare_data;
logic[7:0] internal_clock;
logic[7:0] counter;
logic[3:0] length;
logic[2:0] index;
logic[2:0] position;

logic internal_capture;
logic internal_write;
logic internal_any;
logic internal_seek;
logic internal_configured;
logic internal_success;
logic internal_fail;
logic internal_push;

assign length = (internal_clock >= 8'd8) ? 4'd8 : internal_clock[3:0];
assign position = msb ? (length[2:0] - 3'd1 - index) : index;

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		compare_data <= '0;
		internal_clock <= '0;
		counter <= '0;
		index <= '0;
		internal_capture <= 1'b0;
		internal_write <= 1'b0;
		internal_any <= 1'b0;
		internal_seek <= 1'b0;
		internal_configured <= 1'b0;
		internal_success <= 1'b0;
		internal_fail <= 1'b0;
		internal_push <= 1'b0;
	end else begin
		internal_fail <= 1'b0;
		internal_push <= 1'b0;
		if (configuration) begin
			internal_clock <= clock_cycles;
			compare_data <= compare_bit;
			internal_capture <= capture;
			internal_write <= write_config;
			internal_any <= any_config && !write_config;
			internal_seek <= seek_config && !write_config && !any_config;
			internal_configured <= 1'b1;
			counter <= '0;
			index <= '0;
			internal_success <= 1'b0;
		end else if (complete || abort) begin
			counter <= '0;
			index <= '0;
			internal_success <= 1'b0;
		end else if (internal_write) begin
			if (enable && !internal_success) begin
				internal_success <= 1'b1;
				internal_push <= 1'b1;
			end
		end else if (enable && tick && !internal_success && !internal_fail) begin
			if (internal_seek && counter == 8'd0 && input_bit != compare_data[position]) begin
				counter <= '0;
			end else if (internal_any || input_bit == compare_data[position]) begin
				if (internal_any) begin
					compare_data[position] <= input_bit;
				end
				counter <= counter + 1'b1;
				index <= index + 1'b1;
				if (counter + 1'b1 == internal_clock) begin
					internal_success <= 1'b1;
					internal_push <= internal_capture;
				end
			end else begin
				internal_fail <= 1'b1;
				counter <= '0;
				index <= '0;
			end
		end
	end
end

assign success = internal_success;
assign fail = internal_fail;
assign configured = internal_configured;
assign writing = internal_write;
assign compare_out = compare_data & ~(8'hFF << length);
assign push = internal_push;
assign push_len = length;

endmodule
