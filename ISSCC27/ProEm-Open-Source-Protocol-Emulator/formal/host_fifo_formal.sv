// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: formal/host_fifo_formal.sv
// Module: host_fifo_formal
// Type: Formal harness (SymbiYosys)
// Hierarchy: host_fifo_formal
// Submodules: host_fifo
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module host_fifo_formal (
	input logic clk,
	input logic rst_n,
	input logic flush,
	input logic wr_en,
	input logic [3:0] din,
	input logic rd_en,
	input logic pick
);

localparam int DEPTH = 4;

logic full;
logic empty;
logic [3:0] dout;

host_fifo #(
	.depth(DEPTH),
	.width(4)
) dut (
	.clk(clk),
	.rst_n(rst_n),
	.flush(flush),
	.wr_en(wr_en),
	.din(din),
	.rd_en(rd_en),
	.full(full),
	.empty(empty),
	.dout(dout)
);

logic started;
logic [3:0] count;
logic tracking;
logic [3:0] trackedValue;
logic [3:0] trackedPos;
logic wrFire;
logic rdFire;

assign wrFire = wr_en && !full && !flush;
assign rdFire = rd_en && !empty && !flush;

initial assume (!rst_n);
initial started = 1'b0;

always_ff @(posedge clk) begin
	started <= 1'b1;
end

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		count <= '0;
		tracking <= 1'b0;
		trackedValue <= '0;
		trackedPos <= '0;
	end else if (flush) begin
		count <= '0;
		tracking <= 1'b0;
	end else begin
		count <= count + wrFire - rdFire;
		if (tracking && rdFire) begin
			if (trackedPos == 0) begin
				tracking <= 1'b0;
			end else begin
				trackedPos <= trackedPos - 1'b1;
			end
		end
		if (!tracking && wrFire && pick) begin
			tracking <= 1'b1;
			trackedValue <= din;
			trackedPos <= count - rdFire;
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		assert (count <= DEPTH);
		assert (empty == (count == 0));
		assert (full == (count == DEPTH));
		if (tracking) begin
			assert (trackedPos < count);
			if (trackedPos == 0) begin
				assert (dout == trackedValue);
			end
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		cover (full);
		cover (tracking && trackedPos == DEPTH - 1);
	end
end

endmodule
