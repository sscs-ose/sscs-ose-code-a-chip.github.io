module input_buffer (
	clk,
	reset,
	enable,
	parallel_input_array,
	loading_in_parallel,
	shift_input_buffer,
	serial_input,
	mode,
	clear,
	output_array
);
	input clk;
	input reset;
	input clear;
	input enable;
	input loading_in_parallel;
	input [2:0] mode;
	localparam parameters_MAXIMUM_DILATION_BITS = 8;
	input [7:0] shift_input_buffer;
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	localparam integer parameters_N_DIM_ARRAY = 4;
	input signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] parallel_input_array;
	input signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] serial_input;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] output_array;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] FIFO [parameters_N_DIM_ARRAY - 1:0];
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] FIFO_output [parameters_N_DIM_ARRAY - 1:0];
	localparam integer parameters_N_DIM_ARRAY_LOG = 2;
	reg [parameters_N_DIM_ARRAY_LOG - 1:0] FIFO_POINTER;
	reg [parameters_N_DIM_ARRAY_LOG - 1:0] index [parameters_N_DIM_ARRAY - 1:0];
	reg [1:0] index_FIFO [parameters_N_DIM_ARRAY - 1:0];
	reg [parameters_N_DIM_ARRAY - 1:0] index_y [parameters_N_DIM_ARRAY - 1:0];
	reg loading_in_parallel_reg;
	integer i;
	integer j;
	reg [parameters_N_DIM_ARRAY_LOG - 1:0] index_0;
	reg [parameters_N_DIM_ARRAY_LOG - 1:0] index_1;
	always @(posedge clk or negedge reset)
		if (!reset)
			loading_in_parallel_reg <= 0;
		else
			loading_in_parallel_reg <= loading_in_parallel;
	localparam integer parameters_MODE_CNN = 1;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				FIFO[i] <= 0;
		end
		else if (clear == 1) begin
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				FIFO[i] <= 0;
		end
		else if (mode == parameters_MODE_CNN)
			if (loading_in_parallel_reg == 1) begin
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					FIFO[i] <= parallel_input_array[i * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
			end
			else if (enable == 1)
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					if (j < shift_input_buffer)
						FIFO[index_FIFO[j]] <= serial_input[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
	always @(*)
		for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
			if (j < shift_input_buffer) begin
				index_y[j] = j;
				index_FIFO[j] = FIFO_POINTER + index_y[j];
			end
			else begin
				index_y[j] = 0;
				index_FIFO[j] = 0;
			end
	always @(posedge clk or negedge reset)
		if (!reset)
			FIFO_POINTER <= 0;
		else if (clear == 1)
			FIFO_POINTER <= 0;
		else if (mode == parameters_MODE_CNN)
			if (loading_in_parallel_reg == 1)
				FIFO_POINTER <= 0;
			else if (enable)
				FIFO_POINTER <= FIFO_POINTER + shift_input_buffer;
	always @(*) begin
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
			FIFO_output[i] = 0;
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
			begin
				index[i] = i - FIFO_POINTER;
				FIFO_output[index[i]] = FIFO[i];
			end
	end
	localparam integer parameters_MODE_EWS = 3;
	localparam integer parameters_MODE_FC = 0;
	always @(*) begin
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
			output_array[i * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = 0;
		if ((mode == parameters_MODE_FC) || (mode == parameters_MODE_EWS)) begin
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				output_array[i * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = parallel_input_array[i * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH];
		end
		else
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				output_array[i * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] = FIFO_output[i];
	end
endmodule
