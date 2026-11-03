// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/frame_chain/end_counter.sv
// Module: end_counter
// Type: RTL, core (frame chain)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain > end_counter
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module end_counter #(
	parameter int width = 16
) (
	input logic clk,
	input logic rst_n,
	input logic tick,
	input logic configuration,
	input logic[width-1:0] compare_bit,
	input logic[7:0] clock_cycles,
	input logic input_bit,
	input logic msb,
	input logic enable,
	input logic complete,
	input logic abort,

	output logic success
);

localparam logic[7:0] WIDTH_BITS = width;

logic[width-1:0] compare_data;
logic[width-1:0] compare_mask;
logic[width-1:0] window;
logic[width-1:0] next_window;
logic[width-1:0] top_mask;
logic[width-1:0] bottom_mask;
logic[7:0] internal_clock;
logic[7:0] counter;
logic[7:0] length;

logic internal_success;
logic match;

assign length = (clock_cycles >= WIDTH_BITS) ? WIDTH_BITS : clock_cycles;
assign bottom_mask = ~({width{1'b1}} << length);
assign top_mask = ~({width{1'b1}} >> length);
assign next_window = msb ? {window[width-2:0], input_bit} : {input_bit, window[width-1:1]};
assign match = ((next_window ^ compare_data) & compare_mask) == '0;

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		compare_data <= '0;
		compare_mask <= '1;
		internal_clock <= 8'd8;
		window <= '0;
		counter <= '0;
		internal_success <= 1'b0;
	end else begin
		if (configuration) begin
			internal_clock <= length;
			compare_data <= msb ? (compare_bit & bottom_mask) : (compare_bit << (width - length));
			compare_mask <= msb ? bottom_mask : top_mask;
			window <= '0;
			counter <= '0;
			internal_success <= 1'b0;
		end else if (complete || abort) begin
			window <= '0;
			counter <= '0;
			internal_success <= 1'b0;
		end else if (enable && tick && !internal_success) begin
			window <= next_window;
			if (counter != internal_clock) begin
				counter <= counter + 1'b1;
			end
			if ((counter + 1'b1 >= internal_clock) && match) begin
				internal_success <= 1'b1;
			end
		end else if (!enable) begin
			window <= '0;
			counter <= '0;
		end
	end
end

assign success = internal_success;

endmodule
