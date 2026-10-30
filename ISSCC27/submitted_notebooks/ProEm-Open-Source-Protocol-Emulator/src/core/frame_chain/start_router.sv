// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/frame_chain/start_router.sv
// Module: start_router
// Type: RTL, core (frame chain)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain > start_router
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module start_router #(
	parameter int blocks = 7
) (
	input logic[blocks-1:0] block_success,
	input logic[blocks-1:0] block_configured,
	input logic[blocks-1:0] block_active,

	output logic[blocks-1:0] block_enable,
	output logic main_enable
);

logic[blocks-1:0] carry;
logic[blocks-1:0] ended;

assign block_enable[0] = 1'b1;
assign carry[0] = block_success[0];
assign ended[0] = 1'b0;

genvar i;
generate
	for (i = 1; i < blocks; i++) begin : g_route
		assign ended[i] = ended[i-1] || !block_configured[i];
		assign block_enable[i] = carry[i-1] && block_active[i] && !ended[i];
		assign carry[i] = (block_active[i] && !ended[i]) ? block_success[i] : carry[i-1];
	end
endgenerate

assign main_enable = carry[blocks-1];

endmodule
