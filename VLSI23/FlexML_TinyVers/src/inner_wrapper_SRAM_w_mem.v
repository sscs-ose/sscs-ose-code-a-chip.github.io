module inner_wrapper_SRAM_w_mem (
	clk,
	reset,
	scan_en_in,
	rd_enable,
	rd_addr,
	rd_data,
	wr_enable,
	wr_addr,
	wr_data
);
	parameter integer SRAM_blocks_per_row = 4;
	parameter integer SRAM_blocks_per_column = 2;
	parameter SRAM_numBit = 8;
	parameter SRAM_numWordAddr = 10;
	parameter SRAM_blocks_per_row_log = $clog2(SRAM_blocks_per_row);
	localparam integer parameters_N_DIM_ARRAY = 4;
	localparam parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS = parameters_N_DIM_ARRAY;
	localparam parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS_log = 2;
	parameter SRAM_totalWordAddr = ((SRAM_numWordAddr + SRAM_blocks_per_row_log) + $clog2(SRAM_blocks_per_column)) + parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS_log;
	input clk;
	input reset;
	input scan_en_in;
	input rd_enable;
	input wr_enable;
	input signed [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] wr_data;
	input [SRAM_totalWordAddr - 1:0] wr_addr;
	input [SRAM_totalWordAddr - 1:0] rd_addr;
	output reg signed [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] rd_data;
	wire [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] D_concatenated [SRAM_blocks_per_column - 1:0];
	wire [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] Q_concatenated [SRAM_blocks_per_column - 1:0];
	reg rd_enable_reg;
	reg [(SRAM_totalWordAddr - (SRAM_numWordAddr + SRAM_blocks_per_row_log)) - 1:0] last_block_column;
	reg [(SRAM_totalWordAddr - (SRAM_numWordAddr + SRAM_blocks_per_row_log)) - 1:0] current_block_column;
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] CEB;
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] WEB;
	reg [((SRAM_blocks_per_column * SRAM_blocks_per_row) * SRAM_numWordAddr) - 1:0] A;
	reg [((SRAM_blocks_per_column * SRAM_blocks_per_row) * SRAM_numBit) - 1:0] D;
	reg [(SRAM_blocks_per_column * SRAM_numBit) - 1:0] BWEB;
	wire [SRAM_numBit - 1:0] Q [SRAM_blocks_per_column - 1:0][SRAM_blocks_per_row - 1:0];
	reg [(SRAM_blocks_per_column * 2) - 1:0] TSEL;
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] CEB_RP;
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] WEB_RP;
	reg [((SRAM_blocks_per_column * SRAM_blocks_per_row) * SRAM_numWordAddr) - 1:0] A_RP;
	reg [((SRAM_blocks_per_column * SRAM_blocks_per_row) * SRAM_numBit) - 1:0] D_RP;
	reg [(SRAM_blocks_per_column * SRAM_numBit) - 1:0] BWEB_RP;
	reg [(SRAM_blocks_per_column * 2) - 1:0] TSEL_RP;
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] CEB_WP;
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] WEB_WP;
	reg [((SRAM_blocks_per_column * SRAM_blocks_per_row) * SRAM_numWordAddr) - 1:0] A_WP;
	reg [((SRAM_blocks_per_column * SRAM_blocks_per_row) * SRAM_numBit) - 1:0] D_WP;
	reg [(SRAM_blocks_per_column * SRAM_numBit) - 1:0] BWEB_WP;
	wire [SRAM_numWordAddr - 1:0] A_temp;
	wire [SRAM_numBit - 1:0] D_temp;
	reg [(SRAM_blocks_per_column * 2) - 1:0] TSEL_WP;
	integer i;
	integer m;
	genvar j;
	genvar k;
	always @(*)
		for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
			begin
				TSEL_RP[m * 2+:2] = 2'b01;
				BWEB_RP[m * SRAM_numBit+:SRAM_numBit] = 0;
				for (i = 0; i < SRAM_blocks_per_row; i = i + 1)
					begin
						D_RP[((m * SRAM_blocks_per_row) + i) * SRAM_numBit+:SRAM_numBit] = 0;
						CEB_RP[(m * SRAM_blocks_per_row) + i] = 1;
						A_RP[((m * SRAM_blocks_per_row) + i) * SRAM_numWordAddr+:SRAM_numWordAddr] = 0;
						WEB_RP[(m * SRAM_blocks_per_row) + i] = 1;
					end
				for (i = 0; i < SRAM_blocks_per_row; i = i + 1)
					if (last_block_column != current_block_column)
						rd_data[i * SRAM_numBit+:SRAM_numBit] = Q[last_block_column][i][SRAM_numBit - 1:0];
					else
						rd_data[i * SRAM_numBit+:SRAM_numBit] = Q[current_block_column][i][SRAM_numBit - 1:0];
				if ((rd_enable == 1) && (m == rd_addr[SRAM_totalWordAddr - 1:SRAM_numWordAddr + SRAM_blocks_per_row_log])) begin
					if (last_block_column != current_block_column) begin
						for (i = 0; i < SRAM_blocks_per_row; i = i + 1)
							rd_data[i * SRAM_numBit+:SRAM_numBit] = Q[last_block_column][i][SRAM_numBit - 1:0];
					end
					else
						for (i = 0; i < SRAM_blocks_per_row; i = i + 1)
							rd_data[i * SRAM_numBit+:SRAM_numBit] = Q[current_block_column][i][SRAM_numBit - 1:0];
					for (i = 0; i < SRAM_blocks_per_row; i = i + 1)
						begin
							CEB_RP[(m * SRAM_blocks_per_row) + i] = 0;
							WEB_RP[(m * SRAM_blocks_per_row) + i] = 1;
							A_RP[((m * SRAM_blocks_per_row) + i) * SRAM_numWordAddr+:SRAM_numWordAddr] = rd_addr[(SRAM_numWordAddr + SRAM_blocks_per_row_log) - 1:SRAM_blocks_per_row_log];
						end
				end
			end
	always @(*)
		for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
			begin
				BWEB_WP[m * SRAM_numBit+:SRAM_numBit] = 0;
				TSEL_WP[m * 2+:2] = 2'b01;
				for (i = 0; i < SRAM_blocks_per_row; i = i + 1)
					begin
						A_WP[((m * SRAM_blocks_per_row) + i) * SRAM_numWordAddr+:SRAM_numWordAddr] = 0;
						D_WP[((m * SRAM_blocks_per_row) + i) * SRAM_numBit+:SRAM_numBit] = 0;
						CEB_WP[(m * SRAM_blocks_per_row) + i] = 1;
						WEB_WP[(m * SRAM_blocks_per_row) + i] = 1;
					end
				for (i = 0; i < SRAM_blocks_per_row; i = i + 1)
					if ((wr_enable == 1) && (m == wr_addr[SRAM_totalWordAddr - 1:SRAM_numWordAddr + SRAM_blocks_per_row_log])) begin
						A_WP[((m * SRAM_blocks_per_row) + i) * SRAM_numWordAddr+:SRAM_numWordAddr] = wr_addr[(SRAM_numWordAddr + SRAM_blocks_per_row_log) - 1:SRAM_blocks_per_row_log];
						D_WP[((m * SRAM_blocks_per_row) + i) * SRAM_numBit+:SRAM_numBit] = wr_data[i * SRAM_numBit+:SRAM_numBit];
						CEB_WP[(m * SRAM_blocks_per_row) + i] = 0;
						WEB_WP[(m * SRAM_blocks_per_row) + i] = 0;
					end
			end
	always @(*)
		if (wr_enable == 1) begin
			CEB = CEB_WP;
			WEB = WEB_WP;
			A = A_WP;
			D = D_WP;
			BWEB = BWEB_WP;
			TSEL = TSEL_WP;
		end
		else begin
			CEB = CEB_RP;
			WEB = WEB_RP;
			A = A_RP;
			D = D_RP;
			BWEB = BWEB_RP;
			TSEL = TSEL_RP;
		end
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	generate
		for (k = 0; k < SRAM_blocks_per_column; k = k + 1) begin : r_q
			for (j = 0; j < SRAM_blocks_per_row; j = j + 1) begin : c_q
				assign Q[k][j] = Q_concatenated[k][((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:j * parameters_INPUT_CHANNEL_DATA_WIDTH];
			end
		end
		for (k = 0; k < SRAM_blocks_per_column; k = k + 1) begin : r_d
			for (j = 0; j < SRAM_blocks_per_row; j = j + 1) begin : c_d
				assign D_concatenated[k][((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:j * parameters_INPUT_CHANNEL_DATA_WIDTH] = D[((k * SRAM_blocks_per_row) + j) * SRAM_numBit+:SRAM_numBit];
			end
		end
	endgenerate
	localparam integer parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT = 32;
	localparam integer parameters_MACRO_SRAM_N_WORDS_WEIGHT = 512;
	localparam integer parameters_W_NUMBER_OF_WORDS_PER_BANK = parameters_MACRO_SRAM_N_WORDS_WEIGHT * (parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT / 8);
	localparam integer parameters_W_NUMBER_OF_WORDS_PER_ROW = parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT / 8;
	localparam parameters_W_MEMORY_SIZE_BANK = parameters_W_NUMBER_OF_WORDS_PER_BANK / parameters_W_NUMBER_OF_WORDS_PER_ROW;
	generate
		for (k = 0; k < SRAM_blocks_per_column; k = k + 1) begin : generation_blocks
			for (j = 0; j < (SRAM_blocks_per_row / parameters_W_NUMBER_OF_WORDS_PER_ROW); j = j + 1) begin : generation_per_column
				SRAM_parametrizable_w_equivalent #(
					.numWord(parameters_W_MEMORY_SIZE_BANK),
					.numBit(parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT)
				) SRAM_equivalent_i(
					.CLK(clk),
					.CEB(CEB[k * SRAM_blocks_per_row]),
					.WEB(WEB[k * SRAM_blocks_per_row]),
					.scan_en_in(scan_en_in),
					.A(A[(k * SRAM_blocks_per_row) * SRAM_numWordAddr+:SRAM_numWordAddr]),
					.D(D_concatenated[k][(parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT * (j + 1)) - 1:parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT * j]),
					.Q(Q_concatenated[k][(parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT * (j + 1)) - 1:parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT * j])
				);
			end
		end
	endgenerate
	always @(*) current_block_column = rd_addr[SRAM_totalWordAddr - 1:SRAM_numWordAddr + SRAM_blocks_per_row_log];
	always @(posedge clk or negedge reset)
		if (!reset)
			last_block_column <= 0;
		else
			last_block_column <= current_block_column;
endmodule
