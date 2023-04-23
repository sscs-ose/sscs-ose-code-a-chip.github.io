module weight_memory (
	clk,
	reset,
	enable,
	scan_en_in,
	wr_en_ext_fc_w,
	wr_addr_ext_fc_w,
	wr_data_ext_fc_w,
	wr_en_ext_cnn_w,
	wr_addr_ext_cnn_w,
	wr_data_ext_cnn_w,
	mode,
	rd_en,
	rd_addr,
	MEMORY_POINTER_FC,
	FIRST_INDEX_FC_LOG,
	weight_memory_pointer,
	read_word
);
	input clk;
	input reset;
	input enable;
	input scan_en_in;
	input wr_en_ext_fc_w;
	localparam integer parameters_TOTAL_WEIGHT_MEMORY_SIZE = 16384;
	localparam integer parameters_WEIGHT_MEMORY_ADDR_SIZE = 14;
	input [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] wr_addr_ext_fc_w;
	localparam integer parameters_N_DIM_ARRAY = 4;
	localparam integer parameters_WEIGHT_DATA_WIDTH = 8;
	input signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_ext_fc_w;
	input wr_en_ext_cnn_w;
	input [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] wr_addr_ext_cnn_w;
	input signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_ext_cnn_w;
	input rd_en;
	input [2:0] mode;
	input [31:0] MEMORY_POINTER_FC;
	input [31:0] FIRST_INDEX_FC_LOG;
	input [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] rd_addr;
	input [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] weight_memory_pointer;
	output reg signed [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_WEIGHT_DATA_WIDTH) - 1:0] read_word;
	reg signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] read_word_CNN_Memory;
	reg signed [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_WEIGHT_DATA_WIDTH) - 1:0] read_word_FC_Memory_reordered;
	wire [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] rd_addr_plus_offset;
	localparam parameters_FC_W_MEM_SRAM_totalWordAddr = parameters_WEIGHT_MEMORY_ADDR_SIZE;
	wire [parameters_FC_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_fc;
	localparam parameters_CNN_W_MEM_SRAM_totalWordAddr = parameters_WEIGHT_MEMORY_ADDR_SIZE;
	wire [parameters_CNN_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_cnn;
	reg wr_en_ext_fc_w_0;
	reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] wr_addr_ext_fc_w_0;
	reg signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_ext_fc_w_0;
	reg wr_en_ext_cnn_w_0;
	reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] wr_addr_ext_cnn_w_0;
	reg signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_ext_cnn_w_0;
	reg rd_en_0;
	reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] rd_addr_0;
	reg [parameters_FC_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_fc_0;
	reg [parameters_CNN_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_cnn_0;
	wire signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] read_word_CNN_Memory_0;
	wire signed [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_WEIGHT_DATA_WIDTH) - 1:0] read_word_FC_Memory_reordered_0;
	reg wr_en_ext_fc_w_1;
	reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] wr_addr_ext_fc_w_1;
	reg signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_ext_fc_w_1;
	reg wr_en_ext_cnn_w_1;
	reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] wr_addr_ext_cnn_w_1;
	reg signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] wr_data_ext_cnn_w_1;
	reg rd_en_1;
	reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] rd_addr_1;
	reg [parameters_FC_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_fc_1;
	reg [parameters_CNN_W_MEM_SRAM_totalWordAddr - 1:0] rd_addr_cnn_1;
	wire signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] read_word_CNN_Memory_1;
	wire signed [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_WEIGHT_DATA_WIDTH) - 1:0] read_word_FC_Memory_reordered_1;
	reg rd_en_reg;
	reg ping_pong_bit;
	integer i;
	integer j;
	integer k;
	integer m;
	genvar r;
	assign rd_addr_plus_offset = rd_addr + weight_memory_pointer;
	localparam integer parameters_N_DIM_ARRAY_LOG = 2;
	assign rd_addr_fc = {rd_addr_plus_offset[(parameters_FC_W_MEM_SRAM_totalWordAddr - (2 * parameters_N_DIM_ARRAY_LOG)) - 1:0], {2 * parameters_N_DIM_ARRAY_LOG {1'b0}}};
	assign rd_addr_cnn = {rd_addr_plus_offset[(parameters_CNN_W_MEM_SRAM_totalWordAddr - parameters_N_DIM_ARRAY_LOG) - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
	localparam integer parameters_MODE_CNN = 1;
	localparam integer parameters_MODE_FC = 0;
	always @(*) begin
		if (wr_en_ext_fc_w) begin
			if (wr_addr_ext_fc_w[parameters_WEIGHT_MEMORY_ADDR_SIZE - 1] == 1) begin
				wr_en_ext_fc_w_0 = 0;
				wr_addr_ext_fc_w_0 = 0;
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					wr_data_ext_fc_w_0[j * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = {parameters_WEIGHT_DATA_WIDTH {1'b0}};
				wr_en_ext_fc_w_1 = wr_en_ext_fc_w;
				wr_addr_ext_fc_w_1 = wr_addr_ext_fc_w;
				wr_data_ext_fc_w_1 = wr_data_ext_fc_w;
			end
			else begin
				wr_en_ext_fc_w_1 = 0;
				wr_addr_ext_fc_w_1 = 0;
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					wr_data_ext_fc_w_1[j * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = {parameters_WEIGHT_DATA_WIDTH {1'b0}};
				wr_en_ext_fc_w_0 = wr_en_ext_fc_w;
				wr_addr_ext_fc_w_0 = wr_addr_ext_fc_w;
				wr_data_ext_fc_w_0 = wr_data_ext_fc_w;
			end
		end
		else begin
			wr_en_ext_fc_w_0 = 0;
			wr_addr_ext_fc_w_0 = 0;
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				wr_data_ext_fc_w_0[j * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = {parameters_WEIGHT_DATA_WIDTH {1'b0}};
			wr_en_ext_fc_w_1 = 0;
			wr_addr_ext_fc_w_1 = 0;
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				wr_data_ext_fc_w_1[j * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = {parameters_WEIGHT_DATA_WIDTH {1'b0}};
		end
		if (wr_en_ext_cnn_w) begin
			if (wr_addr_ext_cnn_w[parameters_WEIGHT_MEMORY_ADDR_SIZE - 1] == 1) begin
				wr_en_ext_cnn_w_0 = 0;
				wr_addr_ext_cnn_w_0 = 0;
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					wr_data_ext_cnn_w_0[j * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = {parameters_WEIGHT_DATA_WIDTH {1'b0}};
				wr_en_ext_cnn_w_1 = wr_en_ext_cnn_w;
				wr_addr_ext_cnn_w_1 = wr_addr_ext_cnn_w;
				wr_data_ext_cnn_w_1 = wr_data_ext_cnn_w;
			end
			else begin
				wr_en_ext_cnn_w_1 = 0;
				wr_addr_ext_cnn_w_1 = 0;
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					wr_data_ext_cnn_w_1[j * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = {parameters_WEIGHT_DATA_WIDTH {1'b0}};
				wr_en_ext_cnn_w_0 = wr_en_ext_cnn_w;
				wr_addr_ext_cnn_w_0 = wr_addr_ext_cnn_w;
				wr_data_ext_cnn_w_0 = wr_data_ext_cnn_w;
			end
		end
		else begin
			wr_en_ext_cnn_w_0 = 0;
			wr_addr_ext_cnn_w_0 = 0;
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				wr_data_ext_cnn_w_0[j * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = {parameters_WEIGHT_DATA_WIDTH {1'b0}};
			wr_en_ext_cnn_w_1 = 0;
			wr_addr_ext_cnn_w_1 = 0;
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				wr_data_ext_cnn_w_1[j * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = {parameters_WEIGHT_DATA_WIDTH {1'b0}};
		end
		if (rd_en) begin
			if (weight_memory_pointer[(parameters_WEIGHT_MEMORY_ADDR_SIZE - (2 * parameters_N_DIM_ARRAY_LOG)) - 1]) begin
				rd_addr_fc_1 = rd_addr_fc;
				rd_addr_fc_0 = 0;
			end
			else begin
				rd_addr_fc_0 = rd_addr_fc;
				rd_addr_fc_1 = 0;
			end
		end
		else begin
			rd_addr_fc_0 = 0;
			rd_addr_fc_1 = 0;
		end
		if (rd_en) begin
			if (weight_memory_pointer[(parameters_WEIGHT_MEMORY_ADDR_SIZE - parameters_N_DIM_ARRAY_LOG) - 1]) begin
				rd_addr_cnn_1 = rd_addr_cnn;
				rd_addr_cnn_0 = 0;
			end
			else begin
				rd_addr_cnn_0 = rd_addr_cnn;
				rd_addr_cnn_1 = 0;
			end
		end
		else begin
			rd_addr_cnn_0 = 0;
			rd_addr_cnn_1 = 0;
		end
		if (rd_en) begin
			if (((mode == parameters_MODE_CNN) && rd_addr_cnn[parameters_WEIGHT_MEMORY_ADDR_SIZE - 1]) || ((mode == parameters_MODE_FC) && weight_memory_pointer[(parameters_WEIGHT_MEMORY_ADDR_SIZE - (2 * parameters_N_DIM_ARRAY_LOG)) - 1])) begin
				rd_en_1 = rd_en;
				rd_en_0 = 0;
			end
			else begin
				rd_en_0 = rd_en;
				rd_en_1 = 0;
			end
		end
		else begin
			rd_en_0 = 0;
			rd_en_1 = 0;
		end
		if (rd_en_reg) begin
			if (ping_pong_bit == 1) begin
				read_word_FC_Memory_reordered = read_word_FC_Memory_reordered_1;
				read_word_CNN_Memory = read_word_CNN_Memory_1;
			end
			else begin
				read_word_FC_Memory_reordered = read_word_FC_Memory_reordered_0;
				read_word_CNN_Memory = read_word_CNN_Memory_0;
			end
		end
		else begin
			read_word_FC_Memory_reordered = read_word_FC_Memory_reordered_0;
			read_word_CNN_Memory = read_word_CNN_Memory_0;
		end
	end
	localparam parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS = parameters_N_DIM_ARRAY;
	localparam parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row = parameters_N_DIM_ARRAY;
	localparam integer parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT = 32;
	localparam integer parameters_MACRO_SRAM_N_WORDS_WEIGHT = 512;
	localparam integer parameters_W_NUMBER_OF_WORDS_PER_BANK = parameters_MACRO_SRAM_N_WORDS_WEIGHT * (parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT / 8);
	localparam integer parameters_W_NUMBER_OF_WORDS_PER_ROW = parameters_MACRO_SRAM_BITS_PER_WORD_WEIGHT / 8;
	localparam parameters_W_MEMORY_SIZE_BANK = parameters_W_NUMBER_OF_WORDS_PER_BANK / parameters_W_NUMBER_OF_WORDS_PER_ROW;
	localparam parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_column = (parameters_TOTAL_WEIGHT_MEMORY_SIZE / (parameters_SUBBLOCK_W_MEM_NUMBER_OF_SUBBLOCKS * (parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row / parameters_W_NUMBER_OF_WORDS_PER_ROW))) / (parameters_W_MEMORY_SIZE_BANK * parameters_W_NUMBER_OF_WORDS_PER_ROW);
	localparam parameters_SUBBLOCK_W_MEM_SRAM_numBit = parameters_WEIGHT_DATA_WIDTH;
	localparam parameters_SUBBLOCK_W_MEM_SRAM_numWordAddr = $clog2(parameters_W_MEMORY_SIZE_BANK);
	outter_wrapper_SRAM_w_mem #(
		.SRAM_blocks_per_row(parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row),
		.SRAM_numBit(parameters_SUBBLOCK_W_MEM_SRAM_numBit),
		.SRAM_numWordAddr(parameters_SUBBLOCK_W_MEM_SRAM_numWordAddr),
		.SRAM_blocks_per_column(parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_column / 2)
	) UNIFIED_W_0(
		.clk(clk),
		.reset(reset),
		.scan_en_in(scan_en_in),
		.MEMORY_POINTER_FC(MEMORY_POINTER_FC),
		.FIRST_INDEX_FC_LOG(FIRST_INDEX_FC_LOG),
		.mode(mode),
		.rd_enable(rd_en_0),
		.rd_addr_fc({1'b0, rd_addr_fc_0[parameters_WEIGHT_MEMORY_ADDR_SIZE - 2:0]}),
		.rd_addr_cnn(rd_addr_cnn_0),
		.wr_enable_fc(wr_en_ext_fc_w_0),
		.wr_addr_fc({1'b0, wr_addr_ext_fc_w_0[parameters_WEIGHT_MEMORY_ADDR_SIZE - 2:0]}),
		.wr_data_fc(wr_data_ext_fc_w_0),
		.wr_enable_cnn(wr_en_ext_cnn_w_0),
		.wr_addr_cnn(wr_addr_ext_cnn_w_0),
		.wr_data_cnn(wr_data_ext_cnn_w_0),
		.rd_data(read_word_CNN_Memory_0),
		.rd_data_FC(read_word_FC_Memory_reordered_0)
	);
	outter_wrapper_SRAM_w_mem #(
		.SRAM_blocks_per_row(parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_row),
		.SRAM_numBit(parameters_SUBBLOCK_W_MEM_SRAM_numBit),
		.SRAM_numWordAddr(parameters_SUBBLOCK_W_MEM_SRAM_numWordAddr),
		.SRAM_blocks_per_column(parameters_SUBBLOCK_W_MEM_SRAM_blocks_per_column / 2)
	) UNIFIED_W_1(
		.clk(clk),
		.reset(reset),
		.scan_en_in(scan_en_in),
		.MEMORY_POINTER_FC(MEMORY_POINTER_FC),
		.FIRST_INDEX_FC_LOG(FIRST_INDEX_FC_LOG),
		.mode(mode),
		.rd_enable(rd_en_1),
		.rd_addr_fc({1'b0, rd_addr_fc_1[parameters_WEIGHT_MEMORY_ADDR_SIZE - 2:0]}),
		.rd_addr_cnn(rd_addr_cnn_1),
		.wr_enable_fc(wr_en_ext_fc_w_1),
		.wr_addr_fc({1'b0, wr_addr_ext_fc_w_1[parameters_WEIGHT_MEMORY_ADDR_SIZE - 2:0]}),
		.wr_data_fc(wr_data_ext_fc_w_1),
		.wr_enable_cnn(wr_en_ext_cnn_w_1),
		.wr_addr_cnn(wr_addr_ext_cnn_w_1),
		.wr_data_cnn(wr_data_ext_cnn_w_1),
		.rd_data(read_word_CNN_Memory_1),
		.rd_data_FC(read_word_FC_Memory_reordered_1)
	);
	always @(*) begin
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				read_word[((i * parameters_N_DIM_ARRAY) + j) * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = 0;
		if (mode == parameters_MODE_CNN) begin
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				if (j == 0) begin
					for (k = 0; k < parameters_N_DIM_ARRAY; k = k + 1)
						read_word[((j * parameters_N_DIM_ARRAY) + k) * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = read_word_CNN_Memory[k * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH];
				end
				else
					for (k = 0; k < parameters_N_DIM_ARRAY; k = k + 1)
						read_word[((j * parameters_N_DIM_ARRAY) + k) * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH] = 0;
		end
		else
			read_word = read_word_FC_Memory_reordered;
	end
	always @(posedge clk or negedge reset)
		if (!reset) begin
			rd_en_reg <= 0;
			ping_pong_bit <= 0;
		end
		else begin
			rd_en_reg <= rd_en;
			if (mode == parameters_MODE_CNN)
				ping_pong_bit <= rd_addr_cnn[parameters_WEIGHT_MEMORY_ADDR_SIZE - 1];
			else
				ping_pong_bit <= weight_memory_pointer[(parameters_WEIGHT_MEMORY_ADDR_SIZE - (2 * parameters_N_DIM_ARRAY_LOG)) - 1];
		end
endmodule
