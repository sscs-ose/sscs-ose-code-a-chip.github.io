// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/frame_chain/branch_unit.sv
// Module: branch_unit
// Type: RTL, core (frame chain)
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain > branch_unit
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module branch_unit #(
	parameter int blocks = 7
) (
	input logic clk,
	input logic rst_n,
	input logic cfg_we,
	input logic[3:0] cfg_sel,
	input logic[7:0] cfg_rule,
	input logic[7:0] cfg_mask,
	input logic[7:0] cfg_value,
	input logic[blocks-1:0] block_success,
	input logic[blocks*8-1:0] block_values,
	input logic mismatch,
	input logic crc_event,
	input logic crc_good,
	input logic in_frame,
	input logic frame_reset,

	output logic stall,
	output logic set_mode,
	output logic[1:0] new_mode,
	output logic hit,
	output logic branch_abort,
	output logic line_watch
);

localparam logic[1:0] ACT_KEEP = 2'd0;
localparam logic[1:0] ACT_READ = 2'd1;
localparam logic[1:0] ACT_WRITE = 2'd2;
localparam logic[1:0] ACT_ABORT = 2'd3;

logic[1:0] ruleHit [0:1];
logic[1:0] ruleMiss [0:1];
logic[2:0] ruleBlock [0:1];
logic[7:0] ruleMask [0:1];
logic[7:0] ruleValue [0:1];
logic[7:0] watched [0:1];
logic[1:0] action [0:1];
logic[1:0] ruleSrc;
logic[1:0] ruleOn;
logic[1:0] fired;
logic[1:0] fireBlock;
logic[1:0] fireLine;
logic[1:0] fire;
logic[1:0] matched;
logic[1:0] tookHit;
logic[1:0] chosen;
logic[1:0] lineEvent;
logic[1:0] lineHit;

logic internal_hit;
logic internal_abort;
logic hitNow;

always_comb begin
	for (int r = 0; r < 2; r++) begin
		watched[r] = '0;
		for (int k = 0; k < blocks; k++) begin
			if ({29'd0, ruleBlock[r]} == k) begin
				watched[r] = block_values[k*8 +: 8];
			end
		end
		matched[r] = ((watched[r] ^ ruleValue[r]) & ruleMask[r]) == 8'd0;
		fireBlock[r] = ruleOn[r] && !ruleSrc[r] && !fired[r] && in_frame && ({29'd0, ruleBlock[r]} < blocks) && block_success[ruleBlock[r]];
	end
end

always_comb begin
	for (int r = 0; r < 2; r++) begin
		lineEvent[r] = (ruleBlock[r] == 3'd0) ? mismatch : ((ruleBlock[r] == 3'd1) && crc_event);
		lineHit[r] = (ruleBlock[r] == 3'd0) || crc_good;
		fireLine[r] = ruleOn[r] && ruleSrc[r] && !fired[r] && in_frame && lineEvent[r];
		fire[r] = fireBlock[r] || fireLine[r];
		tookHit[r] = (fireLine[r] && lineHit[r]) || (fireBlock[r] && matched[r]);
		action[r] = (fireLine[r] ? lineHit[r] : matched[r]) ? ruleHit[r] : ruleMiss[r];
	end
end

always_comb begin
	chosen = ACT_KEEP;
	if (fire[0] && action[0] != ACT_KEEP) begin
		chosen = action[0];
	end else if (fire[1] && action[1] != ACT_KEEP) begin
		chosen = action[1];
	end
end

assign hitNow = |tookHit;

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		ruleSrc <= '0;
		internal_hit <= 1'b0;
		internal_abort <= 1'b0;
		ruleOn <= '0;
		fired <= '0;
		for (int r = 0; r < 2; r++) begin
			ruleHit[r] <= ACT_KEEP;
			ruleMiss[r] <= ACT_KEEP;
			ruleBlock[r] <= '0;
			ruleMask[r] <= '0;
			ruleValue[r] <= '0;
		end
	end else begin
		internal_hit <= hitNow && !frame_reset;
		internal_abort <= (chosen == ACT_ABORT) && !frame_reset;
		for (int r = 0; r < 2; r++) begin
			if (cfg_we && cfg_sel == ((r == 0) ? 4'd8 : 4'd9)) begin
				ruleHit[r] <= cfg_rule[7:6];
				ruleMiss[r] <= cfg_rule[5:4];
				ruleSrc[r] <= cfg_rule[3];
				ruleBlock[r] <= cfg_rule[2:0];
				ruleMask[r] <= cfg_mask;
				ruleValue[r] <= cfg_value;
				ruleOn[r] <= (cfg_rule != 8'd0);
				fired[r] <= 1'b0;
			end else if (frame_reset) begin
				fired[r] <= 1'b0;
			end else if (fire[r]) begin
				fired[r] <= 1'b1;
			end
		end
	end
end

assign stall = (|fireBlock) || internal_abort;
assign set_mode = (chosen == ACT_READ) || (chosen == ACT_WRITE);
assign new_mode = (chosen == ACT_READ) ? 2'd1 : 2'd2;
assign hit = internal_hit;
assign branch_abort = internal_abort;
assign line_watch = (ruleOn[0] && ruleSrc[0] && ruleBlock[0] == 3'd0) || (ruleOn[1] && ruleSrc[1] && ruleBlock[1] == 3'd0);

endmodule
