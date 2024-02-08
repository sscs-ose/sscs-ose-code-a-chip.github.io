module pe (
	clk,
	reset,
	enable_mac,
	passing_data_between_pes_cnn,
	PRECISION,
	clear_mac,
	input_adder_tree,
	input_bias,
	input_activation,
	input_weight,
	input_neighbour_pe,
	input_vertical,
	cr_0,
	cr_1,
	cr_2,
	cr_3,
	cr_4,
	cr_5,
	cr_6,
	cr_7,
	cr_8,
	cr_9,
	cr_10,
	cr_11,
	cr_12,
	cr_13,
	cr_14,
	cr_15_design_v2,
	cr_16_design_v2,
	cr_17,
	out_vertical,
	shift_fixed_point,
	out
);
	input clk;
	input reset;
	input [1:0] PRECISION;
	input passing_data_between_pes_cnn;
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	input signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] input_activation;
	localparam integer parameters_ACC_DATA_WIDTH = 32;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] input_bias;
	input signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] input_weight;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] input_neighbour_pe;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] input_vertical;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] input_adder_tree;
	input cr_0;
	input cr_1;
	input cr_2;
	input cr_3;
	input cr_4;
	input cr_5;
	input cr_6;
	input cr_7;
	input cr_8;
	input cr_9;
	input cr_10;
	input cr_11;
	input cr_12;
	input cr_13;
	input cr_14;
	input cr_15_design_v2;
	input cr_16_design_v2;
	input cr_17;
	input enable_mac;
	input clear_mac;
	input [7:0] shift_fixed_point;
	output reg signed [parameters_ACC_DATA_WIDTH - 1:0] out;
	output reg signed [parameters_ACC_DATA_WIDTH - 1:0] out_vertical;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] input_neighbour_pe_OR_input_adder_tree;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] acc_output_shifted;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] acc_output_shifted_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] input_neighbour_pe_reg;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] input_vertical_reg;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] next_input_vertical;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] mult_1;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] mult_1_muxed_with_design_v2;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] mult_0;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] mult_0_muxed_with_design_v2;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] mult_1_reordered;
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] pre_mult_1;
	reg signed [(2 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] mult_out;
	reg signed [(2 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] mult_out_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] sum_1;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] sum_0;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] sum_0_muxed_with_design_v2;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] pre_sum_0;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] pre_sum_1;
	wire signed [parameters_ACC_DATA_WIDTH - 1:0] sum_out;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] acc_input;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] acc_output;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] next_acc_output;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] acc_output_muxed;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] input_relu;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] output_relu;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] activation;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] pre_out;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] pre_out_vertical;
	reg overflow_p;
	reg overflow_n;
	reg overflow_p_0;
	reg overflow_p_1;
	reg overflow_n_0;
	reg overflow_n_1;
	reg overflow_p_0_0;
	reg overflow_p_0_1;
	reg overflow_p_1_0;
	reg overflow_p_1_1;
	reg overflow_n_0_0;
	reg overflow_n_0_1;
	reg overflow_n_1_0;
	reg overflow_n_1_1;
	localparam integer parameters_ACT_DATA_WIDTH = 8;
	reg [parameters_ACT_DATA_WIDTH - 1:0] MAX_value;
	reg [parameters_ACT_DATA_WIDTH - 1:0] MIN_value;
	reg [2:0] mode_precision_layer;
	reg [2:0] mode_precision_mult;
	reg [2:0] mode_precision_adder;
	integer i;
	always @(*)
		for (i = 0; i < parameters_ACC_DATA_WIDTH; i = i + 1)
			if (i > shift_fixed_point)
				acc_output_shifted_temp[(parameters_ACC_DATA_WIDTH - 1) - i] = acc_output[((parameters_ACC_DATA_WIDTH - 1) - i) + shift_fixed_point];
			else
				acc_output_shifted_temp[(parameters_ACC_DATA_WIDTH - 1) - i] = acc_output[parameters_ACC_DATA_WIDTH - 1];
	always @(*) begin
		case (cr_17)
			0: input_neighbour_pe_OR_input_adder_tree = input_adder_tree;
			1: input_neighbour_pe_OR_input_adder_tree = input_adder_tree;
		endcase
		case (cr_14)
			1'b0: acc_output_shifted = acc_output;
			1'b1: acc_output_shifted = acc_output_shifted_temp;
		endcase
		case (cr_8)
			1'b0: acc_output_muxed = acc_output;
			1'b1: acc_output_muxed = acc_output_shifted_temp;
		endcase
		case (cr_4)
			1'b0: pre_mult_1 = input_weight;
			1'b1:
				if (overflow_n == 1)
					pre_mult_1 = $signed(MIN_value);
				else if (overflow_p == 1)
					pre_mult_1 = $signed(MAX_value);
				else
					pre_mult_1 = acc_output_muxed[parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0];
			default: pre_mult_1 = input_weight;
		endcase
		case (cr_6)
			1'b0: mult_0 = input_activation;
			1'b1: mult_0 = 1;
		endcase
		case (cr_5)
			1'b0: pre_sum_1 = input_neighbour_pe;
			1'b1: pre_sum_1 = acc_output_muxed;
		endcase
		case (cr_7)
			1'b0: sum_1 = pre_sum_1;
			1'b1: sum_1 = 0;
		endcase
		case (cr_12)
			1'b0: mult_1 = pre_mult_1;
			1'b1:
				if (mode_precision_adder == 3'b100)
					mult_1 = 1;
				else if (mode_precision_adder == 3'b010)
					mult_1 = 8'b00010001;
				else
					mult_1 = 8'b01010101;
		endcase
		case (cr_0)
			1'b0: pre_sum_0 = mult_out;
			1'b1: pre_sum_0 = input_neighbour_pe_OR_input_adder_tree;
		endcase
		case (cr_1)
			1'b0: acc_input = sum_out;
			1'b1: acc_input = acc_output_muxed;
		endcase
		case (cr_2)
			1'b0: begin
				input_relu = 0;
				if (mode_precision_adder == 3'b100) begin
					if (overflow_n == 1)
						activation = $signed(MIN_value);
					else if (overflow_p == 1)
						activation = $signed(MAX_value);
					else
						activation = acc_output_shifted;
				end
				else begin
					activation = acc_output_shifted;
					if (overflow_n_0 == 1)
						activation[3:0] = $signed(MIN_value);
					if (overflow_n_1 == 1)
						activation[3:0] = $signed(MAX_value);
					if (overflow_p_0 == 1)
						activation[7:4] = $signed(MIN_value);
					if (overflow_p_1 == 1)
						activation[7:4] = $signed(MAX_value);
				end
			end
			1'b1: begin
				input_relu = acc_output_shifted;
				if (overflow_n == 1)
					activation = 0;
				else if (overflow_p == 1)
					activation = $signed(MAX_value);
				else
					activation = output_relu;
			end
		endcase
		case (cr_3)
			1'b0: pre_out = activation;
			1'b1: pre_out = input_neighbour_pe_reg;
		endcase
		case (cr_9)
			1'b0: out = pre_out;
			1'b1: out = acc_output_shifted;
		endcase
		case (cr_11)
			1'b0: pre_out_vertical = activation;
			1'b1: pre_out_vertical = input_vertical_reg;
		endcase
		case (cr_10)
			1'b0: out_vertical = pre_out_vertical;
			1'b1: out_vertical = acc_output_shifted;
		endcase
		case (cr_13)
			1'b0: sum_0 = pre_sum_0;
			1'b1: sum_0 = input_bias;
		endcase
	end
	always @(*)
		if (input_relu[parameters_ACC_DATA_WIDTH - 1] == 1'b1)
			output_relu = 0;
		else
			output_relu = input_relu;
	always @(*)
		if (clear_mac || !((cr_8 == 0) && (cr_1 == 1))) begin
			if (clear_mac == 0)
				next_acc_output = acc_input;
			else
				next_acc_output = 0;
		end
		else
			next_acc_output = acc_output;
	always @(posedge clk or negedge reset)
		if (!reset)
			acc_output <= 0;
		else if (enable_mac)
			acc_output <= next_acc_output;
	always @(posedge clk or negedge reset)
		if (!reset)
			input_vertical_reg <= 0;
		else if (enable_mac)
			input_vertical_reg <= next_input_vertical;
	always @(*)
		if (passing_data_between_pes_cnn)
			next_input_vertical = input_vertical;
		else
			next_input_vertical = input_vertical_reg;
	always @(*)
		case (PRECISION)
			0: begin
				MIN_value = 1 << (parameters_ACT_DATA_WIDTH - 1);
				MAX_value = {parameters_ACT_DATA_WIDTH - 1 {1'b1}};
			end
			1: begin
				MIN_value = 1 << ((parameters_ACT_DATA_WIDTH / 2) - 1);
				MAX_value = {(parameters_ACT_DATA_WIDTH / 2) - 1 {1'b1}};
			end
			2: begin
				MIN_value = 1 << ((parameters_ACT_DATA_WIDTH / 4) - 1);
				MAX_value = {(parameters_ACT_DATA_WIDTH / 4) - 1 {1'b1}};
			end
			default: begin
				MIN_value = 1 << ((parameters_ACT_DATA_WIDTH / 2) - 1);
				MAX_value = {(parameters_ACT_DATA_WIDTH / 2) - 1 {1'b1}};
			end
		endcase
	always @(*) begin
		overflow_p_0 = 0;
		overflow_p_1 = 0;
		overflow_n_0 = 0;
		overflow_n_1 = 0;
		overflow_n = 0;
		overflow_p = 0;
		overflow_p_0_0 = 0;
		overflow_p_0_1 = 0;
		overflow_p_1_0 = 0;
		overflow_p_1_1 = 0;
		overflow_n_0_0 = 0;
		overflow_n_0_1 = 0;
		overflow_n_1_0 = 0;
		overflow_n_1_1 = 0;
		if (mode_precision_adder == 3'b100)
			case (PRECISION)
				0: begin
					if (acc_output_shifted < $signed(MIN_value[7:0]))
						overflow_n = 1;
					else
						overflow_n = 0;
					if (acc_output_shifted > $signed(MAX_value[7:0]))
						overflow_p = 1;
					else
						overflow_p = 0;
				end
				1: begin
					if (acc_output_shifted < $signed(MIN_value[3:0]))
						overflow_n = 1;
					else
						overflow_n = 0;
					if (acc_output_shifted > $signed(MAX_value[3:0]))
						overflow_p = 1;
					else
						overflow_p = 0;
					if (mode_precision_adder == 3'b010) begin
						if ($signed(acc_output_shifted[3:0]) < $signed(MIN_value[3:0]))
							overflow_n_0 = 1;
						if ($signed(acc_output_shifted[7:4]) < $signed(MIN_value[3:0]))
							overflow_n_1 = 1;
						if ($signed(acc_output_shifted[3:0]) > $signed(MIN_value[3:0]))
							overflow_p_0 = 1;
						if ($signed(acc_output_shifted[7:4]) > $signed(MIN_value[3:0]))
							overflow_p_1 = 1;
					end
				end
				2: begin
					if (acc_output_shifted < $signed(MIN_value[1:0]))
						overflow_n = 1;
					else
						overflow_n = 0;
					if (acc_output_shifted > $signed(MAX_value[1:0]))
						overflow_p = 1;
					else
						overflow_p = 0;
					if (mode_precision_adder == 3'b001) begin
						if ($signed(acc_output_shifted[1:0]) < $signed(MIN_value[1:0]))
							overflow_n_0_0 = 1;
						if ($signed(acc_output_shifted[3:2]) < $signed(MIN_value[1:0]))
							overflow_n_0_1 = 1;
						if ($signed(acc_output_shifted[5:4]) < $signed(MIN_value[1:0]))
							overflow_n_1_0 = 1;
						if ($signed(acc_output_shifted[7:6]) < $signed(MIN_value[1:0]))
							overflow_n_1_1 = 1;
						if ($signed(acc_output_shifted[1:0]) > $signed(MIN_value[1:0]))
							overflow_p_0_0 = 1;
						if ($signed(acc_output_shifted[3:2]) > $signed(MIN_value[1:0]))
							overflow_p_0_1 = 1;
						if ($signed(acc_output_shifted[5:4]) > $signed(MIN_value[1:0]))
							overflow_p_1_0 = 1;
						if ($signed(acc_output_shifted[7:6]) > $signed(MIN_value[1:0]))
							overflow_p_1_1 = 1;
					end
				end
			endcase
	end
	always @(*)
		case (PRECISION)
			0: mode_precision_layer = 3'b100;
			1: mode_precision_layer = 3'b010;
			2: mode_precision_layer = 3'b001;
			default: mode_precision_layer = 3'b100;
		endcase
	always @(*)
		case (mode_precision_mult)
			3'b100: mult_1_reordered = mult_1_muxed_with_design_v2;
			3'b010: mult_1_reordered = {mult_1_muxed_with_design_v2[3:0], mult_1_muxed_with_design_v2[7:4]};
			3'b001: mult_1_reordered = {mult_1_muxed_with_design_v2[1:0], mult_1_muxed_with_design_v2[3:2], mult_1_muxed_with_design_v2[5:4], mult_1_muxed_with_design_v2[7:6]};
			default: mult_1_reordered = mult_1_muxed_with_design_v2;
		endcase
	always @(*)
		if (((!cr_6 && !cr_12) && !cr_4) && !cr_0)
			mode_precision_mult = mode_precision_layer;
		else
			mode_precision_mult = 3'b100;
	always @(*)
		if ((((cr_5 && !cr_7) && !cr_0) && !cr_6) && cr_12)
			mode_precision_adder = mode_precision_layer;
		else
			mode_precision_adder = 3'b100;
	always @(*)
		case (mode_precision_mult)
			3'b100: mult_out = mult_out_temp;
			3'b010: mult_out = {{7 {mult_out_temp[12]}}, mult_out_temp[12:4]};
			3'b001: mult_out = {{10 {mult_out_temp[11]}}, mult_out_temp[11:6]};
			default: mult_out = mult_out_temp;
		endcase
	always @(*) begin
		sum_0_muxed_with_design_v2 = sum_0;
		mult_1_muxed_with_design_v2 = mult_1;
		mult_0_muxed_with_design_v2 = mult_0;
	end
	M88_top MULT_0(
		.a(mult_0_muxed_with_design_v2),
		.w(mult_1_reordered),
		.mode_8b(mode_precision_mult[2]),
		.mode_4b(mode_precision_mult[1]),
		.mode_2b(mode_precision_mult[0]),
		.p(mult_out_temp)
	);
	adder ADD_0(
		.accumulation_between_pes(cr_0 || cr_13),
		.mode_precision_adder(mode_precision_adder),
		.mode_precision_mult(mode_precision_mult),
		.mode_precision_layer(mode_precision_layer),
		.input_0(sum_0_muxed_with_design_v2),
		.input_1(sum_1),
		.out(sum_out)
	);
endmodule
