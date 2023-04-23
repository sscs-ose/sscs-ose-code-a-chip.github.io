module configuration_registers (
	clk,
	reset,
	wr_en_ext,
	wr_addr_ext,
	wr_data_ext,
	MEMORY_POINTER_FC,
	EXECUTION_FRAME_BY_FRAME,
	FIRST_INDEX_FC_LOG
);
	input clk;
	input reset;
	input wr_en_ext;
	input [31:0] wr_addr_ext;
	input [31:0] wr_data_ext;
	output reg [31:0] MEMORY_POINTER_FC;
	output reg [31:0] FIRST_INDEX_FC_LOG;
	output reg [31:0] EXECUTION_FRAME_BY_FRAME;
	localparam integer parameters_CONF_REGISTERS_SIZE = 32;
	reg [31:0] conf_file [0:parameters_CONF_REGISTERS_SIZE - 1];
	integer i;
	wire [32:1] sv2v_tmp_94321;
	assign sv2v_tmp_94321 = conf_file[0];
	always @(*) MEMORY_POINTER_FC = sv2v_tmp_94321;
	wire [32:1] sv2v_tmp_E8DDA;
	assign sv2v_tmp_E8DDA = conf_file[1];
	always @(*) FIRST_INDEX_FC_LOG = sv2v_tmp_E8DDA;
	wire [32:1] sv2v_tmp_F4E0B;
	assign sv2v_tmp_F4E0B = conf_file[2];
	always @(*) EXECUTION_FRAME_BY_FRAME = sv2v_tmp_F4E0B;
	always @(posedge clk or negedge reset)
		if (!reset) begin
			for (i = 0; i < parameters_CONF_REGISTERS_SIZE; i = i + 1)
				conf_file[i] <= 0;
		end
		else if (wr_en_ext)
			conf_file[wr_addr_ext] <= wr_data_ext;
endmodule
