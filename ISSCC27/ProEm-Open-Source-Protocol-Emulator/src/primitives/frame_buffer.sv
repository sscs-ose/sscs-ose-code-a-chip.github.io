// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/primitives/frame_buffer.sv
// Module: frame_buffer
// Type: Primitive
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > emulator_channel > frame_chain > frame_buffer
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module frame_buffer #(
	parameter int depth = 16,
	parameter int width = 13
) (
	input logic clk,
	input logic rst_n,
	input logic wr_en,
	input logic[width-1:0] din,
	input logic commit,
	input logic commit_all,
	input logic rollback,
	input logic rd_en,

	output logic full,
	output logic almost_full,
	output logic empty,
	output logic[width-1:0] dout
);

localparam int ADDR_WIDTH = $clog2(depth);
localparam int PTR_WIDTH = ADDR_WIDTH + 1;
localparam logic[PTR_WIDTH-1:0] DEPTH_COUNT = depth;


logic[PTR_WIDTH-1:0] wr_ptr;
logic[PTR_WIDTH-1:0] cm_ptr;
logic[PTR_WIDTH-1:0] rd_ptr;
logic[PTR_WIDTH-1:0] used;
logic[width-1:0] internal_d [0:depth-1];

logic wr_en_int;
logic writeLate;
logic[ADDR_WIDTH-1:0] writeAddr;
logic[width-1:0] writeData;
logic rd_en_int;

assign empty = (rd_ptr == cm_ptr);
assign full = (used == DEPTH_COUNT);
assign almost_full = (used >= DEPTH_COUNT - 1'b1);
assign rd_en_int = rd_en && !empty;
assign wr_en_int = wr_en && !full && !rollback;

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		wr_ptr <= '0;
		cm_ptr <= '0;
		rd_ptr <= '0;
		used <= '0;
		dout <= '0;
	end else begin
		if (rollback) begin
			used <= cm_ptr - rd_ptr - {{(PTR_WIDTH-1){1'b0}}, rd_en_int};
		end else begin
			used <= used + {{(PTR_WIDTH-1){1'b0}}, wr_en_int} - {{(PTR_WIDTH-1){1'b0}}, rd_en_int};
		end
		if (rd_en_int) begin
			dout <= (writeLate && writeAddr == rd_ptr[ADDR_WIDTH-1:0]) ? writeData : internal_d[rd_ptr[ADDR_WIDTH-1:0]];
			rd_ptr <= rd_ptr + 1'b1;
		end
		if (rollback) begin
			wr_ptr <= cm_ptr;
		end else begin
			if (wr_en_int) begin
				wr_ptr <= wr_ptr + 1'b1;
			end
			if (commit_all) begin
				cm_ptr <= wr_ptr + wr_en_int;
			end else if (commit) begin
				cm_ptr <= wr_ptr;
			end
		end
	end
end

always_ff@(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		writeLate <= 1'b0;
		writeAddr <= '0;
		writeData <= '0;
	end else begin
		writeLate <= wr_en_int;
		writeAddr <= wr_ptr[ADDR_WIDTH-1:0];
		writeData <= din;
	end
end

always_ff@(posedge clk) begin
	if (writeLate) begin
		internal_d[writeAddr] <= writeData;
	end
end

endmodule
