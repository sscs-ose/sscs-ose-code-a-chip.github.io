// This file is generated from the original systemverilog RTL with sv2v 
module config_registers (
	clk,
	rst,
	instr_stream_start_addr_io,
	instr_stream_end_addr_io,
	ld_stream_start_addr_io,
	ld_stream_end_addr_io,
	st_stream_start_addr_io,
	st_stream_end_addr_io,
	precision_config,
	config_local_mem_slp,
	config_local_mem_sd,
	config_global_mem_slp,
	config_global_mem_sd,
	config_stream_instr_slp,
	config_stream_ld_slp,
	config_stream_st_slp,
	config_stream_instr_sd,
	config_stream_ld_sd,
	config_stream_st_sd,
	data_in,
	data_out,
	shift_en
);
	parameter CONFIG_L = 32;
	input clk;
	input rst;
	localparam hw_pkg_N_PE = 2;
	localparam stream_pkg_INSTR_STR_ADDR_L = 10;
	output wire [19:0] instr_stream_start_addr_io;
	output wire [19:0] instr_stream_end_addr_io;
	localparam stream_pkg_LD_STR_ADDR_L = 10;
	output wire [19:0] ld_stream_start_addr_io;
	output wire [19:0] ld_stream_end_addr_io;
	localparam stream_pkg_ST_STR_ADDR_L = 10;
	output wire [19:0] st_stream_start_addr_io;
	output wire [19:0] st_stream_end_addr_io;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	output wire [1:0] precision_config;
	output wire [1:0] config_local_mem_slp;
	output wire [1:0] config_local_mem_sd;
	output wire [1:0] config_global_mem_slp;
	output wire [1:0] config_global_mem_sd;
	output wire [1:0] config_stream_instr_slp;
	output wire [1:0] config_stream_ld_slp;
	output wire [1:0] config_stream_st_slp;
	output wire [1:0] config_stream_instr_sd;
	output wire [1:0] config_stream_ld_sd;
	output wire [1:0] config_stream_st_sd;
	input [CONFIG_L - 1:0] data_in;
	output wire [CONFIG_L - 1:0] data_out;
	input shift_en;
	localparam N_REG = 13 + ((hw_pkg_N_PE / CONFIG_L) * 10);
	localparam PRECISION_CONFIG_REG_I = 12;
	reg [(N_REG * CONFIG_L) - 1:0] shift_reg;
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			shift_reg <= 1'sb0;
		else if (shift_en) begin
			shift_reg[0+:CONFIG_L] <= data_in;
			begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i < N_REG; i = i + 1)
					shift_reg[i * CONFIG_L+:CONFIG_L] <= shift_reg[(i - 1) * CONFIG_L+:CONFIG_L];
			end
		end
	genvar i;
	generate
		for (i = 0; i < hw_pkg_N_PE; i = i + 1) begin : config_loog
			assign instr_stream_start_addr_io[i * 10+:10] = shift_reg[((i * 6) + 0) * CONFIG_L+:CONFIG_L];
			assign instr_stream_end_addr_io[i * 10+:10] = shift_reg[((i * 6) + 1) * CONFIG_L+:CONFIG_L];
			assign ld_stream_start_addr_io[i * 10+:10] = shift_reg[((i * 6) + 2) * CONFIG_L+:CONFIG_L];
			assign ld_stream_end_addr_io[i * 10+:10] = shift_reg[((i * 6) + 3) * CONFIG_L+:CONFIG_L];
			assign st_stream_start_addr_io[i * 10+:10] = shift_reg[((i * 6) + 4) * CONFIG_L+:CONFIG_L];
			assign st_stream_end_addr_io[i * 10+:10] = shift_reg[((i * 6) + 5) * CONFIG_L+:CONFIG_L];
		end
	endgenerate
	assign precision_config = shift_reg[PRECISION_CONFIG_REG_I * CONFIG_L+:CONFIG_L];
	assign config_local_mem_slp = 0;
	assign config_local_mem_slp = 0;
	assign config_local_mem_sd = 0;
	assign config_local_mem_sd = 0;
	assign config_global_mem_slp = 0;
	assign config_global_mem_slp = 0;
	assign config_global_mem_sd = 0;
	assign config_global_mem_sd = 0;
	assign config_stream_instr_slp = 0;
	assign config_stream_instr_slp = 0;
	assign config_stream_ld_slp = 0;
	assign config_stream_ld_slp = 0;
	assign config_stream_st_slp = 0;
	assign config_stream_st_slp = 0;
	assign config_stream_instr_sd = 0;
	assign config_stream_instr_sd = 0;
	assign config_stream_ld_sd = 0;
	assign config_stream_ld_sd = 0;
	assign config_stream_st_sd = 0;
	assign config_stream_st_sd = 0;
	assign data_out = shift_reg[(N_REG - 1) * CONFIG_L+:CONFIG_L];
endmodule
module io_mem_access (
	clk,
	rst,
	in,
	wr_en,
	rd_en,
	init_global_mem_addr,
	init_global_mem_vld,
	init_global_mem_wr_en,
	init_global_mem_wr_data,
	init_global_mem_rd_data,
	init_global_mem_rd_data_vld,
	init_local_mem_addr,
	init_local_mem_vld,
	init_local_mem_wr_en,
	init_local_mem_wr_data,
	init_local_mem_rd_data,
	init_local_mem_rd_data_vld,
	init_stream_wr_data,
	init_stream_addr,
	init_stream_wr_vld,
	init_stream_rd_vld,
	init_stream_rd_data,
	init_stream_rd_data_vld,
	out
);
	input clk;
	input rst;
	localparam periphery_pkg_INPUT_REG_L = 64;
	input [63:0] in;
	input wr_en;
	input rd_en;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	output wire [11:0] init_global_mem_addr;
	output wire init_global_mem_vld;
	output wire init_global_mem_wr_en;
	localparam hw_pkg_DATA_L = 32;
	output wire [31:0] init_global_mem_wr_data;
	input [31:0] init_global_mem_rd_data;
	input init_global_mem_rd_data_vld;
	localparam hw_pkg_LOCAL_MEM_ADDR_L = 9;
	output wire [8:0] init_local_mem_addr;
	output wire [1:0] init_local_mem_vld;
	output wire [1:0] init_local_mem_wr_en;
	output wire [31:0] init_local_mem_wr_data;
	input [63:0] init_local_mem_rd_data;
	input [1:0] init_local_mem_rd_data_vld;
	output wire [31:0] init_stream_wr_data;
	localparam stream_pkg_INSTR_STR_ADDR_L = 10;
	output wire [12:0] init_stream_addr;
	output wire init_stream_wr_vld;
	output wire init_stream_rd_vld;
	input [31:0] init_stream_rd_data;
	input init_stream_rd_data_vld;
	localparam periphery_pkg_OUTPUT_DATA_L = 32;
	output wire [31:0] out;
	wire [31:0] in_data;
	wire [31:0] in_addr;
	assign in_data = in[0+:hw_pkg_DATA_L];
	assign in_addr = in[hw_pkg_DATA_L+:hw_pkg_DATA_L];
	reg [31:0] out_pre;
	wire is_global;
	wire is_local;
	wire is_stream;
	wire [0:0] local_bank_id;
	reg [1:0] init_local_mem_vld_pre;
	reg [1:0] init_local_mem_wr_en_pre;
	assign local_bank_id = in_addr[hw_pkg_LOCAL_MEM_ADDR_L+:1];
	localparam periphery_pkg_ADDR_TYPE_GLOBAL = 1;
	localparam periphery_pkg_ADDR_TYPE_L = 2;
	assign is_global = (in_addr[31-:periphery_pkg_ADDR_TYPE_L] == periphery_pkg_ADDR_TYPE_GLOBAL ? 1'b1 : 1'b0);
	localparam periphery_pkg_ADDR_TYPE_LOCAL = 2;
	assign is_local = (in_addr[31-:periphery_pkg_ADDR_TYPE_L] == periphery_pkg_ADDR_TYPE_LOCAL ? 1'b1 : 1'b0);
	localparam periphery_pkg_ADDR_TYPE_STREAM = 0;
	assign is_stream = (in_addr[31-:periphery_pkg_ADDR_TYPE_L] == periphery_pkg_ADDR_TYPE_STREAM ? 1'b1 : 1'b0);
	always @(*) begin
		out_pre = init_global_mem_rd_data;
		begin : sv2v_autoblock_1
			integer i;
			for (i = 1; i >= 0; i = i - 1)
				if (init_local_mem_rd_data_vld[i] == 1)
					out_pre = init_local_mem_rd_data[i * 32+:32];
		end
		if (init_global_mem_rd_data_vld)
			out_pre = init_global_mem_rd_data;
		if (init_stream_rd_data_vld)
			out_pre = init_stream_rd_data;
	end
	always @(*) begin
		init_local_mem_vld_pre = 1'sb0;
		init_local_mem_wr_en_pre = 1'sb0;
		init_local_mem_wr_en_pre[local_bank_id] = (is_local ? wr_en : 1'b0);
		init_local_mem_vld_pre[local_bank_id] = (is_local ? wr_en | rd_en : 1'b0);
	end
	assign init_global_mem_wr_data = in_data;
	assign init_local_mem_wr_data = in_data;
	assign init_global_mem_addr = in_addr;
	assign init_local_mem_addr = in_addr;
	assign out = out_pre;
	assign init_global_mem_wr_en = (is_global ? wr_en : 1'b0);
	assign init_global_mem_vld = (is_global ? wr_en | rd_en : 1'b0);
	assign init_local_mem_vld = init_local_mem_vld_pre;
	assign init_local_mem_wr_en = init_local_mem_wr_en_pre;
	assign init_stream_wr_data = in_data;
	assign init_stream_addr = in_addr;
	assign init_stream_wr_vld = (is_stream ? wr_en : 1'b0);
	assign init_stream_rd_vld = (is_stream ? rd_en : 1'b0);
endmodule
module io_registers (
	clk,
	rst,
	in,
	shift_en,
	reg_data
);
	input clk;
	input rst;
	localparam periphery_pkg_INPUT_DATA_L = 16;
	input [15:0] in;
	input shift_en;
	localparam periphery_pkg_INPUT_REG_L = 64;
	output wire [63:0] reg_data;
	localparam MULTIPLE_FACTOR = 4;
	reg [63:0] reg_data_q;
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			reg_data_q <= 1'sb0;
		else if (shift_en) begin
			reg_data_q[0+:periphery_pkg_INPUT_DATA_L] <= in;
			begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i < MULTIPLE_FACTOR; i = i + 1)
					reg_data_q[i * periphery_pkg_INPUT_DATA_L+:periphery_pkg_INPUT_DATA_L] <= reg_data_q[(i - 1) * periphery_pkg_INPUT_DATA_L+:periphery_pkg_INPUT_DATA_L];
			end
		end
	assign reg_data = reg_data_q;
endmodule
module io_monitor (
	reg_data,
	global_rd_req,
	global_rd_gnt,
	global_wr_req,
	global_wr_gnt,
	instr_stream_req,
	instr_stream_gnt,
	ld_stream_req,
	ld_stream_gnt,
	st_stream_req,
	st_stream_gnt,
	pe_out,
	instr,
	out
);
	localparam periphery_pkg_INPUT_REG_L = 64;
	input [63:0] reg_data;
	localparam hw_pkg_N_PE = 2;
	input [1:0] global_rd_req;
	input [1:0] global_rd_gnt;
	input [1:0] global_wr_req;
	input [1:0] global_wr_gnt;
	input [1:0] instr_stream_req;
	input [1:0] instr_stream_gnt;
	input [1:0] ld_stream_req;
	input [1:0] ld_stream_gnt;
	input [1:0] st_stream_req;
	input [1:0] st_stream_gnt;
	localparam hw_pkg_DATA_L = 32;
	input [63:0] pe_out;
	localparam hw_pkg_OPCODE_L = 4;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam hw_pkg_INSTR_L = 22;
	input [43:0] instr;
	output wire [31:0] out;
	reg [31:0] out_pre;
	localparam periphery_pkg_MONITOR_OPCODE_L = 5;
	wire [4:0] monitor_opcode;
	assign monitor_opcode = reg_data[0+:periphery_pkg_MONITOR_OPCODE_L];
	always @(*) out_pre = global_rd_req[0+:hw_pkg_DATA_L];
	assign out = out_pre;
endmodule
module io_decode (
	io_opcode,
	config_shift_en,
	rd_en,
	wr_en,
	monitor,
	reg_shift_en
);
	localparam periphery_pkg_IO_OPCODE_L = 4;
	input [3:0] io_opcode;
	output wire config_shift_en;
	output wire rd_en;
	output wire wr_en;
	output wire monitor;
	output wire reg_shift_en;
	reg config_shift_en_pre;
	reg rd_en_pre;
	reg wr_en_pre;
	reg monitor_pre;
	reg reg_shift_en_pre;
	localparam periphery_pkg_IO_OPCODE_CONFIG_SHIFT_EN = 3;
	localparam periphery_pkg_IO_OPCODE_MONITOR = 4;
	localparam periphery_pkg_IO_OPCODE_NOP = 0;
	localparam periphery_pkg_IO_OPCODE_RD_EN = 1;
	localparam periphery_pkg_IO_OPCODE_REG_SHIFT_EN = 5;
	localparam periphery_pkg_IO_OPCODE_WR_EN = 2;
	always @(*)
		case (io_opcode)
			periphery_pkg_IO_OPCODE_NOP: begin
				config_shift_en_pre = 0;
				rd_en_pre = 0;
				wr_en_pre = 0;
				monitor_pre = 0;
				reg_shift_en_pre = 0;
			end
			periphery_pkg_IO_OPCODE_RD_EN: begin
				config_shift_en_pre = 0;
				rd_en_pre = 1;
				wr_en_pre = 0;
				monitor_pre = 0;
				reg_shift_en_pre = 0;
			end
			periphery_pkg_IO_OPCODE_WR_EN: begin
				config_shift_en_pre = 0;
				rd_en_pre = 0;
				wr_en_pre = 1;
				monitor_pre = 0;
				reg_shift_en_pre = 0;
			end
			periphery_pkg_IO_OPCODE_CONFIG_SHIFT_EN: begin
				config_shift_en_pre = 1;
				rd_en_pre = 0;
				wr_en_pre = 0;
				monitor_pre = 0;
				reg_shift_en_pre = 0;
			end
			periphery_pkg_IO_OPCODE_MONITOR: begin
				config_shift_en_pre = 0;
				rd_en_pre = 0;
				wr_en_pre = 0;
				monitor_pre = 1;
				reg_shift_en_pre = 0;
			end
			periphery_pkg_IO_OPCODE_REG_SHIFT_EN: begin
				config_shift_en_pre = 0;
				rd_en_pre = 0;
				wr_en_pre = 0;
				monitor_pre = 0;
				reg_shift_en_pre = 1;
			end
			default: begin
				config_shift_en_pre = 0;
				rd_en_pre = 0;
				wr_en_pre = 0;
				monitor_pre = 0;
				reg_shift_en_pre = 0;
			end
		endcase
	assign config_shift_en = config_shift_en_pre;
	assign rd_en = rd_en_pre;
	assign wr_en = wr_en_pre;
	assign monitor = monitor_pre;
	assign reg_shift_en = reg_shift_en_pre;
endmodule
module interconnect_datapath (
	clk,
	rst,
	ld_mem_bank_id,
	ld_bank_addrs,
	ld_gnt,
	granted_requester_id,
	grant_out_port_wise,
	ld_data,
	ld_data_vld,
	st_addr,
	st_data,
	st_gnt,
	init_bank_id,
	init_bank_addr,
	init_mem_vld,
	init_mem_wr_en,
	init_mem_wr_data,
	init_mem_rd_data,
	init_mem_rd_data_vld,
	mem_addr,
	mem_wr_data,
	mem_wr_en,
	mem_rd_en,
	mem_rd_data
);
	input clk;
	input rst;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_N_GLOBAL_MEM_BANKS = hw_pkg_N_PE;
	input [1:0] ld_mem_bank_id;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	localparam interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L = 10;
	input [19:0] ld_bank_addrs;
	input [1:0] ld_gnt;
	input [1:0] granted_requester_id;
	input [1:0] grant_out_port_wise;
	localparam hw_pkg_DATA_L = 32;
	output wire [63:0] ld_data;
	output wire [1:0] ld_data_vld;
	input [19:0] st_addr;
	input [63:0] st_data;
	input [1:0] st_gnt;
	input [0:0] init_bank_id;
	input [9:0] init_bank_addr;
	input init_mem_vld;
	input init_mem_wr_en;
	input [31:0] init_mem_wr_data;
	output wire [31:0] init_mem_rd_data;
	output wire init_mem_rd_data_vld;
	output wire [19:0] mem_addr;
	output wire [63:0] mem_wr_data;
	output wire [1:0] mem_wr_en;
	output wire [1:0] mem_rd_en;
	input [63:0] mem_rd_data;
	wire [63:0] ld_data_pre;
	wire [1:0] ld_data_vld_pre;
	reg [1:0] init_mem_wr_en_decoded;
	reg [1:0] init_mem_vld_decoded;
	always @(*) begin
		init_mem_wr_en_decoded = 1'sb0;
		init_mem_vld_decoded = 1'sb0;
		init_mem_wr_en_decoded[init_bank_id] = init_mem_wr_en;
		init_mem_vld_decoded[init_bank_id] = init_mem_vld;
	end
	genvar bank_i;
	generate
		for (bank_i = 0; bank_i < hw_pkg_N_GLOBAL_MEM_BANKS; bank_i = bank_i + 1) begin : incoming_datapath_loop
			interconnect_incoming_datapath_per_bank INTERCONNECT_INCOMING_DATAPATH_PER_BANK_INS(
				.ld_bank_addrs(ld_bank_addrs),
				.granted_requester_id(granted_requester_id[bank_i+:1]),
				.grant_out_port_wise(grant_out_port_wise[bank_i]),
				.st_bank_addr(st_addr[bank_i * 10+:10]),
				.st_data(st_data[bank_i * 32+:32]),
				.st_gnt(st_gnt[bank_i]),
				.init_bank_addr(init_bank_addr),
				.init_mem_vld(init_mem_vld_decoded[bank_i]),
				.init_mem_wr_en(init_mem_wr_en_decoded[bank_i]),
				.init_mem_wr_data(init_mem_wr_data),
				.mem_addr(mem_addr[bank_i * 10+:10]),
				.mem_wr_data(mem_wr_data[bank_i * 32+:32]),
				.mem_wr_en(mem_wr_en[bank_i]),
				.mem_rd_en(mem_rd_en[bank_i])
			);
		end
	endgenerate
	genvar pe_i;
	generate
		for (pe_i = 0; pe_i < hw_pkg_N_PE; pe_i = pe_i + 1) begin : outgoing_datapath_loop
			interconnect_outgoing_datapath_per_pe INTERCONNECT_OUTGOING_DATAPATH_PER_PE_INS(
				.clk(clk),
				.rst(rst),
				.ld_mem_bank_id(ld_mem_bank_id[pe_i+:1]),
				.ld_gnt(ld_gnt[pe_i]),
				.mem_rd_data(mem_rd_data),
				.ld_data(ld_data_pre[pe_i * 32+:32]),
				.ld_data_vld(ld_data_vld_pre[pe_i])
			);
		end
	endgenerate
	interconnect_outgoing_datapath_init INTERCONNECT_OUTGOING_DATAPATH_INIT_INS(
		.clk(clk),
		.rst(rst),
		.mem_rd_data(mem_rd_data),
		.init_bank_id(init_bank_id),
		.init_mem_vld(init_mem_vld),
		.init_mem_wr_en(init_mem_wr_en),
		.init_mem_rd_data(init_mem_rd_data),
		.init_mem_rd_data_vld(init_mem_rd_data_vld)
	);
	assign ld_data = ld_data_pre;
	assign ld_data_vld = ld_data_vld_pre;
	always @(posedge clk) begin : sv2v_autoblock_1
		integer i;
		for (i = 0; i < hw_pkg_N_PE; i = i + 1)
			begin : sv2v_autoblock_2
				integer j;
				for (j = 0; j < hw_pkg_N_PE; j = j + 1)
					if (((i != j) && (ld_gnt[i] == 1)) && (ld_gnt[j] == 1))
						;
			end
	end
endmodule
module interconnect_incoming_datapath_per_bank (
	ld_bank_addrs,
	granted_requester_id,
	grant_out_port_wise,
	st_bank_addr,
	st_data,
	st_gnt,
	init_bank_addr,
	init_mem_vld,
	init_mem_wr_en,
	init_mem_wr_data,
	mem_addr,
	mem_wr_data,
	mem_wr_en,
	mem_rd_en
);
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	localparam hw_pkg_N_GLOBAL_MEM_BANKS = hw_pkg_N_PE;
	localparam interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L = 10;
	input [19:0] ld_bank_addrs;
	input [0:0] granted_requester_id;
	input grant_out_port_wise;
	input [9:0] st_bank_addr;
	localparam hw_pkg_DATA_L = 32;
	input [31:0] st_data;
	input st_gnt;
	input [9:0] init_bank_addr;
	input init_mem_vld;
	input init_mem_wr_en;
	input [31:0] init_mem_wr_data;
	output wire [9:0] mem_addr;
	output wire [31:0] mem_wr_data;
	output wire mem_wr_en;
	output wire mem_rd_en;
	reg [9:0] mem_addr_pre;
	reg mem_wr_en_pre;
	reg mem_rd_en_pre;
	reg [31:0] mem_wr_data_pre;
	always @(*) begin
		mem_wr_data_pre = st_data;
		if (init_mem_vld) begin
			mem_addr_pre = init_bank_addr;
			mem_wr_en_pre = init_mem_wr_en;
			mem_rd_en_pre = ~init_mem_wr_en;
			mem_wr_data_pre = init_mem_wr_data;
		end
		else if (st_gnt) begin
			mem_addr_pre = st_bank_addr;
			mem_wr_en_pre = 1;
			mem_rd_en_pre = 0;
		end
		else if (grant_out_port_wise) begin
			mem_addr_pre = ld_bank_addrs[granted_requester_id * 10+:10];
			mem_wr_en_pre = 0;
			mem_rd_en_pre = 1;
		end
		else begin
			mem_addr_pre = ld_bank_addrs[granted_requester_id * 10+:10];
			mem_wr_en_pre = 0;
			mem_rd_en_pre = 0;
		end
	end
	assign mem_wr_data = mem_wr_data_pre;
	assign mem_wr_en = mem_wr_en_pre;
	assign mem_rd_en = mem_rd_en_pre;
	assign mem_addr = mem_addr_pre;
endmodule
module interconnect_outgoing_datapath_init (
	clk,
	rst,
	mem_rd_data,
	init_bank_id,
	init_mem_vld,
	init_mem_wr_en,
	init_mem_rd_data,
	init_mem_rd_data_vld
);
	input clk;
	input rst;
	localparam hw_pkg_DATA_L = 32;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_N_GLOBAL_MEM_BANKS = hw_pkg_N_PE;
	input [63:0] mem_rd_data;
	input [0:0] init_bank_id;
	input init_mem_vld;
	input init_mem_wr_en;
	output wire [31:0] init_mem_rd_data;
	output wire init_mem_rd_data_vld;
	localparam interconnect_pkg_GLOBAL_MEM_RD_LATENCY = 1;
	localparam DELAY = interconnect_pkg_GLOBAL_MEM_RD_LATENCY;
	reg [0:0] init_bank_id_delayed;
	reg [0:0] rd_en_delayed;
	wire rd_en;
	assign rd_en = (init_mem_vld ? ~init_mem_wr_en : 1'b0);
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE) begin
			init_bank_id_delayed <= 1'sb0;
			rd_en_delayed <= 1'sb0;
		end
		else begin
			init_bank_id_delayed[0+:1] <= init_bank_id;
			rd_en_delayed[0] <= rd_en;
			begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i < DELAY; i = i + 1)
					begin
						init_bank_id_delayed[i+:1] <= init_bank_id_delayed[i - 1+:1];
						rd_en_delayed[i] <= rd_en_delayed[i - 1];
					end
			end
		end
	assign init_mem_rd_data = mem_rd_data[init_bank_id_delayed[0+:1] * 32+:32];
	assign init_mem_rd_data_vld = rd_en_delayed[0];
endmodule
module interconnect_outgoing_datapath_per_pe (
	clk,
	rst,
	ld_mem_bank_id,
	ld_gnt,
	mem_rd_data,
	ld_data,
	ld_data_vld
);
	input clk;
	input rst;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_N_GLOBAL_MEM_BANKS = hw_pkg_N_PE;
	input [0:0] ld_mem_bank_id;
	input ld_gnt;
	localparam hw_pkg_DATA_L = 32;
	input [63:0] mem_rd_data;
	output wire [31:0] ld_data;
	output wire ld_data_vld;
	localparam interconnect_pkg_GLOBAL_MEM_RD_LATENCY = 1;
	localparam DELAY = interconnect_pkg_GLOBAL_MEM_RD_LATENCY;
	reg [0:0] ld_mem_bank_id_delayed;
	reg [0:0] ld_gnt_delayed;
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE) begin
			ld_mem_bank_id_delayed <= 1'sb0;
			ld_gnt_delayed <= 1'sb0;
		end
		else begin
			ld_mem_bank_id_delayed[0+:1] <= ld_mem_bank_id;
			ld_gnt_delayed[0] <= ld_gnt;
			begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i < DELAY; i = i + 1)
					begin
						ld_mem_bank_id_delayed[i+:1] <= ld_mem_bank_id_delayed[i - 1+:1];
						ld_gnt_delayed[i] <= ld_gnt_delayed[i - 1];
					end
			end
		end
	assign ld_data = mem_rd_data[ld_mem_bank_id_delayed[0+:1] * 32+:32];
	assign ld_data_vld = ld_gnt_delayed[0];
endmodule
module simple_rr_arbiter (
	clk,
	rst,
	req,
	grant,
	granted_requester_id
);
	parameter N_IN_PORTS = 8;
	input clk;
	input rst;
	input wire [N_IN_PORTS - 1:0] req;
	output wire [N_IN_PORTS - 1:0] grant;
	output wire [$clog2(N_IN_PORTS) - 1:0] granted_requester_id;
	reg [$clog2(N_IN_PORTS) - 1:0] priority_pointer;
	wire [N_IN_PORTS - 1:0] grant_pre;
	wire [$clog2(N_IN_PORTS) - 1:0] granted_requester_id_pre;
	always @(posedge clk or negedge rst)
		if (rst == 0)
			priority_pointer <= 1'sb0;
		else if (grant_pre != 0)
			priority_pointer <= granted_requester_id_pre + 1;
	programmable_priority_encode #(.N_IN_PORTS(N_IN_PORTS)) programmable_priority_encode_ins(
		.req(req),
		.priority_pointer(priority_pointer),
		.grant(grant_pre),
		.granted_requester(granted_requester_id_pre)
	);
	assign grant = grant_pre;
	assign granted_requester_id = granted_requester_id_pre;
endmodule
module crossbar_arbiter (
	clk,
	rst,
	req,
	req_out_port,
	grant,
	grant_out_port_wise,
	detailed_grant,
	granted_requester_id
);
	parameter N_IN_PORTS = 8;
	parameter N_OUT_PORTS = 8;
	input clk;
	input rst;
	input wire [N_IN_PORTS - 1:0] req;
	input wire [(N_IN_PORTS * $clog2(N_OUT_PORTS)) - 1:0] req_out_port;
	output wire [N_IN_PORTS - 1:0] grant;
	output wire [N_OUT_PORTS - 1:0] grant_out_port_wise;
	output wire [(N_OUT_PORTS * N_IN_PORTS) - 1:0] detailed_grant;
	output wire [(N_OUT_PORTS * $clog2(N_IN_PORTS)) - 1:0] granted_requester_id;
	reg [(N_OUT_PORTS * $clog2(N_IN_PORTS)) - 1:0] priority_pointer;
	reg [N_IN_PORTS - 1:0] grant_to_reqesters;
	reg [N_OUT_PORTS - 1:0] grant_out_port_wise_pre;
	wire [(N_OUT_PORTS * $clog2(N_IN_PORTS)) - 1:0] granted_requester_id_pre;
	wire [(N_OUT_PORTS * N_IN_PORTS) - 1:0] detailed_grant_pre;
	reg [(N_IN_PORTS * N_OUT_PORTS) - 1:0] detailed_grant_transposed;
	reg [(N_IN_PORTS * N_OUT_PORTS) - 1:0] req_based_on_out_port_transposed;
	reg [(N_OUT_PORTS * N_IN_PORTS) - 1:0] req_based_on_out_port;
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = N_IN_PORTS - 1; i >= 0; i = i - 1)
			if (req[i])
				req_based_on_out_port_transposed[i * N_OUT_PORTS+:N_OUT_PORTS] = 1 << req_out_port[i * $clog2(N_OUT_PORTS)+:$clog2(N_OUT_PORTS)];
			else
				req_based_on_out_port_transposed[i * N_OUT_PORTS+:N_OUT_PORTS] = 1'sb0;
	end
	always @(*) begin : sv2v_autoblock_2
		integer i;
		for (i = N_OUT_PORTS - 1; i >= 0; i = i - 1)
			begin : sv2v_autoblock_3
				integer j;
				for (j = 0; j < N_OUT_PORTS; j = j + 1)
					req_based_on_out_port[(i * N_IN_PORTS) + j] = req_based_on_out_port_transposed[(j * N_OUT_PORTS) + i];
			end
	end
	always @(posedge clk or negedge rst)
		if (rst == 0)
			priority_pointer <= 1'sb0;
		else begin : sv2v_autoblock_4
			integer out_port;
			for (out_port = N_OUT_PORTS - 1; out_port >= 0; out_port = out_port - 1)
				if (grant_out_port_wise_pre[out_port] == 1)
					priority_pointer[out_port * $clog2(N_IN_PORTS)+:$clog2(N_IN_PORTS)] <= granted_requester_id_pre[out_port * $clog2(N_IN_PORTS)+:$clog2(N_IN_PORTS)] + 1;
		end
	genvar out_port_i;
	generate
		for (out_port_i = 0; out_port_i < N_OUT_PORTS; out_port_i = out_port_i + 1) begin : ppe_loop
			programmable_priority_encode #(.N_IN_PORTS(N_IN_PORTS)) programmable_priority_encode_ins(
				.req(req_based_on_out_port[out_port_i * N_IN_PORTS+:N_IN_PORTS]),
				.priority_pointer(priority_pointer[out_port_i * $clog2(N_IN_PORTS)+:$clog2(N_IN_PORTS)]),
				.grant(detailed_grant_pre[out_port_i * N_IN_PORTS+:N_IN_PORTS]),
				.granted_requester(granted_requester_id_pre[out_port_i * $clog2(N_IN_PORTS)+:$clog2(N_IN_PORTS)])
			);
		end
	endgenerate
	always @(*) begin : sv2v_autoblock_5
		integer i;
		for (i = N_IN_PORTS - 1; i >= 0; i = i - 1)
			begin : sv2v_autoblock_6
				integer j;
				for (j = 0; j < N_OUT_PORTS; j = j + 1)
					detailed_grant_transposed[(i * N_OUT_PORTS) + j] = detailed_grant_pre[(j * N_IN_PORTS) + i];
			end
	end
	always @(*) begin : sv2v_autoblock_7
		integer i;
		for (i = N_OUT_PORTS - 1; i >= 0; i = i - 1)
			if (detailed_grant_pre[i * N_IN_PORTS+:N_IN_PORTS] == 0)
				grant_out_port_wise_pre[i] = 0;
			else
				grant_out_port_wise_pre[i] = 1;
	end
	always @(*) begin : sv2v_autoblock_8
		integer i;
		for (i = N_IN_PORTS - 1; i >= 0; i = i - 1)
			if (detailed_grant_transposed[i * N_OUT_PORTS+:N_OUT_PORTS] == 0)
				grant_to_reqesters[i] = 0;
			else
				grant_to_reqesters[i] = 1;
	end
	assign grant = grant_to_reqesters;
	assign grant_out_port_wise = grant_out_port_wise_pre;
	assign detailed_grant = detailed_grant_pre;
	assign granted_requester_id = granted_requester_id_pre;
