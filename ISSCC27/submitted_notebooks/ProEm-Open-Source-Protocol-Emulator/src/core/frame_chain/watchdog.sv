// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/frame_chain/watchdog.sv
// Module: watchdog
// Type: RTL, core (frame chain)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain > watchdog
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module watchdog (
	input logic clk,
	input logic rst_n,
	input logic configuration,
	input logic[15:0] clock_limit,
	input logic busy,
	input logic tick,
	input logic frame_reset,

	output logic timeout
);

logic[15:0] internal_limit;
logic[15:0] counter;

logic internal_timeout;

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		internal_limit <= '0;
		counter <= '0;
		internal_timeout <= 1'b0;
	end else begin
		internal_timeout <= 1'b0;
		if (configuration) begin
			internal_limit <= clock_limit;
			counter <= '0;
		end else if (frame_reset || !busy || tick) begin
			counter <= '0;
		end else if (internal_limit != '0) begin
			if (counter + 1'b1 == internal_limit) begin
				internal_timeout <= 1'b1;
				counter <= '0;
			end else begin
				counter <= counter + 1'b1;
			end
		end
	end
end

assign timeout = internal_timeout;

endmodule
