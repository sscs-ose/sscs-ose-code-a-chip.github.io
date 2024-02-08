module activation_memory (
	clk,
	reset,
	scan_en_in,
	wr_en_ext,
	wr_addr_ext,
	wr_data_ext,
	wr_en,
	wr_addr_input,
	wr_input_word,
	rd_en_ext,
	rd_addr_ext,
	rd_data_ext,
	rd_en,
	rd_addr,
	read_word,
	mode,
	loading_in_parallel,
	input_memory_pointer,
	output_memory_pointer
);
	input clk;
	input reset;
	input rd_en;
	input scan_en_in;
	input [2:0] mode;
	input wr_en_ext;
	localparam integer parameters_TOTAL_ACTIVATION_MEMORY_SIZE = 16384;
	localparam integer parameters_INPUT_CHANNEL_ADDR_SIZE = 14;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_ext;
	localparam integer parameters_ACT_DATA_WIDTH = 8;
	localparam integer parameters_N_DIM_ARRAY = 4;
	input signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] wr_data_ext;
	input loading_in_parallel;
	input signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] wr_input_word;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] input_memory_pointer;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] output_memory_pointer;
	input wr_en;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_input;
	input rd_en_ext;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_ext;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] rd_data_ext;
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] read_word;
	wire signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] read_word_SRAM_0;
	wire signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] read_word_SRAM_1;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] output_channel_addresses;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] output_memory_pointer_shifted;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_shifted;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_counter;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_plus_offset;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_plus_offset;
	reg loading_in_parallel_reg;
	reg wr_en_0;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_0;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] wr_data_0;
	reg wr_en_1;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_1;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] wr_data_1;
	reg wr_en_ext_0;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_ext_0;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] wr_data_ext_0;
	reg wr_en_ext_1;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_ext_1;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] wr_data_ext_1;
	reg rd_en_ext_0;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_ext_0;
	wire signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] rd_data_ext_0;
	reg rd_en_ext_1;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_ext_1;
	wire signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] rd_data_ext_1;
	localparam integer parameters_N_DIM_ARRAY_LOG = 2;
	wire [parameters_N_DIM_ARRAY_LOG - 1:0] j_signal [parameters_N_DIM_ARRAY - 1:0];
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_plus_offset_reg;
	reg rd_enable_muxed;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_muxed;
	reg rd_enable_0;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_0;
	reg rd_enable_1;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_1;
	reg [parameters_N_DIM_ARRAY_LOG - 1:0] index_vector;
	reg wr_en_ext_muxed;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_ext_muxed;
	reg signed [parameters_ACT_DATA_WIDTH - 1:0] wr_data_ext_muxed [parameters_N_DIM_ARRAY - 1:0];
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_addr_ext_reg;
	genvar gj;
	integer i;
	integer j;
	assign wr_addr_plus_offset = wr_addr_input + (output_memory_pointer >> parameters_N_DIM_ARRAY_LOG);
	assign rd_addr_plus_offset = rd_addr + (input_memory_pointer >> parameters_N_DIM_ARRAY_LOG);
	assign rd_addr_shifted = (rd_addr >> parameters_N_DIM_ARRAY_LOG) + (input_memory_pointer >> parameters_N_DIM_ARRAY_LOG);
	always @(*) begin
		wr_en_0 = 0;
		wr_en_1 = 0;
		wr_addr_0 = 0;
		wr_addr_1 = 0;
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			begin
				wr_data_0[j * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = 0;
				wr_data_1[j * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = 0;
			end
		if ((wr_en == 1) && (output_memory_pointer[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 0)) begin
			wr_en_0 = wr_en;
			wr_data_0 = wr_input_word;
			wr_addr_0 = {wr_addr_plus_offset[(parameters_INPUT_CHANNEL_ADDR_SIZE - parameters_N_DIM_ARRAY_LOG) - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
		end
		else if ((wr_en == 1) && (output_memory_pointer[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 1)) begin
			wr_en_1 = wr_en;
			wr_data_1 = wr_input_word;
			wr_addr_1 = {wr_addr_plus_offset[(parameters_INPUT_CHANNEL_ADDR_SIZE - parameters_N_DIM_ARRAY_LOG) - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
		end
	end
	always @(*) begin
		wr_en_ext_0 = 0;
		wr_en_ext_1 = 0;
		wr_addr_ext_0 = 0;
		wr_addr_ext_1 = 0;
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			begin
				wr_data_ext_0[j * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = 0;
				wr_data_ext_1[j * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = 0;
			end
		if ((wr_en_ext == 1) && (wr_addr_ext[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 0)) begin
			wr_en_ext_0 = wr_en_ext;
			wr_data_ext_0 = wr_data_ext;
			wr_addr_ext_0 = wr_addr_ext;
		end
		else if ((wr_en_ext == 1) && (wr_addr_ext[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 1)) begin
			wr_en_ext_1 = wr_en_ext;
			wr_data_ext_1 = wr_data_ext;
			wr_addr_ext_1 = wr_addr_ext;
		end
	end
	localparam integer parameters_MODE_EWS = 3;
	localparam integer parameters_MODE_FC = 0;
	always @(*) begin
		rd_addr_0 = 0;
		rd_enable_0 = 0;
		rd_addr_1 = 0;
		rd_enable_1 = 0;
		if ((rd_en == 1) && (input_memory_pointer[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 0)) begin
			rd_enable_0 = rd_en;
			if ((mode == parameters_MODE_FC) || (mode == parameters_MODE_EWS))
				rd_addr_0 = {rd_addr_plus_offset[(parameters_INPUT_CHANNEL_ADDR_SIZE - parameters_N_DIM_ARRAY_LOG) - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
			else if (loading_in_parallel == 1)
				rd_addr_0 = {rd_addr_shifted[parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
			else
				rd_addr_0 = {rd_addr_shifted[parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0], rd_addr_plus_offset[parameters_N_DIM_ARRAY_LOG - 1:0]};
		end
		else if ((rd_en == 1) && (input_memory_pointer[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 1)) begin
			rd_enable_1 = rd_en;
			if ((mode == parameters_MODE_FC) || (mode == parameters_MODE_EWS))
				rd_addr_1 = {rd_addr_plus_offset[(parameters_INPUT_CHANNEL_ADDR_SIZE - parameters_N_DIM_ARRAY_LOG) - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
			else if (loading_in_parallel == 1)
				rd_addr_1 = {rd_addr_shifted[parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
			else
				rd_addr_1 = {rd_addr_shifted[parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0], rd_addr_plus_offset[parameters_N_DIM_ARRAY_LOG - 1:0]};
		end
		if ((mode == parameters_MODE_FC) || (mode == parameters_MODE_EWS))
			rd_addr_muxed = {rd_addr_plus_offset[(parameters_INPUT_CHANNEL_ADDR_SIZE - parameters_N_DIM_ARRAY_LOG) - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
		else if (loading_in_parallel == 1)
			rd_addr_muxed = {rd_addr_shifted[parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0], {parameters_N_DIM_ARRAY_LOG {1'b0}}};
		else
			rd_addr_muxed = {rd_addr_shifted[parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0], rd_addr_plus_offset[parameters_N_DIM_ARRAY_LOG - 1:0]};
	end
	always @(*) begin
		rd_en_ext_0 = 0;
		rd_en_ext_1 = 0;
		rd_addr_ext_0 = 0;
		rd_addr_ext_1 = 0;
		if ((rd_en_ext == 1) && (rd_addr_ext[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 0)) begin
			rd_en_ext_0 = rd_en_ext;
			rd_addr_ext_0 = rd_addr_ext;
		end
		else if ((rd_en_ext == 1) && (rd_addr_ext[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 1)) begin
			rd_en_ext_1 = rd_en_ext;
			rd_addr_ext_1 = rd_addr_ext;
		end
	end
	always @(*)
		if (rd_addr_ext_reg[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 0)
			rd_data_ext = rd_data_ext_0;
		else
			rd_data_ext = rd_data_ext_1;
	localparam integer parameters_MACRO_SRAM_BITS_PER_WORD_ACT = 32;
	localparam integer parameters_MACRO_SRAM_N_WORDS_ACT = 2048;
	localparam integer parameters_ACT_NUMBER_OF_WORDS_PER_BANK = parameters_MACRO_SRAM_N_WORDS_ACT * (parameters_MACRO_SRAM_BITS_PER_WORD_ACT / 8);
	localparam integer parameters_ACT_NUMBER_OF_WORDS_PER_ROW = parameters_MACRO_SRAM_BITS_PER_WORD_ACT / 8;
	localparam parameters_ACT_MEMORY_SIZE_BANK = parameters_ACT_NUMBER_OF_WORDS_PER_BANK / parameters_ACT_NUMBER_OF_WORDS_PER_ROW;
	localparam parameters_ACT_MEM_SRAM_blocks_per_column = (parameters_TOTAL_ACTIVATION_MEMORY_SIZE / parameters_N_DIM_ARRAY) / parameters_ACT_MEMORY_SIZE_BANK;
	localparam parameters_ACT_MEM_SRAM_blocks_per_row = parameters_N_DIM_ARRAY;
	localparam parameters_ACT_MEM_SRAM_numBit = parameters_INPUT_CHANNEL_DATA_WIDTH;
	localparam parameters_ACT_MEM_SRAM_numWordAddr = $clog2(parameters_ACT_MEMORY_SIZE_BANK);
	localparam parameters_ACT_MEM_SRAM_totalWordAddr = parameters_INPUT_CHANNEL_ADDR_SIZE;
	inner_wrapper_SRAM_act_mem #(
		.SRAM_blocks_per_row(parameters_ACT_MEM_SRAM_blocks_per_row),
		.SRAM_numBit(parameters_ACT_MEM_SRAM_numBit),
		.SRAM_numWordAddr(parameters_ACT_MEM_SRAM_numWordAddr),
		.SRAM_blocks_per_column(parameters_ACT_MEM_SRAM_blocks_per_column / 2)
	) ACT_MEM_0(
		.clk(clk),
		.reset(reset),
		.scan_en_in(scan_en_in),
		.rd_enable(rd_enable_0),
		.rd_addr(rd_addr_0[parameters_ACT_MEM_SRAM_totalWordAddr - 2:0]),
		.rd_data(read_word_SRAM_0),
		.rd_enable_ext(rd_en_ext_0),
		.rd_addr_ext(rd_addr_ext_0[parameters_ACT_MEM_SRAM_totalWordAddr - 2:0]),
		.rd_data_ext(rd_data_ext_0),
		.wr_enable(wr_en_0),
		.wr_addr(wr_addr_0[parameters_ACT_MEM_SRAM_totalWordAddr - 2:0]),
		.wr_data(wr_data_0),
		.wr_enable_ext(wr_en_ext_0),
		.wr_addr_ext(wr_addr_ext_0[parameters_ACT_MEM_SRAM_totalWordAddr - 2:0]),
		.wr_data_ext(wr_data_ext_0)
	);
	inner_wrapper_SRAM_act_mem #(
		.SRAM_blocks_per_row(parameters_ACT_MEM_SRAM_blocks_per_row),
		.SRAM_numBit(parameters_ACT_MEM_SRAM_numBit),
		.SRAM_numWordAddr(parameters_ACT_MEM_SRAM_numWordAddr),
		.SRAM_blocks_per_column(parameters_ACT_MEM_SRAM_blocks_per_column / 2)
	) ACT_MEM_1(
		.clk(clk),
		.reset(reset),
		.scan_en_in(scan_en_in),
		.rd_enable(rd_enable_1),
		.rd_addr(rd_addr_1[parameters_ACT_MEM_SRAM_totalWordAddr - 2:0]),
		.rd_data(read_word_SRAM_1),
		.rd_enable_ext(rd_en_ext_1),
		.rd_addr_ext(rd_addr_ext_1[parameters_ACT_MEM_SRAM_totalWordAddr - 2:0]),
		.rd_data_ext(rd_data_ext_1),
		.wr_enable(wr_en_1),
		.wr_addr(wr_addr_1[parameters_ACT_MEM_SRAM_totalWordAddr - 2:0]),
		.wr_data(wr_data_1),
		.wr_enable_ext(wr_en_ext_1),
		.wr_addr_ext(wr_addr_ext_1[parameters_ACT_MEM_SRAM_totalWordAddr - 2:0]),
		.wr_data_ext(wr_data_ext_1)
	);
	always @(posedge clk or negedge reset)
		if (!reset) begin
			rd_addr_plus_offset_reg <= 0;
			rd_addr_ext_reg <= 0;
		end
		else begin
			rd_addr_plus_offset_reg <= rd_addr_plus_offset;
			rd_addr_ext_reg <= rd_addr_ext;
		end
	always @(posedge clk or negedge reset)
		if (!reset)
			loading_in_parallel_reg <= 0;
		else
			loading_in_parallel_reg <= loading_in_parallel;
	localparam parameters_MAXIMUM_DILATION_BITS = 8;
	localparam integer parameters_MODE_CNN = 1;
	always @(*)
		if (input_memory_pointer[parameters_INPUT_CHANNEL_ADDR_SIZE - 1] == 0) begin
			if ((mode == parameters_MODE_CNN) && (loading_in_parallel_reg == 0)) begin
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					begin
						index_vector = rd_addr_plus_offset_reg[7:0] + j;
						read_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = read_word_SRAM_0[index_vector * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
					end
			end
			else
				read_word = read_word_SRAM_0;
		end
		else if ((mode == parameters_MODE_CNN) && (loading_in_parallel_reg == 0)) begin
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				begin
					index_vector = rd_addr_plus_offset_reg[7:0] + j;
					read_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = read_word_SRAM_1[index_vector * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
				end
		end
		else
			read_word = read_word_SRAM_1;
endmodule
