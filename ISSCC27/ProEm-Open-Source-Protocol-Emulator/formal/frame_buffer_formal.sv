// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: formal/frame_buffer_formal.sv
// Module: frame_buffer_formal
// Type: Formal harness (SymbiYosys)
// Hierarchy: frame_buffer_formal
// Submodules: frame_buffer
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module frame_buffer_formal (
	input logic clk,
	input logic rst_n,
	input logic wr_en,
	input logic [3:0] din,
	input logic commit,
	input logic commit_all,
	input logic rollback,
	input logic rd_en,
	input logic pick
);

localparam int DEPTH = 4;

logic full;
logic almost_full;
logic empty;
logic [3:0] dout;

frame_buffer #(
	.depth(DEPTH),
	.width(4)
) dut (
	.clk(clk),
	.rst_n(rst_n),
	.wr_en(wr_en),
	.din(din),
	.commit(commit),
	.commit_all(commit_all),
	.rollback(rollback),
	.rd_en(rd_en),
	.full(full),
	.almost_full(almost_full),
	.empty(empty),
	.dout(dout)
);

logic started;
logic [3:0] total;
logic [3:0] committed;
logic [3:0] totalNext;
logic tracking;
logic [3:0] trackedValue;
logic [3:0] trackedPos;
logic checkRead;
logic wrFire;
logic rdFire;

assign wrFire = wr_en && !full && !rollback;
assign rdFire = rd_en && !empty;
assign totalNext = (rollback ? committed : total + wrFire) - rdFire;

initial assume (!rst_n);
initial started = 1'b0;

always_ff @(posedge clk) begin
	started <= 1'b1;
end

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		total <= '0;
		committed <= '0;
		tracking <= 1'b0;
		trackedValue <= '0;
		trackedPos <= '0;
		checkRead <= 1'b0;
	end else begin
		total <= totalNext;
		if (rollback) begin
			committed <= committed - rdFire;
		end else if (commit_all) begin
			committed <= total + wrFire - rdFire;
		end else if (commit) begin
			committed <= total - rdFire;
		end else begin
			committed <= committed - rdFire;
		end
		checkRead <= tracking && rdFire && (trackedPos == 0);
		if (tracking) begin
			if (rdFire && trackedPos == 0) begin
				tracking <= 1'b0;
			end else if (rollback && trackedPos >= committed) begin
				tracking <= 1'b0;
			end else if (rdFire) begin
				trackedPos <= trackedPos - 1'b1;
			end
		end else if (wrFire && pick) begin
			tracking <= 1'b1;
			trackedValue <= din;
			trackedPos <= total - rdFire;
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		assert (committed <= total);
		assert (total <= DEPTH);
		assert (full == (total == DEPTH));
		assert (almost_full == (total >= DEPTH - 1));
		assert (empty == (committed == 0));
		if (tracking) begin
			assert (trackedPos < total);
		end
		if (checkRead) begin
			assert (dout == trackedValue);
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		cover (full && empty);
		cover (checkRead);
	end
end

endmodule
