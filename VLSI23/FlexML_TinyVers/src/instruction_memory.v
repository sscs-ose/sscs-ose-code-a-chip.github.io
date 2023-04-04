module instruction_memory (
	clk,
	reset,
	PC,
	wr_addr_ext_im,
	wr_data_ext_im,
	wr_en_ext_im,
	instruction
);
	input clk;
	input reset;
	input wr_en_ext_im;
	localparam integer parameters_BIT_WIDTH_EXTERNAL_PORT = 32;
	input [parameters_BIT_WIDTH_EXTERNAL_PORT - 1:0] wr_addr_ext_im;
	input [parameters_BIT_WIDTH_EXTERNAL_PORT - 1:0] wr_data_ext_im;
	input [31:0] PC;
	localparam integer parameters_INSTRUCTION_MEMORY_FIELDS = 32;
	localparam integer parameters_INSTRUCTION_MEMORY_WIDTH = 32;
	output wire [(parameters_INSTRUCTION_MEMORY_FIELDS * parameters_INSTRUCTION_MEMORY_WIDTH) - 1:0] instruction;
	localparam integer parameters_INSTRUCTION_MEMORY_SIZE = 2;
	reg [(parameters_INSTRUCTION_MEMORY_FIELDS * parameters_INSTRUCTION_MEMORY_WIDTH) - 1:0] instruction_memory [parameters_INSTRUCTION_MEMORY_SIZE - 1:0];
	reg [parameters_INSTRUCTION_MEMORY_WIDTH - 1:0] im_file [0:(parameters_INSTRUCTION_MEMORY_SIZE * parameters_INSTRUCTION_MEMORY_FIELDS) - 1];
	integer i;
	integer l;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (i = 0; i < parameters_INSTRUCTION_MEMORY_SIZE; i = i + 1)
				for (l = 0; l < parameters_INSTRUCTION_MEMORY_FIELDS; l = l + 1)
					instruction_memory[i][l * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH] <= 0;
		end
		else if (wr_en_ext_im)
			instruction_memory[wr_addr_ext_im[31:5]][wr_addr_ext_im[4:0] * parameters_INSTRUCTION_MEMORY_WIDTH+:parameters_INSTRUCTION_MEMORY_WIDTH] <= wr_data_ext_im;
	assign instruction = instruction_memory[PC];
endmodule
