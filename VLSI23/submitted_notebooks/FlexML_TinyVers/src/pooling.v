module pooling (
	clk,
	reset,
	NUMBER_OF_ACTIVATION_CYCLES,
	PRECISION,
	SHIFT_FIXED_POINT,
	enable_nonlinear_block,
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
	input [1:0] PRECISION;
	input enable_nonlinear_block;
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
	integer j;
	integer i;
	integer k;
	reg [3:0] state;
	reg [3:0] next_state;
	localparam IDLE = 0;
	localparam POOLING_1D_PRE_READING = 5;
	localparam POOLING_1D_READING = 6;
	localparam POOLING_1D_OPERATION = 7;
	localparam POOLING_1D_WRITING = 8;
	localparam POOLING_2D_PRE_READING = 9;
	localparam POOLING_2D_READING_1 = 10;
	localparam POOLING_2D_OPERATION = 11;
	localparam POOLING_2D_WRITING = 12;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] max_value [parameters_N_DIM_ARRAY - 1:0];
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] max_value_1d [(parameters_N_DIM_ARRAY / 4) - 1:0];
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] max_value_2d [(parameters_N_DIM_ARRAY / 2) - 1:0];
	reg [15:0] counter;
	reg [15:0] next_counter;
	reg [15:0] counter_row;
	reg [15:0] next_counter_row;
	reg [15:0] counter_X_dimension;
	reg [15:0] next_counter_X_dimension;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] counter_wr_addr;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] next_counter_wr_addr;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] pooling_calculation;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] next_pooling_calculation [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] input_0;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] next_input_0;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] input_1;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] next_input_1;
	wire FINISHED_ROW_1D;
	wire FINISHED_ROW_2D;
	reg enable_pooling_1d;
	reg enable_pooling_2d;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] input_pooling;
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] input_pooling_subword_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] input_pooling_subword_1 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] input_0_subword_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] input_0_subword_1 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] read_word_subword_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] read_word_subword_1 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] max_value_2d_subword_0 [(parameters_N_DIM_ARRAY / 2) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] max_value_2d_subword_1 [(parameters_N_DIM_ARRAY / 2) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] max_value_1d_subword_0 [(parameters_N_DIM_ARRAY / 4) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1:0] max_value_1d_subword_1 [(parameters_N_DIM_ARRAY / 4) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] max_value_2d_subword_0_0 [(parameters_N_DIM_ARRAY / 2) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] max_value_2d_subword_0_1 [(parameters_N_DIM_ARRAY / 2) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] max_value_2d_subword_1_0 [(parameters_N_DIM_ARRAY / 2) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] max_value_2d_subword_1_1 [(parameters_N_DIM_ARRAY / 2) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] max_value_1d_subword_0_0 [(parameters_N_DIM_ARRAY / 4) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] max_value_1d_subword_0_1 [(parameters_N_DIM_ARRAY / 4) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] max_value_1d_subword_1_0 [(parameters_N_DIM_ARRAY / 4) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] max_value_1d_subword_1_1 [(parameters_N_DIM_ARRAY / 4) - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] input_pooling_subword_0_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] input_pooling_subword_0_1 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] input_pooling_subword_1_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] input_pooling_subword_1_1 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] input_0_subword_0_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] input_0_subword_0_1 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] input_0_subword_1_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] input_0_subword_1_1 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] read_word_subword_0_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] read_word_subword_0_1 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] read_word_subword_1_0 [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH / 4) - 1:0] read_word_subword_1_1 [parameters_N_DIM_ARRAY - 1:0];
	wire [1:1] sv2v_tmp_AF784;
	assign sv2v_tmp_AF784 = counter == NUMBER_OF_ACTIVATION_CYCLES;
	always @(*) finished_activation = sv2v_tmp_AF784;
	assign FINISHED_ROW_1D = counter_row == 3;
	assign FINISHED_ROW_2D = counter_row == 1;
	always @(posedge clk or negedge reset)
		if (!reset)
			state <= IDLE;
		else
			state <= next_state;
	always @(*) begin
		next_state = state;
		case (state)
			IDLE:
				if (enable_nonlinear_block)
					case (type_nonlinear_function)
						1: next_state = POOLING_1D_PRE_READING;
						2: next_state = POOLING_2D_PRE_READING;
						default: next_state = state;
					endcase
			POOLING_1D_PRE_READING: next_state = POOLING_1D_READING;
			POOLING_1D_READING: next_state = POOLING_1D_OPERATION;
			POOLING_1D_OPERATION:
				if (FINISHED_ROW_1D == 1)
					next_state = POOLING_1D_WRITING;
				else
					next_state = POOLING_1D_PRE_READING;
			POOLING_1D_WRITING:
				if (!finished_activation)
					next_state = POOLING_1D_PRE_READING;
				else
					next_state = IDLE;
			POOLING_2D_PRE_READING: next_state = POOLING_2D_READING_1;
			POOLING_2D_READING_1: next_state = POOLING_2D_OPERATION;
			POOLING_2D_OPERATION:
				if (FINISHED_ROW_2D == 1)
					next_state = POOLING_2D_WRITING;
				else
					next_state = POOLING_2D_PRE_READING;
			POOLING_2D_WRITING:
				if (!finished_activation)
					next_state = POOLING_2D_PRE_READING;
				else
					next_state = IDLE;
		endcase
	end
	always @(posedge clk or negedge reset)
		if (!reset) begin
			counter <= 0;
			counter_row <= 0;
			counter_X_dimension <= 0;
			counter_wr_addr <= 0;
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				input_0[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= 0;
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				input_1[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= 0;
		end
		else if (enable_nonlinear_block) begin
			counter <= next_counter;
			counter_row <= next_counter_row;
			counter_X_dimension <= next_counter_X_dimension;
			counter_wr_addr <= next_counter_wr_addr;
			input_0 <= next_input_0;
			input_1 <= next_input_1;
		end
	always @(*) begin
		next_counter = counter;
		next_counter_row = counter_row;
		next_counter_X_dimension = counter_X_dimension;
		next_input_0 = input_0;
		next_input_1 = input_1;
		next_counter_wr_addr = counter_wr_addr;
		case (state)
			IDLE: begin
				next_counter = 0;
				next_counter_row = 0;
				next_counter_X_dimension = 0;
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					next_input_0[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = 0;
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					next_input_1[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = 0;
				next_counter_wr_addr = 0;
			end
			POOLING_1D_READING: next_input_0 = read_word;
			POOLING_1D_OPERATION: begin
				if (counter_X_dimension == (PADDED_O_X - parameters_N_DIM_ARRAY))
					next_counter = (counter - (PADDED_O_X - PADDED_C_X)) + parameters_N_DIM_ARRAY;
				else
					next_counter = counter + parameters_N_DIM_ARRAY;
				if (counter_X_dimension == (PADDED_O_X - parameters_N_DIM_ARRAY))
					next_counter_X_dimension = 0;
				else
					next_counter_X_dimension = counter_X_dimension + parameters_N_DIM_ARRAY;
				if (counter_row == 3)
					next_counter_row = 0;
				else
					next_counter_row = counter_row + 1;
			end
			POOLING_1D_WRITING: begin
				next_counter_wr_addr = counter_wr_addr + 1;
				if (counter_row == (parameters_N_DIM_ARRAY - 1))
					next_counter_row = 0;
			end
			POOLING_2D_READING_1: next_input_0 = read_word;
			POOLING_2D_OPERATION: begin
				if (counter_row == 1)
					next_counter_row = 0;
				else
					next_counter_row = counter_row + 1;
				if (counter_X_dimension == (PADDED_O_X - parameters_N_DIM_ARRAY))
					next_counter = ((counter + PADDED_C_X) - (PADDED_O_X - PADDED_C_X)) + parameters_N_DIM_ARRAY;
				else
					next_counter = counter + parameters_N_DIM_ARRAY;
				if (counter_X_dimension == (PADDED_O_X - parameters_N_DIM_ARRAY))
					next_counter_X_dimension = 0;
				else
					next_counter_X_dimension = counter_X_dimension + parameters_N_DIM_ARRAY;
			end
			POOLING_2D_WRITING: begin
				next_counter_wr_addr = counter_wr_addr + 1;
				if (counter_row == (parameters_N_DIM_ARRAY - 1))
					next_counter_row = 0;
			end
			default: begin
				next_counter = counter;
				next_counter_row = counter_row;
			end
		endcase
	end
	always @(*) begin
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			output_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = 0;
		enable_pooling_1d = 0;
		enable_pooling_2d = 0;
		wr_en_output_buffer_nl = 0;
		input_channel_rd_addr = 0;
		input_channel_rd_en = 0;
		wr_addr_nl = 0;
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			input_pooling[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = 0;
		case (state)
			IDLE: begin
				wr_en_output_buffer_nl = 0;
				input_channel_rd_addr = 0;
				input_channel_rd_en = 0;
			end
			POOLING_1D_PRE_READING: begin
				input_channel_rd_addr = counter;
				input_channel_rd_en = 1;
			end
			POOLING_1D_READING: begin
				input_channel_rd_addr = counter;
				input_channel_rd_en = 1;
			end
			POOLING_1D_OPERATION: begin
				input_pooling = input_0;
				enable_pooling_1d = 1;
				input_channel_rd_addr = counter;
				input_channel_rd_en = 0;
			end
			POOLING_1D_WRITING: begin
				output_word = pooling_calculation;
				wr_en_output_buffer_nl = 1;
				wr_addr_nl = counter_wr_addr;
				input_channel_rd_addr = counter;
				input_channel_rd_en = 0;
			end
			POOLING_2D_PRE_READING: begin
				input_channel_rd_addr = counter;
				input_channel_rd_en = 1;
			end
			POOLING_2D_READING_1: begin
				input_channel_rd_addr = counter + PADDED_C_X;
				input_channel_rd_en = 1;
			end
			POOLING_2D_OPERATION: begin
				input_pooling = input_0;
				enable_pooling_2d = 1;
				input_channel_rd_addr = counter;
				input_channel_rd_en = 0;
			end
			POOLING_2D_WRITING: begin
				output_word = pooling_calculation;
				wr_en_output_buffer_nl = 1;
				wr_addr_nl = counter_wr_addr;
				input_channel_rd_addr = counter;
				input_channel_rd_en = 0;
			end
		endcase
	end
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				pooling_calculation[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= 0;
		end
		else if (enable_nonlinear_block)
			case (state)
				IDLE:
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						pooling_calculation[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= 0;
				POOLING_1D_OPERATION:
					for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
						pooling_calculation[(((parameters_N_DIM_ARRAY / 4) * counter_row) + k) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= max_value_1d[k];
				POOLING_2D_OPERATION:
					if (counter_row == 0) begin
						for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
							pooling_calculation[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= max_value_2d[j];
					end
					else
						for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
							pooling_calculation[((parameters_N_DIM_ARRAY / 2) + j) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= max_value_2d[j];
			endcase
	always @(*) begin
		for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
			max_value_1d[k] = 0;
		for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
			max_value_1d_subword_0[k] = input_pooling_subword_0[4 * k];
		for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
			max_value_1d_subword_1[k] = input_pooling_subword_1[4 * k];
		for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
			max_value_1d_subword_0_0[k] = input_0_subword_0_0[4 * k];
		for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
			max_value_1d_subword_0_1[k] = input_0_subword_0_1[4 * k];
		for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
			max_value_1d_subword_1_0[k] = input_0_subword_1_0[4 * k];
		for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
			max_value_1d_subword_1_1[k] = input_0_subword_1_1[4 * k];
		case (PRECISION)
			0: begin
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d[k] = input_pooling[(4 * k) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
				if (enable_pooling_1d)
					for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
						for (j = 0; j < 4; j = j + 1)
							if (input_pooling[((4 * k) + j) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] >= max_value_1d[k])
								max_value_1d[k] = input_pooling[((4 * k) + j) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
							else
								max_value_1d[k] = max_value_1d[k];
			end
			1: begin
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d_subword_0[k] = input_pooling_subword_0[4 * k];
				if (enable_pooling_1d)
					for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
						for (j = 0; j < 4; j = j + 1)
							if (input_pooling_subword_0[(4 * k) + j] >= max_value_1d_subword_0[k])
								max_value_1d_subword_0[k] = input_pooling_subword_0[(4 * k) + j];
							else
								max_value_1d_subword_0[k] = max_value_1d_subword_0[k];
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d_subword_1[k] = input_pooling_subword_1[4 * k];
				if (enable_pooling_1d)
					for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
						for (j = 0; j < 4; j = j + 1)
							if (input_pooling_subword_1[(4 * k) + j] >= max_value_1d_subword_1[k])
								max_value_1d_subword_1[k] = input_pooling_subword_1[(4 * k) + j];
							else
								max_value_1d_subword_1[k] = max_value_1d_subword_1[k];
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d[k] = {max_value_1d_subword_1[k], max_value_1d_subword_0[k]};
			end
			2: begin
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d_subword_0_0[k] = input_pooling_subword_0_0[4 * k];
				if (enable_pooling_1d)
					for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
						for (j = 0; j < 4; j = j + 1)
							if (input_pooling_subword_0_0[(4 * k) + j] >= max_value_1d_subword_0_0[k])
								max_value_1d_subword_0_0[k] = input_pooling_subword_0_0[(4 * k) + j];
							else
								max_value_1d_subword_0_0[k] = max_value_1d_subword_0_0[k];
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d_subword_0_1[k] = input_pooling_subword_0_1[4 * k];
				if (enable_pooling_1d)
					for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
						for (j = 0; j < 4; j = j + 1)
							if (input_pooling_subword_0_1[(4 * k) + j] >= max_value_1d_subword_0_1[k])
								max_value_1d_subword_0_1[k] = input_pooling_subword_0_1[(4 * k) + j];
							else
								max_value_1d_subword_0_1[k] = max_value_1d_subword_0_1[k];
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d_subword_1_0[k] = input_pooling_subword_1_0[4 * k];
				if (enable_pooling_1d)
					for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
						for (j = 0; j < 4; j = j + 1)
							if (input_pooling_subword_1_0[(4 * k) + j] >= max_value_1d_subword_1_0[k])
								max_value_1d_subword_1_0[k] = input_pooling_subword_1_0[(4 * k) + j];
							else
								max_value_1d_subword_1_0[k] = max_value_1d_subword_1_0[k];
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d_subword_1_1[k] = input_pooling_subword_1_1[4 * k];
				if (enable_pooling_1d)
					for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
						for (j = 0; j < 4; j = j + 1)
							if (input_pooling_subword_1_1[(4 * k) + j] >= max_value_1d_subword_1_1[k])
								max_value_1d_subword_1_1[k] = input_pooling_subword_1_1[(4 * k) + j];
							else
								max_value_1d_subword_1_1[k] = max_value_1d_subword_1_1[k];
				for (k = 0; k < (parameters_N_DIM_ARRAY / 4); k = k + 1)
					max_value_1d[k] = {max_value_1d_subword_1_1[k], max_value_1d_subword_1_0[k], max_value_1d_subword_0_1[k], max_value_1d_subword_0_0[k]};
			end
		endcase
	end
	always @(*) begin
		for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
			max_value_2d[j] = input_0[(j * 2) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
		for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
			max_value_2d_subword_0[j] = input_0_subword_0[j * 2];
		for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
			max_value_2d_subword_1[j] = input_0_subword_1[j * 2];
		for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
			max_value_2d_subword_0_0[j] = input_0_subword_0_0[j * 2];
		for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
			max_value_2d_subword_0_1[j] = input_0_subword_0_1[j * 2];
		for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
			max_value_2d_subword_1_0[j] = input_0_subword_1_0[j * 2];
		for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
			max_value_2d_subword_1_1[j] = input_0_subword_1_1[j * 2];
		if (enable_pooling_2d)
			case (PRECISION)
				0: begin
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (read_word[((j * 2) + k) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] > max_value_2d[j])
								max_value_2d[j] = read_word[((j * 2) + k) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (input_0[((j * 2) + k) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] > max_value_2d[j])
								max_value_2d[j] = input_0[((j * 2) + k) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
				end
				1: begin
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (read_word_subword_0[(j * 2) + k] > max_value_2d_subword_0[j])
								max_value_2d_subword_0[j] = read_word_subword_0[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (input_0_subword_0[(j * 2) + k] > max_value_2d_subword_0[j])
								max_value_2d_subword_0[j] = input_0_subword_0[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (read_word_subword_1[(j * 2) + k] > max_value_2d_subword_1[j])
								max_value_2d_subword_1[j] = read_word_subword_1[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (input_0_subword_1[(j * 2) + k] > max_value_2d_subword_1[j])
								max_value_2d_subword_1[j] = input_0_subword_1[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						max_value_2d[j] = {max_value_2d_subword_1[j], max_value_2d_subword_0[j]};
				end
				2: begin
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (read_word_subword_0_0[(j * 2) + k] > max_value_2d_subword_0_0[j])
								max_value_2d_subword_0_0[j] = read_word_subword_0_0[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (input_0_subword_0_0[(j * 2) + k] > max_value_2d_subword_0_0[j])
								max_value_2d_subword_0_0[j] = input_0_subword_0_0[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (read_word_subword_0_1[(j * 2) + k] > max_value_2d_subword_0_1[j])
								max_value_2d_subword_0_1[j] = read_word_subword_0_1[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (input_0_subword_0_1[(j * 2) + k] > max_value_2d_subword_0_1[j])
								max_value_2d_subword_0_1[j] = input_0_subword_0_1[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (read_word_subword_1_0[(j * 2) + k] > max_value_2d_subword_1_0[j])
								max_value_2d_subword_1_0[j] = read_word_subword_1_0[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (input_0_subword_1_0[(j * 2) + k] > max_value_2d_subword_1_0[j])
								max_value_2d_subword_1_0[j] = input_0_subword_1_0[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (read_word_subword_1_1[(j * 2) + k] > max_value_2d_subword_1_1[j])
								max_value_2d_subword_1_1[j] = read_word_subword_1_1[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						for (k = 0; k < 2; k = k + 1)
							if (input_0_subword_1_1[(j * 2) + k] > max_value_2d_subword_1_1[j])
								max_value_2d_subword_1_1[j] = input_0_subword_1_1[(j * 2) + k];
					for (j = 0; j < (parameters_N_DIM_ARRAY / 2); j = j + 1)
						max_value_2d[j] = {max_value_2d_subword_1_1[j], max_value_2d_subword_1_0[j], max_value_2d_subword_0_1[j], max_value_2d_subword_0_0[j]};
				end
			endcase
	end
	always @(*)
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			begin
				input_0_subword_1[j] = input_0[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? parameters_INPUT_CHANNEL_DATA_WIDTH - 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) + ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) - (parameters_INPUT_CHANNEL_DATA_WIDTH / 2)) + 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - (parameters_INPUT_CHANNEL_DATA_WIDTH - 1)) + 1)) - 1)-:((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) - (parameters_INPUT_CHANNEL_DATA_WIDTH / 2)) + 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - (parameters_INPUT_CHANNEL_DATA_WIDTH - 1)) + 1)];
				input_0_subword_0[j] = input_0[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2];
				read_word_subword_1[j] = read_word[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? parameters_INPUT_CHANNEL_DATA_WIDTH - 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) + ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) - (parameters_INPUT_CHANNEL_DATA_WIDTH / 2)) + 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - (parameters_INPUT_CHANNEL_DATA_WIDTH - 1)) + 1)) - 1)-:((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) - (parameters_INPUT_CHANNEL_DATA_WIDTH / 2)) + 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - (parameters_INPUT_CHANNEL_DATA_WIDTH - 1)) + 1)];
				read_word_subword_0[j] = read_word[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2];
				input_pooling_subword_1[j] = input_pooling[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? parameters_INPUT_CHANNEL_DATA_WIDTH - 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) + ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) - (parameters_INPUT_CHANNEL_DATA_WIDTH / 2)) + 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - (parameters_INPUT_CHANNEL_DATA_WIDTH - 1)) + 1)) - 1)-:((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) >= (parameters_INPUT_CHANNEL_DATA_WIDTH / 2) ? ((parameters_INPUT_CHANNEL_DATA_WIDTH - 1) - (parameters_INPUT_CHANNEL_DATA_WIDTH / 2)) + 1 : ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - (parameters_INPUT_CHANNEL_DATA_WIDTH - 1)) + 1)];
				input_pooling_subword_0[j] = input_pooling[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2];
				input_0_subword_1_1[j] = input_0[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 7-:2];
				input_0_subword_1_0[j] = input_0[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 5-:2];
				input_0_subword_0_1[j] = input_0[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 3-:2];
				input_0_subword_0_0[j] = input_0[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 1-:2];
				read_word_subword_1_1[j] = read_word[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 7-:2];
				read_word_subword_1_0[j] = read_word[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 5-:2];
				read_word_subword_0_1[j] = read_word[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 3-:2];
				read_word_subword_0_0[j] = read_word[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 1-:2];
				input_pooling_subword_1_1[j] = input_pooling[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 7-:2];
				input_pooling_subword_1_0[j] = input_pooling[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 5-:2];
				input_pooling_subword_0_1[j] = input_pooling[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 3-:2];
				input_pooling_subword_0_0[j] = input_pooling[(j * parameters_INPUT_CHANNEL_DATA_WIDTH) + 1-:2];
			end
endmodule
