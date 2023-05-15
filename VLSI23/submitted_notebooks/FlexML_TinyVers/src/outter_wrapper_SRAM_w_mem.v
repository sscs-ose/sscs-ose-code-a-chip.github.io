module outter_wrapper_SRAM_w_mem (
	clk,
	reset,
	scan_en_in,
	MEMORY_POINTER_FC,
	FIRST_INDEX_FC_LOG,
	mode,
	rd_enable,
	rd_addr_fc,
	rd_addr_cnn,
	rd_data,
	rd_data_FC,
	wr_enable_fc,
	wr_addr_fc,
	wr_data_fc,
	wr_enable_cnn,
	wr_addr_cnn,
	wr_data_cnn
);
	parameter integer SRAM_blocks_per_row = 4;
	parameter integer SRAM_blocks_per_column = 2;
	parameter SRAM_numBit = 8;
	parameter SRAM_numWordAddr = 10;
	localparam integer parameters_N_DIM_ARRAY = 4;
	localparam parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS = parameters_N_DIM_ARRAY;
	localparam parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS_log = 2;
	parameter SRAM_outter_wrapper_totalWordAddr = ((SRAM_numWordAddr + $clog2(SRAM_blocks_per_row)) + $clog2(SRAM_blocks_per_column)) + parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS_log;
	input clk;
	input reset;
	input scan_en_in;
	input rd_enable;
	input [2:0] mode;
	input wr_enable_cnn;
	localparam parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row = parameters_N_DIM_ARRAY;
	localparam integer parameters_WEIGHT_DATA_WIDTH = 8;
	input signed [(parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_cnn;
	localparam integer parameters_TOTAL_WEIGHT_MEMORY_SIZE = 16384;
	localparam integer parameters_WEIGHT_MEMORY_ADDR_SIZE = 14;
	localparam parameters_CNN_W_MEM_SRAM_totalWordAddr = parameters_WEIGHT_MEMORY_ADDR_SIZE;
	input [parameters_CNN_W_MEM_SRAM_totalWordAddr - 1:0] wr_addr_cnn;
	input wr_enable_fc;
	input signed [(parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_fc;
	localparam parameters_FC_W_MEM_SRAM_totalWordAddr = parameters_WEIGHT_MEMORY_ADDR_SIZE;
	input [parameters_FC_W_MEM_SRAM_totalWordAddr - 1:0] wr_addr_fc;
	input [31:0] MEMORY_POINTER_FC;
	input [31:0] FIRST_INDEX_FC_LOG;
	input [parameters_FC_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_fc;
	input [parameters_CNN_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_cnn;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] rd_data;
	output reg signed [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_WEIGHT_DATA_WIDTH) - 1:0] rd_data_FC;
	wire [31:0] MEMORY_POINTER_FC_PER_BLOCK_fixed;
	reg wr_enable_muxed [parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS - 1:0];
	reg rd_enable_muxed [parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS - 1:0];
	localparam parameters_SUBBLOCK_W_MEM_SRAM_totalWordAddr = parameters_WEIGHT_MEMORY_ADDR_SIZE;
	reg [parameters_SUBBLOCK_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_muxed [parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS - 1:0];
	reg [parameters_SUBBLOCK_W_MEM_SRAM_totalWordAddr - 1:0] wr_addr_muxed [parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS - 1:0];
	reg signed [(parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_muxed [parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS - 1:0];
	reg [SRAM_outter_wrapper_totalWordAddr - 1:0] rd_addr_cnn_reg;
	reg [SRAM_outter_wrapper_totalWordAddr - 1:0] rd_addr_fc_reg;
	reg rd_enable_reg;
	wire signed [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_WEIGHT_DATA_WIDTH) - 1:0] read_word_CNN_Memory;
	reg [SRAM_outter_wrapper_totalWordAddr - 1:0] wr_addr_fc_corrected;
	reg [SRAM_outter_wrapper_totalWordAddr - 1:0] wr_addr_cnn_corrected;
	reg [SRAM_outter_wrapper_totalWordAddr - 1:0] rd_addr_fc_corrected;
	reg [SRAM_outter_wrapper_totalWordAddr - 1:0] rd_addr_cnn_corrected;
	genvar k;
	integer i;
	integer j;
	assign MEMORY_POINTER_FC_PER_BLOCK_fixed = MEMORY_POINTER_FC;
	generate
		for (k = 0; k < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; k = k + 1) begin : row
			inner_wrapper_SRAM_w_mem #(
				.SRAM_blocks_per_row(SRAM_blocks_per_row),
				.SRAM_numBit(SRAM_numBit),
				.SRAM_numWordAddr(SRAM_numWordAddr),
				.SRAM_blocks_per_column(SRAM_blocks_per_column)
			) BLOCK_i(
				.clk(clk),
				.reset(reset),
				.scan_en_in(scan_en_in),
				.wr_enable(wr_enable_muxed[k]),
				.wr_addr(wr_addr_muxed[k][SRAM_outter_wrapper_totalWordAddr - 1:0]),
				.wr_data(wr_data_muxed[k]),
				.rd_enable(rd_enable_muxed[k]),
				.rd_addr(rd_addr_muxed[k][SRAM_outter_wrapper_totalWordAddr - 1:0]),
				.rd_data(read_word_CNN_Memory[parameters_WEIGHT_DATA_WIDTH * (k * parameters_N_DIM_ARRAY)+:parameters_WEIGHT_DATA_WIDTH * parameters_N_DIM_ARRAY])
			);
		end
	endgenerate
	localparam integer parameters_N_DIM_ARRAY_LOG = 2;
	always @(*) begin
		for (i = 0; i < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; i = i + 1)
			begin
				wr_enable_muxed[i] = 0;
				wr_addr_muxed[i] = 0;
				for (j = 0; j < parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row; j = j + 1)
					wr_data_muxed[i][((parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row - 1) - j) * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = 0;
			end
		for (i = 0; i < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; i = i + 1)
			if (wr_enable_cnn == 1)
				if (i == wr_addr_cnn[FIRST_INDEX_FC_LOG - 1-:parameters_N_DIM_ARRAY_LOG]) begin
					wr_enable_muxed[i] = wr_enable_cnn;
					for (j = 0; j < SRAM_outter_wrapper_totalWordAddr; j = j + 1)
						if (j < (FIRST_INDEX_FC_LOG - parameters_N_DIM_ARRAY_LOG))
							wr_addr_cnn_corrected[j] = wr_addr_cnn[j];
						else
							wr_addr_cnn_corrected[j] = 0;
					wr_addr_muxed[i] = wr_addr_cnn_corrected;
					wr_data_muxed[i] = wr_data_cnn;
				end
		for (i = 0; i < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; i = i + 1)
			if (wr_enable_fc == 1)
				if (i == wr_addr_fc[(2 * parameters_N_DIM_ARRAY_LOG) - 1:parameters_N_DIM_ARRAY_LOG]) begin
					wr_enable_muxed[i] = wr_enable_fc;
					wr_addr_fc_corrected = wr_addr_fc >> (2 * parameters_N_DIM_ARRAY_LOG);
					wr_addr_muxed[i] = MEMORY_POINTER_FC_PER_BLOCK_fixed + {wr_addr_fc_corrected, wr_addr_fc[parameters_N_DIM_ARRAY_LOG - 1:0]};
					wr_data_muxed[i] = wr_data_fc;
				end
	end
	wire [31:0] temp_variable;
	assign temp_variable = rd_addr_cnn[FIRST_INDEX_FC_LOG - 1-:parameters_N_DIM_ARRAY_LOG];
	localparam integer parameters_MODE_CNN = 1;
	always @(*) begin
		for (i = 0; i < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; i = i + 1)
			begin
				rd_enable_muxed[i] = 0;
				rd_addr_muxed[i] = 0;
				rd_addr_cnn_corrected = 0;
				rd_addr_fc_corrected = 0;
			end
		for (i = 0; i < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; i = i + 1)
			if ((rd_enable == 1) && (mode == parameters_MODE_CNN))
				if (i == rd_addr_cnn[FIRST_INDEX_FC_LOG - 1-:parameters_N_DIM_ARRAY_LOG]) begin
					rd_enable_muxed[i] = rd_enable;
					for (j = 0; j < SRAM_outter_wrapper_totalWordAddr; j = j + 1)
						if (j < (FIRST_INDEX_FC_LOG - parameters_N_DIM_ARRAY_LOG))
							rd_addr_cnn_corrected[j] = rd_addr_cnn[j];
						else
							rd_addr_cnn_corrected[j] = 0;
					rd_addr_muxed[i] = rd_addr_cnn_corrected;
				end
		for (i = 0; i < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; i = i + 1)
			if ((rd_enable == 1) && (mode != parameters_MODE_CNN)) begin
				rd_enable_muxed[i] = rd_enable;
				rd_addr_fc_corrected = rd_addr_fc >> (2 * parameters_N_DIM_ARRAY_LOG);
				rd_addr_muxed[i] = MEMORY_POINTER_FC_PER_BLOCK_fixed + {rd_addr_fc_corrected, rd_addr_fc[parameters_N_DIM_ARRAY_LOG - 1:0]};
			end
	end
	always @(*) begin
		for (i = 0; i < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; i = i + 1)
			begin
				rd_data[i * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = 0;
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					rd_data_FC[((i * parameters_N_DIM_ARRAY) + j) * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = 0;
			end
		for (i = 0; i < parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS; i = i + 1)
			if ((rd_enable_reg == 1) && (mode == parameters_MODE_CNN))
				if (i == rd_addr_cnn_reg[FIRST_INDEX_FC_LOG - 1-:parameters_N_DIM_ARRAY_LOG])
					rd_data = read_word_CNN_Memory[parameters_WEIGHT_DATA_WIDTH * (i * parameters_N_DIM_ARRAY)+:parameters_WEIGHT_DATA_WIDTH * parameters_N_DIM_ARRAY];
		if ((rd_enable_reg == 1) && (mode != parameters_MODE_CNN))
			rd_data_FC = read_word_CNN_Memory;
	end
	always @(posedge clk or negedge reset)
		if (!reset) begin
			rd_enable_reg <= 0;
			rd_addr_cnn_reg <= 0;
			rd_addr_fc_reg <= 0;
		end
		else begin
			rd_enable_reg <= rd_enable;
			rd_addr_cnn_reg <= rd_addr_cnn;
			rd_addr_fc_reg <= rd_addr_fc;
		end
endmodule
