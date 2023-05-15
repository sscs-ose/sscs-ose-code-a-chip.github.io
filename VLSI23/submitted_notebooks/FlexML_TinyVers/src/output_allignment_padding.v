module output_allignment_padding (
	clk,
	reset,
	reinitialize_padding,
	padd_zeros_left,
	padd_zeros_right,
	input_word,
	input_enable,
	output_word,
	output_enable
);
	input clk;
	input reset;
	input [2:0] padd_zeros_left;
	input [2:0] padd_zeros_right;
	input reinitialize_padding;
	localparam integer parameters_ACT_DATA_WIDTH = 8;
	localparam integer parameters_N_DIM_ARRAY = 4;
	input signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] input_word;
	input input_enable;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] output_word;
	output reg output_enable;
	integer i;
	integer j;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] memory [parameters_N_DIM_ARRAY - 1:0];
	reg [2:0] counter;
	always @(*) begin
		output_enable = input_enable;
		if (padd_zeros_left == 0)
			output_word = input_word;
		else
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				if (i < padd_zeros_left)
					output_word[i * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = memory[counter][((parameters_N_DIM_ARRAY - padd_zeros_left) + i) * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH];
				else
					output_word[i * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = input_word[(i - padd_zeros_left) * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH];
		if (padd_zeros_right == 0)
			output_word = output_word;
		else
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				if (i < padd_zeros_right)
					output_word[((parameters_N_DIM_ARRAY - 1) - i) * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = 0;
	end
	always @(posedge clk or negedge reset)
		if (!reset)
			counter <= 0;
		else if (input_enable)
			counter <= counter + 1;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					memory[i][j * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
		end
		else if (reinitialize_padding) begin
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					memory[i][j * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
		end
		else if (input_enable)
			memory[counter] <= input_word;
endmodule
