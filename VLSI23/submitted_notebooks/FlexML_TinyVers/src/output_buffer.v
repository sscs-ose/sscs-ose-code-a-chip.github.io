module output_buffer (
	mode,
	clk,
	reset,
	input_word,
	input_addr,
	input_en,
	output_word,
	output_addr,
	output_en
);
	input [2:0] mode;
	input clk;
	input reset;
	localparam integer parameters_ACT_DATA_WIDTH = 8;
	localparam integer parameters_N_DIM_ARRAY = 4;
	input signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] input_word;
	input input_en;
	input [31:0] input_addr;
	output reg [31:0] output_addr;
	output reg signed [(parameters_N_DIM_ARRAY * parameters_ACT_DATA_WIDTH) - 1:0] output_word;
	output reg output_en;
	integer i;
	integer j;
	integer k;
	localparam integer parameters_INPUT_CHANNEL_DATA_WIDTH = 8;
	reg signed [(parameters_N_DIM_ARRAY * parameters_INPUT_CHANNEL_DATA_WIDTH) - 1:0] buffer [parameters_N_DIM_ARRAY - 1:0];
	reg signed [parameters_INPUT_CHANNEL_DATA_WIDTH - 1:0] buffer_fc [parameters_N_DIM_ARRAY - 1:0];
	reg signed [(4 * parameters_ACT_DATA_WIDTH) - 1:0] output_word_temp;
	reg output_en_temp;
	reg [2:0] current_mode;
	always @(posedge clk or negedge reset)
		if (!reset)
			current_mode <= 0;
		else if (input_en)
			current_mode <= mode;
	always @(*)
		if (parameters_N_DIM_ARRAY == 4) begin
			output_en = input_en;
			output_word = input_word;
			output_addr = input_addr;
		end
		else if (parameters_N_DIM_ARRAY == 8) begin
			output_en = input_en;
			output_word = input_word;
			output_addr = input_addr;
		end
	reg [3:0] WR_FIFO_POINTER;
	reg [3:0] RD_FIFO_POINTER;
	wire full_cnn;
	wire full_fc;
	wire empty_cnn;
	wire empty_fc;
	reg empty;
	reg full;
	assign full_cnn = (WR_FIFO_POINTER[2:0] == 0) && (RD_FIFO_POINTER[3:0] != WR_FIFO_POINTER[3:0]);
	assign empty_cnn = RD_FIFO_POINTER[3:0] == WR_FIFO_POINTER[3:0];
	assign full_fc = (WR_FIFO_POINTER[0] == 0) && (RD_FIFO_POINTER[1:0] != WR_FIFO_POINTER[1:0]);
	assign empty_fc = RD_FIFO_POINTER[1:0] == WR_FIFO_POINTER[1:0];
	localparam integer parameters_MODE_CNN = 1;
	always @(*) begin
		empty = empty_fc;
		full = full_fc;
		if (current_mode == parameters_MODE_CNN) begin
			empty = empty_cnn;
			full = full_cnn;
		end
	end
	always @(posedge clk or negedge reset)
		if (!reset)
			WR_FIFO_POINTER <= 0;
		else if (input_en)
			WR_FIFO_POINTER <= WR_FIFO_POINTER + 1;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
				for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
					buffer[i][j * parameters_INPUT_CHANNEL_DATA_WIDTH+:parameters_INPUT_CHANNEL_DATA_WIDTH] <= 0;
		end
		else if (input_en)
			buffer[WR_FIFO_POINTER[2:0]] <= input_word;
	localparam [2:0] IDLE = 0;
	localparam [2:0] READING_0 = 1;
	localparam [2:0] READING_1 = 2;
	localparam [2:0] READING_0_FC = 3;
	localparam [2:0] READING_1_FC = 4;
	reg [2:0] state;
	reg [2:0] next_state;
	always @(posedge clk or negedge reset)
		if (!reset)
			state <= IDLE;
		else
			state <= next_state;
	always @(*)
		case (state)
			IDLE:
				if (full)
					next_state = READING_0;
				else
					next_state = state;
			READING_0:
				if (empty)
					next_state = IDLE;
				else
					next_state = READING_1;
			READING_1:
				if (empty)
					next_state = IDLE;
				else
					next_state = READING_0;
		endcase
	always @(posedge clk or negedge reset)
		if (!reset)
			RD_FIFO_POINTER <= 0;
		else
			case (state)
				IDLE: RD_FIFO_POINTER <= RD_FIFO_POINTER;
				READING_0: RD_FIFO_POINTER <= RD_FIFO_POINTER;
				READING_1: RD_FIFO_POINTER <= RD_FIFO_POINTER + 1;
			endcase
	always @(*) begin
		output_en_temp = 0;
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
			output_word_temp[i * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = 0;
		case (state)
			IDLE: begin
				output_en_temp = 0;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					output_word_temp[i * parameters_ACT_DATA_WIDTH+:parameters_ACT_DATA_WIDTH] = 0;
			end
			READING_0:
				if (!empty) begin
					output_en_temp = 1;
					output_word_temp = buffer[RD_FIFO_POINTER[2:0]][0+:parameters_INPUT_CHANNEL_DATA_WIDTH * 4];
				end
			READING_1:
				if (!empty) begin
					output_en_temp = 1;
					output_word_temp = buffer[RD_FIFO_POINTER[2:0]][parameters_INPUT_CHANNEL_DATA_WIDTH * 4+:parameters_INPUT_CHANNEL_DATA_WIDTH * 4];
				end
		endcase
	end
endmodule
