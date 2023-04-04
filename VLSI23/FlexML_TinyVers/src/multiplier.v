module multiplier (
	input_0,
	input_1,
	out
);
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	input signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] input_0;
	input signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] input_1;
	output reg signed [(2 * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] out;
	always @(*) out = input_0 * input_1;
endmodule
