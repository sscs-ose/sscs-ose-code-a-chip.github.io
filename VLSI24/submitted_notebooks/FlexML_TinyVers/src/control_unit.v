module control_unit (
	finished_activation,
	PC,
	EXECUTION_FRAME_BY_FRAME,
	causal_convolution,
	clk,
	reset,
	enable,
	scan_en_in,
	reinitialize_padding,
	wr_en_ext_sparsity,
	wr_addr_ext_sparsity,
	wr_data_ext_sparsity,
	use_adder_tree,
	enable_pe_array,
	CR_PE_array,
	input_channel_rd_en,
	input_channel_rd_addr,
	wr_en_output_buffer,
	input_memory_pointer,
	output_memory_pointer,
	weight_memory_pointer,
	output_channel_size,
	padd_zeros_left,
	padd_zeros_right,
	passing_data_between_pes_cnn,
	wr_addr,
	weight_rd_en,
	weight_rd_addr,
	OUTPUT_TILE_SIZE,
	WEIGHT_TILE_SIZE,
	NB_INPUT_TILE,
	NB_WEIGHT_TILE,
	SPARSITY,
	CONF_K_o,
	done_layer,
	type_nonlinear_function,
	enable_nonlinear_block,
	enable_input_fifo,
	finished_network,
	shift_input_buffer,
	loading_in_parallel,
	instruction,
	enable_pooling,
	enable_sig_tanh,
	clear,
	enable_BUFFERED_OUTPUT,
	NUMBER_OF_ACTIVATION_CYCLES,
	INPUT_PRECISION,
	OUTPUT_PRECISION,
	SHIFT_FIXED_POINT,
	FIFO_TCN_update_pointer,
	FIFO_TCN_total_blocks,
	FIFO_TCN_block_size,
	enable_bias_32bits,
	addr_bias_32bits,
	PADDED_C_X,
	PADDED_O_X,
	write_l2_l1,
	mode
);
	localparam integer parameters_STR_SP_MEMORY_WORD = 32;
	reg [parameters_STR_SP_MEMORY_WORD - 1:0] next_sparse_val;
	reg [parameters_STR_SP_MEMORY_WORD - 1:0] sparse_val_sram;
	input clk;
	input reset;
	input enable;
	input scan_en_in;
	output reg reinitialize_padding;
	input EXECUTION_FRAME_BY_FRAME;
	input finished_activation;
	localparam integer parameters_INSTRUCTION_MEMORY_FIELDS = 32;
	localparam integer parameters_INSTRUCTION_MEMORY_WIDTH = 32;
	input [(parameters_INSTRUCTION_MEMORY_FIELDS * parameters_INSTRUCTION_MEMORY_WIDTH) - 1:0] instruction;
	input wr_en_ext_sparsity;
	localparam integer parameters_BIT_WIDTH_EXTERNAL_PORT = 32;
	input [parameters_BIT_WIDTH_EXTERNAL_PORT - 1:0] wr_addr_ext_sparsity;
	input [parameters_BIT_WIDTH_EXTERNAL_PORT - 1:0] wr_data_ext_sparsity;
	output reg passing_data_between_pes_cnn;
	output reg use_adder_tree;
	output reg [2:0] padd_zeros_left;
	output reg [2:0] padd_zeros_right;
	output reg enable_bias_32bits;
	output reg [1:0] addr_bias_32bits;
	output reg [31:0] PC;
	output reg causal_convolution;
	output reg enable_nonlinear_block;
	localparam integer parameters_NUMBER_OF_NONLINEAR_FUNCTIONS_BITS = 3;
	output reg [parameters_NUMBER_OF_NONLINEAR_FUNCTIONS_BITS - 1:0] type_nonlinear_function;
	output reg wr_en_output_buffer;
	output reg clear;
	localparam integer parameters_TOTAL_ACTIVATION_MEMORY_SIZE = 16384;
	localparam integer parameters_INPUT_CHANNEL_ADDR_SIZE = 14;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] input_channel_rd_addr;
	output reg input_channel_rd_en;
	localparam integer parameters_TOTAL_WEIGHT_MEMORY_SIZE = 16384;
	localparam integer parameters_WEIGHT_MEMORY_ADDR_SIZE = 14;
	output reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] weight_rd_addr;
	output reg weight_rd_en;
	output reg [2:0] mode;
	localparam integer parameters_NUMBER_OF_CR_SIGNALS = 18;
	localparam integer parameters_N_DIM_ARRAY = 4;
	output reg [((parameters_N_DIM_ARRAY * parameters_N_DIM_ARRAY) * parameters_NUMBER_OF_CR_SIGNALS) - 1:0] CR_PE_array;
	output reg enable_pe_array;
	output reg enable_input_fifo;
	output reg loading_in_parallel;
	output wire [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] weight_memory_pointer;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] output_memory_pointer;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] input_memory_pointer;
	output wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] output_channel_size;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr;
	localparam parameters_MAXIMUM_DILATION_BITS = 8;
	output reg [7:0] shift_input_buffer;
	output reg finished_network;
	output reg [7:0] SHIFT_FIXED_POINT;
	output reg [1:0] INPUT_PRECISION;
	output reg [1:0] OUTPUT_PRECISION;
	output reg FIFO_TCN_update_pointer;
	output reg [31:0] FIFO_TCN_block_size;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] FIFO_TCN_total_blocks;
	output reg [31:0] NUMBER_OF_ACTIVATION_CYCLES;
	output reg [31:0] PADDED_C_X;
	output reg [31:0] PADDED_O_X;
	output reg SPARSITY;
	output reg enable_pooling;
	output reg enable_sig_tanh;
	output reg enable_BUFFERED_OUTPUT;
	output reg [15:0] OUTPUT_TILE_SIZE;
	output reg [15:0] WEIGHT_TILE_SIZE;
	output reg [7:0] NB_INPUT_TILE;
	output reg [7:0] NB_WEIGHT_TILE;
	output reg done_layer;
	output reg [15:0] CONF_K_o;
	output reg [1:0] write_l2_l1;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_vertical [parameters_N_DIM_ARRAY - 1:0];
	reg finished_layer;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] output_channel_size_shifted;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_addr_plus_offset;
	reg CNN_FINISHED_FX_LOOP;
	reg CNN_FINISHED_FY_LOOP;
	reg CNN_FINISHED_C_LOOP;
	reg CNN_FINISHED_K_LOOP;
	reg CNN_FINISHED_X_LOOP;
	reg CNN_FINISHED_Y_LOOP;
	reg FC_FINISHED_K_LOOP;
	reg FC_FINISHED_C_LOOP;
	reg BIAS_ACC_FINISHED;
	reg EWS_FINISHED;
	reg ACT_FINISHED;
	reg ACCUMULATION_PES_FINISHED;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] counter_activation_read_address;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] next_counter_activation_read_address;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] counter_current_channel_address;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] next_counter_current_channel_address;
	reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] counter_weight_address;
	reg [parameters_WEIGHT_MEMORY_ADDR_SIZE - 1:0] next_counter_weight_address;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] counter_offset_input_channel;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] next_counter_offset_input_channel;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] counter_input_channel_address;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] next_counter_input_channel_address;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] counter_output_channel_address;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] next_counter_output_channel_address;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] counter_weight_address_after_bias;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] next_counter_weight_address_after_bias;
	reg [1:0] counter_acc_cnn_bias;
	reg [1:0] next_counter_acc_cnn_bias;
	reg [15:0] counter_C;
	reg [15:0] next_counter_C;
	reg [15:0] counter_Y;
	reg [15:0] next_counter_Y;
	reg [15:0] counter_X;
	reg [15:0] next_counter_X;
	reg [15:0] counter_K;
	reg [15:0] next_counter_K;
	reg [15:0] counter_input_buffer_loading;
	reg [15:0] next_counter_input_buffer_loading;
	reg [15:0] counter_sparsity;
	reg [15:0] next_counter_sparsity;
	reg [7:0] counter_FY;
	reg [7:0] next_counter_FY;
	reg [7:0] counter_FX;
	reg [7:0] next_counter_FX;
	reg [7:0] counter_accumulation_pes;
	reg [7:0] next_counter_accumulation_pes;
	reg SPARSITY_SET;
	reg [parameters_STR_SP_MEMORY_WORD - 1:0] sparse_val;
	reg [7:0] number_ones;
	reg [10:0] A;
	reg rd_en_sparsity;
	reg [10:0] sparse_addr;
	reg [10:0] next_sparse_addr;
	localparam parameters_HL_FSM_bits = 6;
	reg [5:0] HL_state;
	reg [5:0] HL_next_state;
	reg HL_enable;
	localparam HL_IDLE = 0;
	localparam HL_RUN = 1;
	localparam HL_RUNNING = 2;
	localparam HL_FINISHED_LAYER = 3;
	localparam HL_END = 4;
	localparam parameters_LL_FSM_bits = 6;
	reg [5:0] state;
	reg [5:0] next_state;
	localparam INITIAL = 0;
	localparam CONV_FILLING_INPUT_FIFO = 1;
	localparam CONV_PADDING_FILLING_INPUT_FIFO = 2;
	localparam CONV_PRE_MAC = 3;
	localparam CONV_MAC = 4;
	localparam CONV_ADD_BIAS = 5;
	localparam CONV_PRE_PASSING_OUTPUTS_VERTICAL = 6;
	localparam CONV_PASSING_OUTPUTS_VERTICAL = 7;
	localparam CONV_CLEAR_MAC = 8;
	localparam CONV_PRE_MAC_2 = 9;
	localparam FC_PRE_MAC = 10;
	localparam FC_MAC = 11;
	localparam FC_PRE_BIAS = 12;
	localparam FC_BIAS = 13;
	localparam FC_PRE_ACCUMULATE_MACS = 14;
	localparam FC_ACCUMULATE_MACS = 15;
	localparam FC_SAVE_OUTPUTS_MACS = 16;
	localparam EWS_PRE_MAC = 17;
	localparam EWS_MAC_0 = 18;
	localparam EWS_MAC_1 = 19;
	localparam EWS_SAVE_MAC = 20;
	localparam ACTIVATION = 21;
	localparam FINISHED_LAYER = 22;
	localparam FC_BIAS_32b_0 = 23;
	localparam CONV_ADD_BIAS_ACC = 24;
	localparam CONV_ADD_BIAS_OPERATION = 25;
	localparam CONV_ADD_BIAS_SHIFTING = 26;
	localparam FC_ADDER_TREE_0 = 29;
	localparam STR_SPARSITY = 27;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] CONF_INPUT_MEMORY_POINTER;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] CONF_OUTPUT_MEMORY_POINTER;
	wire [31:0] CONF_TCN_BLOCK_SIZE;
	wire [15:0] CONF_ZERO_PADDING;
	wire [3:0] CONF_ZERO_PADDING_X_left;
	wire [3:0] CONF_ZERO_PADDING_X_right;
	wire [3:0] CONF_ZERO_PADDING_Y;
	wire [31:0] CONF_TCN_BLOCK_SIZE_input;
	wire [31:0] CONF_C;
	wire [15:0] CONF_K;
	wire [15:0] CONF_C_X;
	wire [15:0] CONF_C_Y;
	wire [15:0] CONF_PADDED_C_X;
	wire [15:0] CONF_PADDED_C_Y;
	wire [15:0] CONF_O_X;
	wire [15:0] CONF_O_Y;
	wire [31:0] CONF_WEIGHT_TILE_SIZE;
	wire [15:0] CONF_SIZE_CHANNEL;
	wire [15:0] CONF_WYdivN;
	wire [15:0] CONF_WXdivN;
	wire [15:0] CONF_STR_SPARSITY;
	wire [15:0] CONF_TCN_TOTAL_BLOCKS;
	wire [15:0] CONF_OUTPUT_CHANNEL_SIZE;
	wire [7:0] CONF_DILATION;
	wire [7:0] CONF_FX;
	wire [7:0] CONF_FY;
	wire [7:0] CONF_SHIFT_FIXED_POINT;
	wire [3:0] CONF_TYPE_NONLINEAR_FUNCTION;
	wire [3:0] CONF_MODE;
	wire [3:0] CONF_ACTIVATION_FUNCTION;
	wire [1:0] CONF_WRITE_L2_L1;
	wire [0:0] CONF_STOP;
	wire [0:0] CONF_CAUSAL_CONVOLUTION;
	wire [1:0] CONF_INPUT_PRECISION;
	wire [1:0] CONF_OUTPUT_PRECISION;
	wire [7:0] CONF_NB_INPUT_TILE;
	wire [7:0] CONF_NB_WEIGHT_TILE;
	wire [0:0] CONF_CONV_STRIDED;
	wire [0:0] CONF_CONV_DECONV;
	wire [1:0] CONF_NORM;
	integer i;
	integer j;
	integer k;
	integer l;
	integer sp;
	sparsity_memory WRAPPER_SPARSITY_MEM(
		.CONF_STR_SPARSITY(CONF_STR_SPARSITY),
		.clk(clk),
		.reset(reset),
		.scan_en_in(scan_en_in),
		.wr_en_ext(wr_en_ext_sparsity),
		.wr_addr_ext(wr_addr_ext_sparsity),
		.wr_data_ext(wr_data_ext_sparsity),
		.rd_en(rd_en_sparsity),
		.rd_addr({CONF_STR_SPARSITY[1], sparse_addr[9:0]}),
		.rd_data(sparse_val_sram)
	);
	assign CONF_MODE = instruction[0+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign weight_memory_pointer = instruction[parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_INPUT_MEMORY_POINTER = instruction[2 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_OUTPUT_MEMORY_POINTER = instruction[3 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_C = instruction[4 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_K = instruction[5 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_C_X = instruction[6 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_C_Y = instruction[7 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_PADDED_C_X = instruction[8 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_PADDED_C_Y = instruction[9 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_SIZE_CHANNEL = instruction[10 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_FX = instruction[11 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_FY = instruction[12 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_O_X = instruction[13 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_O_Y = instruction[14 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_TCN_TOTAL_BLOCKS = instruction[15 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_TCN_BLOCK_SIZE = instruction[16 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_ACTIVATION_FUNCTION = instruction[17 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_WRITE_L2_L1 = instruction[18 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_OUTPUT_CHANNEL_SIZE = instruction[19 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_STR_SPARSITY = instruction[20 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_DILATION = instruction[21 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_STOP = instruction[22 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_SHIFT_FIXED_POINT = instruction[23 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_ZERO_PADDING = instruction[24 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_TYPE_NONLINEAR_FUNCTION = instruction[25 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_WEIGHT_TILE_SIZE = instruction[26 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_NB_WEIGHT_TILE = instruction[27 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_OUTPUT_PRECISION = instruction[31 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	assign CONF_INPUT_PRECISION = instruction[31 * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH];
	wire [1:1] sv2v_tmp_00CFA;
	assign sv2v_tmp_00CFA = finished_layer;
	always @(*) done_layer = sv2v_tmp_00CFA;
	assign CONF_TCN_BLOCK_SIZE_input = CONF_TCN_BLOCK_SIZE[15:0];
	assign CONF_ZERO_PADDING_X_left = CONF_ZERO_PADDING[3:0];
	assign CONF_ZERO_PADDING_X_right = CONF_ZERO_PADDING[7:4];
	assign CONF_ZERO_PADDING_Y = CONF_ZERO_PADDING[11:8];
	always @(posedge clk or negedge reset)
		if (!reset)
			PC <= 0;
		else if (finished_network)
			PC <= 0;
		else if (finished_layer)
			PC <= PC + 1;
	always @(posedge clk or negedge reset)
		if (!reset)
			HL_state <= HL_IDLE;
		else
			HL_state <= HL_next_state;
	always @(*) begin
		HL_next_state = HL_state;
		case (HL_state)
			HL_IDLE:
				if (enable)
					HL_next_state = HL_RUN;
			HL_RUN: HL_next_state = HL_RUNNING;
			HL_RUNNING:
				if (finished_layer)
					HL_next_state = HL_FINISHED_LAYER;
			HL_FINISHED_LAYER:
				if (CONF_STOP == 1)
					HL_next_state = HL_END;
				else
					HL_next_state = HL_RUN;
			HL_END: HL_next_state = HL_IDLE;
		endcase
	end
	always @(*) begin
		finished_network = 0;
		case (HL_state)
			HL_IDLE: begin
				HL_enable = 0;
				rd_en_sparsity = 0;
			end
			HL_RUN: begin
				HL_enable = 1;
				rd_en_sparsity = 1;
			end
			HL_RUNNING: begin
				HL_enable = 0;
				rd_en_sparsity = 1;
			end
			HL_FINISHED_LAYER: begin
				HL_enable = 0;
				rd_en_sparsity = 1;
			end
			HL_END: begin
				finished_network = 1;
				HL_enable = 0;
				rd_en_sparsity = 0;
			end
			default: begin
				HL_enable = 0;
				rd_en_sparsity = 0;
			end
		endcase
	end
	always @(*) begin
		BIAS_ACC_FINISHED = counter_acc_cnn_bias == 3;
		CNN_FINISHED_FX_LOOP = counter_FX == (CONF_FX - 1);
		CNN_FINISHED_FY_LOOP = counter_FY == (CONF_FY - 1);
		CNN_FINISHED_C_LOOP = counter_C == (CONF_C - 1);
		CNN_FINISHED_K_LOOP = counter_K == (CONF_K - 1);
		CNN_FINISHED_X_LOOP = counter_X == (CONF_O_X - 1);
		CNN_FINISHED_Y_LOOP = counter_Y == (CONF_O_Y - 1);
		FC_FINISHED_K_LOOP = counter_K == (CONF_K - 1);
		EWS_FINISHED = counter_C == CONF_C;
		ACCUMULATION_PES_FINISHED = counter_accumulation_pes == (parameters_N_DIM_ARRAY - 1);
		if (((CONF_TCN_BLOCK_SIZE_input != 0) && (EXECUTION_FRAME_BY_FRAME == 1)) && (CONF_DILATION != 1))
			FC_FINISHED_C_LOOP = counter_C == (CONF_C - 1);
		else if (CONF_C > 1)
			FC_FINISHED_C_LOOP = counter_C == (CONF_C - CONF_DILATION);
		else
			FC_FINISHED_C_LOOP = counter_C == 1;
	end
	always @(posedge clk or negedge reset)
		if (!reset) begin
			counter_FX <= 0;
			counter_FY <= 0;
			counter_X <= 0;
			counter_Y <= 0;
			counter_C <= 0;
			counter_K <= 0;
			counter_input_channel_address <= 0;
			counter_weight_address <= 0;
			counter_accumulation_pes <= 0;
			counter_offset_input_channel <= 0;
			counter_activation_read_address <= 0;
			counter_output_channel_address <= 0;
			counter_sparsity <= 0;
			counter_current_channel_address <= 0;
			counter_input_buffer_loading <= 0;
			counter_acc_cnn_bias <= 0;
			counter_weight_address_after_bias <= 0;
			sparse_val <= 0;
			sparse_addr <= 0;
		end
		else begin
			counter_weight_address_after_bias <= next_counter_weight_address_after_bias;
			counter_X <= next_counter_X;
			counter_Y <= next_counter_Y;
			counter_FX <= next_counter_FX;
			counter_FY <= next_counter_FY;
			counter_input_channel_address <= next_counter_input_channel_address;
			counter_weight_address <= next_counter_weight_address;
			counter_accumulation_pes <= next_counter_accumulation_pes;
			counter_C <= next_counter_C;
			counter_offset_input_channel <= next_counter_offset_input_channel;
			counter_K <= next_counter_K;
			counter_activation_read_address <= next_counter_activation_read_address;
			counter_output_channel_address <= next_counter_output_channel_address;
			counter_sparsity <= next_counter_sparsity;
			counter_current_channel_address <= next_counter_current_channel_address;
			counter_input_buffer_loading <= next_counter_input_buffer_loading;
			counter_acc_cnn_bias <= next_counter_acc_cnn_bias;
			sparse_val <= next_sparse_val;
			sparse_addr <= next_sparse_addr;
		end
	localparam integer parameters_BLOCK_SPARSE = 0;
	localparam integer parameters_STR_SP_MEMORY_WORD_LOG = 5;
	always @(*) begin
		next_counter_acc_cnn_bias = counter_acc_cnn_bias;
		next_counter_X = counter_X;
		next_counter_Y = counter_Y;
		next_counter_offset_input_channel = counter_offset_input_channel;
		next_counter_FX = counter_FX;
		next_counter_C = counter_C;
		next_counter_input_channel_address = counter_input_channel_address;
		next_counter_weight_address = counter_weight_address;
		next_counter_accumulation_pes = counter_accumulation_pes;
		next_counter_FY = counter_FY;
		next_counter_K = counter_K;
		next_counter_activation_read_address = counter_activation_read_address;
		next_counter_output_channel_address = counter_output_channel_address;
		next_counter_sparsity = counter_sparsity;
		next_counter_current_channel_address = counter_current_channel_address;
		next_counter_input_buffer_loading = counter_input_buffer_loading;
		next_counter_weight_address_after_bias = counter_weight_address_after_bias;
		number_ones = 0;
		next_sparse_val = sparse_val;
		next_sparse_addr = sparse_addr;
		case (state)
			INITIAL: begin
				next_counter_X = 0;
				next_counter_Y = 0;
				next_counter_offset_input_channel = 0;
				next_counter_FX = 0;
				next_counter_C = 0;
				next_counter_input_channel_address = 0;
				next_counter_weight_address = 0;
				next_counter_accumulation_pes = 0;
				next_counter_FY = 0;
				next_counter_K = 0;
				next_counter_activation_read_address = 0;
				next_counter_output_channel_address = 0;
				next_counter_sparsity = 0;
				SPARSITY_SET = 0;
				next_sparse_val = sparse_val_sram;
				next_sparse_addr = (next_counter_K >> parameters_BLOCK_SPARSE) + (counter_C >> parameters_STR_SP_MEMORY_WORD_LOG);
				number_ones = 0;
			end
			STR_SPARSITY:
				if (next_sparse_val[0] == 1) begin
					if (next_sparse_val[1] == 1) begin
						for (sp = 0; sp < 4; sp = sp + 1)
							if ((next_sparse_val[sp] == 1) && (next_sparse_val[sp + 1] == 1)) begin
								number_ones = number_ones + 1;
								if (number_ones > next_counter_sparsity)
									next_counter_sparsity = number_ones;
							end
					end
					else
						next_counter_sparsity = 0;
					SPARSITY_SET = 1;
					if (((CNN_FINISHED_C_LOOP & CNN_FINISHED_K_LOOP) & CNN_FINISHED_X_LOOP) & CNN_FINISHED_Y_LOOP) begin
						next_counter_X = counter_X;
						next_counter_Y = counter_Y + 1;
						next_counter_FX = 0;
						next_counter_offset_input_channel = 0;
						next_counter_C = 0;
						next_counter_accumulation_pes = counter_accumulation_pes;
						next_counter_weight_address = counter_weight_address + 1;
						next_counter_weight_address_after_bias = 0;
						next_counter_input_channel_address = 0;
						next_counter_FY = 0;
						next_counter_K = 0;
					end
					else if ((CNN_FINISHED_C_LOOP & CNN_FINISHED_K_LOOP) & CNN_FINISHED_X_LOOP) begin
						next_counter_X = 0;
						next_counter_Y = counter_Y + 1;
						next_counter_FX = 0;
						next_counter_offset_input_channel = counter_offset_input_channel + 8;
						next_counter_input_channel_address = counter_offset_input_channel + 8;
						if ((CONF_ZERO_PADDING_Y != 0) && (counter_Y == 0)) begin
							next_counter_offset_input_channel = 0;
							next_counter_input_channel_address = 0;
						end
						next_counter_C = 0;
						next_counter_accumulation_pes = counter_accumulation_pes;
						next_counter_weight_address = counter_weight_address + 1;
						next_counter_weight_address_after_bias = 0;
						next_counter_FY = 0;
						next_counter_K = 0;
					end
					else if (CNN_FINISHED_C_LOOP & CNN_FINISHED_K_LOOP) begin
						next_counter_X = counter_X + 1;
						next_counter_Y = counter_Y;
						next_counter_FX = 0;
						next_counter_C = 0;
						next_counter_accumulation_pes = counter_accumulation_pes;
						next_counter_weight_address = counter_weight_address + 1;
						next_counter_weight_address_after_bias = 0;
						next_counter_FY = 0;
						next_counter_K = 0;
						next_sparse_val = sparse_val_sram;
						next_counter_offset_input_channel = counter_offset_input_channel + parameters_N_DIM_ARRAY;
						next_counter_input_channel_address = counter_offset_input_channel + parameters_N_DIM_ARRAY;
					end
					else if (CNN_FINISHED_C_LOOP || FC_FINISHED_C_LOOP) begin
						next_counter_X = counter_X;
						next_counter_Y = counter_Y;
						next_counter_FX = 0;
						next_counter_offset_input_channel = counter_offset_input_channel;
						next_counter_C = 0;
						next_counter_sparsity = 0;
						next_counter_accumulation_pes = counter_accumulation_pes;
						next_counter_weight_address = counter_weight_address;
						next_counter_weight_address_after_bias = counter_weight_address + 4;
						next_counter_input_channel_address = counter_offset_input_channel;
						next_counter_FY = 0;
						if (CONF_MODE == 1)
							next_counter_K = counter_K + 1;
						else
							next_counter_K = counter_K;
						next_sparse_val = sparse_val >> (next_counter_sparsity + 1);
						next_sparse_addr = (next_counter_K >> parameters_BLOCK_SPARSE) + (next_counter_C >> parameters_STR_SP_MEMORY_WORD_LOG);
					end
					else begin
						next_counter_X = counter_X;
						next_counter_Y = counter_Y;
						next_counter_FX = 0;
						next_counter_offset_input_channel = counter_offset_input_channel;
						next_counter_C = (counter_C + next_counter_sparsity) + 1;
						next_counter_accumulation_pes = counter_accumulation_pes;
						next_counter_weight_address = counter_weight_address;
						next_counter_FY = 0;
						next_counter_K = counter_K;
						next_sparse_val = sparse_val >> (next_counter_sparsity + 1);
						next_counter_input_channel_address = (counter_offset_input_channel + counter_current_channel_address) + (CONF_SIZE_CHANNEL * (next_counter_sparsity + 1));
						next_counter_current_channel_address = counter_current_channel_address + (CONF_SIZE_CHANNEL * (next_counter_sparsity + 1));
					end
				end
				else begin
					next_counter_sparsity = 0;
					next_counter_C = counter_C;
					next_counter_FX = 0;
					next_counter_FY = counter_FY;
					next_counter_X = counter_X;
					next_counter_Y = counter_Y;
					next_counter_offset_input_channel = counter_offset_input_channel;
					next_counter_input_channel_address = counter_input_channel_address;
					next_counter_accumulation_pes = 0;
					next_counter_weight_address = counter_weight_address;
					next_counter_K = counter_K;
					SPARSITY_SET = 0;
				end
			CONV_PADDING_FILLING_INPUT_FIFO: begin
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_C = counter_C;
				next_counter_accumulation_pes = 0;
				next_counter_weight_address = counter_weight_address;
				next_counter_input_channel_address = counter_input_channel_address;
				next_counter_FY = counter_FY;
				next_counter_K = counter_K;
				SPARSITY_SET = 0;
				number_ones = 0;
			end
			CONV_FILLING_INPUT_FIFO: begin
				next_counter_weight_address = counter_weight_address;
				next_counter_FX = 0;
				next_counter_FY = counter_FY;
				if (CONF_ZERO_PADDING_Y == 0)
					next_counter_FY = counter_FY;
				else begin
					if (counter_Y == 0)
						next_counter_FY = counter_FY + CONF_ZERO_PADDING_Y;
					else if ((counter_Y == (CONF_O_Y - 1)) && !CONF_CONV_STRIDED)
						next_counter_FY = counter_FY + CONF_ZERO_PADDING_Y;
					else
						next_counter_FY = counter_FY;
					if ((counter_Y == 0) && (counter_FY == 0))
						next_counter_weight_address = next_counter_weight_address + (CONF_ZERO_PADDING_Y * CONF_FX);
				end
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_C = counter_C;
				next_counter_accumulation_pes = 0;
				next_counter_input_channel_address = counter_input_channel_address + parameters_N_DIM_ARRAY;
				next_counter_K = counter_K;
				SPARSITY_SET = 0;
				number_ones = 0;
			end
			CONV_PRE_MAC: begin
				next_counter_input_buffer_loading = 0;
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_C = counter_C;
				next_counter_accumulation_pes = 0;
				next_counter_weight_address = counter_weight_address + 1;
				next_counter_FY = counter_FY;
				next_counter_K = counter_K;
				next_counter_sparsity = 0;
				next_counter_input_channel_address = counter_input_channel_address + CONF_DILATION;
			end
			CONV_PRE_MAC_2: begin
				next_counter_input_buffer_loading = 0;
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_C = counter_C;
				next_counter_accumulation_pes = 0;
				next_counter_weight_address = counter_weight_address + 1;
				next_counter_FY = counter_FY;
				next_counter_K = counter_K;
				next_counter_input_channel_address = (counter_input_channel_address + CONF_DILATION) + parameters_N_DIM_ARRAY;
			end
			CONV_MAC: begin
				if (((((CNN_FINISHED_FX_LOOP & CNN_FINISHED_FY_LOOP) & CNN_FINISHED_C_LOOP) & CNN_FINISHED_K_LOOP) & CNN_FINISHED_X_LOOP) & CNN_FINISHED_Y_LOOP) begin
					next_counter_X = counter_X;
					next_counter_Y = counter_Y + 1;
					next_counter_FX = 0;
					next_counter_offset_input_channel = 0;
					next_counter_C = 0;
					next_counter_accumulation_pes = counter_accumulation_pes;
					next_counter_weight_address = counter_weight_address + 1;
					next_counter_weight_address_after_bias = 0;
					next_counter_input_channel_address = 0;
					next_counter_FY = 0;
					next_counter_K = 0;
				end
				else if ((((CNN_FINISHED_FX_LOOP & CNN_FINISHED_FY_LOOP) & CNN_FINISHED_C_LOOP) & CNN_FINISHED_K_LOOP) & CNN_FINISHED_X_LOOP) begin
					next_counter_X = 0;
					next_counter_Y = counter_Y + 1;
					next_counter_FX = 0;
					next_counter_offset_input_channel = counter_offset_input_channel + 8;
					next_counter_input_channel_address = counter_offset_input_channel + 8;
					if ((CONF_ZERO_PADDING_Y != 0) && (counter_Y == 0)) begin
						next_counter_offset_input_channel = 0;
						next_counter_input_channel_address = 0;
					end
					next_counter_C = 0;
					next_counter_accumulation_pes = counter_accumulation_pes;
					next_counter_weight_address = counter_weight_address + 1;
					next_counter_weight_address_after_bias = 0;
					next_counter_FY = 0;
					next_counter_K = 0;
				end
				else if (((CNN_FINISHED_FX_LOOP & CNN_FINISHED_FY_LOOP) & CNN_FINISHED_C_LOOP) & CNN_FINISHED_K_LOOP) begin
					next_counter_X = counter_X + 1;
					next_counter_Y = counter_Y;
					next_counter_FX = 0;
					next_counter_C = 0;
					next_counter_accumulation_pes = counter_accumulation_pes;
					next_counter_weight_address = counter_weight_address + 1;
					next_counter_weight_address_after_bias = 0;
					next_counter_FY = 0;
					next_counter_K = 0;
					next_counter_offset_input_channel = counter_offset_input_channel + parameters_N_DIM_ARRAY;
					next_counter_input_channel_address = counter_offset_input_channel + parameters_N_DIM_ARRAY;
				end
				else if ((CNN_FINISHED_FX_LOOP & CNN_FINISHED_FY_LOOP) & CNN_FINISHED_C_LOOP) begin
					next_counter_X = counter_X;
					next_counter_Y = counter_Y;
					next_counter_FX = 0;
					next_counter_offset_input_channel = counter_offset_input_channel;
					next_counter_C = 0;
					next_counter_accumulation_pes = counter_accumulation_pes;
					next_counter_weight_address = counter_weight_address + 1;
					next_counter_weight_address_after_bias = counter_weight_address + 4;
					next_counter_input_channel_address = counter_offset_input_channel;
					next_counter_FY = 0;
					next_counter_K = counter_K + 1;
				end
				else if (CNN_FINISHED_FX_LOOP & CNN_FINISHED_FY_LOOP) begin
					next_counter_X = counter_X;
					next_counter_Y = counter_Y;
					next_counter_FX = 0;
					next_counter_offset_input_channel = counter_offset_input_channel;
					next_counter_C = counter_C + 1;
					next_counter_accumulation_pes = counter_accumulation_pes;
					next_counter_weight_address_after_bias = counter_weight_address_after_bias;
					next_counter_input_channel_address = (counter_offset_input_channel + counter_current_channel_address) + CONF_SIZE_CHANNEL;
					next_counter_current_channel_address = counter_current_channel_address + CONF_SIZE_CHANNEL;
					next_counter_K = counter_K;
					next_counter_sparsity = 0;
					if (CONF_STR_SPARSITY) begin
						next_sparse_val = sparse_val >> (counter_sparsity + 1);
						if ((next_counter_C % parameters_STR_SP_MEMORY_WORD) == (parameters_STR_SP_MEMORY_WORD - 1))
							next_sparse_addr = sparse_addr + 1;
						else
							next_sparse_addr = sparse_addr;
					end
					next_counter_weight_address = counter_weight_address;
					next_counter_FY = 0;
					if (CONF_ZERO_PADDING_Y != 0) begin
						if (counter_Y == 0)
							next_counter_FY = next_counter_FY + CONF_ZERO_PADDING_Y;
						else if ((counter_Y == (CONF_O_Y - 1)) && !CONF_CONV_STRIDED)
							next_counter_FY = next_counter_FY + CONF_ZERO_PADDING_Y;
						else
							next_counter_FY = next_counter_FY;
						if ((counter_Y == 0) && (next_state != STR_SPARSITY))
							next_counter_weight_address = next_counter_weight_address + (CONF_ZERO_PADDING_Y * CONF_FX);
					end
				end
				else if (CNN_FINISHED_FX_LOOP) begin
					next_counter_X = counter_X;
					next_counter_Y = counter_Y;
					next_counter_FX = 0;
					next_counter_offset_input_channel = counter_offset_input_channel;
					next_counter_C = counter_C;
					next_counter_accumulation_pes = counter_accumulation_pes;
					next_counter_weight_address_after_bias = counter_weight_address_after_bias;
					next_counter_input_channel_address = counter_input_channel_address + ((CONF_PADDED_C_X - CONF_FX) - parameters_N_DIM_ARRAY);
					next_counter_K = counter_K;
					next_counter_weight_address = counter_weight_address;
					next_counter_FY = counter_FY + 1;
				end
				else if (!CNN_FINISHED_FX_LOOP) begin
					next_counter_X = counter_X;
					next_counter_Y = counter_Y;
					next_counter_FX = counter_FX + 1;
					next_counter_offset_input_channel = counter_offset_input_channel;
					next_counter_C = counter_C;
					next_counter_accumulation_pes = counter_accumulation_pes;
					next_counter_FY = counter_FY;
					next_counter_K = counter_K;
					next_counter_input_channel_address = counter_input_channel_address + CONF_DILATION;
					next_counter_weight_address = counter_weight_address + 1;
				end
				if (CONF_FX == 1)
					next_counter_input_buffer_loading = 0;
				else if (counter_input_buffer_loading != (CONF_FX - 2))
					next_counter_input_buffer_loading = counter_input_buffer_loading + 1;
				else
					next_counter_input_buffer_loading = counter_input_buffer_loading;
				if (((((CONF_ZERO_PADDING_Y != 0) && (counter_Y == (CONF_O_Y - 1))) && (counter_FY == (CONF_FY - 1))) && (counter_FX == (CONF_FX - 2))) && !CONF_CONV_STRIDED) begin
					next_counter_weight_address = next_counter_weight_address + (CONF_ZERO_PADDING_Y * CONF_FX);
					next_counter_weight_address_after_bias = next_counter_weight_address_after_bias + (CONF_ZERO_PADDING_Y * CONF_FX);
				end
			end
			CONV_ADD_BIAS_ACC: begin
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_C = counter_C;
				next_counter_accumulation_pes = 0;
				if (BIAS_ACC_FINISHED)
					next_counter_weight_address = counter_weight_address;
				else
					next_counter_weight_address = counter_weight_address + 1;
				next_counter_input_channel_address = counter_input_channel_address;
				next_counter_FY = counter_FY;
				next_counter_K = counter_K;
				next_counter_acc_cnn_bias = counter_acc_cnn_bias + 1;
			end
			CONV_ADD_BIAS_OPERATION: begin
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_C = counter_C;
				next_counter_accumulation_pes = 0;
				next_counter_weight_address = counter_weight_address_after_bias;
				next_counter_input_channel_address = counter_input_channel_address;
				next_counter_FY = counter_FY;
				next_counter_K = counter_K;
				if (CONF_STR_SPARSITY)
					next_sparse_addr = (next_counter_K >> parameters_BLOCK_SPARSE) + (next_counter_C >> parameters_STR_SP_MEMORY_WORD_LOG);
			end
			CONV_ADD_BIAS_SHIFTING: begin
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_C = counter_C;
				next_counter_accumulation_pes = 0;
				next_counter_weight_address = counter_weight_address;
				next_counter_input_channel_address = counter_input_channel_address;
				next_counter_FY = counter_FY;
				next_counter_K = counter_K;
			end
			CONV_PRE_PASSING_OUTPUTS_VERTICAL: begin
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_weight_address = counter_weight_address;
				next_counter_accumulation_pes = counter_accumulation_pes + 1;
				next_counter_input_channel_address = counter_input_channel_address;
				next_counter_FY = 0;
				next_counter_K = counter_K;
				if (counter_K == 0)
					next_counter_output_channel_address = counter_output_channel_address + 1;
			end
			CONV_PASSING_OUTPUTS_VERTICAL: begin
				next_counter_X = counter_X;
				next_counter_Y = counter_Y;
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_weight_address = counter_weight_address;
				next_counter_accumulation_pes = counter_accumulation_pes + 1;
				next_counter_input_channel_address = counter_input_channel_address;
				if (CONF_STR_SPARSITY)
					next_sparse_val = sparse_val_sram;
				next_counter_FY = 0;
				next_counter_K = counter_K;
				if (counter_K == 0)
					next_counter_output_channel_address = counter_output_channel_address + 1;
			end
			CONV_CLEAR_MAC: begin
				next_counter_FX = 0;
				next_counter_offset_input_channel = counter_offset_input_channel;
				next_counter_weight_address = counter_weight_address;
				next_counter_accumulation_pes = counter_accumulation_pes;
				next_counter_input_channel_address = counter_input_channel_address;
				next_counter_current_channel_address = 0;
				next_counter_FY = 0;
				next_counter_K = counter_K;
			end
			FC_PRE_MAC: begin
				next_counter_accumulation_pes = 0;
				next_counter_weight_address = counter_weight_address + 1;
				next_counter_Y = 0;
				next_counter_offset_input_channel = 0;
				next_counter_FX = 0;
				next_counter_FY = 0;
				next_counter_input_channel_address = 0;
				next_counter_K = counter_K;
				SPARSITY_SET = 0;
				if (!EXECUTION_FRAME_BY_FRAME) begin
					next_counter_X = 0;
					next_counter_C = counter_C + 1;
					if (CONF_STR_SPARSITY)
						next_sparse_val = sparse_val >> (next_counter_sparsity + 1);
				end
				else begin
					if (counter_X == (CONF_TCN_BLOCK_SIZE_input - 1))
						next_counter_X = 0;
					else
						next_counter_X = counter_X + 1;
					if (counter_X == (CONF_TCN_BLOCK_SIZE_input - 1)) begin
						if (CONF_DILATION == 1)
							next_counter_C = counter_C + 1;
						else if (CONF_TCN_BLOCK_SIZE_input == 1)
							next_counter_C = counter_C + CONF_DILATION;
						else
							next_counter_C = (counter_C + (CONF_TCN_BLOCK_SIZE_input * (CONF_DILATION - 1))) + 1;
					end
					else
						next_counter_C = counter_C + 1;
				end
			end
			FC_MAC: begin
				next_counter_accumulation_pes = counter_accumulation_pes;
				next_counter_Y = 0;
				next_counter_weight_address = counter_weight_address + 1;
				next_counter_offset_input_channel = 0;
				next_counter_FY = 0;
				next_counter_input_channel_address = 0;
				next_counter_K = counter_K;
				SPARSITY_SET = 0;
				if (!EXECUTION_FRAME_BY_FRAME)
					next_counter_X = 0;
				else if (counter_X == (CONF_TCN_BLOCK_SIZE_input - 1))
					next_counter_X = 0;
				else
					next_counter_X = counter_X + 1;
				if (FC_FINISHED_C_LOOP)
					next_counter_C = 0;
				else if (!EXECUTION_FRAME_BY_FRAME) begin
					if (next_state == STR_SPARSITY) begin
						next_counter_C = counter_C;
						next_counter_weight_address = counter_weight_address;
					end
					else begin
						next_counter_C = counter_C + 1;
						next_counter_weight_address = counter_weight_address + 1;
						if (CONF_STR_SPARSITY) begin
							next_sparse_val = sparse_val >> (next_counter_sparsity + 1);
							if ((counter_C % parameters_STR_SP_MEMORY_WORD) == (parameters_STR_SP_MEMORY_WORD - 3))
								next_sparse_addr = sparse_addr + 1;
							if ((counter_C % parameters_STR_SP_MEMORY_WORD) == (parameters_STR_SP_MEMORY_WORD - 1))
								next_sparse_val = sparse_val_sram;
						end
					end
				end
				else if (counter_X == (CONF_TCN_BLOCK_SIZE_input - 1)) begin
					if (CONF_DILATION == 1)
						next_counter_C = counter_C + 1;
					else if (CONF_TCN_BLOCK_SIZE_input == 1)
						next_counter_C = counter_C + CONF_DILATION;
					else
						next_counter_C = (counter_C + (CONF_TCN_BLOCK_SIZE_input * (CONF_DILATION - 1))) + 1;
				end
				else
					next_counter_C = counter_C + 1;
			end
			FC_PRE_BIAS: begin
				next_counter_accumulation_pes = counter_accumulation_pes;
				next_counter_X = 0;
				next_counter_Y = 0;
				next_counter_weight_address = counter_weight_address + 1;
				next_counter_offset_input_channel = 0;
				next_counter_FX = 0;
				next_counter_FY = 0;
				next_counter_C = counter_C;
				next_counter_input_channel_address = 0;
				next_counter_K = counter_K;
				if (CONF_STR_SPARSITY)
					if (counter_K == (CONF_K - 1))
						next_sparse_addr = 1'sb0;
					else
						next_sparse_addr = sparse_addr + 1;
			end
			FC_BIAS: begin
				next_counter_accumulation_pes = counter_accumulation_pes;
				next_counter_X = 0;
				next_counter_Y = 0;
				next_counter_weight_address = counter_weight_address;
				next_counter_offset_input_channel = 0;
				next_counter_FX = 0;
				next_counter_FY = 0;
				next_counter_C = counter_C;
				next_counter_input_channel_address = 0;
				next_counter_K = counter_K;
			end
			FC_PRE_ACCUMULATE_MACS: begin
				next_counter_weight_address = counter_weight_address;
				next_counter_accumulation_pes = counter_accumulation_pes + 1;
				next_counter_Y = 0;
				next_counter_X = 0;
				next_counter_offset_input_channel = 0;
				next_counter_FX = 0;
				next_counter_FY = 0;
				next_counter_C = counter_C;
				next_counter_input_channel_address = 0;
				next_counter_K = counter_K;
			end
			FC_ADDER_TREE_0: begin
				next_counter_weight_address = counter_weight_address;
				next_counter_accumulation_pes = 0;
				next_counter_Y = 0;
				next_counter_X = 0;
				next_counter_offset_input_channel = 0;
				next_counter_FX = 0;
				next_counter_FY = 0;
				next_counter_C = counter_C;
				next_counter_input_channel_address = 0;
				next_counter_K = counter_K;
			end
			FC_ACCUMULATE_MACS: begin
				next_counter_weight_address = counter_weight_address;
				next_counter_accumulation_pes = counter_accumulation_pes + 1;
				next_counter_Y = 0;
				next_counter_X = 0;
				next_counter_offset_input_channel = 0;
				next_counter_FX = 0;
				next_counter_FY = 0;
				next_counter_C = counter_C;
				next_counter_input_channel_address = 0;
				next_counter_K = counter_K;
			end
			FC_SAVE_OUTPUTS_MACS: begin
				next_counter_accumulation_pes = counter_accumulation_pes;
				next_counter_X = 0;
				next_counter_Y = 0;
				next_counter_weight_address = counter_weight_address;
				next_counter_K = counter_K + 1;
				next_counter_offset_input_channel = 0;
				next_counter_FX = 0;
				next_counter_FY = 0;
				next_counter_C = counter_C;
				next_counter_input_channel_address = 0;
				if (CONF_STR_SPARSITY)
					next_sparse_val = sparse_val_sram;
				if (counter_K == 0)
					next_counter_output_channel_address = counter_output_channel_address + 1;
			end
			ACTIVATION: next_counter_C = counter_C;
			EWS_PRE_MAC: next_counter_C = counter_C;
			EWS_MAC_0: next_counter_C = counter_C + 1;
			EWS_MAC_1: next_counter_C = counter_C;
			EWS_SAVE_MAC: next_counter_C = counter_C;
		endcase
	end
	always @(posedge clk or negedge reset)
		if (!reset)
			state <= INITIAL;
		else
			state <= next_state;
	localparam integer parameters_MODE_ACTIVATION = 2;
	localparam integer parameters_MODE_CNN = 1;
	localparam integer parameters_MODE_EWS = 3;
	localparam integer parameters_MODE_FC = 0;
	always @(*) begin
		next_state = state;
		case (state)
			INITIAL:
				if (HL_enable == 1)
					case (CONF_MODE)
						parameters_MODE_EWS: next_state = EWS_PRE_MAC;
						parameters_MODE_ACTIVATION: next_state = ACTIVATION;
						parameters_MODE_CNN:
							if (CONF_STR_SPARSITY)
								next_state = STR_SPARSITY;
							else
								next_state = CONV_FILLING_INPUT_FIFO;
						parameters_MODE_FC:
							if (CONF_STR_SPARSITY)
								next_state = STR_SPARSITY;
							else
								next_state = FC_PRE_MAC;
						default: next_state = INITIAL;
					endcase
				else
					next_state = INITIAL;
			STR_SPARSITY:
				if (CONF_MODE == parameters_MODE_CNN) begin
					if (CNN_FINISHED_X_LOOP && (next_counter_Y == CONF_O_Y))
						next_state = FINISHED_LAYER;
					else if (sparse_val[0] == 0)
						next_state = CONV_FILLING_INPUT_FIFO;
					else
						next_state = state;
				end
				else if (CONF_MODE == 0)
					if (sparse_val[0] == 0)
						next_state = FC_PRE_MAC;
					else
						next_state = state;
			CONV_FILLING_INPUT_FIFO: next_state = CONV_PRE_MAC;
			CONV_PRE_MAC: next_state = CONV_MAC;
			CONV_PRE_MAC_2: next_state = CONV_MAC;
			CONV_MAC:
				if ((CNN_FINISHED_FX_LOOP && CNN_FINISHED_FY_LOOP) && CNN_FINISHED_C_LOOP)
					next_state = CONV_ADD_BIAS_ACC;
				else if (CNN_FINISHED_FX_LOOP && CNN_FINISHED_FY_LOOP) begin
					if (CONF_STR_SPARSITY) begin
						if (sparse_val[1] == 1)
							next_state = STR_SPARSITY;
						else
							next_state = CONV_PRE_MAC_2;
					end
					else
						next_state = CONV_PRE_MAC_2;
				end
				else if (CNN_FINISHED_FX_LOOP)
					next_state = CONV_PRE_MAC_2;
				else
					next_state = state;
			CONV_ADD_BIAS: next_state = CONV_PRE_PASSING_OUTPUTS_VERTICAL;
			CONV_ADD_BIAS_ACC:
				if (BIAS_ACC_FINISHED)
					next_state = CONV_ADD_BIAS_OPERATION;
				else
					next_state = CONV_ADD_BIAS_ACC;
			CONV_ADD_BIAS_OPERATION: next_state = CONV_ADD_BIAS_SHIFTING;
			CONV_ADD_BIAS_SHIFTING: next_state = CONV_PRE_PASSING_OUTPUTS_VERTICAL;
			CONV_PRE_PASSING_OUTPUTS_VERTICAL: next_state = CONV_PASSING_OUTPUTS_VERTICAL;
			CONV_PASSING_OUTPUTS_VERTICAL:
				if (ACCUMULATION_PES_FINISHED)
					next_state = CONV_CLEAR_MAC;
				else
					next_state = CONV_PASSING_OUTPUTS_VERTICAL;
			CONV_CLEAR_MAC:
				if (CNN_FINISHED_X_LOOP && (counter_Y == CONF_O_Y))
					next_state = FINISHED_LAYER;
				else if (CONF_STR_SPARSITY == 0)
					next_state = CONV_FILLING_INPUT_FIFO;
				else if (sparse_val[counter_C % parameters_STR_SP_MEMORY_WORD] == 0)
					next_state = CONV_FILLING_INPUT_FIFO;
				else
					next_state = STR_SPARSITY;
			FC_PRE_MAC:
				if (CONF_STR_SPARSITY) begin
					if (sparse_val[0] == 1)
						next_state = STR_SPARSITY;
					else
						next_state = FC_MAC;
				end
				else
					next_state = FC_MAC;
			FC_MAC:
				if (FC_FINISHED_C_LOOP)
					next_state = FC_PRE_ACCUMULATE_MACS;
				else if (CONF_STR_SPARSITY) begin
					if (sparse_val[0] == 1)
						next_state = STR_SPARSITY;
					else
						next_state = state;
				end
				else
					next_state = state;
			FC_ADDER_TREE_0:
				if ((CONF_NORM == 2'b00) || (CONF_NORM == 2'b11))
					next_state = FC_PRE_BIAS;
				else
					next_state = FC_SAVE_OUTPUTS_MACS;
			FC_PRE_ACCUMULATE_MACS: next_state = FC_ADDER_TREE_0;
			FC_ACCUMULATE_MACS:
				if (counter_accumulation_pes != (parameters_N_DIM_ARRAY - 1))
					next_state = FC_ACCUMULATE_MACS;
				else
					next_state = FC_PRE_BIAS;
			FC_PRE_BIAS: next_state = FC_BIAS;
			FC_BIAS: next_state = FC_SAVE_OUTPUTS_MACS;
			FC_SAVE_OUTPUTS_MACS:
				if (FC_FINISHED_K_LOOP)
					next_state = FINISHED_LAYER;
				else if (CONF_STR_SPARSITY == 0)
					next_state = FC_PRE_MAC;
				else if (sparse_val[0] == 0)
					next_state = FC_PRE_MAC;
				else
					next_state = STR_SPARSITY;
			ACTIVATION:
				if (!finished_activation)
					next_state = ACTIVATION;
				else
					next_state = FINISHED_LAYER;
			EWS_PRE_MAC:
				if (EWS_FINISHED)
					next_state = FINISHED_LAYER;
				else
					next_state = EWS_MAC_0;
			EWS_MAC_0: next_state = EWS_MAC_1;
			EWS_MAC_1: next_state = EWS_SAVE_MAC;
			EWS_SAVE_MAC: next_state = EWS_PRE_MAC;
			FINISHED_LAYER: next_state = INITIAL;
			default: next_state = state;
		endcase
	end
	localparam integer parameters_N_DIM_ARRAY_LOG = 2;
	always @(*) begin
		write_l2_l1 = CONF_WRITE_L2_L1;
		OUTPUT_TILE_SIZE = CONF_OUTPUT_CHANNEL_SIZE;
		WEIGHT_TILE_SIZE = CONF_WEIGHT_TILE_SIZE;
		NB_INPUT_TILE = 0;
		NB_WEIGHT_TILE = CONF_NB_WEIGHT_TILE;
		passing_data_between_pes_cnn = 0;
		use_adder_tree = 0;
		reinitialize_padding = 0;
		padd_zeros_left = CONF_ZERO_PADDING_X_left;
		padd_zeros_right = 0;
		enable_BUFFERED_OUTPUT = 0;
		INPUT_PRECISION = CONF_INPUT_PRECISION[1:0];
		OUTPUT_PRECISION = CONF_OUTPUT_PRECISION[1:0];
		PADDED_C_X = CONF_PADDED_C_X;
		PADDED_O_X = CONF_O_X;
		NUMBER_OF_ACTIVATION_CYCLES = CONF_C;
		SPARSITY = CONF_STR_SPARSITY;
		CONF_K_o = CONF_K;
		mode = CONF_MODE;
		causal_convolution = CONF_CAUSAL_CONVOLUTION[0];
		SHIFT_FIXED_POINT = CONF_SHIFT_FIXED_POINT[7:0];
		finished_layer = 0;
		enable_input_fifo = 0;
		loading_in_parallel = 0;
		input_memory_pointer = CONF_INPUT_MEMORY_POINTER;
		output_memory_pointer = CONF_OUTPUT_MEMORY_POINTER;
		clear = 0;
		enable_pe_array = 0;
		enable_nonlinear_block = 0;
		input_channel_rd_addr = 0;
		input_channel_rd_en = 0;
		weight_rd_addr = 0;
		weight_rd_en = 0;
		wr_en_output_buffer = 0;
		enable_pooling = 0;
		enable_sig_tanh = 0;
		type_nonlinear_function = CONF_TYPE_NONLINEAR_FUNCTION;
		shift_input_buffer = CONF_DILATION;
		FIFO_TCN_total_blocks = CONF_TCN_TOTAL_BLOCKS;
		FIFO_TCN_block_size = CONF_TCN_BLOCK_SIZE;
		wr_addr = 0;
		enable_bias_32bits = 0;
		addr_bias_32bits = 0;
		for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
			for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
				CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
		case (state)
			INITIAL: begin
				enable_input_fifo = 0;
				loading_in_parallel = 0;
				clear = 1;
				enable_pe_array = 0;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = 0;
				input_channel_rd_en = 0;
				weight_rd_addr = 0;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
			end
			STR_SPARSITY: begin
				enable_input_fifo = 0;
				loading_in_parallel = 0;
				clear = 0;
				enable_pe_array = 0;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = 0;
				input_channel_rd_en = 0;
				weight_rd_addr = 0;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
			end
			CONV_FILLING_INPUT_FIFO: begin
				enable_input_fifo = 0;
				loading_in_parallel = 1;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 1;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
				if (counter_X == 0)
					reinitialize_padding = 1;
			end
			CONV_PADDING_FILLING_INPUT_FIFO: begin
				enable_input_fifo = 0;
				loading_in_parallel = 0;
				clear = 1;
				enable_pe_array = 0;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 1;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
			end
			CONV_PRE_MAC: begin
				loading_in_parallel = 0;
				enable_input_fifo = 1;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 1;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 1;
				wr_en_output_buffer = 0;
			end
			CONV_PRE_MAC_2: begin
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_en = 1;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 1;
				wr_en_output_buffer = 0;
				loading_in_parallel = 0;
				enable_input_fifo = 1;
				clear = 0;
				enable_pe_array = 1;
				input_channel_rd_addr = counter_input_channel_address + parameters_N_DIM_ARRAY;
			end
			CONV_MAC: begin
				clear = 0;
				enable_pe_array = 1;
				weight_rd_addr = counter_weight_address;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000100000;
				if (counter_input_buffer_loading != (CONF_FX - 2)) begin
					input_channel_rd_addr = counter_input_channel_address;
					input_channel_rd_en = 1;
				end
				else begin
					input_channel_rd_addr = 0;
					input_channel_rd_en = 0;
				end
				if (next_state == CONV_PRE_MAC_2) begin
					weight_rd_en = 0;
					input_channel_rd_addr = next_counter_input_channel_address;
					input_channel_rd_en = 1;
					loading_in_parallel = 1;
					enable_input_fifo = 0;
				end
				else begin
					weight_rd_en = 1;
					loading_in_parallel = 0;
					enable_input_fifo = 1;
				end
				wr_en_output_buffer = 0;
			end
			CONV_ADD_BIAS: begin
				loading_in_parallel = 0;
				enable_input_fifo = 0;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000101100000;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 1;
				wr_en_output_buffer = 0;
			end
			CONV_ADD_BIAS_ACC: begin
				loading_in_parallel = 0;
				enable_input_fifo = 0;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				if (BIAS_ACC_FINISHED)
					weight_rd_en = 0;
				else
					weight_rd_en = 1;
				wr_en_output_buffer = 0;
				enable_bias_32bits = 1;
				addr_bias_32bits = counter_acc_cnn_bias;
			end
			CONV_ADD_BIAS_OPERATION: begin
				loading_in_parallel = 0;
				enable_input_fifo = 0;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000010000001100000;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
				enable_bias_32bits = 0;
				addr_bias_32bits = 0;
			end
			CONV_ADD_BIAS_SHIFTING: begin
				loading_in_parallel = 0;
				enable_input_fifo = 0;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000100000010;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
				enable_bias_32bits = 0;
				addr_bias_32bits = 0;
			end
			CONV_PRE_PASSING_OUTPUTS_VERTICAL: begin
				passing_data_between_pes_cnn = 1;
				if ((counter_X == 0) || ((counter_X == (CONF_O_X - 1)) && (counter_Y == CONF_O_Y)))
					padd_zeros_right = CONF_ZERO_PADDING_X_right;
				if (CONF_OUTPUT_PRECISION == 0)
					enable_BUFFERED_OUTPUT = 0;
				else
					enable_BUFFERED_OUTPUT = 1;
				loading_in_parallel = 0;
				enable_input_fifo = 0;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						if (CONF_ACTIVATION_FUNCTION == 1)
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000110;
						else
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				if (counter_K == 0)
					wr_addr = ((counter_output_channel_address + ((counter_accumulation_pes >> CONF_OUTPUT_PRECISION) * CONF_OUTPUT_CHANNEL_SIZE)) + (((CONF_K - 1) * (CONF_OUTPUT_CHANNEL_SIZE >> CONF_OUTPUT_PRECISION)) << parameters_N_DIM_ARRAY_LOG)) >> parameters_N_DIM_ARRAY_LOG;
				else
					wr_addr = ((counter_output_channel_address + ((counter_accumulation_pes >> CONF_OUTPUT_PRECISION) * CONF_OUTPUT_CHANNEL_SIZE)) + (((counter_K - 1) * (CONF_OUTPUT_CHANNEL_SIZE >> CONF_OUTPUT_PRECISION)) << parameters_N_DIM_ARRAY_LOG)) >> parameters_N_DIM_ARRAY_LOG;
				if (CONF_OUTPUT_PRECISION == 0)
					wr_en_output_buffer = 1;
				else if (CONF_OUTPUT_PRECISION == 1) begin
					if (counter_accumulation_pes[0] == 1)
						wr_en_output_buffer = 1;
					else
						wr_en_output_buffer = 0;
				end
				else if (counter_accumulation_pes[1:0] == 2'b11)
					wr_en_output_buffer = 1;
				else
					wr_en_output_buffer = 0;
			end
			CONV_PASSING_OUTPUTS_VERTICAL: begin
				passing_data_between_pes_cnn = 1;
				if ((counter_X == 0) || ((counter_X == (CONF_O_X - 1)) && (counter_Y == CONF_O_Y)))
					padd_zeros_right = CONF_ZERO_PADDING_X_right;
				if (CONF_OUTPUT_PRECISION == 0)
					enable_BUFFERED_OUTPUT = 0;
				else
					enable_BUFFERED_OUTPUT = 1;
				loading_in_parallel = 0;
				enable_input_fifo = 0;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						if (CONF_ACTIVATION_FUNCTION == 1)
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000100000000110;
						else
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 13'b0100000000010;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				if (counter_K == 0)
					wr_addr = ((counter_output_channel_address + ((counter_accumulation_pes >> CONF_OUTPUT_PRECISION) * CONF_OUTPUT_CHANNEL_SIZE)) + (((CONF_K - 1) * (CONF_OUTPUT_CHANNEL_SIZE >> CONF_OUTPUT_PRECISION)) << parameters_N_DIM_ARRAY_LOG)) >> parameters_N_DIM_ARRAY_LOG;
				else
					wr_addr = ((counter_output_channel_address + ((counter_accumulation_pes >> CONF_OUTPUT_PRECISION) * CONF_OUTPUT_CHANNEL_SIZE)) + (((counter_K - 1) * (CONF_OUTPUT_CHANNEL_SIZE >> CONF_OUTPUT_PRECISION)) << parameters_N_DIM_ARRAY_LOG)) >> parameters_N_DIM_ARRAY_LOG;
				if (CONF_OUTPUT_PRECISION == 0)
					wr_en_output_buffer = 1;
				else if (CONF_OUTPUT_PRECISION == 1) begin
					if (counter_accumulation_pes[0] == 1)
						wr_en_output_buffer = 1;
					else
						wr_en_output_buffer = 0;
				end
				else if (counter_accumulation_pes[1:0] == 2'b11)
					wr_en_output_buffer = 1;
				else
					wr_en_output_buffer = 0;
			end
			CONV_CLEAR_MAC: begin
				loading_in_parallel = 0;
				enable_input_fifo = 0;
				clear = 1;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_input_channel_address;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
			end
			FC_PRE_MAC: begin
				if (counter_C == 0)
					clear = 1;
				else
					clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 1;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 1;
				wr_en_output_buffer = 0;
				enable_input_fifo = 0;
				loading_in_parallel = 0;
			end
			FC_MAC: begin
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000100000;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 1;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 1;
				wr_en_output_buffer = 0;
				enable_input_fifo = 0;
				loading_in_parallel = 0;
			end
			FC_PRE_ACCUMULATE_MACS: begin
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000100000;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
				enable_input_fifo = 0;
				loading_in_parallel = 0;
			end
			FC_ADDER_TREE_0: begin
				clear = 0;
				enable_pe_array = 1;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 0;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						if (j == 0)
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b100000001010000001;
						else
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000001000000000;
				wr_en_output_buffer = 0;
				enable_input_fifo = 0;
				loading_in_parallel = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
			end
			FC_ACCUMULATE_MACS: begin
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						if (j == 0)
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000100001;
						else
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000001000001000;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 0;
				wr_en_output_buffer = 0;
				enable_input_fifo = 0;
				loading_in_parallel = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
			end
			FC_PRE_BIAS: begin
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 1;
				wr_en_output_buffer = 0;
				enable_input_fifo = 0;
				loading_in_parallel = 0;
			end
			FC_BIAS: begin
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						if (j == 0)
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000010000001100000;
						else
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				wr_en_output_buffer = 0;
				enable_input_fifo = 0;
				loading_in_parallel = 0;
			end
			FC_SAVE_OUTPUTS_MACS: begin
				use_adder_tree = 1;
				if (CONF_OUTPUT_PRECISION == 0)
					enable_BUFFERED_OUTPUT = 0;
				else
					enable_BUFFERED_OUTPUT = 1;
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					for (j = 0; j < parameters_N_DIM_ARRAY; j = j + 1)
						if (CONF_ACTIVATION_FUNCTION == 0)
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000100000000000010;
						else
							CR_PE_array[((i * parameters_N_DIM_ARRAY) + j) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000100000000000110;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 0;
				weight_rd_addr = counter_weight_address;
				weight_rd_en = 0;
				if (CONF_OUTPUT_PRECISION == 0)
					wr_en_output_buffer = 1;
				else if (CONF_OUTPUT_PRECISION == 1) begin
					if (counter_K[0] == 1)
						wr_en_output_buffer = 1;
					else
						wr_en_output_buffer = 0;
				end
				else if (counter_K[1:0] == 2'b11)
					wr_en_output_buffer = 1;
				else
					wr_en_output_buffer = 0;
				enable_input_fifo = 0;
				loading_in_parallel = 0;
				wr_addr = counter_K >> CONF_OUTPUT_PRECISION;
			end
			ACTIVATION: begin
				enable_nonlinear_block = 1;
				enable_sig_tanh = 0;
				enable_pooling = 0;
				case (type_nonlinear_function)
					0: enable_sig_tanh = 1;
					1: enable_pooling = 1;
					2: enable_pooling = 1;
					3: enable_sig_tanh = 1;
					4: enable_sig_tanh = 1;
				endcase
			end
			EWS_PRE_MAC: begin
				clear = 1;
				enable_pe_array = 1;
				input_memory_pointer = CONF_INPUT_MEMORY_POINTER;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					CR_PE_array[(0 + i) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000000000010;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 1;
				wr_en_output_buffer = 0;
			end
			EWS_MAC_0: begin
				clear = 0;
				enable_pe_array = 1;
				input_memory_pointer = weight_memory_pointer;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					CR_PE_array[(0 + i) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000001000000100000;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 1;
				wr_en_output_buffer = 0;
			end
			EWS_MAC_1: begin
				clear = 0;
				enable_pe_array = 1;
				if (CONF_TYPE_NONLINEAR_FUNCTION == 0) begin
					for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
						CR_PE_array[(0 + i) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000001000000100000;
				end
				else
					for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
						CR_PE_array[(0 + i) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000000000010010000;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 0;
				wr_en_output_buffer = 0;
			end
			EWS_SAVE_MAC: begin
				clear = 0;
				enable_pe_array = 1;
				for (i = 0; i < parameters_N_DIM_ARRAY; i = i + 1)
					CR_PE_array[(0 + i) * parameters_NUMBER_OF_CR_SIGNALS+:parameters_NUMBER_OF_CR_SIGNALS] = 18'b000100001000000010;
				input_channel_rd_addr = counter_C;
				input_channel_rd_en = 0;
				wr_en_output_buffer = 1;
				wr_addr = counter_C - 1;
			end
			FINISHED_LAYER: finished_layer = 1;
		endcase
	end
	always @(*) FIFO_TCN_update_pointer = finished_network && EXECUTION_FRAME_BY_FRAME;
endmodule
