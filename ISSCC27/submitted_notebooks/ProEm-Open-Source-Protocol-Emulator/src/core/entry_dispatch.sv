// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/entry_dispatch.sv
// Module: entry_dispatch
// Type: RTL, core
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > entry_dispatch
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module entry_dispatch (
	input logic clk,
	input logic rst_n,
	input logic out_empty,
	input logic [7:0] out_data,
	input logic [3:0] out_len,
	input logic out_wire,
	input logic tx_ready,
	input logic host_ready,
	input logic flush,

	output logic out_rd_en,
	output logic tx_valid,
	output logic [3:0] tx_len,
	output logic [7:0] tx_data,
	output logic host_valid,
	output logic [3:0] host_len,
	output logic [7:0] host_data,
	output logic frame_mark,
	output logic discard
);

logic reading;
logic holding;
logic routed;
logic markSent;
logic flushing;

assign out_rd_en = !holding && !reading && !out_empty;
assign tx_valid = holding && out_wire && !flushing;
assign discard = holding && out_wire && flushing;
assign host_valid = holding && !out_wire;
assign routed = (tx_valid && tx_ready) || (host_valid && host_ready) || discard;

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		reading <= 1'b0;
		holding <= 1'b0;
		markSent <= 1'b0;
		flushing <= 1'b0;
	end else begin
		reading <= out_rd_en;
		if (reading) begin
			holding <= 1'b1;
		end else if (routed) begin
			holding <= 1'b0;
		end
		if (flush) begin
			flushing <= 1'b1;
		end else if (frame_mark) begin
			flushing <= 1'b0;
		end
		if (routed) begin
			markSent <= 1'b0;
		end else if (frame_mark) begin
			markSent <= 1'b1;
		end
	end
end

assign tx_len = out_len;
assign tx_data = out_data;
assign host_len = out_len;
assign host_data = out_data;
assign frame_mark = host_valid && !markSent && (out_len == 4'hF);

endmodule
