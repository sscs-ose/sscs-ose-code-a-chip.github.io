// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/primitives/host_fifo.sv
// Module: host_fifo
// Type: Primitive
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > host_fifo
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module host_fifo #(
	parameter int depth = 16,
	parameter int width = 12
) (
	input logic clk,
	input logic rst_n,
	input logic flush,
	input logic wr_en,
	input logic [width-1:0] din,
	input logic rd_en,

	output logic full,
	output logic empty,
	output logic [width-1:0] dout
);

localparam int ADDR_WIDTH = $clog2(depth);
localparam int PTR_WIDTH = ADDR_WIDTH + 1;

logic [PTR_WIDTH-1:0] wr_ptr;
logic [PTR_WIDTH-1:0] rd_ptr;
logic [width-1:0] internal_d [0:depth-1];
logic wr_en_int;
logic rd_en_int;
logic [ADDR_WIDTH-1:0] rdAddr;
logic [ADDR_WIDTH-1:0] nextAddr;
logic [width-1:0] head;
logic [width-1:0] stayValue;
logic [width-1:0] nextValue;

assign empty = (wr_ptr == rd_ptr);
assign full = (wr_ptr[ADDR_WIDTH-1:0] == rd_ptr[ADDR_WIDTH-1:0]) && (wr_ptr[ADDR_WIDTH] != rd_ptr[ADDR_WIDTH]);
assign wr_en_int = wr_en && !full && !flush;
assign rd_en_int = rd_en && !empty && !flush;
assign rdAddr = rd_ptr[ADDR_WIDTH-1:0];
assign nextAddr = rdAddr + 1'b1;
assign stayValue = (wr_en_int && wr_ptr[ADDR_WIDTH-1:0] == rdAddr) ? din : internal_d[rdAddr];
assign nextValue = (wr_en_int && wr_ptr[ADDR_WIDTH-1:0] == nextAddr) ? din : internal_d[nextAddr];

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		wr_ptr <= '0;
		rd_ptr <= '0;
	end else if (flush) begin
		wr_ptr <= '0;
		rd_ptr <= '0;
	end else begin
		if (wr_en_int) begin
			wr_ptr <= wr_ptr + 1'b1;
		end
		if (rd_en_int) begin
			rd_ptr <= rd_ptr + 1'b1;
		end
	end
end

always_ff @(posedge clk) begin
	if (wr_en_int) begin
		internal_d[wr_ptr[ADDR_WIDTH-1:0]] <= din;
	end
end

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		head <= '0;
	end else begin
		head <= rd_en_int ? nextValue : stayValue;
	end
end

assign dout = head;

endmodule
