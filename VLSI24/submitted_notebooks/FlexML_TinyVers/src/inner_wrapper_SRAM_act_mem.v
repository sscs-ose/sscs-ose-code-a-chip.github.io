module inner_wrapper_SRAM_act_mem (
	clk,
	reset,
	scan_en_in,
	rd_enable,
	rd_addr,
	rd_data,
	wr_enable_ext,
	wr_addr_ext,
	wr_data_ext,
	rd_enable_ext,
	rd_addr_ext,
	rd_data_ext,
	wr_enable,
	wr_addr,
	wr_data
);
	parameter integer SRAM_blocks_per_row = 4;
	parameter integer SRAM_blocks_per_column = 2;
	parameter SRAM_numBit = 8;
	parameter SRAM_numWordAddr = 7;
	parameter SRAM_blocks_per_row_log = $clog2(SRAM_blocks_per_row);
	parameter SRAM_totalWordAddr = (SRAM_numWordAddr + SRAM_blocks_per_row_log) + $clog2(SRAM_blocks_per_column);
	input clk;
	input reset;
	input scan_en_in;
	input rd_enable;
	input wr_enable;
	input signed [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] wr_data;
	input [SRAM_totalWordAddr - 1:0] wr_addr;
	input [SRAM_totalWordAddr - 1:0] rd_addr;
	input [SRAM_totalWordAddr - 1:0] wr_addr_ext;
	input wr_enable_ext;
	input signed [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] wr_data_ext;
	input rd_enable_ext;
	input [SRAM_totalWordAddr - 1:0] rd_addr_ext;
	localparam integer parameters_N_DIM_ARRAY = 4;
	output reg signed [(parameters_N_DIM_ARRAY * SRAM_numBit) - 1:0] rd_data_ext;
	output wire signed [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] rd_data;
	reg signed [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] rd_data_temp;
	reg [SRAM_totalWordAddr - 1:0] rd_addr_muxed;
	reg rd_enable_muxed;
	reg rd_enable_ext_reg;
	reg rd_enable_reg_0;
	reg rd_enable_reg_1;
	reg [SRAM_totalWordAddr - 1:0] rd_addr_reg;
	reg [(SRAM_totalWordAddr - (SRAM_numWordAddr + SRAM_blocks_per_row_log)) - 1:0] last_block_column;
	reg [(SRAM_totalWordAddr - (SRAM_numWordAddr + SRAM_blocks_per_row_log)) - 1:0] current_block_column;
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] CEB;
	reg CEB_reg [SRAM_blocks_per_column - 1:0][SRAM_blocks_per_row - 1:0];
	reg [SRAM_blocks_per_row - 1:0] CEB_RF [SRAM_blocks_per_column - 1:0];
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] CEB_SRAM;
	reg [(SRAM_blocks_per_column * SRAM_blocks_per_row) - 1:0] WEB;
	reg [((SRAM_blocks_per_column * SRAM_blocks_per_row) * SRAM_numWordAddr) - 1:0] A;
	reg [SRAM_numWordAddr - 1:0] A_reg [SRAM_blocks_per_column - 1:0][SRAM_blocks_per_row - 1:0];
	reg [((SRAM_blocks_per_column * SRAM_blocks_per_row) * SRAM_numBit) - 1:0] D;
	wire [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] D_concatenated [SRAM_blocks_per_column - 1:0];
	reg [(SRAM_blocks_per_column * SRAM_numBit) - 1:0] BWEB;
	wire [SRAM_numBit - 1:0] Q [SRAM_blocks_per_column - 1:0][SRAM_blocks_per_row - 1:0];
	reg [(SRAM_blocks_per_column * (SRAM_blocks_per_row * SRAM_numBit)) - 1:0] Q_concatenated;
	wire [(SRAM_blocks_per_column * (SRAM_blocks_per_row * SRAM_numBit)) - 1:0] Q_concatenated_SRAM;
	wire [(SRAM_blocks_per_row * SRAM_numBit) - 1:0] Q_concatenated_RF [SRAM_blocks_per_column - 1:0];
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
	reg [(SRAM_blocks_per_column * 2) - 1:0] TSEL_WP;
	reg updated_rd_address_reg;
	wire updated_rd_address;
	reg state;
	integer i;
	integer m;
	integer n;
	integer h;
	genvar j;
	genvar k;
	assign updated_rd_address = (rd_enable_muxed && (rd_addr_muxed[SRAM_totalWordAddr - 1:SRAM_blocks_per_row_log] != rd_addr_reg[SRAM_totalWordAddr - 1:SRAM_blocks_per_row_log])) || (rd_addr_muxed == rd_addr_reg);
	always @(*)
		if (rd_enable_ext == 1) begin
			rd_enable_muxed = rd_enable_ext;
			rd_addr_muxed = rd_addr_ext;
		end
		else begin
			rd_enable_muxed = rd_enable;
			rd_addr_muxed = rd_addr;
		end
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
					if ((rd_enable_muxed == 1) && (m == rd_addr_muxed[SRAM_totalWordAddr - 1:SRAM_numWordAddr + SRAM_blocks_per_row_log])) begin
						if (last_block_column != current_block_column)
							rd_data_temp[i * SRAM_numBit+:SRAM_numBit] = Q[last_block_column][i][SRAM_numBit - 1:0];
						else
							rd_data_temp[i * SRAM_numBit+:SRAM_numBit] = Q[current_block_column][i][SRAM_numBit - 1:0];
						if (updated_rd_address) begin
							CEB_RP[(m * SRAM_blocks_per_row) + i] = 0;
							WEB_RP[(m * SRAM_blocks_per_row) + i] = 1;
							A_RP[((m * SRAM_blocks_per_row) + i) * SRAM_numWordAddr+:SRAM_numWordAddr] = rd_addr_muxed[(SRAM_numWordAddr + SRAM_blocks_per_row_log) - 1:SRAM_blocks_per_row_log];
						end
						else begin
							CEB_RP[(m * SRAM_blocks_per_row) + i] = 1;
							WEB_RP[(m * SRAM_blocks_per_row) + i] = 1;
							A_RP[((m * SRAM_blocks_per_row) + i) * SRAM_numWordAddr+:SRAM_numWordAddr] = rd_addr_muxed[(SRAM_numWordAddr + SRAM_blocks_per_row_log) - 1:SRAM_blocks_per_row_log];
						end
					end
					else
						rd_data_temp[i * SRAM_numBit+:SRAM_numBit] = Q[last_block_column][i][SRAM_numBit - 1:0];
			end
	always @(*) begin
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
			end
		for (i = 0; i < SRAM_blocks_per_row; i = i + 1)
			for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
				if ((wr_enable_ext == 1) && (m == wr_addr_ext[SRAM_totalWordAddr - 1:SRAM_numWordAddr + SRAM_blocks_per_row_log])) begin
					A_WP[((m * SRAM_blocks_per_row) + i) * SRAM_numWordAddr+:SRAM_numWordAddr] = wr_addr_ext[(SRAM_numWordAddr + SRAM_blocks_per_row_log) - 1:SRAM_blocks_per_row_log];
					D_WP[((m * SRAM_blocks_per_row) + i) * SRAM_numBit+:SRAM_numBit] = wr_data_ext[i * SRAM_numBit+:SRAM_numBit];
					CEB_WP[(m * SRAM_blocks_per_row) + i] = 0;
					WEB_WP[(m * SRAM_blocks_per_row) + i] = 0;
				end
				else if ((wr_enable == 1) && (m == wr_addr[SRAM_totalWordAddr - 1:SRAM_numWordAddr + SRAM_blocks_per_row_log])) begin
					A_WP[((m * SRAM_blocks_per_row) + i) * SRAM_numWordAddr+:SRAM_numWordAddr] = wr_addr[(SRAM_numWordAddr + SRAM_blocks_per_row_log) - 1:SRAM_blocks_per_row_log];
					D_WP[((m * SRAM_blocks_per_row) + i) * SRAM_numBit+:SRAM_numBit] = wr_data[i * SRAM_numBit+:SRAM_numBit];
					CEB_WP[(m * SRAM_blocks_per_row) + i] = 0;
					WEB_WP[(m * SRAM_blocks_per_row) + i] = 0;
				end
	end
	always @(*)
		if ((wr_enable_ext == 1) || (wr_enable == 1)) begin
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
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
				for (n = 0; n < SRAM_blocks_per_row; n = n + 1)
					A_reg[m][n] <= 0;
		end
		else
			for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
				for (n = 0; n < SRAM_blocks_per_row; n = n + 1)
					A_reg[m][n] <= A[((m * SRAM_blocks_per_row) + n) * SRAM_numWordAddr+:SRAM_numWordAddr];
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
				for (n = 0; n < SRAM_blocks_per_row; n = n + 1)
					CEB_reg[m][n] <= 0;
		end
		else
			for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
				for (n = 0; n < SRAM_blocks_per_row; n = n + 1)
					CEB_reg[m][n] <= CEB[(m * SRAM_blocks_per_row) + n];
	always @(*) begin
		Q_concatenated = Q_concatenated_SRAM;
		for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
			if ((m == 0) && (A_reg[m][0] < 64))
				Q_concatenated[m * (SRAM_blocks_per_row * SRAM_numBit)+:SRAM_blocks_per_row * SRAM_numBit] = Q_concatenated_RF[m];
			else
				Q_concatenated[m * (SRAM_blocks_per_row * SRAM_numBit)+:SRAM_blocks_per_row * SRAM_numBit] = Q_concatenated_SRAM[m * (SRAM_blocks_per_row * SRAM_numBit)+:SRAM_blocks_per_row * SRAM_numBit];
	end
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	generate
		for (k = 0; k < SRAM_blocks_per_column; k = k + 1) begin : r_q
			for (j = 0; j < SRAM_blocks_per_row; j = j + 1) begin : c_q
				assign Q[k][j] = Q_concatenated[(k * (SRAM_blocks_per_row * SRAM_numBit)) + ((((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1) >= (j * parameters_INPUT_CHANNEL_DATA_WIDTH) ? ((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1 : ((((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1) + ((((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1) >= (j * parameters_INPUT_CHANNEL_DATA_WIDTH) ? ((((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1) - (j * parameters_INPUT_CHANNEL_DATA_WIDTH)) + 1 : ((j * parameters_INPUT_CHANNEL_DATA_WIDTH) - (((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1)) + 1)) - 1)-:((((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1) >= (j * parameters_INPUT_CHANNEL_DATA_WIDTH) ? ((((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1) - (j * parameters_INPUT_CHANNEL_DATA_WIDTH)) + 1 : ((j * parameters_INPUT_CHANNEL_DATA_WIDTH) - (((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1)) + 1)];
			end
		end
		for (k = 0; k < SRAM_blocks_per_column; k = k + 1) begin : r_d
			for (j = 0; j < SRAM_blocks_per_row; j = j + 1) begin : c_d
				assign D_concatenated[k][((j + 1) * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:j * parameters_INPUT_CHANNEL_DATA_WIDTH] = D[((k * SRAM_blocks_per_row) + j) * SRAM_numBit+:SRAM_numBit];
			end
		end
	endgenerate
	always @(*) begin
		CEB_SRAM = CEB;
		for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
			CEB_RF[m][0] = 1;
		for (m = 0; m < SRAM_blocks_per_column; m = m + 1)
			if ((m == 0) && (A[(m * SRAM_blocks_per_row) * SRAM_numWordAddr+:SRAM_numWordAddr] < 64)) begin
				CEB_SRAM[m * SRAM_blocks_per_row] = 1;
				CEB_RF[m] = CEB[m * SRAM_blocks_per_row+:SRAM_blocks_per_row];
			end
			else begin
				CEB_SRAM[m * SRAM_blocks_per_row+:SRAM_blocks_per_row] = CEB[m * SRAM_blocks_per_row+:SRAM_blocks_per_row];
				CEB_RF[m][0] = 1;
			end
	end
	localparam integer parameters_MACRO_SRAM_BITS_PER_WORD_ACT = 32;
	localparam integer parameters_MACRO_SRAM_N_WORDS_ACT = 2048;
	localparam integer parameters_ACT_NUMBER_OF_WORDS_PER_BANK = parameters_MACRO_SRAM_N_WORDS_ACT * (parameters_MACRO_SRAM_BITS_PER_WORD_ACT / 8);
	localparam integer parameters_ACT_NUMBER_OF_WORDS_PER_ROW = parameters_MACRO_SRAM_BITS_PER_WORD_ACT / 8;
	localparam parameters_ACT_MEMORY_SIZE_BANK = parameters_ACT_NUMBER_OF_WORDS_PER_BANK / parameters_ACT_NUMBER_OF_WORDS_PER_ROW;
	generate
		for (k = 0; k < SRAM_blocks_per_column; k = k + 1) begin : generation_blocks
			for (j = 0; j < (SRAM_blocks_per_row / parameters_ACT_NUMBER_OF_WORDS_PER_ROW); j = j + 1) begin : generation_blocks_2
				SRAM_parametrizable_equivalent #(
					.numWord(parameters_ACT_MEMORY_SIZE_BANK),
					.numBit(parameters_MACRO_SRAM_BITS_PER_WORD_ACT)
				) SRAM_equivalent_i(
					.CLK(clk),
					.CEB(CEB_SRAM[k * SRAM_blocks_per_row]),
					.WEB(WEB[k * SRAM_blocks_per_row]),
					.scan_en_in(scan_en_in),
					.A(A[(k * SRAM_blocks_per_row) * SRAM_numWordAddr+:SRAM_numWordAddr]),
					.D(D_concatenated[k][(parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1:parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j]),
					.Q(Q_concatenated_SRAM[(k * (SRAM_blocks_per_row * SRAM_numBit)) + (((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1) >= (parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j) ? (parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1 : (((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1) + (((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1) >= (parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j) ? (((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1) - (parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j)) + 1 : ((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j) - ((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1)) + 1)) - 1)-:(((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1) >= (parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j) ? (((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1) - (parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j)) + 1 : ((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j) - ((parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1)) + 1)])
				);
			end
		end
		for (k = 0; k < 1; k = k + 1) begin : generation_RF_column
			for (j = 0; j < (SRAM_blocks_per_row / parameters_ACT_NUMBER_OF_WORDS_PER_ROW); j = j + 1) begin : generation_blocks_RF_row
				SRAM_parametrizable_equivalent #(
					.numWord(64),
					.numBit(parameters_MACRO_SRAM_BITS_PER_WORD_ACT)
				) REGISTER_FILE_0(
					.CLK(clk),
					//.reset(reset),
					.CEB(CEB_RF[k][0]),
					.WEB(WEB[k * SRAM_blocks_per_row]),
					.scan_en_in(scan_en_in),
					.A(A[((k * SRAM_blocks_per_row) * SRAM_numWordAddr) + 5-:6]),
					.D(D_concatenated[k][(parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1:parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j]),
					.Q(Q_concatenated_RF[k][(parameters_MACRO_SRAM_BITS_PER_WORD_ACT * (j + 1)) - 1:parameters_MACRO_SRAM_BITS_PER_WORD_ACT * j])
				);
			end
		end
	endgenerate
	always @(*) current_block_column = rd_addr_muxed[SRAM_totalWordAddr - 1:SRAM_numWordAddr + SRAM_blocks_per_row_log];
	always @(posedge clk or negedge reset)
		if (!reset)
			last_block_column <= 0;
		else if (rd_enable_muxed == 1)
			last_block_column <= current_block_column;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			rd_addr_reg <= 0;
			rd_enable_ext_reg <= 0;
		end
		else begin
			rd_enable_ext_reg <= rd_enable_ext;
			if (rd_enable)
				rd_addr_reg <= rd_addr_muxed;
		end
	always @(*)
		if (rd_enable_ext_reg == 1)
			rd_data_ext = rd_data_temp;
		else
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				rd_data_ext[i * SRAM_numBit+:SRAM_numBit] = 0;
	assign rd_data = rd_data_temp;
endmodule
