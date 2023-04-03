module stream32bTO64b (
	clk,
	reset,
	input_en,
	input_word,
	input_addr,
	output_word,
	output_addr,
	output_en
);
	input clk;
	input reset;
	input input_en;
	localparam integer parameters_ACT_DATA_WIDTH = 8;
	input signed [(4 * parameters_ACT_DATA_WIDTH) - 1:0] input_word;
	input [31:0] input_addr;
	localparam integer parameters_N_DIM_ARRAY = 4;
	output wire signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] output_word;
	output wire [31:0] output_addr;
	output wire output_en;
	integer i;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] output_word_temp;
	reg [31:0] output_addr_temp;
	reg output_en_temp;
	localparam first_32b = 0;
	localparam second_32b = 1;
	reg state;
	reg signed [(4 * parameters_ACT_DATA_WIDTH) - 1:0] last_word;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (i = 0; i < 4; i = i + 1)
				last_word[i * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
		end
		else if (input_en)
			last_word <= input_word;
	always @(posedge clk or negedge reset)
		if (!reset)
			state <= first_32b;
		else if (input_en)
			case (state)
				first_32b: state <= second_32b;
				second_32b: state <= first_32b;
			endcase
	always @(*) output_addr_temp = input_addr;
	always @(*)
		case (state)
			first_32b: output_en_temp = 0;
			second_32b: output_en_temp = input_en;
		endcase
	always @(*)
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
			if (i < (parameters_N_DIM_ARRAY / 2))
				output_word_temp[i * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = last_word[i * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH];
			else
				output_word_temp[i * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = input_word[(i - (parameters_N_DIM_ARRAY / 2)) * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH];
	assign output_addr = output_addr_temp;
	assign output_en = output_en_temp;
	assign output_word = output_word_temp;
endmodule
