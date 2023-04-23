module sparsity_memory (
	clk,
	reset,
	scan_en_in,
	CONF_STR_SPARSITY,
	wr_en_ext,
	wr_addr_ext,
	wr_data_ext,
	rd_en,
	rd_addr,
	rd_data
);
	input wire clk;
	input wire reset;
	input wire scan_en_in;
	input wire [15:0] CONF_STR_SPARSITY;
	input wire wr_en_ext;
	input wire [31:0] wr_addr_ext;
	input wire [31:0] wr_data_ext;
	input wire rd_en;
	input wire [10:0] rd_addr;
	output reg [31:0] rd_data;
	reg wr_en_mem0;
	reg wr_en_mem1;
	reg CEB_mem0;
	reg CEB_mem1;
	reg wr_en_ext_reg;
	reg [31:0] wr_addr_ext_reg;
	reg [31:0] wr_data_ext_reg;
	reg [9:0] wr_addr_mem0;
	reg [9:0] wr_addr_mem1;
	reg [9:0] muxed_addr_mem0;
	reg [9:0] muxed_addr_mem1;
	reg [31:0] wr_data_mem0;
	reg [31:0] wr_data_mem1;
	wire [31:0] rd_data_mem0;
	wire [31:0] rd_data_mem1;
	reg [9:0] rd_addr_mem0;
	reg [9:0] rd_addr_mem1;
	reg [10:0] rd_addr_reg;
	wire rd_en_asserted;
	assign rd_en_asserted = rd_en && (CONF_STR_SPARSITY != 0);
	always @(posedge clk or negedge reset)
		if (~reset) begin
			wr_en_ext_reg <= 0;
			wr_addr_ext_reg <= 0;
			wr_data_ext_reg <= 0;
			rd_addr_reg <= 0;
		end
		else begin
			wr_en_ext_reg <= wr_en_ext;
			wr_addr_ext_reg <= wr_addr_ext;
			wr_data_ext_reg <= wr_data_ext;
			rd_addr_reg <= rd_addr;
		end
	always @(*)
		if (wr_en_ext_reg) begin
			if (wr_addr_ext_reg[10] == 1) begin
				wr_en_mem1 = 1;
				wr_en_mem0 = 0;
				wr_addr_mem1 = wr_addr_ext_reg[9:0];
				wr_data_mem1 = wr_data_ext_reg;
				wr_addr_mem0 = 1'sb0;
				wr_data_mem0 = 1'sb0;
			end
			else begin
				wr_en_mem0 = 1;
				wr_en_mem1 = 0;
				wr_addr_mem0 = wr_addr_ext_reg[9:0];
				wr_data_mem0 = wr_data_ext_reg;
				wr_addr_mem1 = 1'sb0;
				wr_data_mem1 = 1'sb0;
			end
		end
		else begin
			wr_en_mem1 = 0;
			wr_en_mem0 = 0;
			wr_addr_mem1 = 1'sb0;
			wr_addr_mem0 = 1'sb0;
			wr_data_mem0 = 1'sb0;
			wr_data_mem1 = 1'sb0;
		end
	always @(*)
		if (rd_en_asserted) begin
			if (rd_addr[10] == 1) begin
				rd_data = rd_data_mem1;
				rd_addr_mem1 = rd_addr[9:0];
				rd_addr_mem0 = 1'sb0;
			end
			else begin
				rd_data = rd_data_mem0;
				rd_addr_mem0 = rd_addr[9:0];
				rd_addr_mem1 = 1'sb0;
			end
		end
		else begin
			rd_data = rd_data_mem0;
			rd_addr_mem1 = 1'sb0;
			rd_addr_mem0 = 1'sb0;
		end
	always @(*)
		if (rd_en_asserted) begin
			if (wr_en_ext_reg) begin
				if (wr_addr_ext_reg[10] == 1) begin
					muxed_addr_mem0 = rd_addr_mem0;
					muxed_addr_mem1 = wr_addr_mem1;
				end
				else begin
					muxed_addr_mem1 = rd_addr_mem1;
					muxed_addr_mem0 = wr_addr_mem0;
				end
			end
			else if (rd_addr[10] == 1) begin
				muxed_addr_mem1 = rd_addr_mem1;
				muxed_addr_mem0 = rd_addr_mem0;
			end
			else begin
				muxed_addr_mem0 = rd_addr_mem0;
				muxed_addr_mem1 = rd_addr_mem1;
			end
		end
		else if (wr_en_ext_reg) begin
			if (wr_addr_ext_reg[10] == 1) begin
				muxed_addr_mem1 = wr_addr_mem1;
				muxed_addr_mem0 = wr_addr_mem0;
			end
			else begin
				muxed_addr_mem0 = wr_addr_mem0;
				muxed_addr_mem1 = wr_addr_mem1;
			end
		end
		else begin
			muxed_addr_mem0 = 1'sb0;
			muxed_addr_mem1 = 1'sb0;
		end
	always @(*)
		if (rd_en_asserted) begin
			if (rd_addr_reg[9:0] != rd_addr[9:0]) begin
				if (rd_addr_reg[10] == 0) begin
					CEB_mem0 = 0;
					CEB_mem1 = 1;
				end
				else begin
					CEB_mem0 = 1;
					CEB_mem1 = 0;
				end
			end
			else if (wr_en_ext || wr_en_ext_reg) begin
				CEB_mem0 = 0;
				CEB_mem1 = 0;
			end
			else begin
				CEB_mem0 = 1;
				CEB_mem1 = 1;
			end
		end
		else if (wr_en_ext || wr_en_ext_reg) begin
			CEB_mem0 = 0;
			CEB_mem1 = 0;
		end
		else begin
			CEB_mem0 = 1;
			CEB_mem1 = 1;
		end
	SRAM_parametrizable_s_equivalent sparsity_mem0(
		.CLK(clk),
		.CEB(CEB_mem0),
		.WEB(~wr_en_mem0),
		.scan_en_in(scan_en_in),
		.A(muxed_addr_mem0),
		.D(wr_data_mem0),
		.Q(rd_data_mem0)
	);
	SRAM_parametrizable_s_equivalent sparsity_mem1(
		.CLK(clk),
		.CEB(CEB_mem1),
		.WEB(~wr_en_mem1),
		.scan_en_in(scan_en_in),
		.A(muxed_addr_mem1),
		.D(wr_data_mem1),
		.Q(rd_data_mem1)
	);
endmodule
