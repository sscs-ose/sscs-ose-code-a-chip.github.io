module nonlinear_block (
	clk,
	reset,
	PRECISION,
	wr_en_ext_lut,
	wr_addr_ext_lut,
	wr_data_ext_lut,
	NUMBER_OF_ACTIVATION_CYCLES,
	SHIFT_FIXED_POINT,
	enable_nonlinear_block,
	enable_pooling,
	enable_sig_tanh,
	PADDED_C_X,
	PADDED_O_X,
	type_nonlinear_function,
	input_channel_rd_addr,
	input_channel_rd_en,
	read_word,
	wr_en_output_buffer_nl,
	finished_activation,
	wr_addr_nl,
	output_word
);
	input clk;
	input reset;
	input wr_en_ext_lut;
	input [1:0] PRECISION;
	localparam integer parameters_LUT_SIZE = 2;
	localparam integer parameters_LUT_ADDR = 1;
	input [parameters_LUT_ADDR - 1:0] wr_addr_ext_lut;
	localparam integer parameters_LUT_DATA_WIDTH = 8;
	input signed [parameters_LUT_DATA_WIDTH - 1:0] wr_data_ext_lut;
	input enable_nonlinear_block;
	input enable_pooling;
	input enable_sig_tanh;
	input [7:0] SHIFT_FIXED_POINT;
	input [15:0] PADDED_C_X;
	input [15:0] PADDED_O_X;
	input [31:0] NUMBER_OF_ACTIVATION_CYCLES;
	localparam integer parameters_NUMBER_OF_NONLINEAR_FUNCTIONS_BITS = 3;
	input [parameters_NUMBER_OF_NONLINEAR_FUNCTIONS_BITS - 1:0] type_nonlinear_function;
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	localparam integer parameters_N_DIM_ARRAY = 4;
	input signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] read_word;
	localparam integer parameters_TOTAL_ACTIVATION_MEMORY_SIZE = 16384;
	localparam integer parameters_INPUT_CHANNEL_ADDR_SIZE = 14;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] input_channel_rd_addr;
	output reg input_channel_rd_en;
	output reg wr_en_output_buffer_nl;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_nl;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] output_word;
	output reg finished_activation;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] input_channel_rd_addr_pool;
	reg input_channel_rd_en_pool;
	reg wr_en_output_buffer_nl_pool;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_nl_pool;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] output_word_pool;
	reg finished_activation_pool;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] input_channel_rd_addr_st;
	reg input_channel_rd_en_st;
	reg wr_en_output_buffer_nl_st;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_nl_st;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] output_word_st;
	reg finished_activation_st;
	pooling POOLING_BLOCK(
		.clk(clk),
		.reset(reset),
		.PRECISION(PRECISION),
		.NUMBER_OF_ACTIVATION_CYCLES(NUMBER_OF_ACTIVATION_CYCLES),
		.PADDED_C_X(PADDED_C_X),
		.PADDED_O_X(PADDED_O_X),
		.SHIFT_FIXED_POINT(SHIFT_FIXED_POINT),
		.finished_activation(finished_activation_pool),
		.input_channel_rd_addr(input_channel_rd_addr_pool),
		.input_channel_rd_en(input_channel_rd_en_pool),
		.wr_en_output_buffer_nl(wr_en_output_buffer_nl_pool),
		.wr_addr_nl(wr_addr_nl_pool),
		.read_word(read_word),
		.output_word(output_word_pool),
		.type_nonlinear_function(type_nonlinear_function),
		.enable_nonlinear_block(enable_nonlinear_block)
	);
	sig_tanh SIG_TANH_BLOCK(
		.clk(clk),
		.reset(reset),
		.PRECISION(PRECISION),
		.wr_en_ext_lut(wr_en_ext_lut),
		.wr_addr_ext_lut(wr_addr_ext_lut),
		.wr_data_ext_lut(wr_data_ext_lut),
		.NUMBER_OF_ACTIVATION_CYCLES(NUMBER_OF_ACTIVATION_CYCLES),
		.PADDED_C_X(PADDED_C_X),
		.SHIFT_FIXED_POINT(SHIFT_FIXED_POINT),
		.finished_activation(finished_activation_st),
		.input_channel_rd_addr(input_channel_rd_addr_st),
		.input_channel_rd_en(input_channel_rd_en_st),
		.wr_en_output_buffer_nl(wr_en_output_buffer_nl_st),
		.wr_addr_nl(wr_addr_nl_st),
		.read_word(read_word),
		.output_word(output_word_st),
		.type_nonlinear_function(type_nonlinear_function),
		.enable_nonlinear_block(enable_nonlinear_block)
	);
	always @(*)
		if (enable_pooling == 1) begin
			input_channel_rd_addr = input_channel_rd_addr_pool;
			input_channel_rd_en = input_channel_rd_en_pool;
			wr_en_output_buffer_nl = wr_en_output_buffer_nl_pool;
			wr_addr_nl = wr_addr_nl_pool;
			output_word = output_word_pool;
			finished_activation = finished_activation_pool;
		end
		else if (enable_sig_tanh == 1) begin
			input_channel_rd_addr = input_channel_rd_addr_st;
			input_channel_rd_en = input_channel_rd_en_st;
			wr_en_output_buffer_nl = wr_en_output_buffer_nl_st;
			wr_addr_nl = wr_addr_nl_st;
			output_word = output_word_st;
			finished_activation = finished_activation_st;
		end
		else begin
			input_channel_rd_addr = input_channel_rd_addr_pool;
			input_channel_rd_en = input_channel_rd_en_pool;
			wr_en_output_buffer_nl = wr_en_output_buffer_nl_pool;
			wr_addr_nl = wr_addr_nl_pool;
			output_word = output_word_pool;
			finished_activation = finished_activation_pool;
		end
endmodule
