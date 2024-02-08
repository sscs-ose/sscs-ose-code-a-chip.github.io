module adder_tree (
	use_adder_tree,
	operand_0,
	operand_1,
	operand_2,
	operand_3,
	operand_4,
	operand_5,
	operand_6,
	operand_7,
	result
);
	input use_adder_tree;
	localparam integer parameters_ACC_DATA_WIDTH = 32;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] operand_0;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] operand_1;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] operand_2;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] operand_3;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] operand_4;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] operand_5;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] operand_6;
	input signed [parameters_ACC_DATA_WIDTH - 1:0] operand_7;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] intermediate_0_0;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] intermediate_0_1;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] intermediate_0_2;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] intermediate_0_3;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] intermediate_1_0;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] intermediate_1_1;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] operand_0_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] operand_1_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] operand_2_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] operand_3_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] operand_4_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] operand_5_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] operand_6_temp;
	reg signed [parameters_ACC_DATA_WIDTH - 1:0] operand_7_temp;
	output reg signed [parameters_ACC_DATA_WIDTH - 1:0] result;
	always @(*)
		if (use_adder_tree) begin
			operand_0_temp = operand_0;
			operand_1_temp = operand_1;
			operand_2_temp = operand_2;
			operand_3_temp = operand_3;
			operand_4_temp = operand_4;
			operand_5_temp = operand_5;
			operand_6_temp = operand_6;
			operand_7_temp = operand_7;
		end
		else begin
			operand_0_temp = 0;
			operand_1_temp = 0;
			operand_2_temp = 0;
			operand_3_temp = 0;
			operand_4_temp = 0;
			operand_5_temp = 0;
			operand_6_temp = 0;
			operand_7_temp = 0;
		end
	always @(*) begin
		intermediate_0_0 = operand_0_temp + operand_1_temp;
		intermediate_0_1 = operand_2_temp + operand_3_temp;
		intermediate_0_2 = operand_4_temp + operand_5_temp;
		intermediate_0_3 = operand_6_temp + operand_7_temp;
		intermediate_1_0 = intermediate_0_0 + intermediate_0_1;
		intermediate_1_1 = intermediate_0_2 + intermediate_0_3;
		result = intermediate_1_0 + intermediate_1_1;
	end
endmodule
