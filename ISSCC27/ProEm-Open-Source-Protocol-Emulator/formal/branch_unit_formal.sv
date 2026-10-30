// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: formal/branch_unit_formal.sv
// Module: branch_unit_formal
// Type: Formal harness (SymbiYosys)
// Hierarchy: branch_unit_formal
// Submodules: branch_unit
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module branch_unit_formal (
	input logic clk,
	input logic rst_n,
	input logic cfg_we,
	input logic [3:0] cfg_sel,
	input logic [7:0] cfg_rule,
	input logic [7:0] cfg_mask,
	input logic [7:0] cfg_value,
	input logic [6:0] block_success,
	input logic [55:0] block_values,
	input logic mismatch,
	input logic crc_event,
	input logic crc_good,
	input logic in_frame,
	input logic frame_reset
);

localparam logic [1:0] ACT_KEEP = 2'd0;
localparam logic [1:0] ACT_READ = 2'd1;
localparam logic [1:0] ACT_WRITE = 2'd2;
localparam logic [1:0] ACT_ABORT = 2'd3;

logic stall;
logic set_mode;
logic [1:0] new_mode;
logic hit;
logic branch_abort;
logic line_watch;

branch_unit #(
	.blocks(7)
) dut (
	.clk(clk),
	.rst_n(rst_n),
	.cfg_we(cfg_we),
	.cfg_sel(cfg_sel),
	.cfg_rule(cfg_rule),
	.cfg_mask(cfg_mask),
	.cfg_value(cfg_value),
	.block_success(block_success),
	.block_values(block_values),
	.mismatch(mismatch),
	.crc_event(crc_event),
	.crc_good(crc_good),
	.in_frame(in_frame),
	.frame_reset(frame_reset),
	.stall(stall),
	.set_mode(set_mode),
	.new_mode(new_mode),
	.hit(hit),
	.branch_abort(branch_abort),
	.line_watch(line_watch)
);

logic started;
logic [7:0] rule [0:1];
logic [7:0] mask [0:1];
logic [7:0] value [0:1];
logic [1:0] used;
logic [1:0] trigger;
logic [1:0] byBlock;
logic [1:0] byLine;
logic [1:0] lineEvent;
logic [1:0] lineHit;
logic [1:0] tookHit;
logic [1:0] act [0:1];
logic [1:0] choice;
logic expectHit;
logic expectAbort;
logic [7:0] seen;
logic [63:0] padded;
logic [7:0] successPadded;

assign padded = {8'd0, block_values};
assign successPadded = {1'b0, block_success};

initial assume (!rst_n);
initial started = 1'b0;

always_ff @(posedge clk) begin
	started <= 1'b1;
end

always_comb begin
	for (int r = 0; r < 2; r++) begin
		seen = padded[rule[r][2:0] * 8 +: 8];
		byBlock[r] = (rule[r] != 8'd0) && !rule[r][3] && !used[r] && in_frame && (rule[r][2:0] != 3'd7) && successPadded[rule[r][2:0]];
		lineEvent[r] = (rule[r][2:0] == 3'd0) ? mismatch : ((rule[r][2:0] == 3'd1) && crc_event);
		lineHit[r] = (rule[r][2:0] == 3'd0) || crc_good;
		byLine[r] = (rule[r] != 8'd0) && rule[r][3] && !used[r] && in_frame && lineEvent[r];
		trigger[r] = byBlock[r] || byLine[r];
		tookHit[r] = (byLine[r] && lineHit[r]) || (byBlock[r] && (((seen ^ value[r]) & mask[r]) == 8'd0));
		act[r] = tookHit[r] ? rule[r][7:6] : rule[r][5:4];
	end
	if (trigger[0] && act[0] != ACT_KEEP) begin
		choice = act[0];
	end else if (trigger[1] && act[1] != ACT_KEEP) begin
		choice = act[1];
	end else begin
		choice = ACT_KEEP;
	end
end

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		used <= '0;
		expectHit <= 1'b0;
		expectAbort <= 1'b0;
		for (int r = 0; r < 2; r++) begin
			rule[r] <= '0;
			mask[r] <= '0;
			value[r] <= '0;
		end
	end else begin
		expectHit <= (|tookHit) && !frame_reset;
		expectAbort <= (choice == ACT_ABORT) && !frame_reset;
		for (int r = 0; r < 2; r++) begin
			if (cfg_we && cfg_sel == ((r == 0) ? 4'd8 : 4'd9)) begin
				rule[r] <= cfg_rule;
				mask[r] <= cfg_mask;
				value[r] <= cfg_value;
				used[r] <= 1'b0;
			end else if (frame_reset) begin
				used[r] <= 1'b0;
			end else if (trigger[r]) begin
				used[r] <= 1'b1;
			end
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		assert (set_mode == (choice == ACT_READ || choice == ACT_WRITE));
		if (set_mode) begin
			assert (new_mode == ((choice == ACT_READ) ? 2'd1 : 2'd2));
			assert (in_frame);
		end
		assert (stall == ((|byBlock) || expectAbort));
		assert (hit == expectHit);
		assert (branch_abort == expectAbort);
		assert (line_watch == (((rule[0] != 8'd0) && rule[0][3] && (rule[0][2:0] == 3'd0)) || ((rule[1] != 8'd0) && rule[1][3] && (rule[1][2:0] == 3'd0))));
	end
end

always_comb begin
	if (started && rst_n) begin
		cover (set_mode && new_mode == 2'd1);
		cover (branch_abort && hit);
		cover (trigger[0] && trigger[1]);
		cover (byLine[0] && rule[0][2:0] == 3'd1 && tookHit[0]);
		cover (byLine[1] && rule[1][2:0] == 3'd1 && !tookHit[1]);
	end
end

endmodule