endmodule
module programmable_priority_encode (
	req,
	priority_pointer,
	grant,
	granted_requester
);
	parameter N_IN_PORTS = 8;
	input [N_IN_PORTS - 1:0] req;
	input [$clog2(N_IN_PORTS) - 1:0] priority_pointer;
	output wire [N_IN_PORTS - 1:0] grant;
	output wire [$clog2(N_IN_PORTS) - 1:0] granted_requester;
	wire [(2 * N_IN_PORTS) - 1:0] req_pre_shift;
	wire [N_IN_PORTS - 1:0] req_post_shift;
	wire [N_IN_PORTS - 1:0] grant_out;
	reg [$clog2(N_IN_PORTS) - 1:0] granted_requester_pre_shift;
	wire [$clog2(N_IN_PORTS) - 1:0] granted_requester_post_shift;
	assign req_pre_shift = {req, req};
	assign req_post_shift = req_pre_shift >> priority_pointer;
	always @(*) begin
		granted_requester_pre_shift = 0;
		begin : sv2v_autoblock_1
			integer i;
			for (i = N_IN_PORTS - 1; i >= 0; i = i - 1)
				if (req_post_shift[i] == 1)
					granted_requester_pre_shift = i;
		end
	end
	assign granted_requester_post_shift = granted_requester_pre_shift + priority_pointer;
	assign grant_out = (req ? 1 << granted_requester_post_shift : {N_IN_PORTS {1'sb0}});
	assign grant = grant_out;
	assign granted_requester = granted_requester_post_shift;
endmodule
module crossbar_arbiter_w_priority (
	clk,
	rst,
	req,
	req_out_port,
	grant,
	priority_req,
	priority_grant,
	grant_out_port_wise,
	detailed_grant,
	granted_requester_id
);
	parameter N_IN_PORTS = 8;
	parameter N_OUT_PORTS = 8;
	input clk;
	input rst;
	input wire [N_IN_PORTS - 1:0] req;
	input wire [(N_IN_PORTS * $clog2(N_OUT_PORTS)) - 1:0] req_out_port;
	output wire [N_IN_PORTS - 1:0] grant;
	input [N_OUT_PORTS - 1:0] priority_req;
	output wire [N_OUT_PORTS - 1:0] priority_grant;
	output wire [N_OUT_PORTS - 1:0] grant_out_port_wise;
	output wire [(N_OUT_PORTS * N_IN_PORTS) - 1:0] detailed_grant;
	output wire [(N_OUT_PORTS * $clog2(N_IN_PORTS)) - 1:0] granted_requester_id;
	wire [N_OUT_PORTS - 1:0] priority_grant_pre;
	reg [N_IN_PORTS - 1:0] grant_to_reqesters;
	reg [N_OUT_PORTS - 1:0] grant_out_port_wise_pre;
	wire [(N_OUT_PORTS * N_IN_PORTS) - 1:0] detailed_grant_pre;
	reg [(N_IN_PORTS * N_OUT_PORTS) - 1:0] detailed_grant_transposed;
	reg [(N_IN_PORTS * N_OUT_PORTS) - 1:0] req_based_on_out_port_transposed;
	reg [(N_OUT_PORTS * N_IN_PORTS) - 1:0] req_based_on_out_port;
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = N_IN_PORTS - 1; i >= 0; i = i - 1)
			if (req[i])
				req_based_on_out_port_transposed[i * N_OUT_PORTS+:N_OUT_PORTS] = 1 << req_out_port[i * $clog2(N_OUT_PORTS)+:$clog2(N_OUT_PORTS)];
			else
				req_based_on_out_port_transposed[i * N_OUT_PORTS+:N_OUT_PORTS] = 1'sb0;
	end
	always @(*) begin : sv2v_autoblock_2
		integer i;
		for (i = N_OUT_PORTS - 1; i >= 0; i = i - 1)
			begin : sv2v_autoblock_3
				integer j;
				for (j = 0; j < N_OUT_PORTS; j = j + 1)
					req_based_on_out_port[(i * N_IN_PORTS) + j] = req_based_on_out_port_transposed[(j * N_OUT_PORTS) + i];
			end
	end
	always @(*) begin : sv2v_autoblock_4
		integer i;
		for (i = N_IN_PORTS - 1; i >= 0; i = i - 1)
			begin : sv2v_autoblock_5
				integer j;
				for (j = 0; j < N_OUT_PORTS; j = j + 1)
					detailed_grant_transposed[(i * N_OUT_PORTS) + j] = detailed_grant_pre[(j * N_IN_PORTS) + i];
			end
	end
	always @(*) begin : sv2v_autoblock_6
		integer i;
		for (i = N_OUT_PORTS - 1; i >= 0; i = i - 1)
			if ((detailed_grant_pre[i * N_IN_PORTS+:N_IN_PORTS] == 0) && (priority_grant_pre[i] == 0))
				grant_out_port_wise_pre[i] = 0;
			else
				grant_out_port_wise_pre[i] = 1;
	end
	always @(*) begin : sv2v_autoblock_7
		integer i;
		for (i = N_IN_PORTS - 1; i >= 0; i = i - 1)
			if (detailed_grant_transposed[i * N_OUT_PORTS+:N_OUT_PORTS] == 0)
				grant_to_reqesters[i] = 0;
			else
				grant_to_reqesters[i] = 1;
	end
	genvar out_port_i;
	generate
		for (out_port_i = 0; out_port_i < N_OUT_PORTS; out_port_i = out_port_i + 1) begin : arbiter_loop
			arbiter_w_prority #(.N_IN_PORTS(N_IN_PORTS)) ARBITER_W_PRIORITY_INS(
				.clk(clk),
				.rst(rst),
				.req(req_based_on_out_port[out_port_i * N_IN_PORTS+:N_IN_PORTS]),
				.grant(detailed_grant_pre[out_port_i * N_IN_PORTS+:N_IN_PORTS]),
				.granted_requester_id(granted_requester_id[out_port_i * $clog2(N_IN_PORTS)+:$clog2(N_IN_PORTS)]),
				.priority_req(priority_req[out_port_i]),
				.priority_grant(priority_grant_pre[out_port_i])
			);
		end
	endgenerate
	assign grant = grant_to_reqesters;
	assign grant_out_port_wise = grant_out_port_wise_pre;
	assign detailed_grant = detailed_grant_pre;
	assign priority_grant = priority_grant_pre;
endmodule
module arbiter_w_prority (
	clk,
	rst,
	req,
	grant,
	granted_requester_id,
	priority_req,
	priority_grant
);
	parameter N_IN_PORTS = 8;
	input clk;
	input rst;
	input wire [N_IN_PORTS - 1:0] req;
	output wire [N_IN_PORTS - 1:0] grant;
	output wire [$clog2(N_IN_PORTS) - 1:0] granted_requester_id;
	input priority_req;
	output wire priority_grant;
	wire [N_IN_PORTS - 1:0] gated_req;
	assign gated_req = (priority_req ? {N_IN_PORTS {1'sb0}} : req);
	simple_rr_arbiter #(.N_IN_PORTS(N_IN_PORTS)) SIMPLE_RR_ARBITER_INS(
		.clk(clk),
		.rst(rst),
		.req(gated_req),
		.grant(grant),
		.granted_requester_id(granted_requester_id)
	);
	assign priority_grant = priority_req;
endmodule
module interconnect_top (
	clk,
	rst,
	ld_addr,
	ld_req,
	ld_gnt,
	ld_data,
	ld_data_vld,
	st_addr,
	st_data,
	st_req,
	st_gnt,
	mem_addr,
	mem_wr_data,
	mem_wr_en,
	mem_rd_en,
	mem_rd_data,
	init_mem_addr,
	init_mem_vld,
	init_mem_wr_en,
	init_mem_wr_data,
	init_mem_rd_data,
	init_mem_rd_data_vld
);
	input clk;
	input rst;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	input [23:0] ld_addr;
	input [1:0] ld_req;
	output wire [1:0] ld_gnt;
	localparam hw_pkg_DATA_L = 32;
	output wire [63:0] ld_data;
	output wire [1:0] ld_data_vld;
	localparam hw_pkg_N_GLOBAL_MEM_BANKS = hw_pkg_N_PE;
	localparam interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L = 10;
	input [19:0] st_addr;
	input [63:0] st_data;
	input [1:0] st_req;
	output wire [1:0] st_gnt;
	output wire [19:0] mem_addr;
	output wire [63:0] mem_wr_data;
	output wire [1:0] mem_wr_en;
	output wire [1:0] mem_rd_en;
	input [63:0] mem_rd_data;
	input [11:0] init_mem_addr;
	input init_mem_vld;
	input init_mem_wr_en;
	input [31:0] init_mem_wr_data;
	output wire [31:0] init_mem_rd_data;
	output wire init_mem_rd_data_vld;
	wire [1:0] ld_gnt_pre;
	wire [1:0] st_gnt_pre;
	wire [1:0] granted_requester_id;
	wire [1:0] grant_out_port_wise;
	reg [1:0] ld_bank_id;
	reg [19:0] ld_bank_addr;
	wire [1:0] ld_req_gated;
	wire [1:0] st_req_gated;
	assign ld_req_gated = (init_mem_vld ? {2 {1'sb0}} : ld_req);
	assign st_req_gated = (init_mem_vld ? {2 {1'sb0}} : st_req);
	wire [0:0] init_bank_id;
	wire [9:0] init_bank_addr;
	localparam interconnect_pkg_BANK_ADDR_START = 0;
	localparam interconnect_pkg_BANK_ID_START = interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L;
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			begin
				ld_bank_id[i+:1] = ld_addr[(i * 12) + interconnect_pkg_BANK_ID_START+:1];
				ld_bank_addr[i * 10+:10] = ld_addr[(i * 12) + interconnect_pkg_BANK_ADDR_START+:interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L];
			end
	end
	assign init_bank_id = init_mem_addr[interconnect_pkg_BANK_ID_START+:1];
	assign init_bank_addr = init_mem_addr[interconnect_pkg_BANK_ADDR_START+:10];
	crossbar_arbiter_w_priority #(
		.N_IN_PORTS(hw_pkg_N_PE),
		.N_OUT_PORTS(hw_pkg_N_GLOBAL_MEM_BANKS)
	) ARBITER_INS(
		.clk(clk),
		.rst(rst),
		.req(ld_req_gated),
		.req_out_port(ld_bank_id),
		.grant(ld_gnt_pre),
		.priority_req(st_req_gated),
		.priority_grant(st_gnt_pre),
		.grant_out_port_wise(grant_out_port_wise),
		.granted_requester_id(granted_requester_id)
	);
	interconnect_datapath INTERCONNECT_DATAPATH_INS(
		.clk(clk),
		.rst(rst),
		.ld_mem_bank_id(ld_bank_id),
		.ld_bank_addrs(ld_bank_addr),
		.ld_gnt(ld_gnt_pre),
		.granted_requester_id(granted_requester_id),
		.grant_out_port_wise(grant_out_port_wise),
		.ld_data(ld_data),
		.ld_data_vld(ld_data_vld),
		.st_addr(st_addr),
		.st_data(st_data),
		.st_gnt(st_gnt_pre),
		.init_bank_id(init_bank_id),
		.init_bank_addr(init_bank_addr),
		.init_mem_vld(init_mem_vld),
		.init_mem_wr_en(init_mem_wr_en),
		.init_mem_wr_data(init_mem_wr_data),
		.init_mem_rd_data(init_mem_rd_data),
		.init_mem_rd_data_vld(init_mem_rd_data_vld),
		.mem_addr(mem_addr),
		.mem_wr_data(mem_wr_data),
		.mem_wr_en(mem_wr_en),
		.mem_rd_en(mem_rd_en),
		.mem_rd_data(mem_rd_data)
	);
	assign ld_gnt = ld_gnt_pre;
	assign st_gnt = st_gnt_pre;
	always @(posedge clk) begin
		begin : sv2v_autoblock_2
			integer i;
			for (i = 1; i >= 0; i = i - 1)
				if (ld_data_vld[i])
					;
		end
		begin : sv2v_autoblock_3
			integer i;
			for (i = 1; i >= 0; i = i - 1)
				if (ld_req[i])
					;
		end
		begin : sv2v_autoblock_4
			integer i;
			for (i = 1; i >= 0; i = i - 1)
				if (st_req[i])
					;
		end
	end
endmodule
module priority_encoder_active_high (
	in,
	out,
	all_zeroes
);
	parameter N_IN = 8;
	input [N_IN - 1:0] in;
	output wire [$clog2(N_IN) - 1:0] out;
	output wire all_zeroes;
	reg [$clog2(N_IN) - 1:0] out_pre;
	reg all_zeroes_pre;
	always @(*) begin
		out_pre = 1'sbx;
		all_zeroes_pre = 1;
		begin : sv2v_autoblock_1
			integer i;
			for (i = 0; i < N_IN; i = i + 1)
				if (in[i] == 1) begin
					all_zeroes_pre = 0;
					out_pre = i;
				end
		end
	end
	assign all_zeroes = all_zeroes_pre;
	assign out = out_pre;
endmodule
module priority_encoder_active_low (
	in,
	out,
	all_ones
);
	parameter N_IN = 8;
	input [N_IN - 1:0] in;
	output wire [$clog2(N_IN) - 1:0] out;
	output wire all_ones;
	reg [$clog2(N_IN) - 1:0] out_pre;
	reg all_ones_pre;
	always @(*) begin
		out_pre = 1'sbx;
		all_ones_pre = 1;
		begin : sv2v_autoblock_1
			integer i;
			for (i = 0; i < N_IN; i = i + 1)
				if (in[i] == 0) begin
					all_ones_pre = 0;
					out_pre = i;
				end
		end
	end
	assign all_ones = all_ones_pre;
	assign out = out_pre;
endmodule
module lzd_decomposable (
	in,
	out_full,
	all_ones_full,
	out_half,
	all_ones_half,
	out_quarter,
	all_ones_quarter
);
	parameter MAX_BITS = 32;
	input [MAX_BITS - 1:0] in;
	output wire [$clog2(MAX_BITS) - 1:0] out_full;
	output wire all_ones_full;
	output wire [(2 * $clog2(MAX_BITS / 2)) - 1:0] out_half;
	output wire [1:0] all_ones_half;
	output wire [(4 * $clog2(MAX_BITS / 4)) - 1:0] out_quarter;
	output wire [3:0] all_ones_quarter;
	localparam OUT_L = $clog2(MAX_BITS);
	reg [OUT_L - 1:0] out_full_pre;
	wire all_ones_full_pre;
	reg [((OUT_L - 2) >= 0 ? (2 * (OUT_L - 1)) - 1 : (2 * (3 - OUT_L)) + (OUT_L - 3)):((OUT_L - 2) >= 0 ? 0 : OUT_L - 2)] out_half_pre;
	wire [1:0] all_ones_half_pre;
	wire [((OUT_L - 3) >= 0 ? (4 * (OUT_L - 2)) - 1 : (4 * (4 - OUT_L)) + (OUT_L - 4)):((OUT_L - 3) >= 0 ? 0 : OUT_L - 3)] out_quarter_pre;
	wire [3:0] all_ones_quarter_pre;
	assign all_ones_half_pre[1] = all_ones_quarter_pre[3] & all_ones_quarter_pre[2];
	assign all_ones_half_pre[0] = all_ones_quarter_pre[1] & all_ones_quarter_pre[0];
	assign all_ones_full_pre = all_ones_half_pre[1] & all_ones_half_pre[0];
	genvar quarter_i;
	generate
		for (quarter_i = 0; quarter_i < 4; quarter_i = quarter_i + 1) begin : quarter_loop
			priority_encoder_active_low #(.N_IN(MAX_BITS / 4)) PRIORITY_ENCODER_ACTIVE_LOW_INS(
				.in(in[quarter_i * (MAX_BITS / 4)+:MAX_BITS / 4]),
				.out(out_quarter_pre[((OUT_L - 3) >= 0 ? 0 : OUT_L - 3) + (quarter_i * ((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L))+:((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L)]),
				.all_ones(all_ones_quarter_pre[quarter_i])
			);
		end
	endgenerate
	always @(*)
		if (all_ones_quarter_pre[3] == 0)
			out_half_pre[((OUT_L - 2) >= 0 ? 0 : OUT_L - 2) + ((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)+:((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)] = {1'b1, out_quarter_pre[((OUT_L - 3) >= 0 ? 0 : OUT_L - 3) + (3 * ((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L))+:((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L)]};
		else
			out_half_pre[((OUT_L - 2) >= 0 ? 0 : OUT_L - 2) + ((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)+:((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)] = {1'b0, out_quarter_pre[((OUT_L - 3) >= 0 ? 0 : OUT_L - 3) + (2 * ((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L))+:((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L)]};
	always @(*)
		if (all_ones_quarter_pre[1] == 0)
			out_half_pre[((OUT_L - 2) >= 0 ? 0 : OUT_L - 2) + 0+:((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)] = {1'b1, out_quarter_pre[((OUT_L - 3) >= 0 ? 0 : OUT_L - 3) + ((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L)+:((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L)]};
		else
			out_half_pre[((OUT_L - 2) >= 0 ? 0 : OUT_L - 2) + 0+:((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)] = {1'b0, out_quarter_pre[((OUT_L - 3) >= 0 ? 0 : OUT_L - 3) + 0+:((OUT_L - 3) >= 0 ? OUT_L - 2 : 4 - OUT_L)]};
	always @(*)
		if (all_ones_half_pre[1] == 0)
			out_full_pre = {1'b1, out_half_pre[((OUT_L - 2) >= 0 ? 0 : OUT_L - 2) + ((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)+:((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)]};
		else
			out_full_pre = {1'b0, out_half_pre[((OUT_L - 2) >= 0 ? 0 : OUT_L - 2) + 0+:((OUT_L - 2) >= 0 ? OUT_L - 1 : 3 - OUT_L)]};
	assign out_full = out_full_pre;
	assign all_ones_full = all_ones_full_pre;
	assign out_half = out_half_pre;
	assign all_ones_half = all_ones_half_pre;
	assign out_quarter = out_quarter_pre;
	assign all_ones_quarter = all_ones_quarter_pre;
endmodule
module left_shift_decomposable (
	in,
	shift_val,
	full_shift,
	mode,
	out
);
	parameter ARITH_SHIFT = 0;
	parameter EXTENSION_BIT = 0;
	input [31:0] in;
	input [19:0] shift_val;
	input full_shift;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	output wire [31:0] out;
	localparam EACH_SHIFTER_LEN = 8;
	localparam N_SHIFTER = 4;
	localparam TOTAL_LEN = 32;
	localparam N_STAGES = 5;
	wire [3:0] extend_0;
	reg [3:0] extend_0_gated;
	wire [7:0] extend_1;
	reg [7:0] extend_1_gated;
	wire [15:0] extend_2;
	reg [15:0] extend_2_gated;
	wire [31:0] extend_3;
	reg [31:0] extend_3_gated;
	wire [63:0] extend_4;
	reg [63:0] extend_4_gated;
	wire [159:0] out_per_shifter;
	reg [31:0] out_pre;
	genvar shifter_i;
	generate
		for (shifter_i = 0; shifter_i < N_SHIFTER; shifter_i = shifter_i + 1) begin : shifter_loop
			if (shifter_i > 0) begin : shifter_last_bit_if
				assign extend_0[shifter_i] = in[(shifter_i * EACH_SHIFTER_LEN) - 1];
				assign extend_1[shifter_i * 2+:2] = out_per_shifter[(((shifter_i - 1) * 5) * 8) + 7-:2];
				assign extend_2[shifter_i * 4+:4] = out_per_shifter[((((shifter_i - 1) * 5) + 1) * 8) + 7-:4];
				assign extend_3[shifter_i * 8+:8] = out_per_shifter[((((shifter_i - 1) * 5) + 2) * 8) + 7-:8];
			end
			else begin : shifter_last_bit_else
				if (ARITH_SHIFT == 0) begin : block_0
					assign extend_0[shifter_i] = (EXTENSION_BIT ? 1'b1 : 1'b0);
					assign extend_1[shifter_i * 2+:2] = (EXTENSION_BIT ? {2 {1'sb1}} : {2 {1'sb0}});
					assign extend_2[shifter_i * 4+:4] = (EXTENSION_BIT ? {4 {1'sb1}} : {4 {1'sb0}});
					assign extend_3[shifter_i * 8+:8] = (EXTENSION_BIT ? {8 {1'sb1}} : {8 {1'sb0}});
				end
				else begin : block_1
					assign extend_0[shifter_i] = (in[0] ? 1'b1 : 1'b0);
					assign extend_1[shifter_i * 2+:2] = (in[0] ? {2 {1'sb1}} : {2 {1'sb0}});
					assign extend_2[shifter_i * 4+:4] = (in[0] ? {4 {1'sb1}} : {4 {1'sb0}});
					assign extend_3[shifter_i * 8+:8] = (in[0] ? {8 {1'sb1}} : {8 {1'sb0}});
				end
			end
			if (shifter_i > 1) begin : shifter_second_last_bit_if
				assign extend_4[shifter_i * 16+:16] = {out_per_shifter[(((shifter_i - 1) * 5) + 3) * 8+:8], out_per_shifter[(((shifter_i - 2) * 5) + 3) * 8+:8]};
			end
			else begin : shifter_second_last_bit_else
				if (ARITH_SHIFT == 0) begin : block_2
					assign extend_4[shifter_i * 16+:16] = (EXTENSION_BIT ? {16 {1'sb1}} : {16 {1'sb0}});
				end
				else begin : block_3
					assign extend_4[shifter_i * 16+:16] = (in[0] ? {16 {1'sb1}} : {16 {1'sb0}});
				end
			end
			left_shift_building_block #(.LEN(EACH_SHIFTER_LEN)) LEFT_SHIFT_BUILDING_BLOCK_INS(
				.in(in[shifter_i * EACH_SHIFTER_LEN+:EACH_SHIFTER_LEN]),
				.extend_0(extend_0_gated[shifter_i]),
				.extend_1(extend_1_gated[shifter_i * 2+:2]),
				.extend_2(extend_2_gated[shifter_i * 4+:4]),
				.extend_3(extend_3_gated[shifter_i * 8+:8]),
				.extend_4(extend_4_gated[shifter_i * 16+:16]),
				.shift_val(shift_val[shifter_i * 5+:5]),
				.out(out_per_shifter[8 * (shifter_i * 5)+:40])
			);
		end
	endgenerate
	localparam pe_pkg_PRECISION_CONFIG_16B = 1;
	localparam pe_pkg_PRECISION_CONFIG_8B = 2;
	always @(*) begin
		extend_0_gated = extend_0;
		extend_1_gated = extend_1;
		extend_2_gated = extend_2;
		extend_3_gated = extend_3;
		extend_4_gated = extend_4;
		if (mode == pe_pkg_PRECISION_CONFIG_16B)
			if (ARITH_SHIFT == 0) begin
				extend_4_gated = (EXTENSION_BIT ? {64 {1'sb1}} : {64 {1'sb0}});
				extend_3_gated[16+:8] = (EXTENSION_BIT ? {8 {1'sb1}} : {8 {1'sb0}});
				extend_2_gated[8+:4] = (EXTENSION_BIT ? {4 {1'sb1}} : {4 {1'sb0}});
				extend_1_gated[4+:2] = (EXTENSION_BIT ? {2 {1'sb1}} : {2 {1'sb0}});
				extend_0_gated[2] = (EXTENSION_BIT ? 1'b1 : 1'b0);
			end
			else begin
				begin : sv2v_autoblock_1
					integer i;
					for (i = 3; i >= 0; i = i - 1)
						extend_4_gated[i * 16+:16] = (in[((i / 2) * 2) * EACH_SHIFTER_LEN] ? {16 {1'sb1}} : {16 {1'sb0}});
				end
				extend_3_gated[16+:8] = (in[16] ? {8 {1'sb1}} : {8 {1'sb0}});
				extend_2_gated[8+:4] = (in[16] ? {4 {1'sb1}} : {4 {1'sb0}});
				extend_1_gated[4+:2] = (in[16] ? {2 {1'sb1}} : {2 {1'sb0}});
				extend_0_gated[2] = (in[16] ? 1'b1 : 1'b0);
			end
		if (mode == pe_pkg_PRECISION_CONFIG_8B)
			if (ARITH_SHIFT == 0) begin
				extend_4_gated = (EXTENSION_BIT ? {64 {1'sb1}} : {64 {1'sb0}});
				extend_3_gated = (EXTENSION_BIT ? {32 {1'sb1}} : {32 {1'sb0}});
				extend_2_gated = (EXTENSION_BIT ? {16 {1'sb1}} : {16 {1'sb0}});
				extend_1_gated = (EXTENSION_BIT ? {8 {1'sb1}} : {8 {1'sb0}});
				extend_0_gated = (EXTENSION_BIT ? {4 {1'sb1}} : {4 {1'sb0}});
			end
			else begin : sv2v_autoblock_2
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					begin
						extend_4_gated[i * 16+:16] = (in[i * EACH_SHIFTER_LEN] ? {16 {1'sb1}} : {16 {1'sb0}});
						extend_3_gated[i * 8+:8] = (in[i * EACH_SHIFTER_LEN] ? {8 {1'sb1}} : {8 {1'sb0}});
						extend_2_gated[i * 4+:4] = (in[i * EACH_SHIFTER_LEN] ? {4 {1'sb1}} : {4 {1'sb0}});
						extend_1_gated[i * 2+:2] = (in[i * EACH_SHIFTER_LEN] ? {2 {1'sb1}} : {2 {1'sb0}});
						extend_0_gated[i] = (in[i * EACH_SHIFTER_LEN] ? 1'b1 : 1'b0);
					end
			end
	end
	always @(*)
		if (full_shift == 0) begin : sv2v_autoblock_3
			integer i;
			for (i = 3; i >= 0; i = i - 1)
				out_pre[i * EACH_SHIFTER_LEN+:EACH_SHIFTER_LEN] = out_per_shifter[((i * 5) + 4) * 8+:8];
		end
		else
			out_pre = (EXTENSION_BIT ? {32 {1'sb1}} : {32 {1'sb0}});
	assign out = out_pre;
endmodule
module left_shift_building_block (
	in,
	extend_0,
	extend_1,
	extend_2,
	extend_3,
	extend_4,
	shift_val,
	out
);
	parameter LEN = 8;
	input [LEN - 1:0] in;
	input extend_0;
	input [1:0] extend_1;
	input [3:0] extend_2;
	input [7:0] extend_3;
	input [15:0] extend_4;
	input [4:0] shift_val;
	output wire [(5 * LEN) - 1:0] out;
	localparam N_STAGES = 5;
	wire [(5 * LEN) - 1:0] out_pre;
	left_shift_fixed #(
		.IN_LEN(LEN + 1),
		.OUT_LEN(LEN),
		.SHIFT_VAL(1)
	) LEFT_SHIFT_FIXED_INS_0(
		.in({in, extend_0}),
		.out(out_pre[0+:LEN]),
		.shift_en(shift_val[0])
	);
	left_shift_fixed #(
		.IN_LEN(LEN + 2),
		.OUT_LEN(LEN),
		.SHIFT_VAL(2)
	) LEFT_SHIFT_FIXED_INS_1(
		.in({out_pre[0+:LEN], extend_1}),
		.out(out_pre[LEN+:LEN]),
		.shift_en(shift_val[1])
	);
	left_shift_fixed #(
		.IN_LEN(LEN + 4),
		.OUT_LEN(LEN),
		.SHIFT_VAL(4)
	) LEFT_SHIFT_FIXED_INS_2(
		.in({out_pre[LEN+:LEN], extend_2}),
		.out(out_pre[2 * LEN+:LEN]),
		.shift_en(shift_val[2])
	);
	left_shift_fixed #(
		.IN_LEN(LEN + 8),
		.OUT_LEN(LEN),
		.SHIFT_VAL(8)
	) LEFT_SHIFT_FIXED_INS_3(
		.in({out_pre[2 * LEN+:LEN], extend_3}),
		.out(out_pre[3 * LEN+:LEN]),
		.shift_en(shift_val[3])
	);
	left_shift_fixed #(
		.IN_LEN(LEN + 16),
		.OUT_LEN(LEN),
		.SHIFT_VAL(16)
	) LEFT_SHIFT_FIXED_INS_4(
		.in({out_pre[3 * LEN+:LEN], extend_4}),
		.out(out_pre[4 * LEN+:LEN]),
		.shift_en(shift_val[4])
	);
	assign out[0+:LEN] = out_pre[0+:LEN];
	assign out[LEN+:LEN] = out_pre[LEN+:LEN];
	assign out[2 * LEN+:LEN] = out_pre[2 * LEN+:LEN];
	assign out[3 * LEN+:LEN] = out_pre[3 * LEN+:LEN];
	assign out[4 * LEN+:LEN] = out_pre[4 * LEN+:LEN];
endmodule
module left_shift_fixed (
	in,
	out,
	shift_en
);
	parameter IN_LEN = 8;
	parameter OUT_LEN = 8;
	parameter SHIFT_VAL = 1;
	input [IN_LEN - 1:0] in;
	output wire [OUT_LEN - 1:0] out;
	input shift_en;
	reg [OUT_LEN - 1:0] out_pre;
	wire [IN_LEN - 1:0] shifted;
	assign shifted = in << SHIFT_VAL;
	always @(*)
		if (shift_en)
			out_pre = shifted[IN_LEN - 1-:OUT_LEN];
		else
			out_pre = in[IN_LEN - 1-:OUT_LEN];
	assign out = out_pre;
endmodule
module right_shift_decomposable (
	in,
	shift_val,
	full_shift,
	mode,
	out
);
	parameter ARITH_SHIFT = 0;
	parameter EXTENSION_BIT = 0;
	input [31:0] in;
	input [19:0] shift_val;
	input full_shift;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	output wire [31:0] out;
	reg [19:0] shift_val_reversed;
	reg [31:0] in_reversed;
	wire [31:0] out_reversed;
	reg [31:0] out_pre;
	always @(*) begin
		begin : sv2v_autoblock_1
			integer i;
			for (i = 31; i >= 0; i = i - 1)
				begin
					in_reversed[i] = in[31 - i];
					out_pre[i] = out_reversed[31 - i];
				end
		end
		begin : sv2v_autoblock_2
			integer j;
			for (j = 3; j >= 0; j = j - 1)
				shift_val_reversed[j * 5+:5] = shift_val[(3 - j) * 5+:5];
		end
	end
	left_shift_decomposable #(
		.ARITH_SHIFT(ARITH_SHIFT),
		.EXTENSION_BIT(EXTENSION_BIT)
	) LEFT_SHIFT_DECOMPOSABLE_INS(
		.in(in_reversed),
		.shift_val(shift_val_reversed),
		.full_shift(full_shift),
		.mode(mode),
		.out(out_reversed)
	);
	assign out = out_pre;
endmodule
module extract_fields (
	clk,
	in,
	exp32,
	mant32,
	exp16,
	mant16,
	exp8,
	mant8,
	mode
);
	parameter ES_L_32 = 6;
	parameter ES_L_16 = 4;
	parameter ES_L_8 = 2;
	input clk;
	input [31:0] in;
	output wire [ES_L_32 + 5:0] exp32;
	output wire [30 - ES_L_32:0] mant32;
	output wire [((ES_L_16 + 4) >= 0 ? (2 * (ES_L_16 + 5)) - 1 : (2 * (1 - (ES_L_16 + 4))) + (ES_L_16 + 3)):((ES_L_16 + 4) >= 0 ? 0 : ES_L_16 + 4)] exp16;
	output wire [((14 - ES_L_16) >= 0 ? (2 * (15 - ES_L_16)) - 1 : (2 * (ES_L_16 - 13)) + ((14 - ES_L_16) - 1)):((14 - ES_L_16) >= 0 ? 0 : 14 - ES_L_16)] mant16;
	output wire [((ES_L_8 + 3) >= 0 ? (4 * (ES_L_8 + 4)) - 1 : (4 * (1 - (ES_L_8 + 3))) + (ES_L_8 + 2)):((ES_L_8 + 3) >= 0 ? 0 : ES_L_8 + 3)] exp8;
	output wire [((6 - ES_L_8) >= 0 ? (4 * (7 - ES_L_8)) - 1 : (4 * (ES_L_8 - 5)) + ((6 - ES_L_8) - 1)):((6 - ES_L_8) >= 0 ? 0 : 6 - ES_L_8)] mant8;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	localparam FULL_L = 32;
	localparam HALF_L = 16;
	localparam QUART_L = 8;
	localparam MANT_FULL_L = 31 - ES_L_32;
	localparam MANT_HALF_L = 15 - ES_L_16;
	localparam MANT_QUART_L = 7 - ES_L_8;
	wire first_bit_32B;
	wire all_zeroes_full;
	wire all_ones_full;
	wire [1:0] first_bit_16B;
	reg [1:0] all_zeroes_half;
	reg [1:0] all_ones_half;
	wire [3:0] first_bit_8B;
	reg [3:0] all_zeroes_quart;
	reg [3:0] all_ones_quart;
	reg signed [5:0] regime_full;
	reg signed [9:0] regime_half;
	reg signed [15:0] regime_quart;
	wire [ES_L_32 - 1:0] exp_fx_len_full;
	wire [(2 * ES_L_16) - 1:0] exp_fx_len_half;
	wire [(4 * ES_L_8) - 1:0] exp_fx_len_quart;
	wire [(6 + ES_L_32) - 1:0] exp_full;
	reg [(2 * (5 + ES_L_16)) - 1:0] exp_half;
	reg [(4 * (4 + ES_L_8)) - 1:0] exp_quart;
	wire [MANT_FULL_L - 1:0] mant_full;
	reg [(2 * MANT_HALF_L) - 1:0] mant_half;
	reg [(4 * MANT_QUART_L) - 1:0] mant_quart;
	reg [31:0] lzd_in;
	wire [4:0] lzd_out_full;
	wire lzd_all_ones_full;
	wire [7:0] lzd_out_half;
	wire [1:0] lzd_all_ones_half;
	wire [11:0] lzd_out_quart;
	wire [3:0] lzd_all_ones_quart;
	reg [19:0] shift_val;
	reg full_shift;
	wire [31:0] shift_out;
	assign first_bit_32B = in[31];
	assign first_bit_16B[0] = in[15];
	assign first_bit_16B[1] = in[31];
	assign first_bit_8B[0] = in[7];
	assign first_bit_8B[1] = in[15];
	assign first_bit_8B[2] = in[23];
	assign first_bit_8B[3] = in[31];
	assign all_zeroes_full = (in == {32 {1'sb0}} ? 1 : 0);
	assign all_ones_full = (in == {32 {1'sb1}} ? 1 : 0);
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = 0; i < 2; i = i + 1)
			begin
				all_zeroes_half[i] = (in[i * HALF_L+:HALF_L] == {16 {1'sb0}} ? 1 : 0);
				all_ones_half[i] = (in[i * HALF_L+:HALF_L] == {16 {1'sb1}} ? 1 : 0);
			end
	end
	always @(*) begin : sv2v_autoblock_2
		integer i;
		for (i = 0; i < 4; i = i + 1)
			begin
				all_zeroes_quart[i] = (in[i * QUART_L+:QUART_L] == {8 {1'sb0}} ? 1 : 0);
				all_ones_quart[i] = (in[i * QUART_L+:QUART_L] == {8 {1'sb1}} ? 1 : 0);
			end
	end
	localparam pe_pkg_PRECISION_CONFIG_16B = 1;
	localparam pe_pkg_PRECISION_CONFIG_32B = 0;
	localparam pe_pkg_PRECISION_CONFIG_8B = 2;
	always @(*)
		case (mode)
			pe_pkg_PRECISION_CONFIG_32B: lzd_in = (first_bit_32B ? in : ~in);
			pe_pkg_PRECISION_CONFIG_16B: begin : sv2v_autoblock_3
				integer i;
				for (i = 0; i < 2; i = i + 1)
					lzd_in[i * HALF_L+:HALF_L] = (first_bit_16B[i] ? in[i * HALF_L+:HALF_L] : ~in[i * HALF_L+:HALF_L]);
			end
			pe_pkg_PRECISION_CONFIG_8B: begin : sv2v_autoblock_4
				integer i;
				for (i = 0; i < 4; i = i + 1)
					lzd_in[i * QUART_L+:QUART_L] = (first_bit_8B[i] ? in[i * QUART_L+:QUART_L] : ~in[i * QUART_L+:QUART_L]);
			end
			default: lzd_in = 1'sbx;
		endcase
	lzd_decomposable #(.MAX_BITS(FULL_L)) LZD_DECOMPOSABLE_INS(
		.in(lzd_in),
		.out_full(lzd_out_full),
		.all_ones_full(lzd_all_ones_full),
		.out_half(lzd_out_half),
		.all_ones_half(lzd_all_ones_half),
		.out_quarter(lzd_out_quart),
		.all_ones_quarter(lzd_all_ones_quart)
	);
	always @(*) begin
		regime_full = 1'sbx;
		regime_half = 1'sbx;
		regime_quart = 1'sbx;
		shift_val = 1'sbx;
		full_shift = 1'b0;
		case (mode)
			pe_pkg_PRECISION_CONFIG_32B:
				if (all_zeroes_full) begin
					regime_full = 1'sb0;
					shift_val = 1'sb0;
				end
				else begin
					if (first_bit_32B == 1)
						regime_full = (31 - lzd_out_full) - 1;
					else
						regime_full = (1 - FULL_L) + lzd_out_full;
					begin : sv2v_autoblock_5
						integer i;
						for (i = 0; i < 4; i = i + 1)
							shift_val[i * 5+:5] = FULL_L - lzd_out_full;
					end
					if (lzd_out_full == 0)
						full_shift = 1'b1;
				end
			pe_pkg_PRECISION_CONFIG_16B: begin : sv2v_autoblock_6
				integer i;
				for (i = 0; i < 2; i = i + 1)
					if (all_zeroes_half[i]) begin
						regime_half[i * 5+:5] = 1'sb0;
						shift_val[(i * 2) * 5+:5] = 1'sb0;
						shift_val[((i * 2) + 1) * 5+:5] = 1'sb0;
					end
					else begin
						if (first_bit_16B[i] == 1)
							regime_half[i * 5+:5] = (15 - lzd_out_half[i * 4+:4]) - 1;
						else
							regime_half[i * 5+:5] = (1 - HALF_L) + lzd_out_half[i * 4+:4];
						shift_val[(i * 2) * 5+:5] = HALF_L - lzd_out_half[i * 4+:4];
						shift_val[((i * 2) + 1) * 5+:5] = HALF_L - lzd_out_half[i * 4+:4];
					end
			end
			pe_pkg_PRECISION_CONFIG_8B: begin : sv2v_autoblock_7
				integer i;
				for (i = 0; i < 4; i = i + 1)
					if (all_zeroes_quart[i]) begin
						regime_quart[i * 4+:4] = 1'sb0;
						shift_val[i * 5+:5] = 1'sb0;
					end
					else begin
						if (first_bit_8B[i] == 1)
							regime_quart[i * 4+:4] = (7 - lzd_out_quart[i * 3+:3]) - 1;
						else
							regime_quart[i * 4+:4] = (1 - QUART_L) + lzd_out_quart[i * 3+:3];
						shift_val[i * 5+:5] = QUART_L - lzd_out_quart[i * 3+:3];
					end
			end
		endcase
	end
	left_shift_decomposable #(
		.ARITH_SHIFT(0),
		.EXTENSION_BIT(0)
	) LEFT_SHIFT_DECOMPOSABLE_INS(
		.in(in),
		.shift_val(shift_val),
		.full_shift(full_shift),
		.mode(mode),
		.out(shift_out)
	);
	assign exp_full = {regime_full, shift_out[31-:ES_L_32]};
	always @(*) begin : sv2v_autoblock_8
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			exp_half[i * (5 + ES_L_16)+:5 + ES_L_16] = {regime_half[i * 5+:5], shift_out[((i + 1) * HALF_L) - 1-:ES_L_16]};
	end
	always @(*) begin : sv2v_autoblock_9
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			exp_quart[i * (4 + ES_L_8)+:4 + ES_L_8] = {regime_quart[i * 4+:4], shift_out[((i + 1) * QUART_L) - 1-:ES_L_8]};
	end
	assign mant_full = {~all_zeroes_full, shift_out[31 - ES_L_32-:MANT_FULL_L - 1]};
	always @(*) begin : sv2v_autoblock_10
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			mant_half[i * MANT_HALF_L+:MANT_HALF_L] = {~all_zeroes_half[i], shift_out[(((i + 1) * HALF_L) - 1) - ES_L_16-:MANT_HALF_L - 1]};
	end
	always @(*) begin : sv2v_autoblock_11
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			mant_quart[i * MANT_QUART_L+:MANT_QUART_L] = {~all_zeroes_quart[i], shift_out[(((i + 1) * QUART_L) - 1) - ES_L_8-:MANT_QUART_L - 1]};
	end
	assign exp32 = exp_full;
	assign mant32 = mant_full;
	assign exp16 = exp_half;
	assign mant16 = mant_half;
	assign exp8 = exp_quart;
	assign mant8 = mant_quart;
endmodule
module adder_decomposable (
	in0,
	in1,
	mode,
	out_quart,
	out_half,
	out_full
);
	parameter EACH_ADDER_LEN = 8;
	parameter N_ADDERS = 4;
	input [(EACH_ADDER_LEN * N_ADDERS) - 1:0] in0;
	input [(EACH_ADDER_LEN * N_ADDERS) - 1:0] in1;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	output wire [(EACH_ADDER_LEN >= 0 ? (N_ADDERS * (EACH_ADDER_LEN + 1)) - 1 : (N_ADDERS * (1 - EACH_ADDER_LEN)) + (EACH_ADDER_LEN - 1)):(EACH_ADDER_LEN >= 0 ? 0 : EACH_ADDER_LEN + 0)] out_quart;
	output wire [((2 * EACH_ADDER_LEN) >= 0 ? (2 * ((2 * EACH_ADDER_LEN) + 1)) - 1 : (2 * (1 - (2 * EACH_ADDER_LEN))) + ((2 * EACH_ADDER_LEN) - 1)):((2 * EACH_ADDER_LEN) >= 0 ? 0 : (2 * EACH_ADDER_LEN) + 0)] out_half;
	output wire [4 * EACH_ADDER_LEN:0] out_full;
	localparam TOTAL_LEN = N_ADDERS * EACH_ADDER_LEN;
	wire [(EACH_ADDER_LEN >= 0 ? (N_ADDERS * (EACH_ADDER_LEN + 1)) - 1 : (N_ADDERS * (1 - EACH_ADDER_LEN)) + (EACH_ADDER_LEN - 1)):(EACH_ADDER_LEN >= 0 ? 0 : EACH_ADDER_LEN + 0)] out_quart_pre;
	wire [N_ADDERS - 1:0] carry_out;
	reg [N_ADDERS - 1:0] carry_in;
	localparam pe_pkg_PRECISION_CONFIG_16B = 1;
	localparam pe_pkg_PRECISION_CONFIG_8B = 2;
	always @(*) begin
		carry_in = 1'sbx;
		carry_in[0] = 1'b0;
		begin : sv2v_autoblock_1
			integer i;
			for (i = 1; i < N_ADDERS; i = i + 1)
				carry_in[i] = carry_out[i - 1];
		end
		if (mode == pe_pkg_PRECISION_CONFIG_16B)
			carry_in[2] = 0;
		if (mode == pe_pkg_PRECISION_CONFIG_8B) begin : sv2v_autoblock_2
			integer i;
			for (i = 1; i < N_ADDERS; i = i + 1)
				carry_in[i] = 0;
		end
	end
	genvar part_i;
	generate
		for (part_i = 0; part_i < N_ADDERS; part_i = part_i + 1) begin : part_loop
			adder_building_block #(.LEN(EACH_ADDER_LEN)) ADDER_BUILDING_BLOCK_INS(
				.in0(in0[part_i * EACH_ADDER_LEN+:EACH_ADDER_LEN]),
				.in1(in1[part_i * EACH_ADDER_LEN+:EACH_ADDER_LEN]),
				.carry_in(carry_in[part_i]),
				.out(out_quart_pre[(EACH_ADDER_LEN >= 0 ? 0 : EACH_ADDER_LEN) + (part_i * (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN))+:(EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)]),
				.carry_out(carry_out[part_i])
			);
		end
	endgenerate
	assign out_quart = out_quart_pre;
	assign out_half[((2 * EACH_ADDER_LEN) >= 0 ? 0 : 2 * EACH_ADDER_LEN) + 0+:((2 * EACH_ADDER_LEN) >= 0 ? (2 * EACH_ADDER_LEN) + 1 : 1 - (2 * EACH_ADDER_LEN))] = {out_quart_pre[(EACH_ADDER_LEN >= 0 ? 0 : EACH_ADDER_LEN) + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)+:(EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)], out_quart_pre[(EACH_ADDER_LEN >= 0 ? 0 + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1)) : ((0 + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1))) + EACH_ADDER_LEN) - 1)-:EACH_ADDER_LEN]};
	assign out_half[((2 * EACH_ADDER_LEN) >= 0 ? 0 : 2 * EACH_ADDER_LEN) + ((2 * EACH_ADDER_LEN) >= 0 ? (2 * EACH_ADDER_LEN) + 1 : 1 - (2 * EACH_ADDER_LEN))+:((2 * EACH_ADDER_LEN) >= 0 ? (2 * EACH_ADDER_LEN) + 1 : 1 - (2 * EACH_ADDER_LEN))] = {out_quart_pre[(EACH_ADDER_LEN >= 0 ? 0 : EACH_ADDER_LEN) + (3 * (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN))+:(EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)], out_quart_pre[(EACH_ADDER_LEN >= 0 ? (2 * (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1)) : (((2 * (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1))) + EACH_ADDER_LEN) - 1)-:EACH_ADDER_LEN]};
	assign out_full = {out_quart_pre[(EACH_ADDER_LEN >= 0 ? (3 * (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) + (EACH_ADDER_LEN >= 0 ? (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN : (EACH_ADDER_LEN + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) - 1) : EACH_ADDER_LEN - (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN : (EACH_ADDER_LEN + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) - 1)) : (((3 * (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) + (EACH_ADDER_LEN >= 0 ? (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN : (EACH_ADDER_LEN + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) - 1) : EACH_ADDER_LEN - (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN : (EACH_ADDER_LEN + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) - 1))) + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) - 1)-:(EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)], out_quart_pre[(EACH_ADDER_LEN >= 0 ? (2 * (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1)) : (((2 * (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN)) + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1))) + EACH_ADDER_LEN) - 1)-:EACH_ADDER_LEN], out_quart_pre[(EACH_ADDER_LEN >= 0 ? (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN) + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1)) : (((EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN + 1 : 1 - EACH_ADDER_LEN) + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1))) + EACH_ADDER_LEN) - 1)-:EACH_ADDER_LEN], out_quart_pre[(EACH_ADDER_LEN >= 0 ? 0 + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1)) : ((0 + (EACH_ADDER_LEN >= 0 ? EACH_ADDER_LEN - 1 : EACH_ADDER_LEN - (EACH_ADDER_LEN - 1))) + EACH_ADDER_LEN) - 1)-:EACH_ADDER_LEN]};
endmodule
module adder_building_block (
	in0,
	in1,
	carry_in,
	out,
	carry_out
);
	parameter LEN = 8;
	input [LEN - 1:0] in0;
	input [LEN - 1:0] in1;
	input carry_in;
	output wire [LEN:0] out;
	output wire carry_out;
	wire [LEN:0] out_pre;
	assign out_pre = (in0 + in1) + carry_in;
	assign out = out_pre;
	assign carry_out = out_pre[LEN];
endmodule
module round_norm_overflow_underflow (
	exp_full_in,
	exp_half_in,
	exp_quart_in,
	mant_full_in,
	mant_half_in,
	mant_quart_in,
	exp_full_out,
	mant_full_out,
	exp_half_out,
	mant_half_out,
	exp_quart_out,
	mant_quart_out
);
	localparam posit_pkg_ES_FULL_L = 6;
	localparam posit_pkg_FULL_L = 32;
	localparam posit_pkg_EXP_COMBINED_FULL_L = 12;
	input [posit_pkg_EXP_COMBINED_FULL_L:0] exp_full_in;
	localparam posit_pkg_ES_HALF_L = 4;
	localparam posit_pkg_HALF_L = 16;
	localparam posit_pkg_EXP_COMBINED_HALF_L = 9;
	input [19:0] exp_half_in;
	localparam posit_pkg_ES_QUART_L = 2;
	localparam posit_pkg_QUART_L = 8;
	localparam posit_pkg_EXP_COMBINED_QUART_L = 6;
	input [27:0] exp_quart_in;
	localparam posit_pkg_MANT_FULL_L = 25;
	input [26:0] mant_full_in;
	localparam posit_pkg_MANT_HALF_L = 11;
	input [25:0] mant_half_in;
	localparam posit_pkg_MANT_QUART_L = 5;
	input [27:0] mant_quart_in;
	output wire [11:0] exp_full_out;
	output wire [24:0] mant_full_out;
	output wire [17:0] exp_half_out;
	output wire [21:0] mant_half_out;
	output wire [23:0] exp_quart_out;
	output wire [19:0] mant_quart_out;
	localparam MAX_EXP_FULL = 1920;
	localparam MIN_EXP_FULL = (1 - posit_pkg_FULL_L) << posit_pkg_ES_FULL_L;
	localparam MAX_EXP_HALF = 224;
	localparam MIN_EXP_HALF = (1 - posit_pkg_HALF_L) << posit_pkg_ES_HALF_L;
	localparam MAX_EXP_QUART = 24;
	localparam MIN_EXP_QUART = (1 - posit_pkg_QUART_L) << posit_pkg_ES_QUART_L;
	reg [11:0] exp_full_out_pre;
	reg [24:0] mant_full_out_pre;
	reg [17:0] exp_half_out_pre;
	reg [21:0] mant_half_out_pre;
	reg [23:0] exp_quart_out_pre;
	reg [19:0] mant_quart_out_pre;
	reg [11:0] norm;
	reg [posit_pkg_MANT_FULL_L:0] mant_full_post_round;
	reg [posit_pkg_MANT_FULL_L:0] mant_full_post_norm;
	reg [23:0] mant_half_post_round;
	reg [23:0] mant_half_post_norm;
	reg [23:0] mant_quart_post_round;
	reg [23:0] mant_quart_post_norm;
	reg [posit_pkg_EXP_COMBINED_FULL_L:0] exp_full_post_norm;
	wire [posit_pkg_EXP_COMBINED_FULL_L:0] exp_full_post_round;
	reg [19:0] exp_half_post_norm;
	reg [19:0] exp_half_post_round;
	reg [27:0] exp_quart_post_norm;
	reg [27:0] exp_quart_post_round;
	localparam posit_pkg_REGIME_FULL_L = 6;
	wire [posit_pkg_REGIME_FULL_L:0] regime_full_post_round;
	wire [posit_pkg_REGIME_FULL_L:0] regime_full_post_norm;
	localparam posit_pkg_REGIME_HALF_L = 5;
	reg [11:0] regime_half_post_round;
	reg [11:0] regime_half_post_norm;
	localparam posit_pkg_REGIME_QUART_L = 4;
	reg [19:0] regime_quart_post_round;
	reg [19:0] regime_quart_post_norm;
	reg [5:0] round_bit_ptr_full;
	reg [9:0] round_bit_ptr_half;
	reg [15:0] round_bit_ptr_quart;
	wire [37:0] num_pre_round_full;
	reg [41:0] num_pre_round_half;
	reg [47:0] num_pre_round_quart;
	wire [36:0] num_post_round_full;
	reg [39:0] num_post_round_half;
	reg [43:0] num_post_round_quart;
	reg [32:0] round_val_full;
	reg [33:0] round_val_half;
	reg [35:0] round_val_quart;
	wire [1:1] sv2v_tmp_8CD97;
	assign sv2v_tmp_8CD97 = mant_full_in[26];
	always @(*) norm[0] = sv2v_tmp_8CD97;
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			norm[4 + i] = mant_half_in[(i * 13) + 12];
	end
	always @(*) begin : sv2v_autoblock_2
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			norm[8 + i] = mant_quart_in[(i * 7) + 6];
	end
	always @(*)
		if (norm[0]) begin
			exp_full_post_norm = $signed(exp_full_in) + 1;
			mant_full_post_norm = mant_full_in[1+:26];
		end
		else begin
			exp_full_post_norm = exp_full_in;
			mant_full_post_norm = mant_full_in[0+:26];
		end
	always @(*) begin : sv2v_autoblock_3
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			if (norm[4 + i]) begin
				exp_half_post_norm[0 + (i * 10)+:10] = $signed(exp_half_in[0 + (i * 10)+:10]) + 1;
				mant_half_post_norm[0 + (i * 12)+:12] = mant_half_in[(i * 13) + 1+:12];
			end
			else begin
				exp_half_post_norm[0 + (i * 10)+:10] = exp_half_in[0 + (i * 10)+:10];
				mant_half_post_norm[0 + (i * 12)+:12] = mant_half_in[i * 13+:12];
			end
	end
	always @(*) begin : sv2v_autoblock_4
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			if (norm[8 + i]) begin
				exp_quart_post_norm[0 + (i * 7)+:7] = $signed(exp_quart_in[0 + (i * 7)+:7]) + 1;
				mant_quart_post_norm[0 + (i * 6)+:6] = mant_quart_in[(i * 7) + 1+:6];
			end
			else begin
				exp_quart_post_norm[0 + (i * 7)+:7] = exp_quart_in[0 + (i * 7)+:7];
				mant_quart_post_norm[0 + (i * 6)+:6] = mant_quart_in[i * 7+:6];
			end
	end
	assign regime_full_post_norm = exp_full_post_norm[posit_pkg_ES_FULL_L+:7];
	always @(*) begin : sv2v_autoblock_5
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			regime_half_post_norm[0 + (i * 6)+:6] = exp_half_post_norm[(i * 10) + posit_pkg_ES_HALF_L+:6];
	end
	always @(*) begin : sv2v_autoblock_6
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			regime_quart_post_norm[0 + (i * 5)+:5] = exp_quart_post_norm[(i * 7) + posit_pkg_ES_QUART_L+:5];
	end
	assign num_pre_round_full = {exp_full_post_norm, mant_full_post_norm[0+:posit_pkg_MANT_FULL_L]};
	always @(*) begin : sv2v_autoblock_7
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			num_pre_round_half[i * 21+:21] = {exp_half_post_norm[0 + (i * 10)+:10], mant_half_post_norm[(i * 12) + 0+:posit_pkg_MANT_HALF_L]};
	end
	always @(*) begin : sv2v_autoblock_8
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			num_pre_round_quart[i * 12+:12] = {exp_quart_post_norm[0 + (i * 7)+:7], mant_quart_post_norm[(i * 6) + 0+:posit_pkg_MANT_QUART_L]};
	end
	always @(*) begin
		round_val_full = 1'sbx;
		round_bit_ptr_full = 1'sbx;
		if (($signed(exp_full_post_norm) >= MAX_EXP_FULL) || ($signed(exp_full_post_norm) <= MIN_EXP_FULL)) begin
			round_val_full = 1'sb0;
			round_bit_ptr_full = 1'sbx;
		end
		else begin
			if ($signed(regime_full_post_norm) < 0)
				round_bit_ptr_full = -($signed(regime_full_post_norm) + 1);
			else
				round_bit_ptr_full = $signed(regime_full_post_norm);
			round_val_full = num_pre_round_full[round_bit_ptr_full] << round_bit_ptr_full;
		end
	end
	always @(*) begin
		round_val_half = 1'sbx;
		round_bit_ptr_half = 1'sbx;
		begin : sv2v_autoblock_9
			integer i;
			for (i = 1; i >= 0; i = i - 1)
				if (($signed(exp_half_post_norm[0 + (i * 10)+:10]) >= MAX_EXP_HALF) || ($signed(exp_half_post_norm[0 + (i * 10)+:10]) <= MIN_EXP_HALF)) begin
					round_val_half[i * 17+:17] = 1'sb0;
					round_bit_ptr_half[i * 5+:5] = 1'sbx;
				end
				else begin
					if ($signed(regime_half_post_norm[0 + (i * 6)+:6]) < 0)
						round_bit_ptr_half[i * 5+:5] = -($signed(regime_half_post_norm[0 + (i * 6)+:6]) + 1);
					else
						round_bit_ptr_half[i * 5+:5] = $signed(regime_half_post_norm[0 + (i * 6)+:6]);
					round_val_half[i * 17+:17] = num_pre_round_half[(i * 21) + round_bit_ptr_half[i * 5+:5]] << round_bit_ptr_half[i * 5+:5];
				end
		end
	end
	always @(*) begin
		round_val_quart = 1'sbx;
		round_bit_ptr_quart = 1'sbx;
		begin : sv2v_autoblock_10
			integer i;
			for (i = 3; i >= 0; i = i - 1)
				if (($signed(exp_quart_post_norm[0 + (i * 7)+:7]) >= MAX_EXP_QUART) || ($signed(exp_quart_post_norm[0 + (i * 7)+:7]) <= MIN_EXP_QUART)) begin
					round_val_quart[i * 9+:9] = 1'sb0;
					round_bit_ptr_quart[i * 4+:4] = 1'sbx;
				end
				else begin
					if ($signed(regime_quart_post_norm[0 + (i * 5)+:5]) < 0)
						round_bit_ptr_quart[i * 4+:4] = -($signed(regime_quart_post_norm[0 + (i * 5)+:5]) + 1);
					else
						round_bit_ptr_quart[i * 4+:4] = $signed(regime_quart_post_norm[0 + (i * 5)+:5]);
					round_val_quart[i * 9+:9] = num_pre_round_quart[(i * 12) + round_bit_ptr_quart[i * 4+:4]] << round_bit_ptr_quart[i * 4+:4];
				end
		end
	end
	assign num_post_round_full = num_pre_round_full[1+:37] + $unsigned(round_val_full);
	always @(*) begin : sv2v_autoblock_11
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			num_post_round_half[i * 20+:20] = num_pre_round_half[(i * 21) + 1+:20] + $unsigned(round_val_half[i * 17+:17]);
	end
	always @(*) begin : sv2v_autoblock_12
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			num_post_round_quart[i * 11+:11] = num_pre_round_quart[(i * 12) + 1+:11] + $unsigned(round_val_quart[i * 9+:9]);
	end
	assign regime_full_post_round = num_post_round_full[30+:7];
	always @(*) begin : sv2v_autoblock_13
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			regime_half_post_round[0 + (i * 6)+:6] = num_post_round_half[(i * 20) + 14+:6];
	end
	always @(*) begin : sv2v_autoblock_14
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			regime_quart_post_round[0 + (i * 5)+:5] = num_post_round_quart[(i * 11) + 6+:5];
	end
	assign exp_full_post_round = ($signed(regime_full_post_round) == ($signed(regime_full_post_norm) + 1) ? {regime_full_post_round, {posit_pkg_ES_FULL_L {1'b0}}} : num_post_round_full[24+:13]);
	always @(*) begin : sv2v_autoblock_15
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			if ($signed(regime_half_post_round[0 + (i * 6)+:6]) == ($signed(regime_half_post_norm[0 + (i * 6)+:6]) + 1))
				exp_half_post_round[0 + (i * 10)+:10] = {regime_half_post_round[0 + (i * 6)+:6], {posit_pkg_ES_HALF_L {1'b0}}};
			else
				exp_half_post_round[0 + (i * 10)+:10] = num_post_round_half[(i * 20) + 10+:10];
	end
	always @(*) begin : sv2v_autoblock_16
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			if ($signed(regime_quart_post_round[0 + (i * 5)+:5]) == ($signed(regime_quart_post_norm[0 + (i * 5)+:5]) + 1))
				exp_quart_post_round[0 + (i * 7)+:7] = {regime_quart_post_round[0 + (i * 5)+:5], {posit_pkg_ES_QUART_L {1'b0}}};
			else
				exp_quart_post_round[0 + (i * 7)+:7] = num_post_round_quart[(i * 11) + 4+:7];
	end
	always @(*)
		if (($signed(exp_full_post_round) == ($signed(exp_full_post_norm) + 1)) || ($signed(regime_full_post_round) == ($signed(regime_full_post_norm) + 1)))
			mant_full_post_round = {mant_full_post_norm[posit_pkg_MANT_FULL_L], {24 {1'b0}}};
		else
			mant_full_post_round = {mant_full_post_norm[posit_pkg_MANT_FULL_L], num_post_round_full[23-:24]};
	always @(*) begin : sv2v_autoblock_17
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			if (($signed(exp_half_post_round[0 + (i * 10)+:10]) == ($signed(exp_half_post_norm[0 + (i * 10)+:10]) + 1)) || ($signed(regime_half_post_round[0 + (i * 6)+:6]) == ($signed(regime_half_post_norm[0 + (i * 6)+:6]) + 1)))
				mant_half_post_round[0 + (i * 12)+:12] = {mant_half_post_norm[(i * 12) + posit_pkg_MANT_HALF_L], {10 {1'b0}}};
			else
				mant_half_post_round[0 + (i * 12)+:12] = {mant_half_post_norm[(i * 12) + posit_pkg_MANT_HALF_L], num_post_round_half[(i * 20) + 9-:10]};
	end
	always @(*) begin : sv2v_autoblock_18
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			if (($signed(exp_quart_post_round[0 + (i * 7)+:7]) == ($signed(exp_quart_post_norm[0 + (i * 7)+:7]) + 1)) || ($signed(regime_quart_post_round[0 + (i * 5)+:5]) == ($signed(regime_quart_post_norm[0 + (i * 5)+:5]) + 1)))
				mant_quart_post_round[0 + (i * 6)+:6] = {mant_quart_post_norm[(i * 6) + posit_pkg_MANT_QUART_L], {4 {1'b0}}};
			else
				mant_quart_post_round[0 + (i * 6)+:6] = {mant_quart_post_norm[(i * 6) + posit_pkg_MANT_QUART_L], num_post_round_quart[(i * 11) + 3-:4]};
	end
	always @(*) begin
		mant_full_out_pre = 1'sbx;
		if ($signed(exp_full_post_round) > MAX_EXP_FULL)
			exp_full_out_pre = MAX_EXP_FULL;
		else if ($signed(exp_full_post_round) < MIN_EXP_FULL)
			exp_full_out_pre = MIN_EXP_FULL;
		else begin
			exp_full_out_pre = exp_full_post_round;
			mant_full_out_pre = mant_full_post_round;
		end
	end
	always @(*) begin : sv2v_autoblock_19
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			begin
				mant_half_out_pre[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L] = 1'sbx;
				if ($signed(exp_half_post_round[0 + (i * 10)+:10]) > MAX_EXP_HALF)
					exp_half_out_pre[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L] = MAX_EXP_HALF;
				else if ($signed(exp_half_post_round[0 + (i * 10)+:10]) < MIN_EXP_HALF)
					exp_half_out_pre[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L] = MIN_EXP_HALF;
				else begin
					exp_half_out_pre[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L] = exp_half_post_round[0 + (i * 10)+:10];
					mant_half_out_pre[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L] = mant_half_post_round[0 + (i * 12)+:12];
				end
			end
	end
	always @(*) begin : sv2v_autoblock_20
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			begin
				mant_quart_out_pre[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L] = 1'sbx;
				if ($signed(exp_quart_post_round[0 + (i * 7)+:7]) > MAX_EXP_QUART)
					exp_quart_out_pre[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L] = MAX_EXP_QUART;
				else if ($signed(exp_quart_post_round[0 + (i * 7)+:7]) < MIN_EXP_QUART)
					exp_quart_out_pre[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L] = MIN_EXP_QUART;
				else begin
					exp_quart_out_pre[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L] = exp_quart_post_round[0 + (i * 7)+:7];
					mant_quart_out_pre[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L] = mant_quart_post_round[0 + (i * 6)+:6];
				end
			end
	end
	assign exp_full_out = exp_full_out_pre;
	assign mant_full_out = mant_full_out_pre;
	assign exp_half_out = exp_half_out_pre;
	assign mant_half_out = mant_half_out_pre;
	assign exp_quart_out = exp_quart_out_pre;
	assign mant_quart_out = mant_quart_out_pre;
endmodule
module flt_adder_decomposable (
	exp_full_in_0,
	mant_full_in_0,
	exp_half_in_0,
	mant_half_in_0,
	exp_quart_in_0,
	mant_quart_in_0,
	exp_full_in_1,
	mant_full_in_1,
	exp_half_in_1,
	mant_half_in_1,
	exp_quart_in_1,
	mant_quart_in_1,
	mode,
	exp_full_out,
	exp_half_out,
	exp_quart_out,
	mant_full_out,
	mant_half_out,
	mant_quart_out
);
	localparam posit_pkg_ES_FULL_L = 6;
	localparam posit_pkg_FULL_L = 32;
	localparam posit_pkg_EXP_COMBINED_FULL_L = 12;
	input wire [11:0] exp_full_in_0;
	localparam posit_pkg_MANT_FULL_L = 25;
	input wire [24:0] mant_full_in_0;
	localparam posit_pkg_ES_HALF_L = 4;
	localparam posit_pkg_HALF_L = 16;
	localparam posit_pkg_EXP_COMBINED_HALF_L = 9;
	input wire [17:0] exp_half_in_0;
	localparam posit_pkg_MANT_HALF_L = 11;
	input wire [21:0] mant_half_in_0;
	localparam posit_pkg_ES_QUART_L = 2;
	localparam posit_pkg_QUART_L = 8;
	localparam posit_pkg_EXP_COMBINED_QUART_L = 6;
	input wire [23:0] exp_quart_in_0;
	localparam posit_pkg_MANT_QUART_L = 5;
	input wire [19:0] mant_quart_in_0;
	input wire [11:0] exp_full_in_1;
	input wire [24:0] mant_full_in_1;
	input wire [17:0] exp_half_in_1;
	input wire [21:0] mant_half_in_1;
	input wire [23:0] exp_quart_in_1;
	input wire [19:0] mant_quart_in_1;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	output wire [posit_pkg_EXP_COMBINED_FULL_L:0] exp_full_out;
	output wire [19:0] exp_half_out;
	output wire [27:0] exp_quart_out;
	output wire [26:0] mant_full_out;
	output wire [25:0] mant_half_out;
	output wire [27:0] mant_quart_out;
	localparam MAX_SHIFT_FULL = 31;
	localparam MAX_SHIFT_HALF = 15;
	localparam MAX_SHIFT_QUART = 7;
	reg [31:0] adder_in_0;
	reg [31:0] adder_in_1_pre_shift;
	wire [31:0] adder_in_1_post_shift;
	wire [posit_pkg_FULL_L:0] adder_out_full;
	wire [33:0] adder_out_half;
	wire [35:0] adder_out_quart;
	reg [posit_pkg_EXP_COMBINED_FULL_L:0] exp_full_diff;
	reg [posit_pkg_EXP_COMBINED_FULL_L:0] bigger_exp_full;
	reg [19:0] exp_half_diff;
	reg [19:0] bigger_exp_half;
	reg [27:0] exp_quart_diff;
	reg [27:0] bigger_exp_quart;
	reg [19:0] shift_val;
	wire [26:0] adder_mant_out_full;
	reg [25:0] adder_mant_out_half;
	reg [27:0] adder_mant_out_quart;
	reg [posit_pkg_EXP_COMBINED_FULL_L:0] exp_full_out_pre;
	reg [19:0] exp_half_out_pre;
	reg [27:0] exp_quart_out_pre;
	reg [26:0] mant_full_out_pre;
	reg [25:0] mant_half_out_pre;
	reg [27:0] mant_quart_out_pre;
	localparam pe_pkg_PRECISION_CONFIG_16B = 1;
	localparam pe_pkg_PRECISION_CONFIG_32B = 0;
	localparam pe_pkg_PRECISION_CONFIG_8B = 2;
	always @(*) begin
		adder_in_0 = 1'sb0;
		adder_in_1_pre_shift = 1'sb0;
		exp_full_diff = 1'sbx;
		exp_half_diff = 1'sbx;
		exp_quart_diff = 1'sbx;
		bigger_exp_full = 1'sbx;
		bigger_exp_half = 1'sbx;
		bigger_exp_quart = 1'sbx;
		case (mode)
			pe_pkg_PRECISION_CONFIG_32B:
				if ($signed(exp_full_in_0) > $signed(exp_full_in_1)) begin
					exp_full_diff = $signed(exp_full_in_0) - $signed(exp_full_in_1);
					adder_in_0[1+:posit_pkg_MANT_FULL_L] = mant_full_in_0;
					adder_in_1_pre_shift[1+:posit_pkg_MANT_FULL_L] = mant_full_in_1;
					bigger_exp_full = $signed(exp_full_in_0);
				end
				else begin
					exp_full_diff = $signed(exp_full_in_1) - $signed(exp_full_in_0);
					adder_in_0[1+:posit_pkg_MANT_FULL_L] = mant_full_in_1;
					adder_in_1_pre_shift[1+:posit_pkg_MANT_FULL_L] = mant_full_in_0;
					bigger_exp_full = $signed(exp_full_in_1);
				end
			pe_pkg_PRECISION_CONFIG_16B: begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i >= 0; i = i - 1)
					if ($signed(exp_half_in_0[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]) > $signed(exp_half_in_1[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L])) begin
						exp_half_diff[0 + (i * 10)+:10] = $signed(exp_half_in_0[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]) - $signed(exp_half_in_1[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]);
						adder_in_0[(i * posit_pkg_HALF_L) + 1+:posit_pkg_MANT_HALF_L] = mant_half_in_0[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L];
						adder_in_1_pre_shift[(i * posit_pkg_HALF_L) + 1+:posit_pkg_MANT_HALF_L] = mant_half_in_1[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L];
						bigger_exp_half[0 + (i * 10)+:10] = $signed(exp_half_in_0[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]);
					end
					else begin
						exp_half_diff[0 + (i * 10)+:10] = $signed(exp_half_in_1[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]) - $signed(exp_half_in_0[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]);
						adder_in_0[(i * posit_pkg_HALF_L) + 1+:posit_pkg_MANT_HALF_L] = mant_half_in_1[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L];
						adder_in_1_pre_shift[(i * posit_pkg_HALF_L) + 1+:posit_pkg_MANT_HALF_L] = mant_half_in_0[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L];
						bigger_exp_half[0 + (i * 10)+:10] = $signed(exp_half_in_1[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]);
					end
			end
			pe_pkg_PRECISION_CONFIG_8B: begin : sv2v_autoblock_2
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					if ($signed(exp_quart_in_0[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]) > $signed(exp_quart_in_1[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L])) begin
						exp_quart_diff[0 + (i * 7)+:7] = $signed(exp_quart_in_0[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]) - $signed(exp_quart_in_1[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]);
						adder_in_0[(i * posit_pkg_QUART_L) + 1+:posit_pkg_MANT_QUART_L] = mant_quart_in_0[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L];
						adder_in_1_pre_shift[(i * posit_pkg_QUART_L) + 1+:posit_pkg_MANT_QUART_L] = mant_quart_in_1[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L];
						bigger_exp_quart[0 + (i * 7)+:7] = $signed(exp_quart_in_0[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]);
					end
					else begin
						exp_quart_diff[0 + (i * 7)+:7] = $signed(exp_quart_in_1[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]) - $signed(exp_quart_in_0[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]);
						adder_in_0[(i * posit_pkg_QUART_L) + 1+:posit_pkg_MANT_QUART_L] = mant_quart_in_1[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L];
						adder_in_1_pre_shift[(i * posit_pkg_QUART_L) + 1+:posit_pkg_MANT_QUART_L] = mant_quart_in_0[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L];
						bigger_exp_quart[0 + (i * 7)+:7] = $signed(exp_quart_in_1[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]);
					end
			end
		endcase
	end
	always @(*) begin
		shift_val = 1'sb0;
		case (mode)
			pe_pkg_PRECISION_CONFIG_32B: begin : sv2v_autoblock_3
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					if (exp_full_diff > MAX_SHIFT_FULL)
						shift_val[i * 5+:5] = MAX_SHIFT_FULL;
					else
						shift_val[i * 5+:5] = exp_full_diff;
			end
			pe_pkg_PRECISION_CONFIG_16B: begin : sv2v_autoblock_4
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					if (exp_half_diff[0 + ((i / 2) * 10)+:10] > MAX_SHIFT_HALF)
						shift_val[i * 5+:5] = MAX_SHIFT_HALF;
					else
						shift_val[i * 5+:5] = exp_half_diff[0 + ((i / 2) * 10)+:10];
			end
			pe_pkg_PRECISION_CONFIG_8B: begin : sv2v_autoblock_5
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					if (exp_quart_diff[0 + (i * 7)+:7] > MAX_SHIFT_QUART)
						shift_val[i * 5+:5] = MAX_SHIFT_QUART;
					else
						shift_val[i * 5+:5] = exp_quart_diff[0 + (i * 7)+:7];
			end
		endcase
	end
	right_shift_decomposable #(
		.ARITH_SHIFT(0),
		.EXTENSION_BIT(0)
	) RIGHT_SHIFT_DECOMPOSABLE_INS(
		.in(adder_in_1_pre_shift),
		.shift_val(shift_val),
		.full_shift(1'b0),
		.mode(mode),
		.out(adder_in_1_post_shift)
	);
	adder_decomposable #(
		.EACH_ADDER_LEN(posit_pkg_QUART_L),
		.N_ADDERS(4)
	) ADDER_DECOMPOSABLE_INS(
		.in0(adder_in_0),
		.in1(adder_in_1_post_shift),
		.mode(mode),
		.out_quart(adder_out_quart),
		.out_half(adder_out_half),
		.out_full(adder_out_full)
	);
	assign adder_mant_out_full = adder_out_full[0+:27];
	always @(*) begin : sv2v_autoblock_6
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			adder_mant_out_half[i * 13+:13] = adder_out_half[(i * 17) + 0+:13];
	end
	always @(*) begin : sv2v_autoblock_7
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			adder_mant_out_quart[i * 7+:7] = adder_out_quart[(i * 9) + 0+:7];
	end
	always @(*)
		if (mant_full_in_0 == {25 {1'sb0}}) begin
			exp_full_out_pre = $signed(exp_full_in_1);
			mant_full_out_pre = {mant_full_in_1, 1'b0};
		end
		else if (mant_full_in_1 == {25 {1'sb0}}) begin
			exp_full_out_pre = $signed(exp_full_in_0);
			mant_full_out_pre = {mant_full_in_0, 1'b0};
		end
		else begin
			exp_full_out_pre = bigger_exp_full;
			mant_full_out_pre = adder_mant_out_full;
		end
	always @(*) begin : sv2v_autoblock_8
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			if (mant_half_in_0[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L] == {11 {1'sb0}}) begin
				exp_half_out_pre[0 + (i * 10)+:10] = $signed(exp_half_in_1[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]);
				mant_half_out_pre[i * 13+:13] = {mant_half_in_1[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L], 1'b0};
			end
			else if (mant_half_in_1[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L] == {11 {1'sb0}}) begin
				exp_half_out_pre[0 + (i * 10)+:10] = $signed(exp_half_in_0[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]);
				mant_half_out_pre[i * 13+:13] = {mant_half_in_0[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L], 1'b0};
			end
			else begin
				exp_half_out_pre[0 + (i * 10)+:10] = bigger_exp_half[0 + (i * 10)+:10];
				mant_half_out_pre[i * 13+:13] = adder_mant_out_half[i * 13+:13];
			end
	end
	always @(*) begin : sv2v_autoblock_9
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			if (mant_quart_in_0[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L] == {5 {1'sb0}}) begin
				exp_quart_out_pre[0 + (i * 7)+:7] = $signed(exp_quart_in_1[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]);
				mant_quart_out_pre[i * 7+:7] = {mant_quart_in_1[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L], 1'b0};
			end
			else if (mant_quart_in_1[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L] == {5 {1'sb0}}) begin
				exp_quart_out_pre[0 + (i * 7)+:7] = $signed(exp_quart_in_0[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]);
				mant_quart_out_pre[i * 7+:7] = {mant_quart_in_0[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L], 1'b0};
			end
			else begin
				exp_quart_out_pre[0 + (i * 7)+:7] = bigger_exp_quart[0 + (i * 7)+:7];
				mant_quart_out_pre[i * 7+:7] = adder_mant_out_quart[i * 7+:7];
			end
	end
	assign exp_full_out = exp_full_out_pre;
	assign exp_half_out = exp_half_out_pre;
	assign exp_quart_out = exp_quart_out_pre;
	assign mant_full_out = mant_full_out_pre;
	assign mant_half_out = mant_half_out_pre;
	assign mant_quart_out = mant_quart_out_pre;
endmodule
module multiplier_decomposable (
	in0,
	in1,
	mode,
	out_full,
	out_half,
	out_quarter
);
	parameter EACH_PART_LEN = 8;
	parameter N_PARTS = 4;
	input [(EACH_PART_LEN * N_PARTS) - 1:0] in0;
	input [(EACH_PART_LEN * N_PARTS) - 1:0] in1;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	output wire [((2 * EACH_PART_LEN) * N_PARTS) - 1:0] out_full;
	output wire [(2 * (EACH_PART_LEN * N_PARTS)) - 1:0] out_half;
	output wire [(4 * (EACH_PART_LEN * 2)) - 1:0] out_quarter;
	localparam TOTAL_LEN = EACH_PART_LEN * N_PARTS;
	reg [(2 * EACH_PART_LEN) - 1:0] partial_prods [N_PARTS - 1:0][N_PARTS - 1:0];
	wire [(2 * EACH_PART_LEN) - 1:0] partial_prods_0_0;
	wire [(2 * EACH_PART_LEN) - 1:0] partial_prods_0_1;
	wire [(2 * EACH_PART_LEN) - 1:0] partial_prods_1_0;
	wire [(2 * EACH_PART_LEN) - 1:0] partial_prods_1_1;
	wire [(2 * EACH_PART_LEN) - 1:0] partial_prods_2_2;
	wire [(2 * EACH_PART_LEN) - 1:0] partial_prods_2_3;
	wire [(2 * EACH_PART_LEN) - 1:0] partial_prods_3_2;
	wire [(2 * EACH_PART_LEN) - 1:0] partial_prods_3_3;
	reg [EACH_PART_LEN - 1:0] gated_in0 [N_PARTS - 1:0][N_PARTS - 1:0];
	reg [EACH_PART_LEN - 1:0] gated_in1 [N_PARTS - 1:0][N_PARTS - 1:0];
	wire [((2 * EACH_PART_LEN) * N_PARTS) - 1:0] out_full_pre;
	wire [(EACH_PART_LEN * N_PARTS) - 1:0] out_half_pre [3:0];
	wire [(EACH_PART_LEN * N_PARTS) - 1:0] out_half_pre_0_0;
	wire [(EACH_PART_LEN * N_PARTS) - 1:0] out_half_pre_0_1;
	wire [(EACH_PART_LEN * N_PARTS) - 1:0] out_half_pre_3_0;
	wire [(EACH_PART_LEN * N_PARTS) - 1:0] out_half_pre_3_1;
	reg [(4 * (EACH_PART_LEN * 2)) - 1:0] out_quarter_pre;
	localparam pe_pkg_PRECISION_CONFIG_16B = 1;
	localparam pe_pkg_PRECISION_CONFIG_32B = 0;
	localparam pe_pkg_PRECISION_CONFIG_8B = 2;
	always @(*) begin
		begin : sv2v_autoblock_1
			integer i;
			for (i = 0; i < N_PARTS; i = i + 1)
				begin : sv2v_autoblock_2
					integer j;
					for (j = 0; j < N_PARTS; j = j + 1)
						begin
							gated_in0[i][j] = 1'sb0;
							gated_in1[i][j] = 1'sb0;
						end
				end
		end
		case (mode)
			pe_pkg_PRECISION_CONFIG_32B: begin : sv2v_autoblock_3
				integer i;
				for (i = 0; i < N_PARTS; i = i + 1)
					begin : sv2v_autoblock_4
						integer j;
						for (j = 0; j < N_PARTS; j = j + 1)
							begin
								gated_in0[i][j] = in0[i * EACH_PART_LEN+:EACH_PART_LEN];
								gated_in1[i][j] = in1[j * EACH_PART_LEN+:EACH_PART_LEN];
							end
					end
			end
			pe_pkg_PRECISION_CONFIG_16B: begin : sv2v_autoblock_5
				integer i;
				for (i = 0; i < N_PARTS; i = i + 1)
					begin : sv2v_autoblock_6
						integer j;
						for (j = 0; j < N_PARTS; j = j + 1)
							begin
								if ((i < 2) && (j < 2)) begin
									gated_in0[i][j] = in0[i * EACH_PART_LEN+:EACH_PART_LEN];
									gated_in1[i][j] = in1[j * EACH_PART_LEN+:EACH_PART_LEN];
								end
								if ((i >= 2) && (j >= 2)) begin
									gated_in0[i][j] = in0[i * EACH_PART_LEN+:EACH_PART_LEN];
									gated_in1[i][j] = in1[j * EACH_PART_LEN+:EACH_PART_LEN];
								end
							end
					end
			end
			pe_pkg_PRECISION_CONFIG_8B: begin : sv2v_autoblock_7
				integer i;
				for (i = 0; i < N_PARTS; i = i + 1)
					begin : sv2v_autoblock_8
						integer j;
						for (j = 0; j < N_PARTS; j = j + 1)
							if (i == j) begin
								gated_in0[i][j] = in0[i * EACH_PART_LEN+:EACH_PART_LEN];
								gated_in1[i][j] = in1[j * EACH_PART_LEN+:EACH_PART_LEN];
							end
					end
			end
		endcase
	end
	always @(*) begin : sv2v_autoblock_9
		integer i;
		for (i = 0; i < N_PARTS; i = i + 1)
			begin : sv2v_autoblock_10
				integer j;
				for (j = 0; j < N_PARTS; j = j + 1)
					partial_prods[i][j] = gated_in0[i][j] * gated_in1[i][j];
			end
	end
	always @(*) begin
		out_quarter_pre = 1'sbx;
		begin : sv2v_autoblock_11
			integer i;
			for (i = 3; i >= 0; i = i - 1)
				out_quarter_pre[i * (EACH_PART_LEN * 2)+:EACH_PART_LEN * 2] = partial_prods[i][i];
		end
	end
	assign out_half_pre[0] = (({16'b0000000000000000, partial_prods[0][0]} + {8'b00000000, partial_prods[0][1], 8'b00000000}) + {8'b00000000, partial_prods[1][0], 8'b00000000}) + {partial_prods[1][1], 16'b0000000000000000};
	assign out_half_pre[3] = (({16'b0000000000000000, partial_prods[2][2]} + {8'b00000000, partial_prods[2][3], 8'b00000000}) + {8'b00000000, partial_prods[3][2], 8'b00000000}) + {partial_prods[3][3], 16'b0000000000000000};
	assign out_half_pre[1] = {gated_in0[1][0], gated_in0[0][0]} * {gated_in1[0][3], gated_in1[0][2]};
	assign out_half_pre[2] = {gated_in0[3][0], gated_in0[2][0]} * {gated_in1[0][1], gated_in1[0][0]};
	assign out_full_pre = (({32'b00000000000000000000000000000000, out_half_pre[0]} + {16'b0000000000000000, out_half_pre[1], 16'b0000000000000000}) + {16'b0000000000000000, out_half_pre[2], 16'b0000000000000000}) + {out_half_pre[3], 32'b00000000000000000000000000000000};
	assign out_full = out_full_pre;
	assign out_half[0+:EACH_PART_LEN * N_PARTS] = out_half_pre[0];
	assign out_half[EACH_PART_LEN * N_PARTS+:EACH_PART_LEN * N_PARTS] = out_half_pre[3];
	assign out_quarter = out_quarter_pre;
endmodule
module flt_multiplier_decomposable (
	exp_full_in_0,
	mant_full_in_0,
	exp_half_in_0,
	mant_half_in_0,
	exp_quart_in_0,
	mant_quart_in_0,
	exp_full_in_1,
	mant_full_in_1,
	exp_half_in_1,
	mant_half_in_1,
	exp_quart_in_1,
	mant_quart_in_1,
	mode,
	exp_full_out,
	exp_half_out,
	exp_quart_out,
	mant_full_out,
	mant_half_out,
	mant_quart_out
);
	localparam posit_pkg_ES_FULL_L = 6;
	localparam posit_pkg_FULL_L = 32;
	localparam posit_pkg_EXP_COMBINED_FULL_L = 12;
	input wire [11:0] exp_full_in_0;
	localparam posit_pkg_MANT_FULL_L = 25;
	input wire [24:0] mant_full_in_0;
	localparam posit_pkg_ES_HALF_L = 4;
	localparam posit_pkg_HALF_L = 16;
	localparam posit_pkg_EXP_COMBINED_HALF_L = 9;
	input wire [17:0] exp_half_in_0;
	localparam posit_pkg_MANT_HALF_L = 11;
	input wire [21:0] mant_half_in_0;
	localparam posit_pkg_ES_QUART_L = 2;
	localparam posit_pkg_QUART_L = 8;
	localparam posit_pkg_EXP_COMBINED_QUART_L = 6;
	input wire [23:0] exp_quart_in_0;
	localparam posit_pkg_MANT_QUART_L = 5;
	input wire [19:0] mant_quart_in_0;
	input wire [11:0] exp_full_in_1;
	input wire [24:0] mant_full_in_1;
	input wire [17:0] exp_half_in_1;
	input wire [21:0] mant_half_in_1;
	input wire [23:0] exp_quart_in_1;
	input wire [19:0] mant_quart_in_1;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	output wire [posit_pkg_EXP_COMBINED_FULL_L:0] exp_full_out;
	output wire [19:0] exp_half_out;
	output wire [27:0] exp_quart_out;
	output wire [26:0] mant_full_out;
	output wire [25:0] mant_half_out;
	output wire [27:0] mant_quart_out;
	localparam MAX_EXP_FULL = 2047;
	localparam MIN_EXP_FULL = -2048;
	localparam MAX_EXP_HALF = 255;
	localparam MIN_EXP_HALF = -256;
	localparam MAX_EXP_QUART = 31;
	localparam MIN_EXP_QUART = -32;
	reg [31:0] mul_in_0;
	reg [31:0] mul_in_1;
	wire [63:0] mul_out_full;
	wire [63:0] mul_out_half;
	wire [63:0] mul_out_quart;
	wire [posit_pkg_EXP_COMBINED_FULL_L:0] res_exp_full;
	reg [19:0] res_exp_half;
	reg [27:0] res_exp_quart;
	wire [posit_pkg_EXP_COMBINED_FULL_L:0] exp_full_out_pre;
	wire [19:0] exp_half_out_pre;
	wire [27:0] exp_quart_out_pre;
	wire [26:0] mant_full_out_pre;
	reg [25:0] mant_half_out_pre;
	reg [27:0] mant_quart_out_pre;
	assign res_exp_full = $signed(exp_full_in_0) + $signed(exp_full_in_1);
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			res_exp_half[0 + (i * 10)+:10] = $signed(exp_half_in_0[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]) + $signed(exp_half_in_1[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L]);
	end
	always @(*) begin : sv2v_autoblock_2
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			res_exp_quart[0 + (i * 7)+:7] = $signed(exp_quart_in_0[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]) + $signed(exp_quart_in_1[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L]);
	end
	localparam pe_pkg_PRECISION_CONFIG_16B = 1;
	localparam pe_pkg_PRECISION_CONFIG_32B = 0;
	localparam pe_pkg_PRECISION_CONFIG_8B = 2;
	always @(*) begin
		mul_in_0 = 1'sb0;
		mul_in_1 = 1'sb0;
		case (mode)
			pe_pkg_PRECISION_CONFIG_32B: begin
				mul_in_0 = mant_full_in_0;
				mul_in_1 = mant_full_in_1;
			end
			pe_pkg_PRECISION_CONFIG_16B: begin : sv2v_autoblock_3
				integer i;
				for (i = 1; i >= 0; i = i - 1)
					begin
						mul_in_0[i * posit_pkg_HALF_L+:posit_pkg_HALF_L] = mant_half_in_0[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L];
						mul_in_1[i * posit_pkg_HALF_L+:posit_pkg_HALF_L] = mant_half_in_1[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L];
					end
			end
			pe_pkg_PRECISION_CONFIG_8B: begin : sv2v_autoblock_4
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					begin
						mul_in_0[i * posit_pkg_QUART_L+:posit_pkg_QUART_L] = mant_quart_in_0[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L];
						mul_in_1[i * posit_pkg_QUART_L+:posit_pkg_QUART_L] = mant_quart_in_1[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L];
					end
			end
		endcase
	end
	multiplier_decomposable #(
		.EACH_PART_LEN(posit_pkg_QUART_L),
		.N_PARTS(4)
	) MULTIPLIER_DECOMPOSABLE_INS(
		.in0(mul_in_0),
		.in1(mul_in_1),
		.mode(mode),
		.out_full(mul_out_full),
		.out_half(mul_out_half),
		.out_quarter(mul_out_quart)
	);
	assign mant_full_out_pre = mul_out_full[49-:27];
	always @(*) begin : sv2v_autoblock_5
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			mant_half_out_pre[i * 13+:13] = mul_out_half[(i * 32) + 21-:13];
	end
	always @(*) begin : sv2v_autoblock_6
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			mant_quart_out_pre[i * 7+:7] = mul_out_quart[(i * 16) + 9-:7];
	end
	assign exp_full_out = res_exp_full;
	assign mant_full_out = mant_full_out_pre;
	assign exp_half_out = res_exp_half;
	assign mant_half_out = mant_half_out_pre;
	assign exp_quart_out = res_exp_quart;
	assign mant_quart_out = mant_quart_out_pre;
endmodule
module pack_fields (
	out,
	exp_full,
	mant_full,
	exp_half,
	mant_half,
	exp_quart,
	mant_quart,
	mode
);
	localparam posit_pkg_FULL_L = 32;
	output wire [31:0] out;
	localparam posit_pkg_ES_FULL_L = 6;
	localparam posit_pkg_EXP_COMBINED_FULL_L = 12;
	input wire [11:0] exp_full;
	localparam posit_pkg_MANT_FULL_L = 25;
	input wire [24:0] mant_full;
	localparam posit_pkg_ES_HALF_L = 4;
	localparam posit_pkg_HALF_L = 16;
	localparam posit_pkg_EXP_COMBINED_HALF_L = 9;
	input wire [17:0] exp_half;
	localparam posit_pkg_MANT_HALF_L = 11;
	input wire [21:0] mant_half;
	localparam posit_pkg_ES_QUART_L = 2;
	localparam posit_pkg_QUART_L = 8;
	localparam posit_pkg_EXP_COMBINED_QUART_L = 6;
	input wire [23:0] exp_quart;
	localparam posit_pkg_MANT_QUART_L = 5;
	input wire [19:0] mant_quart;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	wire [31:0] out_pre;
	wire all_zeroes_full;
	reg [1:0] all_zeroes_half;
	reg [3:0] all_zeroes_quart;
	wire [31:0] shift_in_reversed;
	wire [31:0] shift_out_reversed;
	reg [31:0] shift_in;
	wire [31:0] shift_out;
	wire [5:0] exp_fx_len_full;
	reg [7:0] exp_fx_len_half;
	reg [7:0] exp_fx_len_quart;
	localparam posit_pkg_REGIME_FULL_L = 6;
	wire [5:0] regime_full;
	localparam posit_pkg_REGIME_HALF_L = 5;
	reg [9:0] regime_half;
	localparam posit_pkg_REGIME_QUART_L = 4;
	reg [15:0] regime_quart;
	reg [19:0] shift_val;
	assign all_zeroes_full = (mant_full == 0 ? 1 : 0);
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			all_zeroes_half[i] = (mant_half[i * posit_pkg_MANT_HALF_L+:posit_pkg_MANT_HALF_L] == 0 ? 1 : 0);
	end
	always @(*) begin : sv2v_autoblock_2
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			all_zeroes_quart[i] = (mant_quart[i * posit_pkg_MANT_QUART_L+:posit_pkg_MANT_QUART_L] == 0 ? 1 : 0);
	end
	assign regime_full = exp_full >> posit_pkg_ES_FULL_L;
	assign exp_fx_len_full = exp_full[0+:posit_pkg_ES_FULL_L];
	always @(*) begin : sv2v_autoblock_3
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			begin
				regime_half[i * posit_pkg_REGIME_HALF_L+:posit_pkg_REGIME_HALF_L] = exp_half[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_EXP_COMBINED_HALF_L] >> posit_pkg_ES_HALF_L;
				exp_fx_len_half[i * posit_pkg_ES_HALF_L+:posit_pkg_ES_HALF_L] = exp_half[i * posit_pkg_EXP_COMBINED_HALF_L+:posit_pkg_ES_HALF_L];
			end
	end
	always @(*) begin : sv2v_autoblock_4
		integer i;
		for (i = 3; i >= 0; i = i - 1)
			begin
				regime_quart[i * posit_pkg_REGIME_QUART_L+:posit_pkg_REGIME_QUART_L] = exp_quart[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_EXP_COMBINED_QUART_L] >> posit_pkg_ES_QUART_L;
				exp_fx_len_quart[i * posit_pkg_ES_QUART_L+:posit_pkg_ES_QUART_L] = exp_quart[i * posit_pkg_EXP_COMBINED_QUART_L+:posit_pkg_ES_QUART_L];
			end
	end
	localparam pe_pkg_PRECISION_CONFIG_16B = 1;
	localparam pe_pkg_PRECISION_CONFIG_32B = 0;
	localparam pe_pkg_PRECISION_CONFIG_8B = 2;
	always @(*) begin
		shift_in = 1'sbx;
		case (mode)
			pe_pkg_PRECISION_CONFIG_32B: begin
				if (regime_full[5] == 0)
					shift_in = {2'b10, exp_fx_len_full, mant_full[0+:24]};
				else
					shift_in = {2'b01, exp_fx_len_full, mant_full[0+:24]};
				if (all_zeroes_full)
					shift_in = 1'sb0;
			end
			pe_pkg_PRECISION_CONFIG_16B: begin : sv2v_autoblock_5
				integer i;
				for (i = 1; i >= 0; i = i - 1)
					begin
						if (regime_half[(i * posit_pkg_REGIME_HALF_L) + 4] == 0)
							shift_in[i * posit_pkg_HALF_L+:posit_pkg_HALF_L] = {2'b10, exp_fx_len_half[i * posit_pkg_ES_HALF_L+:posit_pkg_ES_HALF_L], mant_half[i * posit_pkg_MANT_HALF_L+:10]};
						else
							shift_in[i * posit_pkg_HALF_L+:posit_pkg_HALF_L] = {2'b01, exp_fx_len_half[i * posit_pkg_ES_HALF_L+:posit_pkg_ES_HALF_L], mant_half[i * posit_pkg_MANT_HALF_L+:10]};
						if (all_zeroes_half[i])
							shift_in[i * posit_pkg_HALF_L+:posit_pkg_HALF_L] = 1'sb0;
					end
			end
			pe_pkg_PRECISION_CONFIG_8B: begin : sv2v_autoblock_6
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					begin
						if (regime_quart[(i * posit_pkg_REGIME_QUART_L) + 3] == 0)
							shift_in[i * posit_pkg_QUART_L+:posit_pkg_QUART_L] = {2'b10, exp_fx_len_quart[i * posit_pkg_ES_QUART_L+:posit_pkg_ES_QUART_L], mant_quart[i * posit_pkg_MANT_QUART_L+:4]};
						else
							shift_in[i * posit_pkg_QUART_L+:posit_pkg_QUART_L] = {2'b01, exp_fx_len_quart[i * posit_pkg_ES_QUART_L+:posit_pkg_ES_QUART_L], mant_quart[i * posit_pkg_MANT_QUART_L+:4]};
						if (all_zeroes_quart[i])
							shift_in[i * posit_pkg_QUART_L+:posit_pkg_QUART_L] = 1'sb0;
					end
			end
		endcase
	end
	always @(*) begin
		shift_val = 1'sbx;
		case (mode)
			pe_pkg_PRECISION_CONFIG_32B: begin : sv2v_autoblock_7
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					if (regime_full[5])
						shift_val[0 + (i * 5)+:5] = -($signed(regime_full) + 1);
					else
						shift_val[0 + (i * 5)+:5] = regime_full;
			end
			pe_pkg_PRECISION_CONFIG_16B: begin : sv2v_autoblock_8
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					if (regime_half[((i / 2) * posit_pkg_REGIME_HALF_L) + 4])
						shift_val[0 + (i * 5)+:5] = -($signed(regime_half[(i / 2) * posit_pkg_REGIME_HALF_L+:posit_pkg_REGIME_HALF_L]) + 1);
					else
						shift_val[0 + (i * 5)+:5] = regime_half[(i / 2) * posit_pkg_REGIME_HALF_L+:posit_pkg_REGIME_HALF_L];
			end
			pe_pkg_PRECISION_CONFIG_8B: begin : sv2v_autoblock_9
				integer i;
				for (i = 3; i >= 0; i = i - 1)
					if (regime_quart[(i * posit_pkg_REGIME_QUART_L) + 3])
						shift_val[0 + (i * 5)+:5] = -($signed(regime_quart[i * posit_pkg_REGIME_QUART_L+:posit_pkg_REGIME_QUART_L]) + 1);
					else
						shift_val[0 + (i * 5)+:5] = regime_quart[i * posit_pkg_REGIME_QUART_L+:posit_pkg_REGIME_QUART_L];
			end
		endcase
	end
	right_shift_decomposable #(.ARITH_SHIFT(1)) RIGHT_SHIFT_DECOMPOSABLE_INS(
		.in(shift_in),
		.shift_val(shift_val),
		.full_shift(1'b0),
		.mode(mode),
		.out(shift_out)
	);
	assign out = shift_out;
endmodule
module posit_arith_unit (
	clk,
	in_0,
	in_1,
	out,
	mode,
	mul_en
);
	input clk;
	localparam posit_pkg_FULL_L = 32;
	input [31:0] in_0;
	input [31:0] in_1;
	output wire [31:0] out;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] mode;
	input mul_en;
	localparam posit_pkg_ES_FULL_L = 6;
	localparam posit_pkg_EXP_COMBINED_FULL_L = 12;
	wire [11:0] exp_full_in_0;
	localparam posit_pkg_MANT_FULL_L = 25;
	wire [24:0] mant_full_in_0;
	localparam posit_pkg_ES_HALF_L = 4;
	localparam posit_pkg_HALF_L = 16;
	localparam posit_pkg_EXP_COMBINED_HALF_L = 9;
	wire [17:0] exp_half_in_0;
	localparam posit_pkg_MANT_HALF_L = 11;
	wire [21:0] mant_half_in_0;
	localparam posit_pkg_ES_QUART_L = 2;
	localparam posit_pkg_QUART_L = 8;
	localparam posit_pkg_EXP_COMBINED_QUART_L = 6;
	wire [23:0] exp_quart_in_0;
	localparam posit_pkg_MANT_QUART_L = 5;
	wire [19:0] mant_quart_in_0;
	wire [11:0] exp_full_in_1;
	wire [24:0] mant_full_in_1;
	wire [17:0] exp_half_in_1;
	wire [21:0] mant_half_in_1;
	wire [23:0] exp_quart_in_1;
	wire [19:0] mant_quart_in_1;
	wire [11:0] add_exp_full_in_0;
	wire [24:0] add_mant_full_in_0;
	wire [17:0] add_exp_half_in_0;
	wire [21:0] add_mant_half_in_0;
	wire [23:0] add_exp_quart_in_0;
	wire [19:0] add_mant_quart_in_0;
	wire [11:0] add_exp_full_in_1;
	wire [24:0] add_mant_full_in_1;
	wire [17:0] add_exp_half_in_1;
	wire [21:0] add_mant_half_in_1;
	wire [23:0] add_exp_quart_in_1;
	wire [19:0] add_mant_quart_in_1;
	wire [11:0] mul_exp_full_in_0;
	wire [24:0] mul_mant_full_in_0;
	wire [17:0] mul_exp_half_in_0;
	wire [21:0] mul_mant_half_in_0;
	wire [23:0] mul_exp_quart_in_0;
	wire [19:0] mul_mant_quart_in_0;
	wire [11:0] mul_exp_full_in_1;
	wire [24:0] mul_mant_full_in_1;
	wire [17:0] mul_exp_half_in_1;
	wire [21:0] mul_mant_half_in_1;
	wire [23:0] mul_exp_quart_in_1;
	wire [19:0] mul_mant_quart_in_1;
	wire [posit_pkg_EXP_COMBINED_FULL_L:0] adder_exp_full_out;
	wire [19:0] adder_exp_half_out;
	wire [27:0] adder_exp_quart_out;
	wire [26:0] adder_mant_full_out;
	wire [25:0] adder_mant_half_out;
	wire [27:0] adder_mant_quart_out;
	wire [posit_pkg_EXP_COMBINED_FULL_L:0] mult_exp_full_out;
	wire [19:0] mult_exp_half_out;
	wire [27:0] mult_exp_quart_out;
	wire [26:0] mult_mant_full_out;
	wire [25:0] mult_mant_half_out;
	wire [27:0] mult_mant_quart_out;
	wire [posit_pkg_EXP_COMBINED_FULL_L:0] pre_round_exp_full;
	wire [19:0] pre_round_exp_half;
	wire [27:0] pre_round_exp_quart;
	wire [26:0] pre_round_mant_full;
	wire [25:0] pre_round_mant_half;
	wire [27:0] pre_round_mant_quart;
	wire [11:0] pre_pack_exp_full;
	wire [24:0] pre_pack_mant_full;
	wire [17:0] pre_pack_exp_half;
	wire [21:0] pre_pack_mant_half;
	wire [23:0] pre_pack_exp_quart;
	wire [19:0] pre_pack_mant_quart;
	assign pre_round_exp_full = (mul_en ? mult_exp_full_out : adder_exp_full_out);
	assign pre_round_mant_full = (mul_en ? mult_mant_full_out : adder_mant_full_out);
	assign pre_round_exp_half = (mul_en ? mult_exp_half_out : adder_exp_half_out);
	assign pre_round_mant_half = (mul_en ? mult_mant_half_out : adder_mant_half_out);
	assign pre_round_exp_quart = (mul_en ? mult_exp_quart_out : adder_exp_quart_out);
	assign pre_round_mant_quart = (mul_en ? mult_mant_quart_out : adder_mant_quart_out);
	assign mul_exp_full_in_0 = (mul_en ? exp_full_in_0 : {12 {1'sb0}});
	assign mul_mant_full_in_0 = (mul_en ? mant_full_in_0 : {25 {1'sb0}});
	assign mul_exp_half_in_0 = (mul_en ? exp_half_in_0 : {18 {1'sb0}});
	assign mul_mant_half_in_0 = (mul_en ? mant_half_in_0 : {22 {1'sb0}});
	assign mul_exp_quart_in_0 = (mul_en ? exp_quart_in_0 : {24 {1'sb0}});
	assign mul_mant_quart_in_0 = (mul_en ? mant_quart_in_0 : {20 {1'sb0}});
	assign mul_exp_full_in_1 = (mul_en ? exp_full_in_1 : {12 {1'sb0}});
	assign mul_mant_full_in_1 = (mul_en ? mant_full_in_1 : {25 {1'sb0}});
	assign mul_exp_half_in_1 = (mul_en ? exp_half_in_1 : {18 {1'sb0}});
	assign mul_mant_half_in_1 = (mul_en ? mant_half_in_1 : {22 {1'sb0}});
	assign mul_exp_quart_in_1 = (mul_en ? exp_quart_in_1 : {24 {1'sb0}});
	assign mul_mant_quart_in_1 = (mul_en ? mant_quart_in_1 : {20 {1'sb0}});
	assign add_exp_full_in_0 = (~mul_en ? exp_full_in_0 : {12 {1'sb0}});
	assign add_mant_full_in_0 = (~mul_en ? mant_full_in_0 : {25 {1'sb0}});
	assign add_exp_half_in_0 = (~mul_en ? exp_half_in_0 : {18 {1'sb0}});
	assign add_mant_half_in_0 = (~mul_en ? mant_half_in_0 : {22 {1'sb0}});
	assign add_exp_quart_in_0 = (~mul_en ? exp_quart_in_0 : {24 {1'sb0}});
	assign add_mant_quart_in_0 = (~mul_en ? mant_quart_in_0 : {20 {1'sb0}});
	assign add_exp_full_in_1 = (~mul_en ? exp_full_in_1 : {12 {1'sb0}});
	assign add_mant_full_in_1 = (~mul_en ? mant_full_in_1 : {25 {1'sb0}});
	assign add_exp_half_in_1 = (~mul_en ? exp_half_in_1 : {18 {1'sb0}});
	assign add_mant_half_in_1 = (~mul_en ? mant_half_in_1 : {22 {1'sb0}});
	assign add_exp_quart_in_1 = (~mul_en ? exp_quart_in_1 : {24 {1'sb0}});
	assign add_mant_quart_in_1 = (~mul_en ? mant_quart_in_1 : {20 {1'sb0}});
	extract_fields #(
		.ES_L_32(posit_pkg_ES_FULL_L),
		.ES_L_16(posit_pkg_ES_HALF_L),
		.ES_L_8(posit_pkg_ES_QUART_L)
	) EXTRACT_FIELDS_INS_0(
		.clk(clk),
		.in(in_0),
		.exp32(exp_full_in_0),
		.mant32(mant_full_in_0),
		.exp16(exp_half_in_0),
		.mant16(mant_half_in_0),
		.exp8(exp_quart_in_0),
		.mant8(mant_quart_in_0),
		.mode(mode)
	);
	extract_fields #(
		.ES_L_32(posit_pkg_ES_FULL_L),
		.ES_L_16(posit_pkg_ES_HALF_L),
		.ES_L_8(posit_pkg_ES_QUART_L)
	) EXTRACT_FIELDS_INS_1(
		.clk(clk),
		.in(in_1),
		.exp32(exp_full_in_1),
		.mant32(mant_full_in_1),
		.exp16(exp_half_in_1),
		.mant16(mant_half_in_1),
		.exp8(exp_quart_in_1),
		.mant8(mant_quart_in_1),
		.mode(mode)
	);
	flt_adder_decomposable FLT_ADDER_DECOMPOSABLE_INS(
		.exp_full_in_0(add_exp_full_in_0),
		.mant_full_in_0(add_mant_full_in_0),
		.exp_half_in_0(add_exp_half_in_0),
		.mant_half_in_0(add_mant_half_in_0),
		.exp_quart_in_0(add_exp_quart_in_0),
		.mant_quart_in_0(add_mant_quart_in_0),
		.exp_full_in_1(add_exp_full_in_1),
		.mant_full_in_1(add_mant_full_in_1),
		.exp_half_in_1(add_exp_half_in_1),
		.mant_half_in_1(add_mant_half_in_1),
		.exp_quart_in_1(add_exp_quart_in_1),
		.mant_quart_in_1(add_mant_quart_in_1),
		.mode(mode),
		.exp_full_out(adder_exp_full_out),
		.exp_half_out(adder_exp_half_out),
		.exp_quart_out(adder_exp_quart_out),
		.mant_full_out(adder_mant_full_out),
		.mant_half_out(adder_mant_half_out),
		.mant_quart_out(adder_mant_quart_out)
	);
	flt_multiplier_decomposable FLT_MULTIPLIER_DECOMPOSABLE_INS(
		.exp_full_in_0(mul_exp_full_in_0),
		.mant_full_in_0(mul_mant_full_in_0),
		.exp_half_in_0(mul_exp_half_in_0),
		.mant_half_in_0(mul_mant_half_in_0),
		.exp_quart_in_0(mul_exp_quart_in_0),
		.mant_quart_in_0(mul_mant_quart_in_0),
		.exp_full_in_1(mul_exp_full_in_1),
		.mant_full_in_1(mul_mant_full_in_1),
		.exp_half_in_1(mul_exp_half_in_1),
		.mant_half_in_1(mul_mant_half_in_1),
		.exp_quart_in_1(mul_exp_quart_in_1),
		.mant_quart_in_1(mul_mant_quart_in_1),
		.mode(mode),
		.exp_full_out(mult_exp_full_out),
		.exp_half_out(mult_exp_half_out),
		.exp_quart_out(mult_exp_quart_out),
		.mant_full_out(mult_mant_full_out),
		.mant_half_out(mult_mant_half_out),
		.mant_quart_out(mult_mant_quart_out)
	);
	round_norm_overflow_underflow ROUND_NORM_OVERFLOW_UNDERFLOW_INS(
		.exp_full_in(pre_round_exp_full),
		.exp_half_in(pre_round_exp_half),
		.exp_quart_in(pre_round_exp_quart),
		.mant_full_in(pre_round_mant_full),
		.mant_half_in(pre_round_mant_half),
		.mant_quart_in(pre_round_mant_quart),
		.exp_full_out(pre_pack_exp_full),
		.mant_full_out(pre_pack_mant_full),
		.exp_half_out(pre_pack_exp_half),
		.mant_half_out(pre_pack_mant_half),
		.exp_quart_out(pre_pack_exp_quart),
		.mant_quart_out(pre_pack_mant_quart)
	);
	pack_fields PACK_FIELDS_INS(
		.out(out),
		.exp_full(pre_pack_exp_full),
		.mant_full(pre_pack_mant_full),
		.exp_half(pre_pack_exp_half),
		.mant_half(pre_pack_mant_half),
		.exp_quart(pre_pack_exp_quart),
		.mant_quart(pre_pack_mant_quart),
		.mode(mode)
	);
endmodule
module pe_operator (
	clk,
	rst,
	in_0,
	in_1,
	out,
	opcode,
	precision_config
);
	input clk;
	input rst;
	localparam hw_pkg_DATA_L = 32;
	input [31:0] in_0;
	input [31:0] in_1;
	output wire [31:0] out;
	localparam hw_pkg_OPCODE_L = 4;
	input [3:0] opcode;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] precision_config;
	reg [31:0] out_pre;
	wire [31:0] sum_out;
	wire [31:0] prod_out;
	reg mul_en;
	wire [31:0] posit_out;
	reg [31:0] in_0_gated;
	reg [31:0] in_1_gated;
	wire in_0_bigger;
	assign in_0_bigger = ($unsigned(in_0) > $unsigned(in_1) ? 1 : 0);
	posit_arith_unit POSIT_ARITH_UNIT_INS(
		.clk(clk),
		.in_0(in_0_gated),
		.in_1(in_1_gated),
		.out(posit_out),
		.mode(precision_config),
		.mul_en(mul_en)
	);
	localparam pe_pkg_MAX_OPCODE = 7;
	localparam pe_pkg_MIN_OPCODE = 8;
	localparam pe_pkg_PASS_OPCODE = 6;
	localparam pe_pkg_PROD_OPCODE = 2;
	localparam pe_pkg_SUM_OPCODE = 1;
	always @(*) begin
		mul_en = 0;
		in_0_gated = 1'sb0;
		in_1_gated = 1'sb0;
		out_pre = 1'sb0;
		case (opcode)
			pe_pkg_SUM_OPCODE: begin
				in_0_gated = in_0;
				in_1_gated = in_1;
				out_pre = posit_out;
			end
			pe_pkg_PROD_OPCODE: begin
				in_0_gated = in_0;
				in_1_gated = in_1;
				out_pre = posit_out;
				mul_en = 1;
			end
			pe_pkg_PASS_OPCODE: out_pre = in_0;
			pe_pkg_MAX_OPCODE: out_pre = (in_0_bigger ? in_0 : in_1);
			pe_pkg_MIN_OPCODE: out_pre = (in_0_bigger ? in_1 : in_0);
			default: out_pre = 1'sb0;
		endcase
	end
	assign out = out_pre;
endmodule
module pe_instr_decd (
	instr,
	opcode,
	reg_rd_addr_0,
	reg_rd_addr_1,
	operator_reg_wr_addr,
	ld_0_en,
	ld_1_en,
	st_en,
	ld_stream_len
);
	localparam hw_pkg_OPCODE_L = 4;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam hw_pkg_INSTR_L = 22;
	input [21:0] instr;
	output wire [3:0] opcode;
	output wire [4:0] reg_rd_addr_0;
	output wire [4:0] reg_rd_addr_1;
	output wire [4:0] operator_reg_wr_addr;
	output wire ld_0_en;
	output wire ld_1_en;
	output wire st_en;
	localparam pe_pkg_LD_STREAM_CNT_L = 15;
	output wire [14:0] ld_stream_len;
	assign opcode = instr[3:0];
	localparam pe_pkg_INPUT_REG_0_L = hw_pkg_REG_ADDR_L;
	localparam pe_pkg_INPUT_REG_0_S = hw_pkg_OPCODE_L;
	assign reg_rd_addr_0 = instr[pe_pkg_INPUT_REG_0_S+:pe_pkg_INPUT_REG_0_L];
	localparam pe_pkg_INPUT_REG_1_L = hw_pkg_REG_ADDR_L;
	localparam pe_pkg_INPUT_REG_1_S = 9;
	assign reg_rd_addr_1 = instr[pe_pkg_INPUT_REG_1_S+:pe_pkg_INPUT_REG_1_L];
	localparam pe_pkg_OUTPUT_REG_L = hw_pkg_REG_ADDR_L;
	localparam pe_pkg_OUTPUT_REG_S = 14;
	assign operator_reg_wr_addr = instr[pe_pkg_OUTPUT_REG_S+:pe_pkg_OUTPUT_REG_L];
	localparam pe_pkg_LD_0_EN_S = 19;
	assign ld_0_en = instr[pe_pkg_LD_0_EN_S+:1];
	localparam pe_pkg_LD_1_EN_S = 20;
	assign ld_1_en = instr[pe_pkg_LD_1_EN_S+:1];
	localparam pe_pkg_ST_EN_S = 21;
	assign st_en = instr[pe_pkg_ST_EN_S+:1];
	localparam pe_pkg_SET_LD_STREAM_LEN_L = pe_pkg_LD_STREAM_CNT_L;
	localparam pe_pkg_SET_LD_STREAM_LEN_S = hw_pkg_OPCODE_L;
	assign ld_stream_len = instr[pe_pkg_SET_LD_STREAM_LEN_S+:pe_pkg_SET_LD_STREAM_LEN_L];
endmodule
module pe_func_unit_interface_flow_control_ld (
	clk,
	rst,
	ifc_en,
	ifc_unblocked,
	instr_done,
	reg_en,
	memory_unit_rdy,
	func_unit_rdy
);
	input clk;
	input rst;
	input ifc_en;
	output wire ifc_unblocked;
	input instr_done;
	output wire reg_en;
	input memory_unit_rdy;
	output wire func_unit_rdy;
	wire func_unit_rdy_pre;
	assign func_unit_rdy_pre = (ifc_en & memory_unit_rdy) & instr_done;
	assign func_unit_rdy = func_unit_rdy_pre;
	assign ifc_unblocked = ~ifc_en | memory_unit_rdy;
	assign reg_en = func_unit_rdy_pre;
endmodule
module pe_func_unit_interface_flow_control_st (
	clk,
	rst,
	ifc_en,
	ifc_unblocked,
	instr_done,
	reg_en,
	memory_unit_rdy,
	func_unit_rdy
);
	input clk;
	input rst;
	input ifc_en;
	output wire ifc_unblocked;
	input instr_done;
	output wire reg_en;
	input memory_unit_rdy;
	output wire func_unit_rdy;
	reg done;
	assign func_unit_rdy = ifc_en & ~done;
	assign ifc_unblocked = (~ifc_en | done) | memory_unit_rdy;
	assign reg_en = (ifc_en & memory_unit_rdy) & ~done;
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			done <= 0;
		else if (done == 0) begin
			if ((ifc_en & memory_unit_rdy) & ~instr_done)
				done <= 1;
		end
		else if (instr_done)
			done <= 0;
endmodule
module pe_func_unit (
	clk,
	rst,
	instr,
	instr_req,
	instr_ack,
	ld_0_data,
	ld_0_addr,
	ld_0_vld,
	ld_0_rdy,
	ld_1_data,
	ld_1_addr,
	ld_1_vld,
	ld_1_rdy,
	st_data,
	st_req,
	st_ack,
	ld_stream_len,
	ld_stream_len_vld,
	all_stored,
	global_barrier_reached,
	global_barrier_reached_by_all_pes,
	precision_config,
	monitor,
	monitor_pe_out,
	monitor_instr
);
	input clk;
	input rst;
	localparam hw_pkg_OPCODE_L = 4;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam hw_pkg_INSTR_L = 22;
	input [21:0] instr;
	input instr_req;
	output wire instr_ack;
	localparam hw_pkg_DATA_L = 32;
	input [31:0] ld_0_data;
	input [4:0] ld_0_addr;
	input ld_0_vld;
	output wire ld_0_rdy;
	input [31:0] ld_1_data;
	input [4:0] ld_1_addr;
	input ld_1_vld;
	output wire ld_1_rdy;
	output wire [31:0] st_data;
	output wire st_req;
	input st_ack;
	localparam pe_pkg_LD_STREAM_CNT_L = 15;
	output wire [14:0] ld_stream_len;
	output wire ld_stream_len_vld;
	input all_stored;
	output wire global_barrier_reached;
	input global_barrier_reached_by_all_pes;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] precision_config;
	input monitor;
	output wire [31:0] monitor_pe_out;
	output wire [21:0] monitor_instr;
	reg [1023:0] registers;
	reg [1023:0] registers_d;
	wire [31:0] reg_out_0;
	wire [4:0] reg_rd_addr_0;
	wire [31:0] reg_out_1;
	wire [4:0] reg_rd_addr_1;
	wire reg_wr_0_en;
	wire reg_wr_1_en;
	wire [21:0] instr_to_decd;
	wire [3:0] opcode;
	wire instr_ld_0_en;
	wire instr_ld_1_en;
	wire instr_st_en;
	wire operator_reg_wr_en;
	reg operator_reg_wr_en_ungated;
	wire [4:0] operator_reg_wr_addr;
	wire [31:0] operator_out;
	wire [31:0] operator_in_0;
	wire [31:0] operator_in_1;
	wire ld_0_rdy_pre;
	wire ld_1_rdy_pre;
	wire st_req_pre;
	reg instr_ack_pre;
	wire ld_0_unblocked;
	wire ld_1_unblocked;
	wire st_unblocked;
	wire local_barrier_unblocked;
	wire global_barrier_unblocked;
	reg global_barrier_reached_pre;
	reg local_barrier_reached;
	reg ld_stream_len_vld_pre;
	reg [32:0] barrier_stalls;
	reg [32:0] ld_stalls;
	reg [32:0] st_stalls;
	reg [32:0] active;
	pe_instr_decd PE_INSTR_DECD_INS(
		.instr(instr_to_decd),
		.opcode(opcode),
		.reg_rd_addr_0(reg_rd_addr_0),
		.reg_rd_addr_1(reg_rd_addr_1),
		.operator_reg_wr_addr(operator_reg_wr_addr),
		.ld_0_en(instr_ld_0_en),
		.ld_1_en(instr_ld_1_en),
		.st_en(instr_st_en),
		.ld_stream_len(ld_stream_len)
	);
	pe_func_unit_interface_flow_control_ld PE_FUNC_UNIT_INTERFACE_FLOW_CONTROL_LD_0_INS(
		.clk(clk),
		.rst(rst),
		.ifc_en(instr_ld_0_en),
		.ifc_unblocked(ld_0_unblocked),
		.instr_done(instr_ack_pre),
		.reg_en(reg_wr_0_en),
		.memory_unit_rdy(ld_0_vld),
		.func_unit_rdy(ld_0_rdy)
	);
	pe_func_unit_interface_flow_control_ld PE_FUNC_UNIT_INTERFACE_FLOW_CONTROL_LD_1_INS(
		.clk(clk),
		.rst(rst),
		.ifc_en(instr_ld_1_en),
		.ifc_unblocked(ld_1_unblocked),
		.instr_done(instr_ack_pre),
		.reg_en(reg_wr_1_en),
		.memory_unit_rdy(ld_1_vld),
		.func_unit_rdy(ld_1_rdy)
	);
	pe_func_unit_interface_flow_control_st PE_FUNC_UNIT_INTERFACE_FLOW_CONTROL_ST_INS(
		.clk(clk),
		.rst(rst),
		.ifc_en(instr_st_en),
		.ifc_unblocked(st_unblocked),
		.instr_done(instr_ack_pre),
		.memory_unit_rdy(st_ack),
		.func_unit_rdy(st_req)
	);
	pe_operator PE_OPERATOR_INS(
		.clk(clk),
		.rst(rst),
		.in_0(operator_in_0),
		.in_1(operator_in_1),
		.out(operator_out),
		.opcode(opcode),
		.precision_config(precision_config)
	);
	assign instr_to_decd = (instr_req ? instr : {22 {1'sb0}});
	assign reg_out_0 = registers[reg_rd_addr_0 * 32+:32];
	assign reg_out_1 = registers[reg_rd_addr_1 * 32+:32];
	assign operator_in_0 = reg_out_0;
	assign operator_in_1 = reg_out_1;
	assign local_barrier_unblocked = (local_barrier_reached ? all_stored : 1);
	assign global_barrier_unblocked = (global_barrier_reached_pre ? global_barrier_reached_by_all_pes : 1);
	always @(*) begin
		instr_ack_pre = 0;
		if (instr_req)
			instr_ack_pre = (((ld_0_unblocked & ld_1_unblocked) & st_unblocked) & local_barrier_unblocked) & global_barrier_unblocked;
	end
	assign operator_reg_wr_en = operator_reg_wr_en_ungated & instr_ack_pre;
	localparam pe_pkg_GLOBAL_BARRIER_OPCODE = 4;
	localparam pe_pkg_LOCAL_BARRIER_OPCODE = 3;
	localparam pe_pkg_PROD_OPCODE = 2;
	localparam pe_pkg_SET_LD_STREAM_LEN_OPCODE = 5;
	localparam pe_pkg_SUM_OPCODE = 1;
	always @(*) begin
		operator_reg_wr_en_ungated = 0;
		local_barrier_reached = 0;
		global_barrier_reached_pre = 0;
		ld_stream_len_vld_pre = 0;
		case (opcode)
			pe_pkg_SUM_OPCODE: operator_reg_wr_en_ungated = 1;
			pe_pkg_PROD_OPCODE: operator_reg_wr_en_ungated = 1;
			pe_pkg_LOCAL_BARRIER_OPCODE: local_barrier_reached = 1;
			pe_pkg_GLOBAL_BARRIER_OPCODE: global_barrier_reached_pre = 1;
			pe_pkg_SET_LD_STREAM_LEN_OPCODE: ld_stream_len_vld_pre = 1;
		endcase
	end
	always @(*) begin
		registers_d = registers;
		if (reg_wr_0_en)
			registers_d[ld_0_addr * 32+:32] = ld_0_data;
		if (reg_wr_1_en)
			registers_d[ld_1_addr * 32+:32] = ld_1_data;
		if (operator_reg_wr_en)
			registers_d[operator_reg_wr_addr * 32+:32] = operator_out;
	end
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			registers <= 1'sb0;
		else
			registers <= registers_d;
	assign st_data = operator_out;
	assign global_barrier_reached = global_barrier_reached_pre;
	assign ld_stream_len_vld = ld_stream_len_vld_pre;
	assign instr_ack = instr_ack_pre;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE) begin
			barrier_stalls <= 0;
			ld_stalls <= 0;
			st_stalls <= 0;
			active <= 0;
		end
		else begin
			if (global_barrier_reached_pre & ~global_barrier_reached_by_all_pes)
				barrier_stalls <= barrier_stalls + 1;
			if (~ld_0_unblocked | ~ld_1_unblocked)
				ld_stalls <= ld_stalls + 1;
			if (~st_unblocked)
				st_stalls <= st_stalls + 1;
			if (instr_ack_pre)
				active <= active + 1;
		end
	assign monitor_pe_out = (monitor ? operator_out : {32 {1'sb0}});
	assign monitor_instr = (monitor ? instr_to_decd : {22 {1'sb0}});
endmodule
module fifo (
	clk,
	rst,
	inputs,
	in_vld,
	fifo_rdy,
	outputs,
	fifo_out_vld,
	receiver_rdy
);
	parameter WORD_L = 8;
	parameter DEPTH = 8;
	parameter PORT_L = 8;
	input wire clk;
	input wire rst;
	input wire [(PORT_L * WORD_L) - 1:0] inputs;
	input wire in_vld;
	output wire fifo_rdy;
	output wire [(PORT_L * WORD_L) - 1:0] outputs;
	output wire fifo_out_vld;
	input wire receiver_rdy;
	localparam ADR_L = $clog2(DEPTH);
	reg [((DEPTH * PORT_L) * WORD_L) - 1:0] fifo_reg;
	reg [ADR_L:0] wr_adr;
	reg [ADR_L:0] rd_adr;
	reg full;
	reg empty;
	wire wr_en;
	wire rd_en;
	wire fifo_rdy_pre;
	wire fifo_out_vld_pre;
	always @(*) begin
		if ((wr_adr[ADR_L - 1:0] == rd_adr[ADR_L - 1:0]) && (wr_adr[ADR_L] != rd_adr[ADR_L]))
			full = 1;
		else
			full = 0;
		if (wr_adr == rd_adr)
			empty = 1;
		else
			empty = 0;
	end
	assign fifo_rdy_pre = ~full;
	assign fifo_out_vld_pre = ~empty;
	assign wr_en = fifo_rdy_pre & in_vld;
	assign rd_en = fifo_out_vld_pre & receiver_rdy;
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE) begin
			wr_adr <= 1'sb0;
			rd_adr <= 1'sb0;
		end
		else begin
			if (wr_en)
				wr_adr <= wr_adr + 1;
			if (rd_en)
				rd_adr <= rd_adr + 1;
		end
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			fifo_reg <= 1'sb0;
		else if (wr_en)
			fifo_reg[WORD_L * (wr_adr[ADR_L - 1:0] * PORT_L)+:WORD_L * PORT_L] <= inputs;
	assign outputs = fifo_reg[WORD_L * (rd_adr[ADR_L - 1:0] * PORT_L)+:WORD_L * PORT_L];
	assign fifo_rdy = fifo_rdy_pre;
	assign fifo_out_vld = fifo_out_vld_pre;
endmodule
module fifo_2out (
	clk,
	rst,
	inputs,
	in_vld,
	fifo_rdy,
	outputs_0,
	outputs_1,
	fifo_out_0_vld,
	fifo_out_1_vld,
	receiver_0_rdy,
	receiver_1_rdy
);
	parameter WORD_L = 8;
	parameter DEPTH = 8;
	parameter PORT_L = 8;
	input wire clk;
	input wire rst;
	input wire [(PORT_L * WORD_L) - 1:0] inputs;
	input wire in_vld;
	output wire fifo_rdy;
	output wire [(PORT_L * WORD_L) - 1:0] outputs_0;
	output wire [(PORT_L * WORD_L) - 1:0] outputs_1;
	output wire fifo_out_0_vld;
	output wire fifo_out_1_vld;
	input wire receiver_0_rdy;
	input wire receiver_1_rdy;
	localparam ADR_L = $clog2(DEPTH);
	reg [((DEPTH * PORT_L) * WORD_L) - 1:0] fifo_reg;
	reg [ADR_L:0] wr_adr;
	reg [ADR_L:0] rd_adr_0;
	wire [ADR_L:0] rd_adr_1;
	reg full;
	reg empty;
	wire wr_en;
	wire rd_en_0;
	wire rd_en_1;
	wire fifo_rdy_pre;
	wire fifo_out_0_vld_pre;
	wire fifo_out_1_vld_pre;
	assign rd_adr_1 = rd_adr_0 + 1;
	always @(*) begin
		if ((wr_adr[ADR_L - 1:0] == rd_adr_0[ADR_L - 1:0]) && (wr_adr[ADR_L] != rd_adr_0[ADR_L]))
			full = 1;
		else
			full = 0;
		if (wr_adr == rd_adr_0)
			empty = 1;
		else
			empty = 0;
	end
	assign fifo_rdy_pre = ~full;
	assign fifo_out_0_vld_pre = ~empty;
	assign fifo_out_1_vld_pre = (empty ? 0 : (wr_adr == rd_adr_1 ? 0 : 1));
	assign wr_en = fifo_rdy_pre & in_vld;
	assign rd_en_0 = fifo_out_0_vld_pre & receiver_0_rdy;
	assign rd_en_1 = fifo_out_1_vld_pre & receiver_1_rdy;
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE) begin
			wr_adr <= 1'sb0;
			rd_adr_0 <= 1'sb0;
		end
		else begin
			if (wr_en)
				wr_adr <= wr_adr + 1;
			if (rd_en_1 && rd_en_0)
				rd_adr_0 <= rd_adr_0 + 2;
			else if (~rd_en_1 && rd_en_0)
				rd_adr_0 <= rd_adr_0 + 1;
		end
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			fifo_reg <= 1'sb0;
		else if (wr_en)
			fifo_reg[WORD_L * (wr_adr[ADR_L - 1:0] * PORT_L)+:WORD_L * PORT_L] <= inputs;
	assign outputs_0 = fifo_reg[WORD_L * (rd_adr_0[ADR_L - 1:0] * PORT_L)+:WORD_L * PORT_L];
	assign outputs_1 = fifo_reg[WORD_L * (rd_adr_1[ADR_L - 1:0] * PORT_L)+:WORD_L * PORT_L];
	assign fifo_rdy = fifo_rdy_pre;
	assign fifo_out_0_vld = fifo_out_0_vld_pre;
	assign fifo_out_1_vld = fifo_out_1_vld_pre;
endmodule
module pe_ld_unit (
	clk,
	rst,
	ld_stream_len,
	ld_stream_len_vld,
	mem_addr_in,
	reg_addr_in,
	mem_addr_in_req,
	mem_addr_in_ack,
	global_mem_addr,
	global_mem_addr_req,
	global_mem_addr_gnt,
	global_mem_data,
	global_mem_data_vld,
	local_mem_addr,
	local_mem_addr_req,
	local_mem_addr_gnt,
	local_mem_data,
	local_mem_data_vld,
	reg_addr_out_0,
	data_out_0,
	data_out_0_vld,
	data_out_0_rdy,
	reg_addr_out_1,
	data_out_1,
	data_out_1_vld,
	data_out_1_rdy
);
	input clk;
	input rst;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam pe_pkg_LD_STREAM_CNT_L = 15;
	input [14:0] ld_stream_len;
	input ld_stream_len_vld;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	input [11:0] mem_addr_in;
	input [4:0] reg_addr_in;
	input mem_addr_in_req;
	output wire mem_addr_in_ack;
	output wire [11:0] global_mem_addr;
	output wire global_mem_addr_req;
	input global_mem_addr_gnt;
	localparam hw_pkg_DATA_L = 32;
	input [31:0] global_mem_data;
	input global_mem_data_vld;
	localparam hw_pkg_LOCAL_MEM_ADDR_L = 9;
	output wire [8:0] local_mem_addr;
	output wire local_mem_addr_req;
	input local_mem_addr_gnt;
	input [31:0] local_mem_data;
	input local_mem_data_vld;
	output wire [4:0] reg_addr_out_0;
	output wire [31:0] data_out_0;
	output wire data_out_0_vld;
	input data_out_0_rdy;
	output wire [4:0] reg_addr_out_1;
	output wire [31:0] data_out_1;
	output wire data_out_1_vld;
	input data_out_1_rdy;
	reg [14:0] ld_counter;
	wire ld_counter_rdy;
	reg mem_addr_in_ack_pre;
	wire ld_unit_rdy_to_accept_addr;
	wire mem_type_fifo_rdy;
	wire reg_fifo_rdy;
	wire reg_out_0_vld;
	wire reg_out_1_vld;
	wire local_mem_addr_range;
	reg global_mem_addr_req_pre;
	reg local_mem_addr_req_pre;
	wire [31:0] data_fifo_in;
	reg data_fifo_in_vld;
	wire data_fifo_in_rdy;
	wire mem_type_fifo_out;
	wire mem_type_fifo_vld;
	wire pop_reg_fifo_0;
	wire pop_reg_fifo_1;
	assign ld_counter_rdy = (ld_counter != 0 ? 1 : 0);
	assign ld_unit_rdy_to_accept_addr = (ld_counter_rdy & reg_fifo_rdy) & mem_type_fifo_rdy;
	localparam hw_pkg_LOCAL_MEM_INDICATOR = 0;
	localparam hw_pkg_LOCAL_MEM_INDICATOR_L = 1;
	localparam hw_pkg_LOCAL_MEM_INDICATOR_S = 11;
	assign local_mem_addr_range = (mem_addr_in[hw_pkg_LOCAL_MEM_INDICATOR_S+:hw_pkg_LOCAL_MEM_INDICATOR_L] == hw_pkg_LOCAL_MEM_INDICATOR ? 1 : 0);
	assign pop_reg_fifo_0 = data_out_0_vld & data_out_0_rdy;
	assign pop_reg_fifo_1 = data_out_1_vld & data_out_1_rdy;
	always @(*) begin
		global_mem_addr_req_pre = 0;
		local_mem_addr_req_pre = 0;
		if (ld_unit_rdy_to_accept_addr & mem_addr_in_req)
			if (local_mem_addr_range)
				local_mem_addr_req_pre = 1;
			else
				global_mem_addr_req_pre = 1;
	end
	always @(*)
		if (local_mem_addr_range)
			mem_addr_in_ack_pre = local_mem_addr_gnt & local_mem_addr_req_pre;
		else
			mem_addr_in_ack_pre = global_mem_addr_gnt & global_mem_addr_req_pre;
	assign data_fifo_in = (mem_type_fifo_out ? local_mem_data : global_mem_data);
	always @(*) begin
		data_fifo_in_vld = 0;
		if (mem_type_fifo_out) begin
			if (local_mem_data_vld)
				data_fifo_in_vld = 1;
		end
		else if (global_mem_data_vld)
			data_fifo_in_vld = 1;
	end
	localparam pe_pkg_LD_DATA_FIFO_DEPTH = 16;
	fifo_2out #(
		.WORD_L(hw_pkg_DATA_L),
		.DEPTH(pe_pkg_LD_DATA_FIFO_DEPTH),
		.PORT_L(1)
	) DATA_FIFO(
		.clk(clk),
		.rst(rst),
		.inputs(data_fifo_in),
		.in_vld(data_fifo_in_vld),
		.fifo_rdy(data_fifo_in_rdy),
		.outputs_0(data_out_0),
		.outputs_1(data_out_1),
		.fifo_out_0_vld(data_out_0_vld),
		.fifo_out_1_vld(data_out_1_vld),
		.receiver_0_rdy(data_out_0_rdy),
		.receiver_1_rdy(data_out_1_rdy)
	);
	fifo_2out #(
		.WORD_L(hw_pkg_REG_ADDR_L),
		.DEPTH(pe_pkg_LD_DATA_FIFO_DEPTH),
		.PORT_L(1)
	) REG_ADDR_FIFO(
		.clk(clk),
		.rst(rst),
		.inputs(reg_addr_in),
		.in_vld(mem_addr_in_ack_pre),
		.fifo_rdy(reg_fifo_rdy),
		.outputs_0(reg_addr_out_0),
		.outputs_1(reg_addr_out_1),
		.fifo_out_0_vld(reg_out_0_vld),
		.fifo_out_1_vld(reg_out_1_vld),
		.receiver_0_rdy(pop_reg_fifo_0),
		.receiver_1_rdy(pop_reg_fifo_1)
	);
	localparam pe_pkg_MAX_OUTSTANDING_LD_REQ = 4;
	fifo #(
		.WORD_L(1),
		.DEPTH(pe_pkg_MAX_OUTSTANDING_LD_REQ),
		.PORT_L(1)
	) MEM_TYPE_FIFO(
		.clk(clk),
		.rst(rst),
		.inputs(local_mem_addr_range),
		.in_vld(mem_addr_in_ack_pre),
		.fifo_rdy(mem_type_fifo_rdy),
		.outputs(mem_type_fifo_out),
		.fifo_out_vld(mem_type_fifo_vld),
		.receiver_rdy(data_fifo_in_vld)
	);
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			ld_counter <= 1'sb0;
		else if (ld_stream_len_vld)
			ld_counter <= ld_stream_len;
		else if (mem_addr_in_ack_pre)
			ld_counter <= ld_counter - 1;
	assign mem_addr_in_ack = mem_addr_in_ack_pre;
	assign global_mem_addr = mem_addr_in;
	assign global_mem_addr_req = global_mem_addr_req_pre;
	assign local_mem_addr = mem_addr_in;
	assign local_mem_addr_req = local_mem_addr_req_pre;
endmodule
module pe_st_unit (
	clk,
	rst,
	mem_addr_in,
	mem_addr_in_req,
	mem_addr_in_ack,
	global_mem_addr,
	global_mem_data,
	global_mem_st_req,
	global_mem_st_gnt,
	local_mem_addr,
	local_mem_data,
	local_mem_st_req,
	local_mem_st_gnt,
	fu_st_data,
	fu_st_data_req,
	fu_st_data_gnt,
	all_stored
);
	input clk;
	input rst;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	input [11:0] mem_addr_in;
	input mem_addr_in_req;
	output wire mem_addr_in_ack;
	output wire [11:0] global_mem_addr;
	localparam hw_pkg_DATA_L = 32;
	output wire [31:0] global_mem_data;
	output wire global_mem_st_req;
	input global_mem_st_gnt;
	localparam hw_pkg_LOCAL_MEM_ADDR_L = 9;
	output wire [8:0] local_mem_addr;
	output wire [31:0] local_mem_data;
	output wire local_mem_st_req;
	input local_mem_st_gnt;
	input [31:0] fu_st_data;
	input fu_st_data_req;
	output wire fu_st_data_gnt;
	output wire all_stored;
	wire global_addr_fifo_out_vld;
	wire global_addr_fifo_in_rdy;
	wire global_data_fifo_in_rdy;
	reg global_data_fifo_in_vld;
	wire global_data_fifo_out_vld;
	reg fu_st_data_gnt_pre;
	wire st_unit_rdy_to_store;
	wire local_mem_addr_range;
	reg local_mem_st_req_pre;
	assign st_unit_rdy_to_store = mem_addr_in_req;
	localparam hw_pkg_LOCAL_MEM_INDICATOR = 0;
	localparam hw_pkg_LOCAL_MEM_INDICATOR_L = 1;
	localparam hw_pkg_LOCAL_MEM_INDICATOR_S = 11;
	assign local_mem_addr_range = (mem_addr_in[hw_pkg_LOCAL_MEM_INDICATOR_S+:hw_pkg_LOCAL_MEM_INDICATOR_L] == hw_pkg_LOCAL_MEM_INDICATOR ? 1 : 0);
	always @(*) begin
		local_mem_st_req_pre = 0;
		if (local_mem_addr_range && st_unit_rdy_to_store)
			local_mem_st_req_pre = fu_st_data_req;
	end
	always @(*) begin
		global_data_fifo_in_vld = 0;
		if (~local_mem_addr_range && st_unit_rdy_to_store)
			global_data_fifo_in_vld = fu_st_data_req;
	end
	always @(*) begin
		fu_st_data_gnt_pre = 0;
		if (local_mem_addr_range)
			fu_st_data_gnt_pre = (st_unit_rdy_to_store & fu_st_data_req) & local_mem_st_gnt;
		else
			fu_st_data_gnt_pre = (st_unit_rdy_to_store & fu_st_data_req) & global_data_fifo_in_rdy;
	end
	localparam pe_pkg_ST_DATA_FIFO_DEPTH = 2;
	fifo #(
		.WORD_L(hw_pkg_GLOBAL_MEM_ADDR_L),
		.DEPTH(pe_pkg_ST_DATA_FIFO_DEPTH),
		.PORT_L(1)
	) GLOBAL_ADDR_FIFO(
		.clk(clk),
		.rst(rst),
		.inputs(mem_addr_in),
		.in_vld(global_data_fifo_in_vld),
		.fifo_rdy(global_addr_fifo_in_rdy),
		.outputs(global_mem_addr),
		.fifo_out_vld(global_addr_fifo_out_vld),
		.receiver_rdy(global_mem_st_gnt)
	);
	fifo #(
		.WORD_L(hw_pkg_DATA_L),
		.DEPTH(pe_pkg_ST_DATA_FIFO_DEPTH),
		.PORT_L(1)
	) GLOBAL_DATA_FIFO(
		.clk(clk),
		.rst(rst),
		.inputs(fu_st_data),
		.in_vld(global_data_fifo_in_vld),
		.fifo_rdy(global_data_fifo_in_rdy),
		.outputs(global_mem_data),
		.fifo_out_vld(global_data_fifo_out_vld),
		.receiver_rdy(global_mem_st_gnt)
	);
	assign all_stored = ~global_data_fifo_out_vld;
	assign fu_st_data_gnt = fu_st_data_gnt_pre;
	assign mem_addr_in_ack = fu_st_data_gnt_pre;
	assign local_mem_addr = mem_addr_in[8:0];
	assign local_mem_data = fu_st_data;
	assign local_mem_st_req = local_mem_st_req_pre;
	assign global_mem_st_req = global_data_fifo_out_vld;
endmodule
module local_mem_arbiter (
	clk,
	rst,
	ld_local_mem_addr,
	ld_local_mem_addr_req,
	ld_local_mem_addr_gnt,
	ld_local_mem_data,
	ld_local_mem_data_vld,
	st_local_mem_addr,
	st_local_mem_data,
	st_local_mem_st_req,
	st_local_mem_st_gnt,
	local_mem_addr,
	local_mem_wr_data,
	local_mem_wr_en,
	local_mem_rd_en,
	local_mem_rd_data,
	init_local_mem_addr,
	init_local_mem_wr_data,
	init_local_mem_vld,
	init_local_mem_wr_en,
	init_local_mem_rd_data,
	init_local_mem_rd_data_vld
);
	input clk;
	input rst;
	localparam hw_pkg_LOCAL_MEM_ADDR_L = 9;
	input [8:0] ld_local_mem_addr;
	input ld_local_mem_addr_req;
	output wire ld_local_mem_addr_gnt;
	localparam hw_pkg_DATA_L = 32;
	output wire [31:0] ld_local_mem_data;
	output wire ld_local_mem_data_vld;
	input [8:0] st_local_mem_addr;
	input [31:0] st_local_mem_data;
	input st_local_mem_st_req;
	output wire st_local_mem_st_gnt;
	output wire [8:0] local_mem_addr;
	output wire [31:0] local_mem_wr_data;
	output wire local_mem_wr_en;
	output wire local_mem_rd_en;
	input [31:0] local_mem_rd_data;
	input [8:0] init_local_mem_addr;
	input [31:0] init_local_mem_wr_data;
	input init_local_mem_vld;
	input init_local_mem_wr_en;
	output wire [31:0] init_local_mem_rd_data;
	output wire init_local_mem_rd_data_vld;
	wire [1:0] req;
	wire [1:0] req_gated;
	wire [1:0] gnt;
	wire ld_gnt;
	wire st_gnt;
	wire init_local_mem_rd_en;
	reg [8:0] local_mem_addr_pre;
	localparam pe_pkg_LOCAL_MEM_RD_LATENCY = 1;
	localparam DELAY = pe_pkg_LOCAL_MEM_RD_LATENCY;
	reg [0:0] ld_gnt_delayed;
	reg [0:0] init_rd_en_delayed;
	assign init_local_mem_rd_en = (init_local_mem_vld ? ~init_local_mem_wr_en : 1'b0);
	assign req[0] = (st_local_mem_st_req ? 1'b0 : ld_local_mem_addr_req);
	assign req[1] = st_local_mem_st_req;
	assign req_gated = (init_local_mem_vld ? {2 {1'sb0}} : req);
	assign ld_gnt = gnt[0];
	assign st_gnt = gnt[1];
	always @(*) begin
		if (ld_gnt)
			local_mem_addr_pre = ld_local_mem_addr;
		else
			local_mem_addr_pre = st_local_mem_addr;
		if (init_local_mem_vld)
			local_mem_addr_pre = init_local_mem_addr;
	end
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE) begin
			ld_gnt_delayed <= 1'sb0;
			init_rd_en_delayed <= 1'sb0;
		end
		else begin
			ld_gnt_delayed[0] <= ld_gnt;
			init_rd_en_delayed[0] <= init_local_mem_rd_en;
			begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i < DELAY; i = i + 1)
					begin
						ld_gnt_delayed[i] <= ld_gnt_delayed[i - 1];
						init_rd_en_delayed[i] <= init_rd_en_delayed[i - 1];
					end
			end
		end
	simple_rr_arbiter #(.N_IN_PORTS(2)) RR_ARBITER_INS(
		.clk(clk),
		.rst(rst),
		.req(req_gated),
		.grant(gnt)
	);
	assign st_local_mem_st_gnt = st_gnt;
	assign ld_local_mem_addr_gnt = ld_gnt;
	assign ld_local_mem_data = local_mem_rd_data;
	assign ld_local_mem_data_vld = ld_gnt_delayed[0];
	assign local_mem_addr = local_mem_addr_pre;
	assign local_mem_wr_en = (init_local_mem_vld ? init_local_mem_wr_en : st_gnt);
	assign local_mem_rd_en = (init_local_mem_vld ? init_local_mem_rd_en : ld_gnt);
	assign local_mem_wr_data = (init_local_mem_vld ? init_local_mem_wr_data : st_local_mem_data);
	assign init_local_mem_rd_data = local_mem_rd_data;
	assign init_local_mem_rd_data_vld = init_rd_en_delayed[0];
endmodule
module sp_mem_model (
	clk,
	rst,
	slp,
	sd,
	wr_en,
	ch_en,
	addr,
	wr_data,
	rd_data
);
	parameter DATA_L = 8;
	parameter ADDR_L = 8;
	parameter RD_LATENCY = 0;
	input clk;
	input rst;
	input slp;
	input sd;
	input wr_en;
	input ch_en;
	input [ADDR_L - 1:0] addr;
	input [DATA_L - 1:0] wr_data;
	output wire [DATA_L - 1:0] rd_data;
	wire [31:0] wr_data_resized_32;
	wire [23:0] wr_data_resized_24;
	wire [31:0] rd_data_resized_32;
	wire [23:0] rd_data_resized_24;
	wire [DATA_L - 1:0] rd_data_pre;
	assign wr_data_resized_32 = wr_data;
	assign wr_data_resized_24 = wr_data;
	assign rd_data = rd_data_pre;
   
  /* reg [31*8 - 1:0] data; */

  /* always @(posedge clk or negedge rst) begin */
   /*  if (rst== 0) begin */
   /*    data= 1'sb0; */
   /*  end else begin */
   /*    if ((wr_en == 1) && (ch_en == 1)) begin */
   /*      data[addr[2:0] * 32+:32] <= wr_data; */
   /*    end */
   /*  end */
  /* end */
	/* assign rd_data_pre = data[addr[2:0] * 32+:32]; */
	generate
		if ($bits(wr_data) > 24) begin : mem_32x256
			assign rd_data_pre = rd_data_resized_32;
      sky130_sram_1rw_32x256_32 sram (
        .clk0 (clk),
        .csb0 (~ch_en),
        .web0 (~wr_en),
        .addr0 (addr),
        .din0  (wr_data_resized_32),
        .dout0 (rd_data_resized_32)
      );
    end
		else if ($bits(wr_data) <= 24) begin : mem_24x128
			assign rd_data_pre = rd_data_resized_24;
      sky130_sram_1rw_24x128_24 sram (
        .clk0 (clk),
        .csb0 (~ch_en),
        .web0 (~wr_en),
        .addr0 (addr),
        .din0  (wr_data_resized_24),
        .dout0 (rd_data_resized_24)
      );
    end
  endgenerate
/* 
	generate
		if (((DATA_L > 24) && (DATA_L <= 32)) && (ADDR_L == 10)) begin : mem_1024x32
			assign rd_data_pre = rd_data_resized_32;
			TS1N28HPCPHVTB1024X32M4SWBASO SRAM_1024x32(
				.SLP(slp),
				.SD(sd),
				.CLK(clk),
				.CEB(~ch_en),
				.WEB(~wr_en),
				.CEBM(1'b1),
				.WEBM(1'b1),
				.AWT(1'b0),
				.A(addr),
				.D(wr_data_resized_32),
				.BWEB(1'sb0),
				.AM(1'sb0),
				.DM(1'sb0),
				.BWEBM({32 {1'b1}}),
				.BIST(1'b0),
				.Q(rd_data_resized_32)
			);
		end
		else if ((DATA_L <= 24) && (ADDR_L == 10)) begin : mem_1024x24
			assign rd_data_pre = rd_data_resized_24;
			TS1N28HPCPHVTB1024X24M4SWBASO SRAM_1024x24(
				.SLP(slp),
				.SD(sd),
				.CLK(clk),
				.CEB(~ch_en),
				.WEB(~wr_en),
				.CEBM(1'b1),
				.WEBM(1'b1),
				.AWT(1'b0),
				.A(addr),
				.D(wr_data_resized_24),
				.BWEB(1'sb0),
				.AM(1'sb0),
				.DM(1'sb0),
				.BWEBM({24 {1'b1}}),
				.BIST(1'b0),
				.Q(rd_data_resized_24)
			);
		end
		else if ((DATA_L <= 24) && (ADDR_L == 9)) begin : mem_512x24
			assign rd_data_pre = rd_data_resized_24;
			TS1N28HPCPHVTB512X24M4SWBASO SRAM_512x24(
				.SLP(slp),
				.SD(sd),
				.CLK(clk),
				.CEB(~ch_en),
				.WEB(~wr_en),
				.CEBM(1'b1),
				.WEBM(1'b1),
				.AWT(1'b0),
				.A(addr),
				.D(wr_data_resized_24),
				.BWEB(1'sb0),
				.AM(1'sb0),
				.DM(1'sb0),
				.BWEBM({24 {1'b1}}),
				.BIST(1'b0),
				.Q(rd_data_resized_24)
			);
		end
		else if (((DATA_L > 24) && (DATA_L <= 32)) && (ADDR_L == 9)) begin : mem_512x32
			assign rd_data_pre = rd_data_resized_32;
			TS1N28HPCPHVTB512X32M4SWBASO SRAM_512x32(
				.SLP(slp),
				.SD(sd),
				.CLK(clk),
				.CEB(~ch_en),
				.WEB(~wr_en),
				.CEBM(1'b1),
				.WEBM(1'b1),
				.AWT(1'b0),
				.A(addr),
				.D(wr_data_resized_32),
				.BWEB(1'sb0),
				.AM(1'sb0),
				.DM(1'sb0),
				.BWEBM({32 {1'b1}}),
				.BIST(1'b0),
				.Q(rd_data_resized_32)
			);
		end
	endgenerate
*/ 
endmodule
module pe_top (
	clk,
	rst,
	config_local_mem_slp,
	config_local_mem_sd,
	instr,
	instr_req,
	instr_ack,
	global_barrier_reached,
	global_barrier_reached_by_all_pes,
	precision_config,
	st_mem_addr_in,
	st_mem_addr_in_req,
	st_mem_addr_in_ack,
	st_global_mem_addr,
	st_global_mem_data,
	st_global_mem_st_req,
	st_global_mem_st_gnt,
	ld_mem_addr_in,
	ld_reg_addr_in,
	ld_mem_addr_in_req,
	ld_mem_addr_in_ack,
	ld_global_mem_addr,
	ld_global_mem_addr_req,
	ld_global_mem_addr_gnt,
	ld_global_mem_data,
	ld_global_mem_data_vld,
	init_local_mem_addr,
	init_local_mem_wr_data,
	init_local_mem_vld,
	init_local_mem_wr_en,
	init_local_mem_rd_data,
	init_local_mem_rd_data_vld,
	monitor,
	monitor_pe_out,
	monitor_instr
);
	input clk;
	input rst;
	input config_local_mem_slp;
	input config_local_mem_sd;
	localparam hw_pkg_OPCODE_L = 4;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam hw_pkg_INSTR_L = 22;
	input [21:0] instr;
	input instr_req;
	output wire instr_ack;
	output wire global_barrier_reached;
	input global_barrier_reached_by_all_pes;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] precision_config;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	input [11:0] st_mem_addr_in;
	input st_mem_addr_in_req;
	output wire st_mem_addr_in_ack;
	output wire [11:0] st_global_mem_addr;
	localparam hw_pkg_DATA_L = 32;
	output wire [31:0] st_global_mem_data;
	output wire st_global_mem_st_req;
	input st_global_mem_st_gnt;
	input [11:0] ld_mem_addr_in;
	input [4:0] ld_reg_addr_in;
	input ld_mem_addr_in_req;
	output wire ld_mem_addr_in_ack;
	output wire [11:0] ld_global_mem_addr;
	output wire ld_global_mem_addr_req;
	input ld_global_mem_addr_gnt;
	input [31:0] ld_global_mem_data;
	input ld_global_mem_data_vld;
	localparam hw_pkg_LOCAL_MEM_ADDR_L = 9;
	input [8:0] init_local_mem_addr;
	input [31:0] init_local_mem_wr_data;
	input init_local_mem_vld;
	input init_local_mem_wr_en;
	output wire [31:0] init_local_mem_rd_data;
	output wire init_local_mem_rd_data_vld;
	input monitor;
	output wire [31:0] monitor_pe_out;
	output wire [21:0] monitor_instr;
	localparam pe_pkg_LD_STREAM_CNT_L = 15;
	wire [14:0] ld_stream_len;
	wire ld_stream_len_vld;
	wire [31:0] st_data;
	wire st_req;
	wire st_ack;
	wire [31:0] ld_0_data;
	wire [4:0] ld_0_addr;
	wire ld_0_vld;
	wire ld_0_rdy;
	wire [31:0] ld_1_data;
	wire [4:0] ld_1_addr;
	wire ld_1_vld;
	wire ld_1_rdy;
	wire [8:0] st_local_mem_addr;
	wire [31:0] st_local_mem_data;
	wire st_local_mem_st_req;
	wire st_local_mem_st_gnt;
	wire [8:0] ld_local_mem_addr;
	wire ld_local_mem_addr_req;
	wire ld_local_mem_addr_gnt;
	wire [31:0] ld_local_mem_data;
	wire ld_local_mem_data_vld;
	wire [8:0] local_mem_addr;
	wire [31:0] local_mem_wr_data;
	wire local_mem_wr_en;
	wire local_mem_rd_en;
	wire local_mem_ch_en;
	wire [31:0] local_mem_rd_data;
	wire all_stored;
	assign local_mem_ch_en = local_mem_rd_en | local_mem_wr_en;
	pe_func_unit PE_FUNC_UNIT_INS(
		.clk(clk),
		.rst(rst),
		.instr(instr),
		.instr_req(instr_req),
		.instr_ack(instr_ack),
		.ld_0_data(ld_0_data),
		.ld_0_addr(ld_0_addr),
		.ld_0_vld(ld_0_vld),
		.ld_0_rdy(ld_0_rdy),
		.ld_1_data(ld_1_data),
		.ld_1_addr(ld_1_addr),
		.ld_1_vld(ld_1_vld),
		.ld_1_rdy(ld_1_rdy),
		.st_data(st_data),
		.st_req(st_req),
		.st_ack(st_ack),
		.ld_stream_len(ld_stream_len),
		.ld_stream_len_vld(ld_stream_len_vld),
		.all_stored(all_stored),
		.global_barrier_reached(global_barrier_reached),
		.global_barrier_reached_by_all_pes(global_barrier_reached_by_all_pes),
		.precision_config(precision_config),
		.monitor(monitor),
		.monitor_pe_out(monitor_pe_out),
		.monitor_instr(monitor_instr)
	);
	pe_st_unit PE_ST_UNIT(
		.clk(clk),
		.rst(rst),
		.mem_addr_in(st_mem_addr_in),
		.mem_addr_in_req(st_mem_addr_in_req),
		.mem_addr_in_ack(st_mem_addr_in_ack),
		.global_mem_addr(st_global_mem_addr),
		.global_mem_data(st_global_mem_data),
		.global_mem_st_req(st_global_mem_st_req),
		.global_mem_st_gnt(st_global_mem_st_gnt),
		.local_mem_addr(st_local_mem_addr),
		.local_mem_data(st_local_mem_data),
		.local_mem_st_req(st_local_mem_st_req),
		.local_mem_st_gnt(st_local_mem_st_gnt),
		.fu_st_data(st_data),
		.fu_st_data_req(st_req),
		.fu_st_data_gnt(st_ack),
		.all_stored(all_stored)
	);
	pe_ld_unit PE_LD_UNIT_INS(
		.clk(clk),
		.rst(rst),
		.ld_stream_len(ld_stream_len),
		.ld_stream_len_vld(ld_stream_len_vld),
		.mem_addr_in(ld_mem_addr_in),
		.reg_addr_in(ld_reg_addr_in),
		.mem_addr_in_req(ld_mem_addr_in_req),
		.mem_addr_in_ack(ld_mem_addr_in_ack),
		.global_mem_addr(ld_global_mem_addr),
		.global_mem_addr_req(ld_global_mem_addr_req),
		.global_mem_addr_gnt(ld_global_mem_addr_gnt),
		.global_mem_data(ld_global_mem_data),
		.global_mem_data_vld(ld_global_mem_data_vld),
		.local_mem_addr(ld_local_mem_addr),
		.local_mem_addr_req(ld_local_mem_addr_req),
		.local_mem_addr_gnt(ld_local_mem_addr_gnt),
		.local_mem_data(ld_local_mem_data),
		.local_mem_data_vld(ld_local_mem_data_vld),
		.reg_addr_out_0(ld_0_addr),
		.data_out_0(ld_0_data),
		.data_out_0_vld(ld_0_vld),
		.data_out_0_rdy(ld_0_rdy),
		.reg_addr_out_1(ld_1_addr),
		.data_out_1(ld_1_data),
		.data_out_1_vld(ld_1_vld),
		.data_out_1_rdy(ld_1_rdy)
	);
	local_mem_arbiter LOCAL_MEM_ARBITER_INS(
		.clk(clk),
		.rst(rst),
		.ld_local_mem_addr(ld_local_mem_addr),
		.ld_local_mem_addr_req(ld_local_mem_addr_req),
		.ld_local_mem_addr_gnt(ld_local_mem_addr_gnt),
		.ld_local_mem_data(ld_local_mem_data),
		.ld_local_mem_data_vld(ld_local_mem_data_vld),
		.st_local_mem_addr(st_local_mem_addr),
		.st_local_mem_data(st_local_mem_data),
		.st_local_mem_st_req(st_local_mem_st_req),
		.st_local_mem_st_gnt(st_local_mem_st_gnt),
		.local_mem_addr(local_mem_addr),
		.local_mem_wr_data(local_mem_wr_data),
		.local_mem_wr_en(local_mem_wr_en),
		.local_mem_rd_en(local_mem_rd_en),
		.local_mem_rd_data(local_mem_rd_data),
		.init_local_mem_addr(init_local_mem_addr),
		.init_local_mem_wr_data(init_local_mem_wr_data),
		.init_local_mem_vld(init_local_mem_vld),
		.init_local_mem_wr_en(init_local_mem_wr_en),
		.init_local_mem_rd_data(init_local_mem_rd_data),
		.init_local_mem_rd_data_vld(init_local_mem_rd_data_vld)
	);
	localparam pe_pkg_LOCAL_MEM_RD_LATENCY = 1;
	sp_mem_model #(
		.DATA_L(hw_pkg_DATA_L),
		.ADDR_L(hw_pkg_LOCAL_MEM_ADDR_L),
		.RD_LATENCY(pe_pkg_LOCAL_MEM_RD_LATENCY)
	) SP_MEM_MODEL_INS(
		.clk(clk),
		.rst(rst),
		.slp(config_local_mem_slp),
		.sd(config_local_mem_sd),
		.wr_en(local_mem_wr_en),
		.ch_en(local_mem_ch_en),
		.addr(local_mem_addr),
		.wr_data(local_mem_wr_data),
		.rd_data(local_mem_rd_data)
	);
endmodule
module processing_logic (
	clk,
	rst,
	config_local_mem_slp,
	config_local_mem_sd,
	precision_config,
	instr,
	instr_req,
	instr_ack,
	st_mem_addr_in,
	st_mem_addr_in_req,
	st_mem_addr_in_ack,
	ld_mem_addr_in,
	ld_reg_addr_in,
	ld_mem_addr_in_req,
	ld_mem_addr_in_ack,
	global_mem_addr,
	global_mem_wr_data,
	global_mem_wr_en,
	global_mem_rd_en,
	global_mem_rd_data,
	init_global_mem_addr,
	init_global_mem_vld,
	init_global_mem_wr_en,
	init_global_mem_wr_data,
	init_global_mem_rd_data,
	init_global_mem_rd_data_vld,
	init_local_mem_addr,
	init_local_mem_wr_data,
	init_local_mem_vld,
	init_local_mem_wr_en,
	init_local_mem_rd_data,
	init_local_mem_rd_data_vld,
	monitor,
	monitor_global_rd_req,
	monitor_global_rd_gnt,
	monitor_global_wr_req,
	monitor_global_wr_gnt,
	monitor_pe_out,
	monitor_instr
);
	input clk;
	input rst;
	localparam hw_pkg_N_PE = 2;
	input [1:0] config_local_mem_slp;
	input [1:0] config_local_mem_sd;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] precision_config;
	localparam hw_pkg_OPCODE_L = 4;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam hw_pkg_INSTR_L = 22;
	input [43:0] instr;
	input [1:0] instr_req;
	output wire [1:0] instr_ack;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	input [23:0] st_mem_addr_in;
	input [1:0] st_mem_addr_in_req;
	output wire [1:0] st_mem_addr_in_ack;
	input [23:0] ld_mem_addr_in;
	input [9:0] ld_reg_addr_in;
	input [1:0] ld_mem_addr_in_req;
	output wire [1:0] ld_mem_addr_in_ack;
	localparam hw_pkg_N_GLOBAL_MEM_BANKS = hw_pkg_N_PE;
	localparam interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L = 10;
	output wire [19:0] global_mem_addr;
	localparam hw_pkg_DATA_L = 32;
	output wire [63:0] global_mem_wr_data;
	output wire [1:0] global_mem_wr_en;
	output wire [1:0] global_mem_rd_en;
	input [63:0] global_mem_rd_data;
	input [11:0] init_global_mem_addr;
	input init_global_mem_vld;
	input init_global_mem_wr_en;
	input [31:0] init_global_mem_wr_data;
	output wire [31:0] init_global_mem_rd_data;
	output wire init_global_mem_rd_data_vld;
	localparam hw_pkg_LOCAL_MEM_ADDR_L = 9;
	input [8:0] init_local_mem_addr;
	input [31:0] init_local_mem_wr_data;
	input [1:0] init_local_mem_vld;
	input [1:0] init_local_mem_wr_en;
	output wire [63:0] init_local_mem_rd_data;
	output wire [1:0] init_local_mem_rd_data_vld;
	input monitor;
	output wire [1:0] monitor_global_rd_req;
	output wire [1:0] monitor_global_rd_gnt;
	output wire [1:0] monitor_global_wr_req;
	output wire [1:0] monitor_global_wr_gnt;
	output wire [63:0] monitor_pe_out;
	output wire [43:0] monitor_instr;
	wire [1:0] global_barrier_reached;
	wire global_barrier_reached_by_all_pes;
	wire [23:0] ld_addr;
	wire [1:0] ld_req;
	wire [1:0] ld_gnt;
	wire [63:0] ld_data;
	wire [1:0] ld_data_vld;
	reg [19:0] st_addr_trimmed;
	wire [23:0] st_addr;
	wire [63:0] st_data;
	wire [1:0] st_req;
	wire [1:0] st_gnt;
	assign global_barrier_reached_by_all_pes = (~global_barrier_reached ? 0 : 1);
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			st_addr_trimmed[i * 10+:10] = st_addr[(i * 12) + 9-:10];
	end
	interconnect_top INTERCONNECT_TOP_INS(
		.clk(clk),
		.rst(rst),
		.ld_addr(ld_addr),
		.ld_req(ld_req),
		.ld_gnt(ld_gnt),
		.ld_data(ld_data),
		.ld_data_vld(ld_data_vld),
		.st_addr(st_addr_trimmed),
		.st_data(st_data),
		.st_req(st_req),
		.st_gnt(st_gnt),
		.mem_addr(global_mem_addr),
		.mem_wr_data(global_mem_wr_data),
		.mem_wr_en(global_mem_wr_en),
		.mem_rd_en(global_mem_rd_en),
		.mem_rd_data(global_mem_rd_data),
		.init_mem_addr(init_global_mem_addr),
		.init_mem_vld(init_global_mem_vld),
		.init_mem_wr_en(init_global_mem_wr_en),
		.init_mem_wr_data(init_global_mem_wr_data),
		.init_mem_rd_data(init_global_mem_rd_data),
		.init_mem_rd_data_vld(init_global_mem_rd_data_vld)
	);
	genvar pe_i;
	generate
		for (pe_i = 0; pe_i < hw_pkg_N_PE; pe_i = pe_i + 1) begin : pe_loop
			pe_top PE_TOP_INS(
				.clk(clk),
				.rst(rst),
				.config_local_mem_slp(config_local_mem_slp[pe_i]),
				.config_local_mem_sd(config_local_mem_sd[pe_i]),
				.instr(instr[pe_i * 22+:22]),
				.instr_req(instr_req[pe_i]),
				.instr_ack(instr_ack[pe_i]),
				.global_barrier_reached(global_barrier_reached[pe_i]),
				.global_barrier_reached_by_all_pes(global_barrier_reached_by_all_pes),
				.precision_config(precision_config),
				.st_mem_addr_in(st_mem_addr_in[pe_i * 12+:12]),
				.st_mem_addr_in_req(st_mem_addr_in_req[pe_i]),
				.st_mem_addr_in_ack(st_mem_addr_in_ack[pe_i]),
				.st_global_mem_addr(st_addr[pe_i * 12+:12]),
				.st_global_mem_data(st_data[pe_i * 32+:32]),
				.st_global_mem_st_req(st_req[pe_i]),
				.st_global_mem_st_gnt(st_gnt[pe_i]),
				.ld_mem_addr_in(ld_mem_addr_in[pe_i * 12+:12]),
				.ld_reg_addr_in(ld_reg_addr_in[pe_i * 5+:5]),
				.ld_mem_addr_in_req(ld_mem_addr_in_req[pe_i]),
				.ld_mem_addr_in_ack(ld_mem_addr_in_ack[pe_i]),
				.ld_global_mem_addr(ld_addr[pe_i * 12+:12]),
				.ld_global_mem_addr_req(ld_req[pe_i]),
				.ld_global_mem_addr_gnt(ld_gnt[pe_i]),
				.ld_global_mem_data(ld_data[pe_i * 32+:32]),
				.ld_global_mem_data_vld(ld_data_vld[pe_i]),
				.init_local_mem_addr(init_local_mem_addr),
				.init_local_mem_wr_data(init_local_mem_wr_data),
				.init_local_mem_vld(init_local_mem_vld[pe_i]),
				.init_local_mem_wr_en(init_local_mem_wr_en[pe_i]),
				.init_local_mem_rd_data(init_local_mem_rd_data[pe_i * 32+:32]),
				.init_local_mem_rd_data_vld(init_local_mem_rd_data_vld[pe_i]),
				.monitor(monitor),
				.monitor_pe_out(monitor_pe_out[pe_i * 32+:32]),
				.monitor_instr(monitor_instr[pe_i * 22+:22])
			);
		end
	endgenerate
	assign monitor_global_rd_req = ld_req;
	assign monitor_global_rd_gnt = ld_gnt;
	assign monitor_global_wr_req = st_req;
	assign monitor_global_wr_gnt = st_gnt;
endmodule
module global_mem (
	clk,
	rst,
	config_global_mem_slp,
	config_global_mem_sd,
	global_mem_addr,
	global_mem_wr_data,
	global_mem_wr_en,
	global_mem_rd_en,
	global_mem_rd_data
);
	input clk;
	input rst;
	localparam hw_pkg_N_PE = 2;
	localparam hw_pkg_N_GLOBAL_MEM_BANKS = hw_pkg_N_PE;
	input [1:0] config_global_mem_slp;
	input [1:0] config_global_mem_sd;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	localparam interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L = 10;
	input [19:0] global_mem_addr;
	localparam hw_pkg_DATA_L = 32;
	input [63:0] global_mem_wr_data;
	input [1:0] global_mem_wr_en;
	input [1:0] global_mem_rd_en;
	output wire [63:0] global_mem_rd_data;
	wire [1:0] global_mem_ch_en;
	assign global_mem_ch_en = global_mem_wr_en | global_mem_rd_en;
	genvar mem_i;
	localparam interconnect_pkg_GLOBAL_MEM_RD_LATENCY = 1;
	generate
		for (mem_i = 0; mem_i < hw_pkg_N_GLOBAL_MEM_BANKS; mem_i = mem_i + 1) begin : mem_loop
			sp_mem_model #(
				.DATA_L(hw_pkg_DATA_L),
				.ADDR_L(interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L),
				.RD_LATENCY(interconnect_pkg_GLOBAL_MEM_RD_LATENCY)
			) SP_MEM_MODEL_INS(
				.clk(clk),
				.rst(rst),
				.slp(config_global_mem_slp[mem_i]),
				.sd(config_global_mem_sd[mem_i]),
				.wr_en(global_mem_wr_en[mem_i]),
				.addr(global_mem_addr[mem_i * 10+:10]),
				.wr_data(global_mem_wr_data[mem_i * 32+:32]),
				.rd_data(global_mem_rd_data[mem_i * 32+:32]),
				.ch_en(global_mem_ch_en[mem_i])
			);
		end
	endgenerate
endmodule
module flow_control_vld_rdy_with_latency (
	clk,
	rst,
	en,
	flush,
	reset_state,
	rdy,
	do_operation,
	vld
);
	parameter LATENCY = 1;
	input clk;
	input rst;
	input en;
	input flush;
	input reset_state;
	input rdy;
	output wire do_operation;
	output wire vld;
	wire pre_vld;
	wire final_vld_pre;
	reg do_operation_pre;
	wire vld_rdy_unblocked;
	reg [LATENCY - 1:0] do_operation_delayed;
	assign pre_vld = do_operation_delayed[LATENCY - 1];
	assign vld_rdy_unblocked = (final_vld_pre ? rdy : 1'b1);
	always @(*) begin
		do_operation_pre = 1'b0;
		if (en)
			do_operation_pre = vld_rdy_unblocked;
		if (flush)
			do_operation_pre = 1'b0;
	end
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			do_operation_delayed <= 1'sb0;
		else if (reset_state)
			do_operation_delayed <= 1'sb0;
		else if ((en | flush) & vld_rdy_unblocked) begin
			do_operation_delayed[0] <= do_operation_pre;
			begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i < LATENCY; i = i + 1)
					do_operation_delayed[i] <= do_operation_delayed[i - 1];
			end
		end
	assign final_vld_pre = pre_vld & (en | flush);
	assign vld = final_vld_pre;
	assign do_operation = do_operation_pre;
endmodule
module multiple_streams (
	clk,
	rst,
	slp,
	sd,
	wr_data_io,
	addr_io,
	stream_id_io,
	wr_vld_io,
	rd_vld_io,
	rd_data_io,
	rd_data_vld_io,
	reset_execution_io,
	enable_execution_io,
	done_execution_io,
	stream_start_addr_io,
	stream_end_addr_io,
	data_pe,
	vld_pe,
	rdy_pe
);
	parameter N_STREAMS = 8;
	parameter STREAM_ADDR_L = 10;
	parameter STREAM_W = 24;
	parameter RD_LATENCY = 1;
	input clk;
	input rst;
	input [N_STREAMS - 1:0] slp;
	input [N_STREAMS - 1:0] sd;
	input [STREAM_W - 1:0] wr_data_io;
	input [STREAM_ADDR_L - 1:0] addr_io;
	input [$clog2(N_STREAMS) - 1:0] stream_id_io;
	input wr_vld_io;
	input rd_vld_io;
	output wire [STREAM_W - 1:0] rd_data_io;
	output wire rd_data_vld_io;
	input reset_execution_io;
	input enable_execution_io;
	output wire done_execution_io;
	input [(N_STREAMS * STREAM_ADDR_L) - 1:0] stream_start_addr_io;
	input [(N_STREAMS * STREAM_ADDR_L) - 1:0] stream_end_addr_io;
	output wire [(N_STREAMS * STREAM_W) - 1:0] data_pe;
	output wire [N_STREAMS - 1:0] vld_pe;
	input [N_STREAMS - 1:0] rdy_pe;
	reg [N_STREAMS - 1:0] wr_vld_per_stream_io;
	reg [N_STREAMS - 1:0] rd_addr_vld_per_stream_io;
	wire [(N_STREAMS * STREAM_W) - 1:0] rd_data_per_stream_io;
	wire [N_STREAMS - 1:0] rd_data_vld_per_stream_io;
	wire [N_STREAMS - 1:0] done_execution_per_stream_io;
	localparam DELAY = RD_LATENCY;
	reg [(DELAY * $clog2(N_STREAMS)) - 1:0] rd_stream_id_io_delayed;
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			rd_stream_id_io_delayed <= 1'sb0;
		else begin
			rd_stream_id_io_delayed[0+:$clog2(N_STREAMS)] <= stream_id_io;
			begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i < DELAY; i = i + 1)
					rd_stream_id_io_delayed[i * $clog2(N_STREAMS)+:$clog2(N_STREAMS)] <= rd_stream_id_io_delayed[(i - 1) * $clog2(N_STREAMS)+:$clog2(N_STREAMS)];
			end
		end
	always @(*) begin
		wr_vld_per_stream_io = 1'sb0;
		rd_addr_vld_per_stream_io = 1'sb0;
		wr_vld_per_stream_io[stream_id_io] = wr_vld_io;
		rd_addr_vld_per_stream_io[stream_id_io] = rd_vld_io;
	end
	genvar stream_i;
	generate
		for (stream_i = 0; stream_i < N_STREAMS; stream_i = stream_i + 1) begin : stream_loop
			stream #(
				.STREAM_ADDR_L(STREAM_ADDR_L),
				.STREAM_W(STREAM_W),
				.RD_LATENCY(RD_LATENCY)
			) STREAM_INS(
				.clk(clk),
				.rst(rst),
				.slp(slp[stream_i]),
				.sd(sd[stream_i]),
				.wr_data_io(wr_data_io),
				.addr_io(addr_io),
				.wr_vld_io(wr_vld_per_stream_io[stream_i]),
				.rd_vld_io(rd_addr_vld_per_stream_io[stream_i]),
				.rd_data_io(rd_data_per_stream_io[stream_i * STREAM_W+:STREAM_W]),
				.rd_data_vld_io(rd_data_vld_per_stream_io[stream_i]),
				.reset_execution_io(reset_execution_io),
				.enable_execution_io(enable_execution_io),
				.done_execution_io(done_execution_per_stream_io[stream_i]),
				.stream_start_addr_io(stream_start_addr_io[stream_i * STREAM_ADDR_L+:STREAM_ADDR_L]),
				.stream_end_addr_io(stream_end_addr_io[stream_i * STREAM_ADDR_L+:STREAM_ADDR_L]),
				.data_pe(data_pe[stream_i * STREAM_W+:STREAM_W]),
				.vld_pe(vld_pe[stream_i]),
				.rdy_pe(rdy_pe[stream_i])
			);
		end
	endgenerate
	assign rd_data_io = rd_data_per_stream_io[rd_stream_id_io_delayed[(DELAY - 1) * $clog2(N_STREAMS)+:$clog2(N_STREAMS)] * STREAM_W+:STREAM_W];
	assign rd_data_vld_io = rd_data_vld_per_stream_io[rd_stream_id_io_delayed[(DELAY - 1) * $clog2(N_STREAMS)+:$clog2(N_STREAMS)]];
	assign done_execution_io = (done_execution_per_stream_io == {N_STREAMS {1'b1}} ? 1'b1 : 1'b0);
endmodule
module stream (
	clk,
	rst,
	slp,
	sd,
	wr_data_io,
	addr_io,
	wr_vld_io,
	rd_vld_io,
	rd_data_io,
	rd_data_vld_io,
	reset_execution_io,
	enable_execution_io,
	done_execution_io,
	stream_start_addr_io,
	stream_end_addr_io,
	data_pe,
	vld_pe,
	rdy_pe
);
	parameter STREAM_ADDR_L = 10;
	parameter STREAM_W = 24;
	parameter RD_LATENCY = 1;
	input clk;
	input rst;
	input slp;
	input sd;
	input [STREAM_W - 1:0] wr_data_io;
	input [STREAM_ADDR_L - 1:0] addr_io;
	input wr_vld_io;
	input rd_vld_io;
	output wire [STREAM_W - 1:0] rd_data_io;
	output wire rd_data_vld_io;
	input reset_execution_io;
	input enable_execution_io;
	output wire done_execution_io;
	input [STREAM_ADDR_L - 1:0] stream_start_addr_io;
	input [STREAM_ADDR_L - 1:0] stream_end_addr_io;
	output wire [STREAM_W - 1:0] data_pe;
	output wire vld_pe;
	input rdy_pe;
	reg [STREAM_ADDR_L - 1:0] mem_addr;
	wire mem_wr_en;
	reg mem_rd_en;
	wire mem_ch_en;
	wire [STREAM_W - 1:0] mem_wr_data;
	wire [STREAM_W - 1:0] mem_rd_data;
	wire ongoing_execution;
	wire done_execution_io_pre;
	wire vld_pe_pre;
	reg [STREAM_ADDR_L - 1:0] stream_addr_q;
	wire stream_addr_incr;
	reg [RD_LATENCY - 1:0] rd_addr_vld_io_delayed;
	reg enable_execution_q;
	assign mem_ch_en = mem_wr_en | mem_rd_en;
	assign mem_wr_en = (ongoing_execution ? 0 : wr_vld_io);
	assign mem_wr_data = wr_data_io;
	assign done_execution_io_pre = (stream_addr_q == (stream_end_addr_io + 1) ? 1'b1 : 1'b0);
	assign ongoing_execution = (done_execution_io_pre ? 1'b0 : enable_execution_q);
	always @(*) begin
		mem_addr = stream_addr_q;
		mem_rd_en = 0;
		if (ongoing_execution) begin
			mem_addr = stream_addr_q;
			mem_rd_en = stream_addr_incr;
		end
		else if (mem_wr_en)
			mem_addr = addr_io;
		else if (rd_vld_io) begin
			mem_addr = addr_io;
			mem_rd_en = 1;
		end
	end
	localparam hw_pkg_RESET_STATE = 0;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			stream_addr_q <= 1'sb0;
		else if (reset_execution_io)
			stream_addr_q <= stream_start_addr_io;
		else if (stream_addr_incr)
			stream_addr_q <= stream_addr_q + 1;
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			rd_addr_vld_io_delayed <= 1'sb0;
		else begin
			rd_addr_vld_io_delayed[0] <= rd_vld_io;
			begin : sv2v_autoblock_1
				integer i;
				for (i = 1; i < RD_LATENCY; i = i + 1)
					rd_addr_vld_io_delayed[i] <= rd_addr_vld_io_delayed[i - 1];
			end
		end
	always @(posedge clk or negedge rst)
		if (rst == hw_pkg_RESET_STATE)
			enable_execution_q <= 1'sb0;
		else
			enable_execution_q <= enable_execution_io;
	sp_mem_model #(
		.DATA_L(STREAM_W),
		.ADDR_L(STREAM_ADDR_L),
		.RD_LATENCY(RD_LATENCY)
	) SP_MEM_MODEL_INS(
		.clk(clk),
		.rst(rst),
		.slp(slp),
		.sd(sd),
		.wr_en(mem_wr_en),
		.ch_en(mem_ch_en),
		.addr(mem_addr),
		.wr_data(mem_wr_data),
		.rd_data(mem_rd_data)
	);
	flow_control_vld_rdy_with_latency #(.LATENCY(RD_LATENCY)) FLOW_CONTROL_VLD_RDY_WITH_LATENCY_INS(
		.clk(clk),
		.rst(rst),
		.en(ongoing_execution),
		.flush(1'b0),
		.reset_state(reset_execution_io),
		.rdy(rdy_pe),
		.do_operation(stream_addr_incr),
		.vld(vld_pe_pre)
	);
	assign rd_data_io = mem_rd_data;
	assign rd_data_vld_io = rd_addr_vld_io_delayed[RD_LATENCY - 1];
	assign data_pe = (enable_execution_q ? mem_rd_data : 0);
	assign vld_pe = vld_pe_pre;
	assign done_execution_io = done_execution_io_pre;
endmodule
module streams_top (
	clk,
	rst,
	config_stream_instr_slp,
	config_stream_ld_slp,
	config_stream_st_slp,
	config_stream_instr_sd,
	config_stream_ld_sd,
	config_stream_st_sd,
	monitor_instr_stream_req,
	monitor_instr_stream_gnt,
	monitor_ld_stream_req,
	monitor_ld_stream_gnt,
	monitor_st_stream_req,
	monitor_st_stream_gnt,
	wr_data_io,
	full_addr_io,
	wr_vld_io,
	rd_vld_io,
	rd_data_io,
	rd_data_vld_io,
	reset_execution_io,
	enable_execution_io,
	done_execution_io,
	instr_stream_start_addr_io,
	instr_stream_end_addr_io,
	ld_stream_start_addr_io,
	ld_stream_end_addr_io,
	st_stream_start_addr_io,
	st_stream_end_addr_io,
	instr,
	instr_vld,
	instr_rdy,
	ld_addr,
	ld_addr_vld,
	ld_addr_rdy,
	st_addr,
	st_addr_vld,
	st_addr_rdy
);
	input clk;
	input rst;
	localparam hw_pkg_N_PE = 2;
	input [1:0] config_stream_instr_slp;
	input [1:0] config_stream_ld_slp;
	input [1:0] config_stream_st_slp;
	input [1:0] config_stream_instr_sd;
	input [1:0] config_stream_ld_sd;
	input [1:0] config_stream_st_sd;
	output wire [1:0] monitor_instr_stream_req;
	output wire [1:0] monitor_instr_stream_gnt;
	output wire [1:0] monitor_ld_stream_req;
	output wire [1:0] monitor_ld_stream_gnt;
	output wire [1:0] monitor_st_stream_req;
	output wire [1:0] monitor_st_stream_gnt;
	localparam hw_pkg_DATA_L = 32;
	input [31:0] wr_data_io;
	localparam stream_pkg_INSTR_STR_ADDR_L = 10;
	input [12:0] full_addr_io;
	input wr_vld_io;
	input rd_vld_io;
	output wire [31:0] rd_data_io;
	output wire rd_data_vld_io;
	input reset_execution_io;
	input enable_execution_io;
	output wire done_execution_io;
	input [19:0] instr_stream_start_addr_io;
	input [19:0] instr_stream_end_addr_io;
	localparam stream_pkg_LD_STR_ADDR_L = 10;
	input [19:0] ld_stream_start_addr_io;
	input [19:0] ld_stream_end_addr_io;
	localparam stream_pkg_ST_STR_ADDR_L = 10;
	input [19:0] st_stream_start_addr_io;
	input [19:0] st_stream_end_addr_io;
	localparam hw_pkg_OPCODE_L = 4;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam hw_pkg_INSTR_L = 22;
	localparam stream_pkg_INSTR_STR_WORD_L = hw_pkg_INSTR_L;
	output wire [43:0] instr;
	output wire [1:0] instr_vld;
	input [1:0] instr_rdy;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	localparam stream_pkg_LD_STR_WORD_L = 17;
	output wire [33:0] ld_addr;
	output wire [1:0] ld_addr_vld;
	input [1:0] ld_addr_rdy;
	localparam stream_pkg_ST_STR_WORD_L = hw_pkg_GLOBAL_MEM_ADDR_L;
	output wire [23:0] st_addr;
	output wire [1:0] st_addr_vld;
	input [1:0] st_addr_rdy;
	localparam STREAM_ID_L = 1;
	localparam MAX_ADDR_L = stream_pkg_INSTR_STR_ADDR_L;
	localparam STREAM_ID_START = MAX_ADDR_L;
	localparam TYPE_START = 11;
	localparam TYPE_L = 2;
	localparam INSTR_TYPE = 0;
	localparam LD_TYPE = 1;
	localparam ST_TYPE = 2;
	wire [1:0] type_io;
	wire [0:0] stream_io;
	wire [9:0] addr_io;
	reg wr_vld_io_instr;
	reg wr_vld_io_ld;
	reg wr_vld_io_st;
	reg rd_vld_io_instr;
	reg rd_vld_io_ld;
	reg rd_vld_io_st;
	wire [21:0] rd_data_io_instr;
	wire [16:0] rd_data_io_ld;
	wire [11:0] rd_data_io_st;
	reg [31:0] rd_data_io_pre;
	wire rd_data_vld_io_instr;
	wire rd_data_vld_io_ld;
	wire rd_data_vld_io_st;
	wire done_execution_io_instr;
	wire done_execution_io_ld;
	wire done_execution_io_st;
	wire [1:0] instr_vld_pre;
	wire [1:0] ld_vld_pre;
	wire [1:0] st_vld_pre;
	assign type_io = full_addr_io[TYPE_START+:TYPE_L];
	assign stream_io = full_addr_io[STREAM_ID_START+:STREAM_ID_L];
	assign addr_io = full_addr_io[0+:MAX_ADDR_L];
	always @(*) begin
		wr_vld_io_instr = 1'sb0;
		wr_vld_io_ld = 1'sb0;
		wr_vld_io_st = 1'sb0;
		case (type_io)
			INSTR_TYPE: wr_vld_io_instr = wr_vld_io;
			LD_TYPE: wr_vld_io_ld = wr_vld_io;
			ST_TYPE: wr_vld_io_st = wr_vld_io;
			default:
				;
		endcase
	end
	always @(*) begin
		rd_vld_io_instr = 1'sb0;
		rd_vld_io_ld = 1'sb0;
		rd_vld_io_st = 1'sb0;
		case (type_io)
			INSTR_TYPE: rd_vld_io_instr = rd_vld_io;
			LD_TYPE: rd_vld_io_ld = rd_vld_io;
			ST_TYPE: rd_vld_io_st = rd_vld_io;
		endcase
	end
	always @(*) begin
		rd_data_io_pre = 1'sb0;
		if (rd_data_vld_io_instr)
			rd_data_io_pre = rd_data_io_instr;
		else if (rd_data_vld_io_ld)
			rd_data_io_pre = rd_data_io_ld;
		else if (rd_data_vld_io_st)
			rd_data_io_pre = rd_data_io_st;
	end
	localparam stream_pkg_STR_RD_LATENCY = 1;
	multiple_streams #(
		.N_STREAMS(hw_pkg_N_PE),
		.STREAM_ADDR_L(stream_pkg_INSTR_STR_ADDR_L),
		.STREAM_W(stream_pkg_INSTR_STR_WORD_L),
		.RD_LATENCY(stream_pkg_STR_RD_LATENCY)
	) MULTIPLE_STREAMS_INSTR_INS(
		.clk(clk),
		.rst(rst),
		.slp(config_stream_instr_slp),
		.sd(config_stream_instr_sd),
		.wr_data_io(wr_data_io[0+:stream_pkg_INSTR_STR_WORD_L]),
		.addr_io(addr_io),
		.stream_id_io(stream_io),
		.wr_vld_io(wr_vld_io_instr),
		.rd_vld_io(rd_vld_io_instr),
		.rd_data_io(rd_data_io_instr[0+:stream_pkg_INSTR_STR_WORD_L]),
		.rd_data_vld_io(rd_data_vld_io_instr),
		.reset_execution_io(reset_execution_io),
		.enable_execution_io(enable_execution_io),
		.done_execution_io(done_execution_io_instr),
		.stream_start_addr_io(instr_stream_start_addr_io),
		.stream_end_addr_io(instr_stream_end_addr_io),
		.data_pe(instr),
		.vld_pe(instr_vld_pre),
		.rdy_pe(instr_rdy)
	);
	multiple_streams #(
		.N_STREAMS(hw_pkg_N_PE),
		.STREAM_ADDR_L(stream_pkg_LD_STR_ADDR_L),
		.STREAM_W(stream_pkg_LD_STR_WORD_L),
		.RD_LATENCY(stream_pkg_STR_RD_LATENCY)
	) MULTIPLE_STREAMS_LD_INS(
		.clk(clk),
		.rst(rst),
		.slp(config_stream_ld_slp),
		.sd(config_stream_ld_sd),
		.wr_data_io(wr_data_io[0+:stream_pkg_LD_STR_WORD_L]),
		.addr_io(addr_io[0+:stream_pkg_LD_STR_ADDR_L]),
		.stream_id_io(stream_io),
		.wr_vld_io(wr_vld_io_ld),
		.rd_vld_io(rd_vld_io_ld),
		.rd_data_io(rd_data_io_ld[0+:stream_pkg_LD_STR_WORD_L]),
		.rd_data_vld_io(rd_data_vld_io_ld),
		.reset_execution_io(reset_execution_io),
		.enable_execution_io(enable_execution_io),
		.done_execution_io(done_execution_io_ld),
		.stream_start_addr_io(ld_stream_start_addr_io),
		.stream_end_addr_io(ld_stream_end_addr_io),
		.data_pe(ld_addr),
		.vld_pe(ld_vld_pre),
		.rdy_pe(ld_addr_rdy)
	);
	multiple_streams #(
		.N_STREAMS(hw_pkg_N_PE),
		.STREAM_ADDR_L(stream_pkg_ST_STR_ADDR_L),
		.STREAM_W(stream_pkg_ST_STR_WORD_L),
		.RD_LATENCY(stream_pkg_STR_RD_LATENCY)
	) MULTIPLE_STREAMS_ST_INS(
		.clk(clk),
		.rst(rst),
		.slp(config_stream_st_slp),
		.sd(config_stream_st_sd),
		.wr_data_io(wr_data_io[0+:stream_pkg_ST_STR_WORD_L]),
		.addr_io(addr_io[0+:stream_pkg_ST_STR_ADDR_L]),
		.stream_id_io(stream_io),
		.wr_vld_io(wr_vld_io_st),
		.rd_vld_io(rd_vld_io_st),
		.rd_data_io(rd_data_io_st[0+:stream_pkg_ST_STR_WORD_L]),
		.rd_data_vld_io(rd_data_vld_io_st),
		.reset_execution_io(reset_execution_io),
		.enable_execution_io(enable_execution_io),
		.done_execution_io(done_execution_io_st),
		.stream_start_addr_io(st_stream_start_addr_io),
		.stream_end_addr_io(st_stream_end_addr_io),
		.data_pe(st_addr),
		.vld_pe(st_vld_pre),
		.rdy_pe(st_addr_rdy)
	);
	assign rd_data_io = rd_data_io_pre;
	assign rd_data_vld_io = (((rd_data_vld_io_instr == 0) && (rd_data_vld_io_ld == 0)) && (rd_data_vld_io_st == 0) ? 0 : 1);
	assign done_execution_io = done_execution_io_instr;
	assign monitor_instr_stream_req = instr_vld_pre;
	assign monitor_instr_stream_gnt = instr_rdy;
	assign monitor_ld_stream_req = ld_vld_pre;
	assign monitor_ld_stream_gnt = ld_addr_rdy;
	assign monitor_st_stream_req = st_vld_pre;
	assign monitor_st_stream_gnt = st_addr_rdy;
	assign instr_vld = instr_vld_pre;
	assign ld_addr_vld = ld_vld_pre;
	assign st_addr_vld = st_vld_pre;
endmodule
module full_design_wo_periphery (
	clk,
	rst,
	config_local_mem_slp,
	config_local_mem_sd,
	config_global_mem_slp,
	config_global_mem_sd,
	config_stream_instr_slp,
	config_stream_ld_slp,
	config_stream_st_slp,
	config_stream_instr_sd,
	config_stream_ld_sd,
	config_stream_st_sd,
	init_global_mem_addr,
	init_global_mem_vld,
	init_global_mem_wr_en,
	init_global_mem_wr_data,
	init_global_mem_rd_data,
	init_global_mem_rd_data_vld,
	init_local_mem_addr,
	init_local_mem_wr_data,
	init_local_mem_vld,
	init_local_mem_wr_en,
	init_local_mem_rd_data,
	init_local_mem_rd_data_vld,
	init_stream_wr_data,
	init_stream_addr,
	init_stream_wr_vld,
	init_stream_rd_vld,
	init_stream_rd_data,
	init_stream_rd_data_vld,
	instr_stream_start_addr_io,
	instr_stream_end_addr_io,
	ld_stream_start_addr_io,
	ld_stream_end_addr_io,
	st_stream_start_addr_io,
	st_stream_end_addr_io,
	precision_config,
	reset_execution_io,
	enable_execution_io,
	done_execution_io,
	monitor,
	monitor_global_rd_req,
	monitor_global_rd_gnt,
	monitor_global_wr_req,
	monitor_global_wr_gnt,
	monitor_instr_stream_req,
	monitor_instr_stream_gnt,
	monitor_ld_stream_req,
	monitor_ld_stream_gnt,
	monitor_st_stream_req,
	monitor_st_stream_gnt,
	monitor_pe_out,
	monitor_instr
);
	input clk;
	input rst;
	localparam hw_pkg_N_PE = 2;
	input [1:0] config_local_mem_slp;
	input [1:0] config_local_mem_sd;
	input [1:0] config_global_mem_slp;
	input [1:0] config_global_mem_sd;
	input [1:0] config_stream_instr_slp;
	input [1:0] config_stream_ld_slp;
	input [1:0] config_stream_st_slp;
	input [1:0] config_stream_instr_sd;
	input [1:0] config_stream_ld_sd;
	input [1:0] config_stream_st_sd;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	input [11:0] init_global_mem_addr;
	input init_global_mem_vld;
	input init_global_mem_wr_en;
	localparam hw_pkg_DATA_L = 32;
	input [31:0] init_global_mem_wr_data;
	output wire [31:0] init_global_mem_rd_data;
	output wire init_global_mem_rd_data_vld;
	localparam hw_pkg_LOCAL_MEM_ADDR_L = 9;
	input [8:0] init_local_mem_addr;
	input [31:0] init_local_mem_wr_data;
	input [1:0] init_local_mem_vld;
	input [1:0] init_local_mem_wr_en;
	output wire [63:0] init_local_mem_rd_data;
	output wire [1:0] init_local_mem_rd_data_vld;
	input [31:0] init_stream_wr_data;
	localparam stream_pkg_INSTR_STR_ADDR_L = 10;
	input [12:0] init_stream_addr;
	input init_stream_wr_vld;
	input init_stream_rd_vld;
	output wire [31:0] init_stream_rd_data;
	output wire init_stream_rd_data_vld;
	input [19:0] instr_stream_start_addr_io;
	input [19:0] instr_stream_end_addr_io;
	localparam stream_pkg_LD_STR_ADDR_L = 10;
	input [19:0] ld_stream_start_addr_io;
	input [19:0] ld_stream_end_addr_io;
	localparam stream_pkg_ST_STR_ADDR_L = 10;
	input [19:0] st_stream_start_addr_io;
	input [19:0] st_stream_end_addr_io;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	input [1:0] precision_config;
	input reset_execution_io;
	input enable_execution_io;
	output wire done_execution_io;
	input monitor;
	output wire [1:0] monitor_global_rd_req;
	output wire [1:0] monitor_global_rd_gnt;
	output wire [1:0] monitor_global_wr_req;
	output wire [1:0] monitor_global_wr_gnt;
	output wire [1:0] monitor_instr_stream_req;
	output wire [1:0] monitor_instr_stream_gnt;
	output wire [1:0] monitor_ld_stream_req;
	output wire [1:0] monitor_ld_stream_gnt;
	output wire [1:0] monitor_st_stream_req;
	output wire [1:0] monitor_st_stream_gnt;
	output wire [63:0] monitor_pe_out;
	localparam hw_pkg_OPCODE_L = 4;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam hw_pkg_INSTR_L = 22;
	output wire [43:0] monitor_instr;
	localparam hw_pkg_N_GLOBAL_MEM_BANKS = hw_pkg_N_PE;
	localparam interconnect_pkg_GLOBAL_MEM_PER_BANK_ADDR_L = 10;
	wire [19:0] global_mem_addr;
	wire [63:0] global_mem_wr_data;
	wire [1:0] global_mem_wr_en;
	wire [1:0] global_mem_rd_en;
	wire [63:0] global_mem_rd_data;
	localparam stream_pkg_INSTR_STR_WORD_L = hw_pkg_INSTR_L;
	wire [43:0] instr;
	wire [1:0] instr_vld;
	wire [1:0] instr_rdy;
	localparam stream_pkg_LD_STR_WORD_L = 17;
	wire [33:0] ld_addr;
	wire [1:0] ld_addr_vld;
	wire [1:0] ld_addr_rdy;
	localparam stream_pkg_ST_STR_WORD_L = hw_pkg_GLOBAL_MEM_ADDR_L;
	wire [23:0] st_addr;
	wire [1:0] st_addr_vld;
	wire [1:0] st_addr_rdy;
	reg [23:0] ld_mem_addr;
	reg [9:0] ld_reg_addr;
	always @(*) begin : sv2v_autoblock_1
		integer i;
		for (i = 1; i >= 0; i = i - 1)
			{ld_reg_addr[i * 5+:5], ld_mem_addr[i * 12+:12]} = ld_addr[i * 17+:17];
	end
	processing_logic PROCESSING_LOGIC_INS(
		.clk(clk),
		.rst(rst),
		.config_local_mem_slp(config_local_mem_slp),
		.config_local_mem_sd(config_local_mem_sd),
		.precision_config(precision_config),
		.instr(instr),
		.instr_req(instr_vld),
		.instr_ack(instr_rdy),
		.st_mem_addr_in(st_addr),
		.st_mem_addr_in_req(st_addr_vld),
		.st_mem_addr_in_ack(st_addr_rdy),
		.ld_mem_addr_in(ld_mem_addr),
		.ld_reg_addr_in(ld_reg_addr),
		.ld_mem_addr_in_req(ld_addr_vld),
		.ld_mem_addr_in_ack(ld_addr_rdy),
		.global_mem_addr(global_mem_addr),
		.global_mem_wr_data(global_mem_wr_data),
		.global_mem_wr_en(global_mem_wr_en),
		.global_mem_rd_en(global_mem_rd_en),
		.global_mem_rd_data(global_mem_rd_data),
		.init_global_mem_addr(init_global_mem_addr),
		.init_global_mem_vld(init_global_mem_vld),
		.init_global_mem_wr_en(init_global_mem_wr_en),
		.init_global_mem_wr_data(init_global_mem_wr_data),
		.init_global_mem_rd_data(init_global_mem_rd_data),
		.init_global_mem_rd_data_vld(init_global_mem_rd_data_vld),
		.init_local_mem_addr(init_local_mem_addr),
		.init_local_mem_wr_data(init_local_mem_wr_data),
		.init_local_mem_vld(init_local_mem_vld),
		.init_local_mem_wr_en(init_local_mem_wr_en),
		.init_local_mem_rd_data(init_local_mem_rd_data),
		.init_local_mem_rd_data_vld(init_local_mem_rd_data_vld),
		.monitor(monitor),
		.monitor_global_rd_req(monitor_global_rd_req),
		.monitor_global_rd_gnt(monitor_global_rd_gnt),
		.monitor_global_wr_req(monitor_global_wr_req),
		.monitor_global_wr_gnt(monitor_global_wr_gnt),
		.monitor_pe_out(monitor_pe_out),
		.monitor_instr(monitor_instr)
	);
	global_mem GLOBAL_MEM_INS(
		.clk(clk),
		.rst(rst),
		.config_global_mem_slp(config_global_mem_slp),
		.config_global_mem_sd(config_global_mem_sd),
		.global_mem_addr(global_mem_addr),
		.global_mem_wr_data(global_mem_wr_data),
		.global_mem_wr_en(global_mem_wr_en),
		.global_mem_rd_en(global_mem_rd_en),
		.global_mem_rd_data(global_mem_rd_data)
	);
	streams_top STREAMS_TOP_INS(
		.clk(clk),
		.rst(rst),
		.config_stream_instr_slp(config_stream_instr_slp),
		.config_stream_ld_slp(config_stream_ld_slp),
		.config_stream_st_slp(config_stream_st_slp),
		.config_stream_instr_sd(config_stream_instr_sd),
		.config_stream_ld_sd(config_stream_ld_sd),
		.config_stream_st_sd(config_stream_st_sd),
		.monitor_instr_stream_req(monitor_instr_stream_req),
		.monitor_instr_stream_gnt(monitor_instr_stream_gnt),
		.monitor_ld_stream_req(monitor_ld_stream_req),
		.monitor_ld_stream_gnt(monitor_ld_stream_gnt),
		.monitor_st_stream_req(monitor_st_stream_req),
		.monitor_st_stream_gnt(monitor_st_stream_gnt),
		.wr_data_io(init_stream_wr_data),
		.full_addr_io(init_stream_addr),
		.wr_vld_io(init_stream_wr_vld),
		.rd_vld_io(init_stream_rd_vld),
		.rd_data_io(init_stream_rd_data),
		.rd_data_vld_io(init_stream_rd_data_vld),
		.reset_execution_io(reset_execution_io),
		.enable_execution_io(enable_execution_io),
		.done_execution_io(done_execution_io),
		.instr_stream_start_addr_io(instr_stream_start_addr_io),
		.instr_stream_end_addr_io(instr_stream_end_addr_io),
		.ld_stream_start_addr_io(ld_stream_start_addr_io),
		.ld_stream_end_addr_io(ld_stream_end_addr_io),
		.st_stream_start_addr_io(st_stream_start_addr_io),
		.st_stream_end_addr_io(st_stream_end_addr_io),
		.instr(instr),
		.instr_vld(instr_vld),
		.instr_rdy(instr_rdy),
		.ld_addr(ld_addr),
		.ld_addr_vld(ld_addr_vld),
		.ld_addr_rdy(ld_addr_rdy),
		.st_addr(st_addr),
		.st_addr_vld(st_addr_vld),
		.st_addr_rdy(st_addr_rdy)
	);
endmodule
module dpu_2core (
	clk,
	rst,
	in,
	io_opcode,
	reset_execution_io,
	enable_execution_io,
	done_execution_io,
	out
);
	input clk;
	input rst;
	localparam periphery_pkg_INPUT_DATA_L = 16;
	input [15:0] in;
	localparam periphery_pkg_IO_OPCODE_L = 4;
	input [3:0] io_opcode;
	input reset_execution_io;
	input enable_execution_io;
	output wire done_execution_io;
	output wire [31:0] out;
	localparam periphery_pkg_OUTPUT_DATA_L = 32;
	localparam IO_OUT_L = periphery_pkg_OUTPUT_DATA_L;
	wire config_shift_en;
	wire rd_en;
	wire wr_en;
	wire monitor;
	wire reg_shift_en;
	localparam periphery_pkg_INPUT_REG_L = 64;
	wire [63:0] reg_data;
	localparam hw_pkg_N_PE = 2;
	wire [1:0] monitor_global_rd_req;
	wire [1:0] monitor_global_rd_gnt;
	wire [1:0] monitor_global_wr_req;
	wire [1:0] monitor_global_wr_gnt;
	wire [1:0] monitor_instr_stream_req;
	wire [1:0] monitor_instr_stream_gnt;
	wire [1:0] monitor_ld_stream_req;
	wire [1:0] monitor_ld_stream_gnt;
	wire [1:0] monitor_st_stream_req;
	wire [1:0] monitor_st_stream_gnt;
	localparam hw_pkg_DATA_L = 32;
	wire [63:0] monitor_pe_out;
	localparam hw_pkg_OPCODE_L = 4;
	localparam hw_pkg_REGBANK_SIZE = 32;
	localparam hw_pkg_REG_ADDR_L = 5;
	localparam hw_pkg_INSTR_L = 22;
	wire [43:0] monitor_instr;
	localparam hw_pkg_GLOBAL_MEM_BANK_DEPTH = 1024;
	localparam hw_pkg_GLOBAL_MEM_ADDR_L = 12;
	wire [11:0] init_global_mem_addr;
	wire init_global_mem_vld;
	wire init_global_mem_wr_en;
	wire [31:0] init_global_mem_wr_data;
	wire [31:0] init_global_mem_rd_data;
	wire init_global_mem_rd_data_vld;
	localparam hw_pkg_LOCAL_MEM_ADDR_L = 9;
	wire [8:0] init_local_mem_addr;
	wire [1:0] init_local_mem_vld;
	wire [1:0] init_local_mem_wr_en;
	wire [31:0] init_local_mem_wr_data;
	wire [63:0] init_local_mem_rd_data;
	wire [1:0] init_local_mem_rd_data_vld;
	wire [31:0] init_stream_wr_data;
	localparam stream_pkg_INSTR_STR_ADDR_L = 10;
	wire [12:0] init_stream_addr;
	wire init_stream_wr_vld;
	wire init_stream_rd_vld;
	wire [31:0] init_stream_rd_data;
	wire init_stream_rd_data_vld;
	wire [19:0] config_instr_stream_start_addr_io;
	wire [19:0] config_instr_stream_end_addr_io;
	localparam stream_pkg_LD_STR_ADDR_L = 10;
	wire [19:0] config_ld_stream_start_addr_io;
	wire [19:0] config_ld_stream_end_addr_io;
	localparam stream_pkg_ST_STR_ADDR_L = 10;
	wire [19:0] config_st_stream_start_addr_io;
	wire [19:0] config_st_stream_end_addr_io;
	localparam hw_pkg_PRECISION_CONFIG_L = 2;
	wire [1:0] config_precision_config;
	wire [1:0] config_local_mem_slp;
	wire [1:0] config_local_mem_sd;
	wire [1:0] config_global_mem_slp;
	wire [1:0] config_global_mem_sd;
	wire [1:0] config_stream_instr_slp;
	wire [1:0] config_stream_ld_slp;
	wire [1:0] config_stream_st_slp;
	wire [1:0] config_stream_instr_sd;
	wire [1:0] config_stream_ld_sd;
	wire [1:0] config_stream_st_sd;
	reg [31:0] out_pre;
	wire [31:0] out_init;
	wire [31:0] out_config;
	wire [31:0] out_monitor;
	io_decode IO_DECODE_INS(
		.io_opcode(io_opcode),
		.config_shift_en(config_shift_en),
		.rd_en(rd_en),
		.wr_en(wr_en),
		.monitor(monitor),
		.reg_shift_en(reg_shift_en)
	);
	io_registers IO_REGISTERS_INS(
		.clk(clk),
		.rst(rst),
		.in(in),
		.shift_en(reg_shift_en),
		.reg_data(reg_data)
	);
	io_mem_access IO_MEM_ACCESS_INS(
		.clk(clk),
		.rst(rst),
		.in(reg_data),
		.wr_en(wr_en),
		.rd_en(rd_en),
		.init_global_mem_addr(init_global_mem_addr),
		.init_global_mem_vld(init_global_mem_vld),
		.init_global_mem_wr_en(init_global_mem_wr_en),
		.init_global_mem_wr_data(init_global_mem_wr_data),
		.init_global_mem_rd_data(init_global_mem_rd_data),
		.init_global_mem_rd_data_vld(init_global_mem_rd_data_vld),
		.init_local_mem_addr(init_local_mem_addr),
		.init_local_mem_vld(init_local_mem_vld),
		.init_local_mem_wr_en(init_local_mem_wr_en),
		.init_local_mem_wr_data(init_local_mem_wr_data),
		.init_local_mem_rd_data(init_local_mem_rd_data),
		.init_local_mem_rd_data_vld(init_local_mem_rd_data_vld),
		.init_stream_wr_data(init_stream_wr_data),
		.init_stream_addr(init_stream_addr),
		.init_stream_wr_vld(init_stream_wr_vld),
		.init_stream_rd_vld(init_stream_rd_vld),
		.init_stream_rd_data(init_stream_rd_data),
		.init_stream_rd_data_vld(init_stream_rd_data_vld),
		.out(out_init)
	);
	config_registers #(.CONFIG_L(IO_OUT_L)) CONFIG_REGISTERS_INS(
		.clk(clk),
		.rst(rst),
		.instr_stream_start_addr_io(config_instr_stream_start_addr_io),
		.instr_stream_end_addr_io(config_instr_stream_end_addr_io),
		.ld_stream_start_addr_io(config_ld_stream_start_addr_io),
		.ld_stream_end_addr_io(config_ld_stream_end_addr_io),
		.st_stream_start_addr_io(config_st_stream_start_addr_io),
		.st_stream_end_addr_io(config_st_stream_end_addr_io),
		.precision_config(config_precision_config),
		.config_local_mem_slp(config_local_mem_slp),
		.config_local_mem_sd(config_local_mem_sd),
		.config_global_mem_slp(config_global_mem_slp),
		.config_global_mem_sd(config_global_mem_sd),
		.config_stream_instr_slp(config_stream_instr_slp),
		.config_stream_ld_slp(config_stream_ld_slp),
		.config_stream_st_slp(config_stream_st_slp),
		.config_stream_instr_sd(config_stream_instr_sd),
		.config_stream_ld_sd(config_stream_ld_sd),
		.config_stream_st_sd(config_stream_st_sd),
		.data_in(reg_data[0+:IO_OUT_L]),
		.data_out(out_config),
		.shift_en(config_shift_en)
	);
	/* io_monitor IO_MONITOR_INS( */
	/* 	.reg_data(reg_data), */
	/* 	.global_rd_req(monitor_global_rd_req), */
	/* 	.global_rd_gnt(monitor_global_rd_gnt), */
	/* 	.global_wr_req(monitor_global_wr_req), */
	/* 	.global_wr_gnt(monitor_global_wr_gnt), */
	/* 	.instr_stream_req(monitor_instr_stream_req), */
	/* 	.instr_stream_gnt(monitor_instr_stream_gnt), */
	/* 	.ld_stream_req(monitor_ld_stream_req), */
	/* 	.ld_stream_gnt(monitor_ld_stream_gnt), */
	/* 	.st_stream_req(monitor_st_stream_req), */
	/* 	.st_stream_gnt(monitor_st_stream_gnt), */
	/* 	.pe_out(monitor_pe_out), */
	/* 	.instr(monitor_instr), */
	/* 	.out(out_monitor) */
	/* ); */
	full_design_wo_periphery FULL_DESIGN_WO_PERIPHERY_INS(
		.clk(clk),
		.rst(rst),
		.config_local_mem_slp(config_local_mem_slp),
		.config_local_mem_sd(config_local_mem_sd),
		.config_global_mem_slp(config_global_mem_slp),
		.config_global_mem_sd(config_global_mem_sd),
		.config_stream_instr_slp(config_stream_instr_slp),
		.config_stream_ld_slp(config_stream_ld_slp),
		.config_stream_st_slp(config_stream_st_slp),
		.config_stream_instr_sd(config_stream_instr_sd),
		.config_stream_ld_sd(config_stream_ld_sd),
		.config_stream_st_sd(config_stream_st_sd),
		.init_global_mem_addr(init_global_mem_addr),
		.init_global_mem_vld(init_global_mem_vld),
		.init_global_mem_wr_en(init_global_mem_wr_en),
		.init_global_mem_wr_data(init_global_mem_wr_data),
		.init_global_mem_rd_data(init_global_mem_rd_data),
		.init_global_mem_rd_data_vld(init_global_mem_rd_data_vld),
		.init_local_mem_addr(init_local_mem_addr),
		.init_local_mem_wr_data(init_local_mem_wr_data),
		.init_local_mem_vld(init_local_mem_vld),
		.init_local_mem_wr_en(init_local_mem_wr_en),
		.init_local_mem_rd_data(init_local_mem_rd_data),
		.init_local_mem_rd_data_vld(init_local_mem_rd_data_vld),
		.init_stream_wr_data(init_stream_wr_data),
		.init_stream_addr(init_stream_addr),
		.init_stream_wr_vld(init_stream_wr_vld),
		.init_stream_rd_vld(init_stream_rd_vld),
		.init_stream_rd_data(init_stream_rd_data),
		.init_stream_rd_data_vld(init_stream_rd_data_vld),
		.instr_stream_start_addr_io(config_instr_stream_start_addr_io),
		.instr_stream_end_addr_io(config_instr_stream_end_addr_io),
		.ld_stream_start_addr_io(config_ld_stream_start_addr_io),
		.ld_stream_end_addr_io(config_ld_stream_end_addr_io),
		.st_stream_start_addr_io(config_st_stream_start_addr_io),
		.st_stream_end_addr_io(config_st_stream_end_addr_io),
		.precision_config(config_precision_config),
		.reset_execution_io(reset_execution_io),
		.enable_execution_io(enable_execution_io),
		.done_execution_io(done_execution_io),
		.monitor(monitor),
		.monitor_global_rd_req(monitor_global_rd_req),
		.monitor_global_rd_gnt(monitor_global_rd_gnt),
		.monitor_global_wr_req(monitor_global_wr_req),
		.monitor_global_wr_gnt(monitor_global_wr_gnt),
		.monitor_instr_stream_req(monitor_instr_stream_req),
		.monitor_instr_stream_gnt(monitor_instr_stream_gnt),
		.monitor_ld_stream_req(monitor_ld_stream_req),
		.monitor_ld_stream_gnt(monitor_ld_stream_gnt),
		.monitor_st_stream_req(monitor_st_stream_req),
		.monitor_st_stream_gnt(monitor_st_stream_gnt),
		.monitor_pe_out(monitor_pe_out),
		.monitor_instr(monitor_instr)
	);
	always @(*) begin
		out_pre = out_init;
		if (config_shift_en)
			out_pre = out_config;
		else if (monitor)
			out_pre = out_monitor;
		else
			out_pre = out_init;
	end
	assign out = out_pre;
endmodule
