module array_pes (
	clk,
	reset,
	enable,
	enable_BUFFERED_OUTPUT,
	INPUT_PRECISION,
	OUTPUT_PRECISION,
	shift_input_buffer,
	enable_bias_32bits,
	addr_bias_32bits,
	done_layer,
	clear,
	enable_input_fifo,
	passing_data_between_pes_cnn,
	mode,
	loading_in_parallel,
	CR_PE_array,
	fc_weights_array,
	cnn_input,
	cnn_weights_array,
	fc_input_array,
	output_array,
	output_array_vertical,
	shift_fixed_point
);
	input passing_data_between_pes_cnn;
	input clk;
	input reset;
	input enable;
	input clear;
	input done_layer;
	input enable_bias_32bits;
	input [1:0] addr_bias_32bits;
	input enable_BUFFERED_OUTPUT;
	input [1:0] INPUT_PRECISION;
	input [1:0] OUTPUT_PRECISION;
	input [2:0] mode;
	input loading_in_parallel;
	input enable_input_fifo;
	localparam integer parameters_NUMBER_OF_CR_SIGNALS = 18;
	localparam integer parameters_N_DIM_ARRAY = 4;
	input [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_NUMBER_OF_CR_SIGNALS) - 1:0] CR_PE_array;
	localparam integer parameters_WEIGHT_DATA_WIDTH = 8;
	input signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] cnn_weights_array;
	input signed [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_WEIGHT_DATA_WIDTH) - 1:0] fc_weights_array;
	input signed [(parameters_N_DIM_ARRAY * parameters_WEIGHT_DATA_WIDTH) - 1:0] fc_input_array;
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	input signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] cnn_input;
	input [7:0] shift_fixed_point;
	localparam parameters_MAXIMUM_DILATION_BITS = 8;
	input [7:0] shift_input_buffer;
	localparam integer parameters_ACT_DATA_WIDTH = 8;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] output_array;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] output_array_vertical;
	localparam integer parameters_ACC_DATA_WIDTH = 32;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACC_DATA_WIDTH) - 1:0] bias_32bits;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACC_DATA_WIDTH) - 1:0] input_bias;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] output_array_temp;
	wire signed [parameters_WEIGHT_DATA_WIDTH - 1:0] cnn_weights_array_reg [parameters_N_DIM_ARRAY - 1:0];
	wire signed [parameters_WEIGHT_DATA_WIDTH - 1:0] fc_weights_array_reg [parameters_N_DIM_ARRAY - 1:0][parameters_N_DIM_ARRAY - 1:0];
	reg signed [parameters_WEIGHT_DATA_WIDTH - 1:0] second_input_PE_array [parameters_N_DIM_ARRAY - 1:0][parameters_N_DIM_ARRAY - 1:0];
	wire signed [(parameters_WEIGHT_DATA_WIDTH * parameters_N_DIM_ARRAY) - 1:0] second_input_PE_array_unrolled [parameters_N_DIM_ARRAY - 1:0];
	wire signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] input_buffer_array;
	wire signed [parameters_ACC_DATA_WIDTH - 1:0] result_adder [parameters_N_DIM_ARRAY - 1:0];
	wire signed [parameters_ACC_DATA_WIDTH - 1:0] output_PE_array [parameters_N_DIM_ARRAY - 1:0][parameters_N_DIM_ARRAY - 1:0];
	wire signed [parameters_ACC_DATA_WIDTH - 1:0] input_2_array [parameters_N_DIM_ARRAY - 1:0][parameters_N_DIM_ARRAY - 1:0];
	wire signed [parameters_ACC_DATA_WIDTH - 1:0] input_2_vertical_array [parameters_N_DIM_ARRAY - 1:0][parameters_N_DIM_ARRAY - 1:0];
	wire signed [parameters_ACC_DATA_WIDTH - 1:0] vertical_signals [parameters_N_DIM_ARRAY - 1:0][parameters_N_DIM_ARRAY - 1:0];
	wire signed [parameters_ACC_DATA_WIDTH - 1:0] adder_tree_signals [parameters_N_DIM_ARRAY - 1:0][parameters_N_DIM_ARRAY - 1:0];
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] BUFFERED_OUTPUT_0;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] BUFFERED_OUTPUT_1;
	reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] BUFFERED_OUTPUT_2;
	integer m;
	integer n;
	genvar i;
	genvar j;
	genvar k;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
				bias_32bits[m * parameters_ACC_DATA_WIDTH+:parameters_ACC_DATA_WIDTH] <= 0;
		end
		else if (enable)
			if (enable_bias_32bits)
				case (addr_bias_32bits)
					0:
						for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
							bias_32bits[(m * parameters_ACC_DATA_WIDTH) + 7-:8] <= cnn_weights_array[m * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH];
					1:
						for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
							bias_32bits[(m * parameters_ACC_DATA_WIDTH) + 15-:8] <= cnn_weights_array[m * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH];
					2:
						for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
							bias_32bits[(m * parameters_ACC_DATA_WIDTH) + 23-:8] <= cnn_weights_array[m * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH];
					3:
						for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
							bias_32bits[(m * parameters_ACC_DATA_WIDTH) + 31-:8] <= cnn_weights_array[m * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH];
				endcase
	input_buffer input_buffer_instance(
		.clk(clk),
		.reset(reset),
		.shift_input_buffer(shift_input_buffer),
		.loading_in_parallel(loading_in_parallel),
		.parallel_input_array(fc_input_array),
		.serial_input(cnn_input),
		.mode(mode),
		.clear(clear),
		.enable(enable_input_fifo),
		.output_array(input_buffer_array)
	);
	generate
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1) begin : dim_0
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1) begin : dim_1
				assign second_input_PE_array_unrolled[i][(parameters_INPUT_CHANNEL_DATA_WIDTH * (j + 1)) - 1:parameters_INPUT_CHANNEL_DATA_WIDTH * j] = second_input_PE_array[i][j];
			end
		end
	endgenerate
	localparam integer parameters_MODE_CNN = 1;
	always @(*) begin
		for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
			input_bias[m * parameters_ACC_DATA_WIDTH+:parameters_ACC_DATA_WIDTH] = 0;
		if (mode == parameters_MODE_CNN)
			input_bias = bias_32bits;
		else
			for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
				input_bias[m * parameters_ACC_DATA_WIDTH+:parameters_ACC_DATA_WIDTH] = second_input_PE_array_unrolled[m][31:0];
	end
	generate
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1) begin : row
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1) begin : column
				if (j != (parameters_N_DIM_ARRAY - 1)) begin : genblk1
					assign input_2_array[i][j] = output_PE_array[i][j + 1];
				end
				else begin : genblk1
					assign input_2_array[i][j] = {parameters_ACC_DATA_WIDTH {1'b0}};
				end
				if (i != (parameters_N_DIM_ARRAY - 1)) begin : genblk2
					assign input_2_vertical_array[i][j] = vertical_signals[i + 1][j];
				end
				else begin : genblk2
					assign input_2_vertical_array[i][j] = {parameters_ACC_DATA_WIDTH {1'b0}};
				end
				if (j == 0) begin : genblk3
					assign adder_tree_signals[i][j] = result_adder[i];
				end
				else begin : genblk3
					assign adder_tree_signals[i][j] = 0;
				end
				pe pe_i(
					.clk(clk),
					.reset(reset),
					.PRECISION(INPUT_PRECISION),
					.passing_data_between_pes_cnn(passing_data_between_pes_cnn),
					.shift_fixed_point(shift_fixed_point),
					.input_activation(input_buffer_array[j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH]),
					.input_weight(second_input_PE_array[i][j]),
					.input_bias(input_bias[i * parameters_ACC_DATA_WIDTH+:parameters_ACC_DATA_WIDTH]),
					.input_neighbour_pe(input_2_array[i][j]),
					.input_adder_tree(adder_tree_signals[i][j]),
					.cr_0(CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS]),
					.cr_1(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 1]),
					.cr_2(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 2]),
					.cr_3(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 3]),
					.cr_4(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 4]),
					.cr_5(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 5]),
					.cr_6(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 6]),
					.cr_7(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 7]),
					.cr_8(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 8]),
					.cr_9(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 9]),
					.cr_10(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 10]),
					.cr_11(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 11]),
					.cr_12(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 12]),
					.cr_13(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 13]),
					.cr_14(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 14]),
					.cr_15_design_v2(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 15]),
					.cr_16_design_v2(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 16]),
					.cr_17(CR_PE_array[(((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS) + 17]),
					.input_vertical(input_2_vertical_array[i][j]),
					.out_vertical(vertical_signals[i][j]),
					.clear_mac(clear),
					.enable_mac(enable),
					.out(output_PE_array[i][j])
				);
			end
		end
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1) begin : adder_row
			adder_tree adder_tree_i(
				.use_adder_tree(1'b1),
				.operand_0(output_PE_array[i][0]),
				.operand_1(output_PE_array[i][1]),
				.operand_2(output_PE_array[i][2]),
				.operand_3(output_PE_array[i][3]),
				.operand_4(output_PE_array[i][4]),
				.operand_5(output_PE_array[i][5]),
				.operand_6(output_PE_array[i][6]),
				.operand_7(output_PE_array[i][7]),
				.result(result_adder[i])
			);
		end
	endgenerate
	localparam integer parameters_MODE_EWS = 3;
	localparam integer parameters_MODE_FC = 0;
	always @(*)
		if ((mode == parameters_MODE_FC) || (mode == parameters_MODE_EWS)) begin
			for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
				for (n = 0; n < parameters_N_DIM_ARRAY; n = n + 1)
					second_input_PE_array[m][n] = fc_weights_array[((m * parameters_N_DIM_ARRAY) + n) * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH];
		end
		else
			for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
				for (n = 0; n < parameters_N_DIM_ARRAY; n = n + 1)
					second_input_PE_array[m][n] = cnn_weights_array[m * parameters_WEIGHT_DATA_WIDTH+:parameters_WEIGHT_DATA_WIDTH];
	always @(*) begin
		for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
			output_array_temp[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = 0;
		for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
			if ((mode == parameters_MODE_CNN) || (mode == parameters_MODE_EWS))
				output_array_temp[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = vertical_signals[0][m];
			else
				output_array_temp[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = output_PE_array[m][0];
	end
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
				begin
					BUFFERED_OUTPUT_0[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
					BUFFERED_OUTPUT_1[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
					BUFFERED_OUTPUT_2[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
				end
		end
		else if (enable == 1)
			if (done_layer) begin
				for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
					begin
						BUFFERED_OUTPUT_0[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
						BUFFERED_OUTPUT_1[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
						BUFFERED_OUTPUT_2[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] <= 0;
					end
			end
			else if (enable_BUFFERED_OUTPUT) begin
				BUFFERED_OUTPUT_0 <= output_array_temp;
				BUFFERED_OUTPUT_1 <= BUFFERED_OUTPUT_0;
				BUFFERED_OUTPUT_2 <= BUFFERED_OUTPUT_1;
			end
	always @(*)
		case (OUTPUT_PRECISION)
			0: output_array = output_array_temp;
			1:
				if (mode != parameters_MODE_CNN) begin
					for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
						if (m < (parameters_N_DIM_ARRAY / 2))
							output_array[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = {BUFFERED_OUTPUT_0[(((2 * m) + 1) * parameters_ACT_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2], BUFFERED_OUTPUT_0[((2 * m) * parameters_ACT_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2]};
						else
							output_array[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = {output_array_temp[(((2 * (m - (parameters_N_DIM_ARRAY / 2))) + 1) * parameters_ACT_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2], output_array_temp[((2 * (m - (parameters_N_DIM_ARRAY / 2))) * parameters_ACT_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2]};
				end
				else
					for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
						output_array[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = {output_array_temp[(m * parameters_ACT_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2], BUFFERED_OUTPUT_0[(m * parameters_ACT_DATA_WIDTH) + ((parameters_INPUT_CHANNEL_DATA_WIDTH / 2) - 1)-:parameters_INPUT_CHANNEL_DATA_WIDTH / 2]};
			2:
				if (mode != parameters_MODE_CNN) begin
					for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
						if (m < (parameters_N_DIM_ARRAY / 4))
							output_array[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = {BUFFERED_OUTPUT_2[(((4 * m) + 3) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_2[(((4 * m) + 2) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_2[(((4 * m) + 1) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_2[((4 * m) * parameters_ACT_DATA_WIDTH) + 1-:2]};
						else if (m < (parameters_N_DIM_ARRAY / 2))
							output_array[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = {BUFFERED_OUTPUT_1[(((4 * (m - (parameters_N_DIM_ARRAY / 4))) + 3) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_1[(((4 * (m - (parameters_N_DIM_ARRAY / 4))) + 2) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_1[(((4 * (m - (parameters_N_DIM_ARRAY / 4))) + 1) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_1[((4 * (m - (parameters_N_DIM_ARRAY / 4))) * parameters_ACT_DATA_WIDTH) + 1-:2]};
						else if (m < ((3 * parameters_N_DIM_ARRAY) / 4))
							output_array[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = {BUFFERED_OUTPUT_0[(((4 * (m - (parameters_N_DIM_ARRAY / 2))) + 3) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_0[(((4 * (m - (parameters_N_DIM_ARRAY / 2))) + 2) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_0[(((4 * (m - (parameters_N_DIM_ARRAY / 2))) + 1) * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_0[((4 * (m - (parameters_N_DIM_ARRAY / 2))) * parameters_ACT_DATA_WIDTH) + 1-:2]};
						else
							output_array[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = {output_array_temp[(((4 * (m - ((3 * parameters_N_DIM_ARRAY) / 4))) + 3) * parameters_ACT_DATA_WIDTH) + 1-:2], output_array_temp[(((4 * (m - ((3 * parameters_N_DIM_ARRAY) / 4))) + 2) * parameters_ACT_DATA_WIDTH) + 1-:2], output_array_temp[(((4 * (m - ((3 * parameters_N_DIM_ARRAY) / 4))) + 1) * parameters_ACT_DATA_WIDTH) + 1-:2], output_array_temp[((4 * (m - ((3 * parameters_N_DIM_ARRAY) / 4))) * parameters_ACT_DATA_WIDTH) + 1-:2]};
				end
				else
					for (m = 0; m < parameters_N_DIM_ARRAY; m = m + 1)
						output_array[m * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = {output_array_temp[(m * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_0[(m * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_1[(m * parameters_ACT_DATA_WIDTH) + 1-:2], BUFFERED_OUTPUT_2[(m * parameters_ACT_DATA_WIDTH) + 1-:2]};
			default: output_array = output_array_temp;
		endcase
endmodule
