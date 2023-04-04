module encoder_FIFO (
	clk,
	reset,
	input_rd_address,
	input_wr_address,
	rd_enable,
	wr_enable,
	FIFO_TCN_total_blocks,
	FIFO_TCN_block_size,
	FIFO_TCN_active,
	FIFO_TCN_update_pointer,
	output_rd_address,
	output_wr_address
);
	input clk;
	input reset;
	localparam integer parameters_TOTAL_ACTIVATION_MEMORY_SIZE = 16384;
	localparam integer parameters_INPUT_CHANNEL_ADDR_SIZE = 14;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] input_wr_address;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] input_rd_address;
	input rd_enable;
	input wr_enable;
	input [31:0] FIFO_TCN_block_size;
	input [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] FIFO_TCN_total_blocks;
	input FIFO_TCN_active;
	input FIFO_TCN_update_pointer;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] output_rd_address;
	output reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] output_wr_address;
	reg [15:0] rd_FIFO_TCN_block_size;
	reg [15:0] wr_FIFO_TCN_block_size;
	wire [16:1] sv2v_tmp_D3052;
	assign sv2v_tmp_D3052 = FIFO_TCN_block_size[15:0];
	always @(*) rd_FIFO_TCN_block_size = sv2v_tmp_D3052;
	wire [16:1] sv2v_tmp_C88D5;
	assign sv2v_tmp_C88D5 = FIFO_TCN_block_size[31:16];
	always @(*) wr_FIFO_TCN_block_size = sv2v_tmp_C88D5;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] FIFO_pointer;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_current_address_pointer_counter;
	reg [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_current_address_pointer_counter;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] total_size_buffer;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_total_size_buffer;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_total_size_buffer;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] rd_diff;
	wire [parameters_INPUT_CHANNEL_ADDR_SIZE - 1:0] wr_diff;
	reg FIFO_TCN_update_pointer_reg;
	assign rd_total_size_buffer = FIFO_TCN_total_blocks * rd_FIFO_TCN_block_size;
	assign wr_total_size_buffer = FIFO_TCN_total_blocks * wr_FIFO_TCN_block_size;
	assign rd_diff = rd_total_size_buffer - rd_current_address_pointer_counter;
	assign wr_diff = wr_total_size_buffer - wr_current_address_pointer_counter;
	always @(*) begin
		rd_current_address_pointer_counter = FIFO_pointer * rd_FIFO_TCN_block_size;
		wr_current_address_pointer_counter = FIFO_pointer * wr_FIFO_TCN_block_size;
	end
	always @(*)
		if (FIFO_TCN_active == 0) begin
			output_rd_address = input_rd_address;
			output_wr_address = input_wr_address;
		end
		else begin
			if ((input_rd_address + (rd_total_size_buffer - rd_current_address_pointer_counter)) < rd_total_size_buffer)
				output_rd_address = input_rd_address + (rd_total_size_buffer - rd_current_address_pointer_counter);
			else
				output_rd_address = input_rd_address - rd_current_address_pointer_counter;
			if ((input_wr_address + (wr_total_size_buffer - wr_current_address_pointer_counter)) < wr_total_size_buffer)
				output_wr_address = input_wr_address + (wr_total_size_buffer - wr_current_address_pointer_counter);
			else
				output_wr_address = input_wr_address - wr_current_address_pointer_counter;
		end
	always @(posedge clk or negedge reset)
		if (!reset)
			FIFO_TCN_update_pointer_reg <= 0;
		else
			FIFO_TCN_update_pointer_reg <= FIFO_TCN_update_pointer;
	always @(posedge clk or negedge reset)
		if (!reset)
			FIFO_pointer <= 0;
		else if (FIFO_TCN_update_pointer_reg)
			if (FIFO_pointer == (FIFO_TCN_total_blocks - 1))
				FIFO_pointer <= 0;
			else
				FIFO_pointer <= FIFO_pointer + 1;
endmodule
