`include "sys_defs.svh"

module core_top (
	clk,
	rstn,
	clean_kv_cache,
	clean_kv_cache_user_id,
	core_mem_addr,
	core_mem_wdata,
	core_mem_wen,
	core_mem_rdata,
	core_mem_ren,
	core_mem_rvld,
	op_cfg_vld,
	op_cfg,
	usr_cfg_vld,
	usr_cfg,
	model_cfg_vld,
	model_cfg,
	pmu_cfg_vld,
	pmu_cfg,
	rc_cfg_vld,
	rc_cfg,
	control_state,
	control_state_update,
	start,
	finish,
	in_gbus_addr,
	in_gbus_wen,
	in_gbus_wdata,
	out_gbus_addr,
	out_gbus_wen,
	out_gbus_wdata,
	rc_scale,
	rc_scale_vld,
	rc_scale_clear,
	vlink_data_in,
	vlink_data_in_vld,
	vlink_data_out,
	vlink_data_out_vld,
	hlink_wdata,
	hlink_wen,
	hlink_rdata,
	hlink_rvalid
);
	reg _sv2v_0;
	parameter GBUS_DATA_WIDTH = MAC_MULT_NUM * IDATA_WIDTH;
	parameter GBUS_ADDR_WIDTH = `GBUS_ADDR_WIDTH;
	parameter CMEM_ADDR_WIDTH = `CMEM_ADDR_WIDTH;
	parameter MAC_MULT_NUM = `MAC_MULT_NUM;
	parameter IDATA_WIDTH = `IDATA_WIDTH;
	parameter VLINK_DATA_WIDTH = MAC_MULT_NUM * IDATA_WIDTH;
	parameter HLINK_DATA_WIDTH = MAC_MULT_NUM * IDATA_WIDTH;
	parameter CMEM_DATA_WIDTH = MAC_MULT_NUM * IDATA_WIDTH;
	parameter ODATA_BIT = `ODATA_WIDTH;
	parameter RECOMPUTE_SCALE_WIDTH = `RECOMPUTE_SCALE_WIDTH;
	parameter RECOMPUTE_SHIFT_WIDTH = `RECOMPUTE_SHIFT_WIDTH;
	parameter RC_RETIMING_REG_NUM = `RC_RETIMING_REG_NUM;
	parameter CDATA_ACCU_NUM_WIDTH = `CDATA_ACCU_NUM_WIDTH;
	parameter CDATA_SCALE_WIDTH = `CDATA_SCALE_WIDTH;
	parameter CDATA_BIAS_WIDTH = `CDATA_BIAS_WIDTH;
	parameter CDATA_SHIFT_WIDTH = `CDATA_SHIFT_WIDTH;
	parameter USER_ID_WIDTH = `USER_ID_WIDTH;
	parameter CORE_MEM_ADDR_WIDTH = `CORE_MEM_ADDR_WIDTH;
	parameter INTERFACE_DATA_WIDTH = `INTERFACE_DATA_WIDTH;
	parameter HEAD_INDEX = 0;
	parameter CORE_INDEX = 0;
	parameter CACHE_DEPTH = `KV_CACHE_DEPTH_SINGLE_USER;
	parameter CACHE_NUM = `MAC_MULT_NUM;

	input clk;
	input rstn;
	input wire clean_kv_cache;
	input wire [USER_ID_WIDTH - 1:0] clean_kv_cache_user_id;
	input wire [CORE_MEM_ADDR_WIDTH - 1:0] core_mem_addr;
	input wire [INTERFACE_DATA_WIDTH - 1:0] core_mem_wdata;
	input wire core_mem_wen;
	output wire [INTERFACE_DATA_WIDTH - 1:0] core_mem_rdata;
	input wire core_mem_ren;
	output wire core_mem_rvld;
	input op_cfg_vld;
	input wire [40:0] op_cfg;
	input usr_cfg_vld;
	input wire [11:0] usr_cfg;
	input model_cfg_vld;
	input wire [29:0] model_cfg;
	input pmu_cfg_vld;
	input wire [3:0] pmu_cfg;
	input wire rc_cfg_vld;
	input wire [83:0] rc_cfg;
	input wire [31:0] control_state;
	input wire control_state_update;
	input wire start;
	output wire finish;
	localparam integer BUS_CMEM_ADDR_WIDTH = 13;
	localparam integer BUS_CORE_ADDR_WIDTH = 4;
	localparam integer HEAD_SRAM_BIAS_WIDTH = 2;
	input wire [((HEAD_SRAM_BIAS_WIDTH + BUS_CORE_ADDR_WIDTH) + BUS_CMEM_ADDR_WIDTH) - 1:0] in_gbus_addr;
	input in_gbus_wen;
	input [GBUS_DATA_WIDTH - 1:0] in_gbus_wdata;
	output wire [((HEAD_SRAM_BIAS_WIDTH + BUS_CORE_ADDR_WIDTH) + BUS_CMEM_ADDR_WIDTH) - 1:0] out_gbus_addr;
	output wire out_gbus_wen;
	output wire [GBUS_DATA_WIDTH - 1:0] out_gbus_wdata;
	input wire [RECOMPUTE_SCALE_WIDTH - 1:0] rc_scale;
	input wire rc_scale_vld;
	input wire rc_scale_clear;
	input wire [VLINK_DATA_WIDTH - 1:0] vlink_data_in;
	input wire vlink_data_in_vld;
	output wire [VLINK_DATA_WIDTH - 1:0] vlink_data_out;
	output wire vlink_data_out_vld;
	input [HLINK_DATA_WIDTH - 1:0] hlink_wdata;
	input hlink_wen;
	output wire [HLINK_DATA_WIDTH - 1:0] hlink_rdata;
	output wire hlink_rvalid;
	reg [40:0] op_cfg_reg;
	reg [11:0] usr_cfg_reg;
	reg [29:0] model_cfg_reg;
	reg [3:0] pmu_cfg_reg;
	reg [CDATA_ACCU_NUM_WIDTH - 1:0] cfg_acc_num;
	reg [CDATA_SCALE_WIDTH - 1:0] cfg_quant_scale;
	reg [CDATA_BIAS_WIDTH - 1:0] cfg_quant_bias;
	reg [CDATA_SHIFT_WIDTH - 1:0] cfg_quant_shift;
	reg clean_kv_cache_delay1;
	reg [USER_ID_WIDTH - 1:0] clean_kv_cache_user_id_delay1;
	always @(posedge clk or negedge rstn)
		if (!rstn)
			op_cfg_reg <= 0;
		else if (op_cfg_vld)
			op_cfg_reg <= op_cfg;
	always @(posedge clk or negedge rstn)
		if (!rstn)
			pmu_cfg_reg <= 0;
		else if (pmu_cfg_vld)
			pmu_cfg_reg <= pmu_cfg;
	always @(*) begin
		if (_sv2v_0)
			;
		cfg_acc_num = op_cfg_reg[40-:10];
		cfg_quant_scale = op_cfg_reg[30-:10];
		cfg_quant_bias = op_cfg_reg[20-:16];
		cfg_quant_shift = op_cfg_reg[4-:5];
	end
	always @(posedge clk or negedge rstn)
		if (!rstn)
			model_cfg_reg <= 0;
		else if (model_cfg_vld)
			model_cfg_reg <= model_cfg;
	always @(posedge clk or negedge rstn)
		if (!rstn)
			usr_cfg_reg <= 0;
		else if (usr_cfg_vld)
			usr_cfg_reg <= usr_cfg;
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			clean_kv_cache_delay1 <= 0;
			clean_kv_cache_user_id_delay1 <= 0;
		end
		else begin
			clean_kv_cache_delay1 <= clean_kv_cache;
			clean_kv_cache_user_id_delay1 <= clean_kv_cache_user_id;
		end
	reg [CMEM_DATA_WIDTH - 1:0] cmem_wdata;
	reg [CMEM_ADDR_WIDTH - 1:0] cmem_waddr;
	reg cmem_wen;
	wire [CMEM_DATA_WIDTH - 1:0] cmem_rdata;
	reg [CMEM_ADDR_WIDTH - 1:0] cmem_raddr;
	reg cmem_ren;
	wire cmem_rvalid;
	wire [CMEM_ADDR_WIDTH - 1:0] self_cmem_raddr;
	wire self_cmem_ren;
	always @(*) begin
		if (_sv2v_0)
			;
		cmem_wdata = 0;
		cmem_waddr = 0;
		cmem_wen = 0;
		if ((in_gbus_wen && (in_gbus_addr[HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))-:((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) >= (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) ? ((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0))) + 1 : ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) - (HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)))) + 1)] == 0)) && (in_gbus_addr[BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)-:((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) >= (BUS_CMEM_ADDR_WIDTH + 0) ? ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) - (BUS_CMEM_ADDR_WIDTH + 0)) + 1 : ((BUS_CMEM_ADDR_WIDTH + 0) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) + 1)] == CORE_INDEX)) begin
			cmem_wen = 1;
			cmem_waddr = in_gbus_addr[BUS_CMEM_ADDR_WIDTH - 1-:BUS_CMEM_ADDR_WIDTH];
			cmem_wdata = in_gbus_wdata;
		end
	end
	always @(*) begin
		if (_sv2v_0)
			;
		cmem_raddr = 0;
		cmem_ren = 0;
		if (self_cmem_ren) begin
			cmem_ren = 1;
			cmem_raddr = self_cmem_raddr;
		end
	end
	core_mem #(
		.CMEM_ADDR_WIDTH(CMEM_ADDR_WIDTH),
		.CMEM_DATA_WIDTH(CMEM_DATA_WIDTH),
		.VLINK_DATA_WIDTH(VLINK_DATA_WIDTH),
		.HEAD_INDEX(HEAD_INDEX)
	) mem_inst(
		.clk(clk),
		.rstn(rstn),
		.clean_kv_cache(clean_kv_cache_delay1),
		.clean_kv_cache_user_id(clean_kv_cache_user_id_delay1),
		.core_mem_addr(core_mem_addr),
		.core_mem_wdata(core_mem_wdata),
		.core_mem_wen(core_mem_wen),
		.core_mem_rdata(core_mem_rdata),
		.core_mem_ren(core_mem_ren),
		.core_mem_rvld(core_mem_rvld),
		.vlink_data_in(vlink_data_in),
		.vlink_data_in_vld(vlink_data_in_vld),
		.vlink_data_out(vlink_data_out),
		.vlink_data_out_vld(vlink_data_out_vld),
		.usr_cfg(usr_cfg_reg),
		.model_cfg(model_cfg_reg),
		.control_state(control_state),
		.control_state_update(control_state_update),
		.pmu_cfg(pmu_cfg_reg),
		.cmem_waddr(cmem_waddr),
		.cmem_wen(cmem_wen),
		.cmem_wdata(cmem_wdata),
		.cmem_raddr(cmem_raddr),
		.cmem_ren(cmem_ren),
		.cmem_rdata(cmem_rdata),
		.cmem_rvalid(cmem_rvalid)
	);
	core_buf #(.CACHE_DATA_WIDTH(CMEM_DATA_WIDTH)) buf_inst(
		.clk(clk),
		.rstn(rstn),
		.hlink_wdata(hlink_wdata),
		.hlink_wen(hlink_wen),
		.hlink_rdata(hlink_rdata),
		.hlink_rvalid(hlink_rvalid)
	);
	wire mac_opa_vld;
	wire [(MAC_MULT_NUM * IDATA_WIDTH) - 1:0] mac_opa;
	wire mac_opb_vld;
	wire [(MAC_MULT_NUM * IDATA_WIDTH) - 1:0] mac_opb;
	wire signed [ODATA_BIT - 1:0] mac_odata;
	wire mac_odata_valid;
	core_mac #(
		.MAC_MULT_NUM(MAC_MULT_NUM),
		.IDATA_WIDTH(IDATA_WIDTH),
		.ODATA_BIT(ODATA_BIT)
	) mac_inst(
		.clk(clk),
		.rstn(rstn),
		.idataA(mac_opa),
		.idataB(mac_opb),
		.idata_valid(mac_opa_vld && mac_opb_vld),
		.odata(mac_odata),
		.odata_valid(mac_odata_valid)
	);
	wire signed [ODATA_BIT - 1:0] acc_odata;
	wire acc_odata_valid;
	core_acc #(
		.IDATA_WIDTH(ODATA_BIT),
		.ODATA_BIT(ODATA_BIT)
	) acc_inst(
		.clk(clk),
		.rstn(rstn),
		.cfg_acc_num(cfg_acc_num),
		.idata($signed(mac_odata)),
		.idata_valid(mac_odata_valid),
		.odata(acc_odata),
		.odata_valid(acc_odata_valid)
	);
	wire recompute_needed;
	wire [IDATA_WIDTH*2+$clog2(MAC_MULT_NUM) + 5 - 1:0] rc_out_data;  // copied from 
	wire rc_out_data_vld;
	wire rc_error;
	wire [RECOMPUTE_SHIFT_WIDTH - 1:0] rms_rc_shift;
	reg rc_cfg_vld_reg;
	reg [83:0] rc_cfg_reg;
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			rc_cfg_vld_reg <= 0;
			rc_cfg_reg <= 0;
		end
		else if (rc_cfg_vld) begin
			rc_cfg_vld_reg <= 1;
			rc_cfg_reg <= rc_cfg;
		end
		else
			rc_cfg_vld_reg <= 0;
	assign rms_rc_shift = rc_cfg_reg[83-:5];
	core_rc #(
		.IN_DATA_WIDTH(`ODATA_WIDTH),
		.OUT_DATA_WIDTH(`ODATA_WIDTH),
		.RECOMPUTE_FIFO_DEPTH(`RECOMPUTE_FIFO_DEPTH),
		.RETIMING_REG_NUM(`RC_RETIMING_REG_NUM)
	) rc_inst(
		.clk(clk),
		.rst_n(rstn),
		.recompute_needed(recompute_needed),
		.rc_scale(rc_scale),
		.rc_scale_vld(rc_scale_vld),
		.rc_scale_clear(rc_scale_clear),
		.rms_rc_shift(rms_rc_shift),
		.in_data(acc_odata),
		.in_data_vld(acc_odata_valid),
		.out_data(rc_out_data),
		.out_data_vld(rc_out_data_vld),
		.error(rc_error)
	);
	wire signed [IDATA_WIDTH - 1:0] quant_odata;
	wire quant_odata_valid;
	core_quant #(
		.IDATA_WIDTH(`ODATA_WIDTH),
		.ODATA_BIT(`IDATA_WIDTH)
	) quant_inst(
		.clk(clk),
		.rstn(rstn),
		.cfg_quant_scale(cfg_quant_scale),
		.cfg_quant_bias(cfg_quant_bias),
		.cfg_quant_shift(cfg_quant_shift),
		.idata(rc_out_data),
		.idata_valid(rc_out_data_vld && ((control_state != 32'd6) && (control_state != 32'd8))),
		.odata(quant_odata),
		.odata_valid(quant_odata_valid)
	);
	wire [GBUS_DATA_WIDTH - 1:0] parallel_data;
	wire parallel_data_valid;
	align_s2p #(
		.IDATA_WIDTH(IDATA_WIDTH),
		.ODATA_BIT(GBUS_DATA_WIDTH)
	) align_s2p_inst(
		.clk(clk),
		.rstn(rstn),
		.idata(quant_odata),
		.idata_valid(quant_odata_valid && (control_state == 32'd4)),
		.odata(parallel_data),
		.odata_valid(parallel_data_valid)
	);
	core_ctrl #(
		.HLINK_DATA_WIDTH(CMEM_DATA_WIDTH),
		.VLINK_DATA_WIDTH(VLINK_DATA_WIDTH),
		.GBUS_DATA_WIDTH(GBUS_DATA_WIDTH),
		.IDATA_WIDTH(IDATA_WIDTH),
		.CMEM_ADDR_WIDTH(CMEM_ADDR_WIDTH),
		.CMEM_DATA_WIDTH(CMEM_DATA_WIDTH),
		.ODATA_BIT(`ODATA_WIDTH),
		.CORE_INDEX(CORE_INDEX),
		.CACHE_DEPTH(CACHE_DEPTH),
		.CACHE_NUM(CACHE_NUM),
		.CACHE_ADDR_WIDTH($clog2(CACHE_NUM) + $clog2(CACHE_DEPTH)),
		.MAX_EMBD_SIZE(`MAX_EMBD_SIZE),
		.HEAD_NUM(`HEAD_NUM),
		.HEAD_CORE_NUM(`HEAD_CORE_NUM),
		.MAC_MULT_NUM(`MAC_MULT_NUM),
		.WMEM_DEPTH(`WMEM_DEPTH),
		.WMEM_NUM_PER_CORE(`WMEM_NUM_PER_CORE),
		.MAX_CONTEXT_LENGTH(`MAX_CONTEXT_LENGTH),
		.OP_GEN_CNT_WIDTH(`OP_GEN_CNT_WIDTH),
		.TOKEN_PER_CORE_WIDTH(`TOKEN_PER_CORE_WIDTH),
		.HEAD_SRAM_DEPTH(`HEAD_SRAM_DEPTH),
		.GLOBAL_SRAM_DEPTH(`GLOBAL_SRAM_DEPTH)
		) 
	inst_core_ctrl(
		.clk(clk),
		.rst_n(rstn),
		.control_state(control_state),
		.control_state_update(control_state_update),
		.usr_cfg(usr_cfg_reg),
		.model_cfg(model_cfg_reg),
		.start(start),
		.finish(finish),
		.hlink_wen(hlink_wen),
		.hlink_rvalid(hlink_rvalid),
		.hlink_rdata(hlink_rdata),
		.cmem_rvalid(cmem_rvalid),
		.cmem_rdata(cmem_rdata),
		.quant_odata(quant_odata),
		.quant_odata_valid(quant_odata_valid),
		.parallel_data(parallel_data),
		.parallel_data_valid(parallel_data_valid),
		.rc_out_data(rc_out_data),
		.rc_out_data_vld(rc_out_data_vld),
		.recompute_needed(recompute_needed),
		.self_cmem_ren(self_cmem_ren),
		.self_cmem_raddr(self_cmem_raddr),
		.mac_opa_vld(mac_opa_vld),
		.mac_opa(mac_opa),
		.mac_opb_vld(mac_opb_vld),
		.mac_opb(mac_opb),
		.out_gbus_addr(out_gbus_addr),
		.out_gbus_wen(out_gbus_wen),
		.out_gbus_wdata(out_gbus_wdata)
	);
	initial _sv2v_0 = 0;
endmodule
