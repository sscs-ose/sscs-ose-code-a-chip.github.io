module sig_tanh (
	wr_en_ext_lut,
	wr_addr_ext_lut,
	wr_data_ext_lut,
	clk,
	reset,
	PRECISION,
	NUMBER_OF_ACTIVATION_CYCLES,
	SHIFT_FIXED_POINT,
	enable_nonlinear_block,
	PADDED_C_X,
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
	input wr_en_ext_lut;
	localparam integer parameters_LUT_SIZE = 2;
	localparam integer parameters_LUT_ADDR = 1;
	input [parameters_LUT_ADDR - 1:0] wr_addr_ext_lut;
	localparam integer parameters_LUT_DATA_WIDTH = 8;
	input signed [parameters_LUT_DATA_WIDTH - 1:0] wr_data_ext_lut;
	input [7:0] SHIFT_FIXED_POINT;
	input [15:0] PADDED_C_X;
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
	localparam ACTIVATION_PRE_READING = 1;
	localparam ACTIVATION_READING = 2;
	localparam ACTIVATION_OPERATION = 3;
	localparam ACTIVATION_WRITING = 4;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] read_word_shifted [parameters_N_DIM_ARRAY - 1:0];
	reg [15:0] counter;
	reg [15:0] next_counter;
	reg [15:0] counter_row;
	reg [15:0] next_counter_row;
	reg [15:0] counter_X_dimension;
	reg [15:0] next_counter_X_dimension;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] counter_wr_addr;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] next_counter_wr_addr;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] output_relu;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] output_act;
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH * 2) - 1:0] MULT_A_X [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_INPUT_CHANNEL_DATA_WIDTH * 2) - 1:0] B_SHIFTED [parameters_N_DIM_ARRAY - 1:0];
	reg enable_relu;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] LUT [parameters_LUT_SIZE - 1:0];
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] A_sigmoid;
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] B_sigmoid;
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] X_initial_PWS_sigmoid;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] index_sigmoid [parameters_N_DIM_ARRAY - 1:0];
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] SHIFT_ADDRESS_sigmoid;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] X_MAX_sigmoid;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] X_MIN_sigmoid;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] Y_MAX_sigmoid;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] Y_MIN_sigmoid;
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] A_tanh;
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] B_tanh;
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] X_initial_PWS_tanh;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] index_tanh [parameters_N_DIM_ARRAY - 1:0];
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] SHIFT_ADDRESS_tanh;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] X_MAX_tanh;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] X_MIN_tanh;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] Y_MAX_tanh;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] Y_MIN_tanh;
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] A;
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] B;
	reg signed [(8 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] X_initial_PWS;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] index [parameters_N_DIM_ARRAY - 1:0];
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] SHIFT_ADDRESS;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] X_MAX;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] X_MIN;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] Y_MAX;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] Y_MIN;
	wire [1:1] sv2v_tmp_AF784;
	assign sv2v_tmp_AF784 = counter == NUMBER_OF_ACTIVATION_CYCLES;
	always @(*) finished_activation = sv2v_tmp_AF784;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (i = 0; i < parameters_LUT_SIZE; i = i + 1)
				LUT[i] <= 0;
		end
		else if (wr_en_ext_lut)
			LUT[wr_addr_ext_lut] <= wr_data_ext_lut;
	always @(*)
		for (i = 0; i < parameters_LUT_SIZE; i = i + 1)
			if (i == 0)
				SHIFT_ADDRESS_sigmoid = LUT[i];
			else if (i == 1)
				X_MIN_sigmoid = LUT[i];
			else if (i == 2)
				X_MAX_sigmoid = LUT[i];
			else if (i == 3)
				Y_MIN_sigmoid = LUT[i];
			else if (i == 4)
				Y_MAX_sigmoid = LUT[i];
			else if (i == 5)
				SHIFT_ADDRESS_tanh = LUT[i];
			else if (i == 6)
				X_MIN_tanh = LUT[i];
			else if (i == 7)
				X_MAX_tanh = LUT[i];
			else if (i == 8)
				Y_MIN_tanh = LUT[i];
			else if (i == 9)
				Y_MAX_tanh = LUT[i];
			else if ((i > 9) && (i <= 17))
				X_initial_PWS_sigmoid[(i - 10) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = LUT[i];
			else if ((i > 17) && (i <= 25))
				A_sigmoid[(i - 18) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = LUT[i];
			else if ((i > 25) && (i <= 33))
				B_sigmoid[(i - 26) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = LUT[i];
			else if ((i > 33) && (i <= 41))
				X_initial_PWS_tanh[(i - 34) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = LUT[i];
			else if ((i > 41) && (i <= 49))
				A_tanh[(i - 42) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = LUT[i];
			else if ((i > 49) && (i <= 57))
				B_tanh[(i - 50) * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = LUT[i];
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
						0: next_state = ACTIVATION_PRE_READING;
						3: next_state = ACTIVATION_PRE_READING;
						4: next_state = ACTIVATION_PRE_READING;
						default: next_state = state;
					endcase
			ACTIVATION_PRE_READING:
				if (finished_activation)
					next_state = IDLE;
				else
					next_state = ACTIVATION_READING;
			ACTIVATION_READING: next_state = ACTIVATION_OPERATION;
			ACTIVATION_OPERATION: next_state = ACTIVATION_WRITING;
			ACTIVATION_WRITING:
				if (!finished_activation)
					next_state = ACTIVATION_PRE_READING;
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
		end
		else if (enable_nonlinear_block) begin
			counter <= next_counter;
			counter_row <= next_counter_row;
			counter_X_dimension <= next_counter_X_dimension;
			counter_wr_addr <= next_counter_wr_addr;
		end
	always @(*) begin
		next_counter = counter;
		next_counter_row = counter_row;
		next_counter_X_dimension = counter_X_dimension;
		next_counter_wr_addr = counter_wr_addr;
		case (state)
			IDLE: begin
				next_counter = 0;
				next_counter_row = 0;
				next_counter_X_dimension = 0;
				next_counter_wr_addr = 0;
			end
			ACTIVATION_READING: next_counter_row = 0;
			ACTIVATION_WRITING: next_counter = counter + 1;
			default: begin
				next_counter = counter;
				next_counter_row = counter_row;
			end
		endcase
	end
	always @(*) begin
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			output_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = 0;
		case (type_nonlinear_function)
			0: output_word = output_relu;
			3: output_word = output_act;
			4: output_word = output_act;
		endcase
	end
	localparam integer parameters_N_DIM_ARRAY_LOG = 2;
	always @(*) begin
		enable_relu = 0;
		wr_en_output_buffer_nl = 0;
		input_channel_rd_addr = 0;
		input_channel_rd_en = 0;
		wr_addr_nl = 0;
		case (state)
			IDLE: begin
				wr_en_output_buffer_nl = 0;
				input_channel_rd_addr = 0;
				input_channel_rd_en = 0;
			end
			ACTIVATION_PRE_READING: begin
				input_channel_rd_addr = counter << parameters_N_DIM_ARRAY_LOG;
				input_channel_rd_en = 1;
			end
			ACTIVATION_READING: begin
				input_channel_rd_addr = counter << parameters_N_DIM_ARRAY_LOG;
				input_channel_rd_en = 1;
			end
			ACTIVATION_OPERATION: begin
				enable_relu = 1;
				input_channel_rd_addr = counter << parameters_N_DIM_ARRAY_LOG;
				input_channel_rd_en = 0;
			end
			ACTIVATION_WRITING: begin
				wr_en_output_buffer_nl = 1;
				input_channel_rd_addr = counter << parameters_N_DIM_ARRAY_LOG;
				input_channel_rd_en = 0;
			end
		endcase
	end
	always @(*) begin
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			output_relu[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = 0;
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			if (read_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] > 0)
				output_relu[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = read_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
			else
				output_relu[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = 0;
	end
	always @(*)
		if (type_nonlinear_function == 3) begin
			A = A_sigmoid;
			B = B_sigmoid;
			X_initial_PWS = X_initial_PWS_sigmoid;
			SHIFT_ADDRESS = SHIFT_ADDRESS_sigmoid;
			X_MAX = X_MAX_sigmoid;
			X_MIN = X_MIN_sigmoid;
			Y_MAX = Y_MAX_sigmoid;
			Y_MIN = Y_MIN_sigmoid;
		end
		else if (type_nonlinear_function == 4) begin
			A = A_tanh;
			B = B_tanh;
			X_initial_PWS = X_initial_PWS_tanh;
			SHIFT_ADDRESS = SHIFT_ADDRESS_tanh;
			X_MAX = X_MAX_tanh;
			X_MIN = X_MIN_tanh;
			Y_MAX = Y_MAX_tanh;
			Y_MIN = Y_MIN_tanh;
		end
		else begin
			A = A_sigmoid;
			B = B_sigmoid;
			X_initial_PWS = X_initial_PWS_sigmoid;
			SHIFT_ADDRESS = SHIFT_ADDRESS_sigmoid;
			X_MAX = X_MAX_sigmoid;
			X_MIN = X_MIN_sigmoid;
			Y_MAX = Y_MAX_sigmoid;
			Y_MIN = Y_MIN_sigmoid;
		end
	always @(*) begin
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			index[j] = 0;
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			begin
				read_word_shifted[j] = read_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] >> SHIFT_ADDRESS;
				for (i = 0; i < 8; i = i + 1)
					if (read_word_shifted[j] == (X_initial_PWS[i * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] >> SHIFT_ADDRESS))
						index[j] = i;
				if (read_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= X_MIN)
					output_act[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = Y_MIN;
				else if (read_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] >= X_MAX)
					output_act[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = Y_MAX;
				else begin
					MULT_A_X[j] = A[index[j] * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] * read_word[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
					B_SHIFTED[j] = {{parameters_INPUT_CHANNEL_DATA_WIDTH {B[(index[j] * parameters_INPUT_CHANNEL_DATA_WIDTH) + (parameters_INPUT_CHANNEL_DATA_WIDTH - 1)]}}, B[index[j] * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH]} << SHIFT_FIXED_POINT;
					output_act[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = (MULT_A_X[j] + B_SHIFTED[j]) >> SHIFT_FIXED_POINT;
				end
			end
	end
endmodule
