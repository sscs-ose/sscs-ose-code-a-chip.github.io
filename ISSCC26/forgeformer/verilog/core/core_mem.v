`include "sys_defs.svh"

module core_mem (
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
	vlink_data_in,
	vlink_data_in_vld,
	vlink_data_out,
	vlink_data_out_vld,
	usr_cfg,
	model_cfg,
	control_state,
	control_state_update,
	pmu_cfg,
	cmem_waddr,
	cmem_wen,
	cmem_wdata,
	cmem_raddr,
	cmem_ren,
	cmem_rdata,
	cmem_rvalid
);
	reg _sv2v_0;
	parameter IDATA_WIDTH = `IDATA_WIDTH;
	parameter CMEM_ADDR_WIDTH = `CMEM_ADDR_WIDTH;
	parameter CMEM_DATA_WIDTH = (`MAC_MULT_NUM * `IDATA_WIDTH);
	parameter CMEM_USER_WIDTH = 2;
	parameter VLINK_DATA_WIDTH = (`MAC_MULT_NUM * `IDATA_WIDTH);
	parameter WMEM_DEPTH = `WMEM_DEPTH;
	parameter WMEM_ADDR_WIDTH = $clog2(WMEM_DEPTH);
	parameter INTERFACE_DATA_WIDTH = `INTERFACE_DATA_WIDTH;
	parameter SINGLE_USR_CACHE_DEPTH = `KV_CACHE_DEPTH_SINGLE_USER;
	parameter KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA = `KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA;
	parameter CACHE_NUM = `MAC_MULT_NUM;
	parameter SINGLE_USR_CACHE_ADDR_WIDTH = $clog2(CACHE_NUM) + $clog2(SINGLE_USR_CACHE_DEPTH);
	parameter HEAD_INDEX = 0;
	parameter USER_ID_WIDTH = `USER_ID_WIDTH;
	parameter CORE_MEM_ADDR_WIDTH = `CORE_MEM_ADDR_WIDTH;
	parameter MAX_EMBD_SIZE = `MAX_EMBD_SIZE;
	parameter HEAD_NUM = `HEAD_NUM;
	parameter HEAD_CORE_NUM = `HEAD_CORE_NUM;
	parameter MAC_MULT_NUM = `MAC_MULT_NUM;
	parameter MAX_CONTEXT_LENGTH = 256;
	input clk;
	input rstn;
	input wire clean_kv_cache;
	input wire [USER_ID_WIDTH - 1:0] clean_kv_cache_user_id;
	input wire [CORE_MEM_ADDR_WIDTH - 1:0] core_mem_addr;
	input wire [INTERFACE_DATA_WIDTH - 1:0] core_mem_wdata;
	input wire core_mem_wen;
	output reg [INTERFACE_DATA_WIDTH - 1:0] core_mem_rdata;
	input wire core_mem_ren;
	output reg core_mem_rvld;
	input wire [VLINK_DATA_WIDTH - 1:0] vlink_data_in;
	input wire vlink_data_in_vld;
	output wire [VLINK_DATA_WIDTH - 1:0] vlink_data_out;
	output wire vlink_data_out_vld;
	input wire [11:0] usr_cfg;
	input wire [29:0] model_cfg;
	input wire [31:0] control_state;
	input wire control_state_update;
	input wire [3:0] pmu_cfg;
	input [CMEM_ADDR_WIDTH - 1:0] cmem_waddr;
	input cmem_wen;
	input [CMEM_DATA_WIDTH - 1:0] cmem_wdata;
	input [CMEM_ADDR_WIDTH - 1:0] cmem_raddr;
	input cmem_ren;
	output reg [CMEM_DATA_WIDTH - 1:0] cmem_rdata;
	output reg cmem_rvalid;
	localparam K_CACHE_ADDR_BASE = 0;
	localparam V_CACHE_ADDR_BASE = (((MAX_CONTEXT_LENGTH * MAX_EMBD_SIZE) / HEAD_NUM) / HEAD_CORE_NUM) / MAC_MULT_NUM;
	reg [31:0] control_state_reg;
	reg [31:0] control_state_reg_d;
	wire state_changed;
	assign state_changed = control_state_reg != control_state_reg_d;
	always @(posedge clk or negedge rstn)
		if (~rstn)
			control_state_reg <= 32'd0;
		else if (control_state_update)
			control_state_reg <= control_state;
	always @(posedge clk or negedge rstn)
		if (~rstn)
			control_state_reg_d <= 32'd0;
		else
			control_state_reg_d <= control_state_reg;
	reg [WMEM_ADDR_WIDTH - 1:0] wmem_addr;
	reg wmem_wen;
	reg [CMEM_DATA_WIDTH - 1:0] wmem_bwe;
	reg [CMEM_DATA_WIDTH - 1:0] wmem_wdata;
	reg wmem_ren;
	wire [CMEM_DATA_WIDTH - 1:0] wmem_rdata;
	reg wmem_rvalid;
	reg wmem_1024_ffn_deepslp;
	reg wmem_1024_ffn_bc1;
	reg wmem_1024_ffn_bc2;
	reg wmem_512_attn_deepslp;
	reg wmem_512_attn_bc1;
	reg wmem_512_attn_bc2;
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			wmem_1024_ffn_deepslp <= 0;
			wmem_1024_ffn_bc1 <= 0;
			wmem_1024_ffn_bc2 <= 0;
			wmem_512_attn_deepslp <= 0;
			wmem_512_attn_bc1 <= 0;
			wmem_512_attn_bc2 <= 0;
		end
		else if (pmu_cfg[1]) begin
			wmem_1024_ffn_bc1 <= pmu_cfg[3];
			wmem_512_attn_bc1 <= pmu_cfg[3];
			wmem_1024_ffn_bc2 <= pmu_cfg[2];
			wmem_512_attn_bc2 <= pmu_cfg[2];
			if (pmu_cfg[0]) begin
				if (state_changed && (control_state_reg == 32'd1)) begin
					wmem_1024_ffn_deepslp <= 1;
					wmem_512_attn_deepslp <= 0;
				end
				else if ((control_state_reg == 32'd7) && state_changed) begin
					wmem_1024_ffn_deepslp <= 0;
					wmem_512_attn_deepslp <= 1;
				end
				else if (control_state_reg == 32'd0) begin
					wmem_1024_ffn_deepslp <= 1;
					wmem_512_attn_deepslp <= 1;
				end
			end
		end
	wire [INTERFACE_DATA_WIDTH - 1:0] weight_mem_rdata;
	wire weight_mem_rvld;
	wmem #(
		.DATA_BIT(CMEM_DATA_WIDTH),
		.IDATA_WIDTH(IDATA_WIDTH),
		.MAC_MULT_NUM(MAC_MULT_NUM),
		.CORE_MEM_ADDR_WIDTH(CORE_MEM_ADDR_WIDTH),
		.INTERFACE_DATA_WIDTH(INTERFACE_DATA_WIDTH),
		.WMEM_DEPTH(WMEM_DEPTH),
		.WMEM_ADDR_WIDTH(WMEM_ADDR_WIDTH)
	)
	wmem_inst(
		.clk(clk),
		.rstn(rstn),
		.wmem_addr(wmem_addr),
		.wmem_ren(wmem_ren),
		.wmem_rdata(wmem_rdata),
		.wmem_wen(wmem_wen),
		.wmem_wdata(wmem_wdata),
		.wmem_bwe(wmem_bwe),
		.weight_mem_addr(core_mem_addr),
		.weight_mem_wdata(core_mem_wdata),
		.weight_mem_wen(core_mem_wen),
		.weight_mem_rdata(weight_mem_rdata),
		.weight_mem_ren(core_mem_ren),
		.weight_mem_rvld(weight_mem_rvld),
		.wmem_1024_ffn_deepslp(wmem_1024_ffn_deepslp),
		.wmem_1024_ffn_bc1(wmem_1024_ffn_bc1),
		.wmem_1024_ffn_bc2(wmem_1024_ffn_bc2),
		.wmem_512_attn_deepslp(wmem_512_attn_deepslp),
		.wmem_512_attn_bc1(wmem_512_attn_bc1),
		.wmem_512_attn_bc2(wmem_512_attn_bc2)
	);
	always @(posedge clk or negedge rstn)
		if (!rstn)
			wmem_rvalid <= 1'b0;
		else
			wmem_rvalid <= wmem_ren;
	reg [SINGLE_USR_CACHE_ADDR_WIDTH - 1:0] cache_waddr;
	reg [SINGLE_USR_CACHE_ADDR_WIDTH - 1:0] nxt_cache_waddr;
	reg [SINGLE_USR_CACHE_ADDR_WIDTH - 1:0] cache_raddr;
	reg [SINGLE_USR_CACHE_ADDR_WIDTH - 1:0] cache_addr;
	reg cache_wen;
	reg nxt_cache_wen;
	reg [CMEM_DATA_WIDTH - 1:0] cache_wdata;
	reg [CMEM_DATA_WIDTH - 1:0] nxt_cache_wdata;
	reg cache_ren;
	wire [CMEM_DATA_WIDTH - 1:0] cache_rdata;
	reg cache_rvalid;
	wire cache_wdata_byte_flag;
	wire [INTERFACE_DATA_WIDTH - 1:0] kv_mem_rdata;
	wire kv_mem_rvld;
	always @(*) begin
		if (_sv2v_0)
			;
		core_mem_rvld = 0;
		core_mem_rdata = 0;
		if (kv_mem_rvld) begin
			core_mem_rvld = 1;
			core_mem_rdata = kv_mem_rdata;
		end
		else if (weight_mem_rvld) begin
			core_mem_rvld = 1;
			core_mem_rdata = weight_mem_rdata;
		end
	end
	assign cache_wdata_byte_flag = 1;
	kv_cache_pkt #(
		.IDATA_WIDTH(CMEM_DATA_WIDTH),
		.ODATA_BIT(CMEM_DATA_WIDTH),
		.CACHE_NUM(CACHE_NUM),
		.CACHE_DEPTH(SINGLE_USR_CACHE_DEPTH),
		.CACHE_ADDR_WIDTH(SINGLE_USR_CACHE_ADDR_WIDTH)
	) kv_cache_inst(
		.clk(clk),
		.rstn(rstn),
		.clean_kv_cache(clean_kv_cache),
		.clean_kv_cache_user_id(clean_kv_cache_user_id),
		.kv_mem_addr(core_mem_addr),
		.kv_mem_wdata(core_mem_wdata),
		.kv_mem_wen(core_mem_wen),
		.kv_mem_rdata(kv_mem_rdata),
		.kv_mem_ren(core_mem_ren),
		.kv_mem_rvld(kv_mem_rvld),
		.cache_wen(cache_wen),
		.cache_addr(cache_addr),
		.cache_wdata(cache_wdata),
		.cache_ren(cache_ren),
		.cache_rdata(cache_rdata),
		.cache_wdata_byte_flag(cache_wdata_byte_flag),
		.usr_cfg(usr_cfg)
	);
	always @(posedge clk or negedge rstn)
		if (!rstn)
			cache_rvalid <= 1'b0;
		else
			cache_rvalid <= cache_ren;
	always @(posedge clk or negedge rstn)
		if (!rstn)
			cmem_rvalid <= 1'b0;
		else
			cmem_rvalid <= cmem_ren;
	reg [CMEM_ADDR_WIDTH - 1:0] cmem_raddr_delay1;
	always @(posedge clk) cmem_raddr_delay1 <= cmem_raddr;
	always @(*)
		if (cache_rvalid && cmem_rvalid) begin
			cmem_rdata = cache_rdata;
			if (model_cfg[0] == 1) begin
				if (control_state_reg == 32'd4) begin
					if ((HEAD_INDEX % 2) == 0) begin
						if (cmem_raddr_delay1[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] >= (K_CACHE_ADDR_BASE + V_CACHE_ADDR_BASE))
							cmem_rdata = vlink_data_in;
					end
					else if (cmem_raddr_delay1[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] < (K_CACHE_ADDR_BASE + V_CACHE_ADDR_BASE))
						cmem_rdata = vlink_data_in;
				end
				else if (control_state_reg == 32'd5) begin
					if ((HEAD_INDEX % 2) == 0) begin
						if (cmem_raddr_delay1[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] >= (V_CACHE_ADDR_BASE + V_CACHE_ADDR_BASE))
							cmem_rdata = vlink_data_in;
					end
					else if (cmem_raddr_delay1[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] < (V_CACHE_ADDR_BASE + V_CACHE_ADDR_BASE))
						cmem_rdata = vlink_data_in;
				end
			end
		end
		else if (wmem_rvalid && cmem_rvalid)
			cmem_rdata = wmem_rdata;
		else
			cmem_rdata = 0;
	reg [WMEM_ADDR_WIDTH - 1:0] wmem_waddr;
	reg [WMEM_ADDR_WIDTH - 1:0] wmem_raddr;
	always @(*) begin
		wmem_waddr = cmem_waddr[WMEM_ADDR_WIDTH - 1:0];
		wmem_wen = cmem_wen && ~cmem_waddr[CMEM_ADDR_WIDTH - 1];
		wmem_wdata = cmem_wdata;
		wmem_bwe = {CMEM_DATA_WIDTH {1'b1}};
	end
	always @(*) begin
		wmem_ren = cmem_ren && ~cmem_raddr[CMEM_ADDR_WIDTH - 1];
		wmem_raddr = cmem_raddr[WMEM_ADDR_WIDTH - 1:0];
	end
	always @(*)
		if (wmem_wen)
			wmem_addr = wmem_waddr;
		else if (wmem_ren)
			wmem_addr = wmem_raddr;
		else
			wmem_addr = 0;
	always @(*) begin
		if (_sv2v_0)
			;
		nxt_cache_wen = cmem_wen && cmem_waddr[CMEM_ADDR_WIDTH - 1];
		nxt_cache_waddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)] = cmem_waddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)];
		nxt_cache_waddr[SINGLE_USR_CACHE_ADDR_WIDTH - 1-:$clog2(CACHE_NUM)] = cmem_waddr[$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)+:$clog2(MAC_MULT_NUM)];
		nxt_cache_wdata = cmem_wdata;
		if (model_cfg[0] == 1) begin
			if (control_state_reg == 32'd2) begin
				if ((HEAD_INDEX % 2) == 0) begin
					if (cmem_waddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] >= (K_CACHE_ADDR_BASE + V_CACHE_ADDR_BASE))
						nxt_cache_wen = 0;
					else begin
						nxt_cache_wen = cmem_wen && cmem_waddr[CMEM_ADDR_WIDTH - 1];
						nxt_cache_waddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)] = cmem_waddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)];
						nxt_cache_waddr[SINGLE_USR_CACHE_ADDR_WIDTH - 1-:$clog2(CACHE_NUM)] = cmem_waddr[$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)+:$clog2(MAC_MULT_NUM)];
						nxt_cache_wdata = cmem_wdata;
					end
				end
				else if (cmem_waddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] < (K_CACHE_ADDR_BASE + V_CACHE_ADDR_BASE))
					nxt_cache_wen = 0;
				else begin
					nxt_cache_wen = cmem_wen && cmem_waddr[CMEM_ADDR_WIDTH - 1];
					nxt_cache_waddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)] = cmem_waddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] - V_CACHE_ADDR_BASE;
					nxt_cache_waddr[SINGLE_USR_CACHE_ADDR_WIDTH - 1-:$clog2(CACHE_NUM)] = cmem_waddr[$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)+:$clog2(MAC_MULT_NUM)];
					nxt_cache_wdata = cmem_wdata;
				end
			end
			else if (control_state_reg == 32'd3) begin
				if ((HEAD_INDEX % 2) == 0) begin
					if (cmem_waddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] >= (V_CACHE_ADDR_BASE + V_CACHE_ADDR_BASE))
						nxt_cache_wen = 0;
					else begin
						nxt_cache_wen = cmem_wen && cmem_waddr[CMEM_ADDR_WIDTH - 1];
						nxt_cache_waddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)] = cmem_waddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)];
						nxt_cache_waddr[SINGLE_USR_CACHE_ADDR_WIDTH - 1-:$clog2(CACHE_NUM)] = cmem_waddr[$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)+:$clog2(MAC_MULT_NUM)];
						nxt_cache_wdata = cmem_wdata;
					end
				end
				else if (cmem_waddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] < (V_CACHE_ADDR_BASE + V_CACHE_ADDR_BASE))
					nxt_cache_wen = 0;
				else begin
					nxt_cache_wen = cmem_wen && cmem_waddr[CMEM_ADDR_WIDTH - 1];
					nxt_cache_waddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)] = cmem_waddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] - V_CACHE_ADDR_BASE;
					nxt_cache_waddr[SINGLE_USR_CACHE_ADDR_WIDTH - 1-:$clog2(CACHE_NUM)] = cmem_waddr[$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)+:$clog2(MAC_MULT_NUM)];
					nxt_cache_wdata = cmem_wdata;
				end
			end
		end
	end
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			cache_wen <= 0;
			cache_waddr <= 0;
			cache_wdata <= 0;
		end
		else begin
			cache_wen <= nxt_cache_wen;
			cache_waddr <= nxt_cache_waddr;
			cache_wdata <= nxt_cache_wdata;
		end
	always @(*) begin
		if (_sv2v_0)
			;
		cache_ren = cmem_ren && cmem_raddr[CMEM_ADDR_WIDTH - 1];
		if ((model_cfg[0] == 1) && ((HEAD_INDEX % 2) == 1))
			cache_raddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)] = cmem_raddr[0+:$clog2(KV_CACHE_DEPTH_SINGLE_USER_WITH_GQA)] - V_CACHE_ADDR_BASE;
		else
			cache_raddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)] = cmem_raddr[0+:$clog2(SINGLE_USR_CACHE_DEPTH)];
		cache_raddr[SINGLE_USR_CACHE_ADDR_WIDTH - 1-:$clog2(CACHE_NUM)] = 0;
	end
	always @(*)
		if (cache_wen)
			cache_addr = cache_waddr;
		else if (cache_ren)
			cache_addr = cache_raddr;
		else
			cache_addr = 0;
	assign vlink_data_out = cache_rdata;
	assign vlink_data_out_vld = cache_rvalid;
	initial _sv2v_0 = 0;
endmodule

module wmem (
	clk,
	rstn,
	wmem_1024_ffn_deepslp,
	wmem_1024_ffn_bc1,
	wmem_1024_ffn_bc2,
	wmem_512_attn_deepslp,
	wmem_512_attn_bc1,
	wmem_512_attn_bc2,
	weight_mem_addr,
	weight_mem_wdata,
	weight_mem_wen,
	weight_mem_rdata,
	weight_mem_ren,
	weight_mem_rvld,
	wmem_addr,
	wmem_ren,
	wmem_rdata,
	wmem_wen,
	wmem_wdata,
	wmem_bwe
);
	reg _sv2v_0;
	parameter DATA_BIT = 128;
	parameter IDATA_WIDTH = 8;
	parameter MAC_MULT_NUM = 16;
	parameter CORE_MEM_ADDR_WIDTH = 14;
	parameter INTERFACE_DATA_WIDTH = 16;
	parameter WMEM_DEPTH = 1536;
	parameter WMEM_ADDR_WIDTH = $clog2(WMEM_DEPTH);
	input wire clk;
	input wire rstn;
	input wire wmem_1024_ffn_deepslp;
	input wire wmem_1024_ffn_bc1;
	input wire wmem_1024_ffn_bc2;
	input wire wmem_512_attn_deepslp;
	input wire wmem_512_attn_bc1;
	input wire wmem_512_attn_bc2;
	input wire [CORE_MEM_ADDR_WIDTH - 1:0] weight_mem_addr;
	input wire [INTERFACE_DATA_WIDTH - 1:0] weight_mem_wdata;
	input wire weight_mem_wen;
	output wire [INTERFACE_DATA_WIDTH - 1:0] weight_mem_rdata;
	input wire weight_mem_ren;
	output reg weight_mem_rvld;
	input wire [WMEM_ADDR_WIDTH - 1:0] wmem_addr;
	input wire wmem_ren;
	output wire [DATA_BIT - 1:0] wmem_rdata;
	input wire wmem_wen;
	input wire [DATA_BIT - 1:0] wmem_wdata;
	input wire [DATA_BIT - 1:0] wmem_bwe;
	reg [WMEM_ADDR_WIDTH - 1:0] wmem_addr_f;
	reg wmem_ren_f;
	reg wmem_wen_f;
	reg [DATA_BIT - 1:0] wmem_wdata_f;
	reg [DATA_BIT - 1:0] wmem_bwe_f;
	reg interface_inst_ren;
	reg [$clog2(WMEM_DEPTH) - 1:0] interface_inst_raddr;
	reg interface_inst_wen;
	reg [$clog2(WMEM_DEPTH) - 1:0] interface_inst_waddr;
	reg [DATA_BIT - 1:0] interface_inst_wdata;
	reg [DATA_BIT - 1:0] interface_inst_bwe;
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			interface_inst_wen <= 0;
			interface_inst_waddr <= 0;
			interface_inst_wdata <= 0;
			interface_inst_bwe <= 0;
		end
		else if (weight_mem_wen) begin
			interface_inst_wen <= weight_mem_addr[CORE_MEM_ADDR_WIDTH - 1:CORE_MEM_ADDR_WIDTH - 2] != 0;
			interface_inst_waddr <= {weight_mem_addr[CORE_MEM_ADDR_WIDTH - 1-:2] - 1'b1, weight_mem_addr[CORE_MEM_ADDR_WIDTH - 3:$clog2(MAC_MULT_NUM / 2)]};
			interface_inst_wdata[weight_mem_addr[$clog2(MAC_MULT_NUM / 2) - 1:0] * (2 * IDATA_WIDTH)+:2 * IDATA_WIDTH] <= weight_mem_wdata;
			interface_inst_bwe[weight_mem_addr[$clog2(MAC_MULT_NUM / 2) - 1:0] * (2 * IDATA_WIDTH)+:2 * IDATA_WIDTH] <= 16'hffff;
		end
		else begin
			interface_inst_bwe <= 0;
			interface_inst_wen <= 0;
		end
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			interface_inst_ren <= 0;
			interface_inst_raddr <= 0;
		end
		else if (weight_mem_ren) begin
			interface_inst_ren <= weight_mem_addr[CORE_MEM_ADDR_WIDTH - 1:CORE_MEM_ADDR_WIDTH - 2] != 0;
			interface_inst_raddr <= {weight_mem_addr[CORE_MEM_ADDR_WIDTH - 1-:2] - 1'b1, weight_mem_addr[CORE_MEM_ADDR_WIDTH - 3:$clog2(MAC_MULT_NUM / 2)]};
		end
		else
			interface_inst_ren <= 0;
	reg [CORE_MEM_ADDR_WIDTH - 1:0] interface_addr_delay1;
	reg [CORE_MEM_ADDR_WIDTH - 1:0] interface_addr_delay2;
	reg weight_mem_ren_delay1;
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			weight_mem_ren_delay1 <= 0;
			weight_mem_rvld <= 0;
		end
		else begin
			weight_mem_ren_delay1 <= weight_mem_ren;
			weight_mem_rvld <= interface_inst_ren;
		end
	assign weight_mem_rdata = wmem_rdata[interface_addr_delay2[$clog2(MAC_MULT_NUM / 2) - 1:0] * (2 * IDATA_WIDTH)+:2 * IDATA_WIDTH];
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			interface_addr_delay1 <= 0;
			interface_addr_delay2 <= 0;
		end
		else begin
			interface_addr_delay1 <= weight_mem_addr;
			interface_addr_delay2 <= interface_addr_delay1;
		end
	always @(*) begin
		if (_sv2v_0)
			;
		wmem_addr_f = wmem_addr;
		wmem_ren_f = wmem_ren;
		wmem_wen_f = wmem_wen;
		wmem_wdata_f = wmem_wdata;
		wmem_bwe_f = wmem_bwe;
		if (interface_inst_wen) begin
			wmem_wen_f = interface_inst_wen;
			wmem_addr_f = interface_inst_waddr;
			wmem_wdata_f = interface_inst_wdata;
			wmem_bwe_f = interface_inst_bwe;
		end
		else if (interface_inst_ren) begin
			wmem_ren_f = interface_inst_ren;
			wmem_addr_f = interface_inst_raddr;
		end
	end
	// mem_sp #(
	// 	.DATA_BIT(DATA_BIT),
	// 	.DEPTH(WMEM_DEPTH),
	// 	.ADDR_BIT(WMEM_ADDR_WIDTH),
	// 	.BWE(1)
	// ) inst_mem_sp(
	sram_sp_sky130 #(
		.DATA_BIT(DATA_BIT),
		.DEPTH(${wmem_depth}),
		.ADDR_BIT(WMEM_ADDR_WIDTH),
		.BWE(1)
	) mem_sp_wmem_inst(
		.clk(clk),
		.addr(wmem_addr_f),
		.wen(wmem_wen_f),
		.bwe(wmem_bwe_f),
		.wdata(wmem_wdata_f),
		.ren(wmem_ren_f),
		.rdata(wmem_rdata)
	);
	initial _sv2v_0 = 0;
endmodule

module kv_cache_pkt (
	clk,
	rstn,
	clean_kv_cache,
	clean_kv_cache_user_id,
	kv_mem_addr,
	kv_mem_wdata,
	kv_mem_wen,
	kv_mem_rdata,
	kv_mem_ren,
	kv_mem_rvld,
	cache_addr,
	cache_ren,
	cache_rdata,
	cache_wen,
	cache_wdata,
	cache_wdata_byte_flag,
	usr_cfg
);
	reg _sv2v_0;
	parameter DATA_WIDTH = (`IDATA_WIDTH * `MAC_MULT_NUM);
	parameter IDATA_WIDTH = `IDATA_WIDTH;
	parameter ODATA_BIT = (`IDATA_WIDTH * `MAC_MULT_NUM);
	parameter CACHE_NUM = `MAC_MULT_NUM;
	parameter MAC_MULT_NUM = `MAC_MULT_NUM;
	parameter MAX_NUM_USER = `MAX_NUM_USER;
	parameter CACHE_DEPTH = `KV_CACHE_DEPTH_SINGLE_USER;
	parameter USER_ID_WIDTH = $clog2(MAX_NUM_USER);
	parameter CACHE_ADDR_WIDTH = $clog2(CACHE_NUM) + $clog2(CACHE_DEPTH);
	parameter CORE_MEM_ADDR_WIDTH = `CORE_MEM_ADDR_WIDTH;
	parameter INTERFACE_DATA_WIDTH = `INTERFACE_DATA_WIDTH;
	input clk;
	input rstn;
	input wire clean_kv_cache;
	input wire [USER_ID_WIDTH - 1:0] clean_kv_cache_user_id;
	input wire [CORE_MEM_ADDR_WIDTH - 1:0] kv_mem_addr;
	input wire [INTERFACE_DATA_WIDTH - 1:0] kv_mem_wdata;
	input wire kv_mem_wen;
	output wire [INTERFACE_DATA_WIDTH - 1:0] kv_mem_rdata;
	input wire kv_mem_ren;
	output reg kv_mem_rvld;
	input [CACHE_ADDR_WIDTH - 1:0] cache_addr;
	input cache_ren;
	output wire [ODATA_BIT - 1:0] cache_rdata;
	input cache_wen;
	input [DATA_WIDTH - 1:0] cache_wdata;
	input cache_wdata_byte_flag;
	input wire [11:0] usr_cfg;
	reg inst_wen;
	reg inst_ren;
	reg [$clog2(MAX_NUM_USER * CACHE_DEPTH) - 1:0] inst_waddr;
	reg [$clog2(MAX_NUM_USER * CACHE_DEPTH) - 1:0] inst_raddr;
	reg [$clog2(MAX_NUM_USER * CACHE_DEPTH) - 1:0] inst_addr;
	reg [ODATA_BIT - 1:0] inst_wdata;
	reg [ODATA_BIT - 1:0] inst_rdata;
	reg [ODATA_BIT - 1:0] inst_bwe;
	wire [$clog2(CACHE_NUM) - 1:0] bank_sel;
	wire [$clog2(CACHE_DEPTH) - 1:0] bank_addr;
	assign bank_sel = cache_addr[CACHE_ADDR_WIDTH - 1-:$clog2(CACHE_NUM)];
	assign bank_addr = cache_addr[0+:$clog2(CACHE_DEPTH)];
	reg inst_wen_w;
	reg [$clog2(MAX_NUM_USER * CACHE_DEPTH) - 1:0] inst_waddr_w;
	reg [ODATA_BIT - 1:0] inst_wdata_w;
	reg [ODATA_BIT - 1:0] inst_bwe_w;
	reg [USER_ID_WIDTH - 1:0] clean_kv_cache_user_id_reg;
	always @(posedge clk or negedge rstn)
		if (~rstn)
			clean_kv_cache_user_id_reg <= 0;
		else if (clean_kv_cache)
			clean_kv_cache_user_id_reg <= clean_kv_cache_user_id;
	reg clean_kv_cache_finish;
	reg nxt_clean_kv_cache_finish;
	reg clean_kv_cache_flag;
	reg clean_wen;
	reg [$clog2(MAC_MULT_NUM * CACHE_DEPTH) - 1:0] clean_addr;
	reg nxt_clean_wen;
	reg [$clog2(MAC_MULT_NUM * CACHE_DEPTH) - 1:0] nxt_clean_addr;
	wire [ODATA_BIT - 1:0] clean_wdata;
	assign clean_wdata = 0;
	wire clean_finish;
	assign clean_finish = clean_kv_cache_finish;
	always @(posedge clk or negedge rstn)
		if (~rstn)
			clean_kv_cache_flag <= 0;
		else if (clean_kv_cache_finish)
			clean_kv_cache_flag <= 0;
		else if (clean_kv_cache)
			clean_kv_cache_flag <= 1;
	always @(*) begin
		if (_sv2v_0)
			;
		nxt_clean_wen = clean_wen;
		nxt_clean_addr = clean_addr;
		nxt_clean_kv_cache_finish = 0;
		if (clean_kv_cache) begin
			nxt_clean_wen = 0;
			nxt_clean_wen = 1;
			nxt_clean_addr = clean_kv_cache_user_id * CACHE_DEPTH;
		end
		else if (clean_kv_cache_flag && clean_wen) begin
			if (clean_addr == ((clean_kv_cache_user_id_reg * CACHE_DEPTH) + CACHE_DEPTH - 1)) begin
				nxt_clean_kv_cache_finish = 1;
				nxt_clean_wen = 0;
				nxt_clean_addr = 0;
			end
			else
				nxt_clean_addr = clean_addr + 1;
		end
	end
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			clean_wen <= 0;
			clean_addr <= 0;
			clean_kv_cache_finish <= 0;
		end
		else begin
			clean_wen <= nxt_clean_wen;
			clean_addr <= nxt_clean_addr;
			clean_kv_cache_finish <= nxt_clean_kv_cache_finish;
		end
	always @(*) begin
		inst_wen_w = 'b0;
		inst_waddr_w = bank_addr + (usr_cfg[11-:2] * CACHE_DEPTH);
		inst_wdata_w = 'b0;
		inst_bwe_w = {DATA_WIDTH {1'b0}};
		begin : sv2v_autoblock_1
			integer i;
			for (i = 0; i < CACHE_NUM; i = i + 1)
				if ((i == bank_sel) && cache_wen) begin
					inst_wen_w = 1'b1;
					inst_wdata_w[(i * `IDATA_WIDTH) +:`IDATA_WIDTH] = cache_wdata[`IDATA_WIDTH - 1:0];
					inst_bwe_w[(i * `IDATA_WIDTH) +:`IDATA_WIDTH] = {`IDATA_WIDTH {1'b1}};
				end
		end
	end
	always @(posedge clk or negedge rstn)
		if (!rstn) begin
			inst_wen <= 1'sb0;
			inst_waddr <= 'b0;
			inst_wdata <= 1'sb0;
			inst_bwe <= 1'sb0;
		end
		else if (cache_wen) begin
			inst_wen <= inst_wen_w;
			inst_waddr <= inst_waddr_w;
			inst_wdata <= inst_wdata_w;
			inst_bwe <= inst_bwe_w;
		end
		else begin
			inst_wen <= 0;
			inst_bwe <= 0;
		end
	reg inst_ren_w;
	reg [$clog2(`MAX_NUM_USER * CACHE_DEPTH) - 1:0] inst_raddr_w;
	always @(*) begin
		inst_ren_w = 1'b0;
		inst_raddr_w = 'b0;
		if (cache_ren) begin
			inst_ren_w = 1'b1;
			inst_raddr_w = bank_addr + (usr_cfg[11-:2] * CACHE_DEPTH);
		end
	end
	always @(*) begin
		inst_ren = inst_ren_w;
		inst_raddr = inst_raddr_w;
	end
	reg [CORE_MEM_ADDR_WIDTH - 1:0] interface_addr_delay1;
	reg [CORE_MEM_ADDR_WIDTH - 1:0] interface_addr_delay2;
	assign cache_rdata = inst_rdata;
	assign kv_mem_rdata = inst_rdata[interface_addr_delay2[$clog2(MAC_MULT_NUM / 2) - 1:0] * (2 * IDATA_WIDTH)+:2 * IDATA_WIDTH];
	wire [$clog2(MAX_NUM_USER * CACHE_DEPTH):1] sv2v_tmp_CE7E6;
	assign sv2v_tmp_CE7E6 = (inst_wen ? inst_waddr : inst_raddr);
	always @(*) inst_addr = sv2v_tmp_CE7E6;
	reg inst_wen_f;
	reg inst_ren_f;
	reg [$clog2(MAX_NUM_USER * CACHE_DEPTH) - 1:0] inst_addr_f;
	reg [ODATA_BIT - 1:0] inst_wdata_f;
	reg [ODATA_BIT - 1:0] inst_bwe_f;
	reg interface_inst_ren;
	reg [$clog2(MAX_NUM_USER * CACHE_DEPTH) - 1:0] interface_inst_raddr;
	reg interface_inst_wen;
	reg [$clog2(MAX_NUM_USER * CACHE_DEPTH) - 1:0] interface_inst_waddr;
	reg [DATA_WIDTH - 1:0] interface_inst_wdata;
	reg [DATA_WIDTH - 1:0] interface_inst_bwe;
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			interface_inst_wen <= 0;
			interface_inst_waddr <= 0;
			interface_inst_wdata <= 0;
			interface_inst_bwe <= 0;
		end
		else if (kv_mem_wen) begin
			interface_inst_wen <= kv_mem_addr[CORE_MEM_ADDR_WIDTH - 1:CORE_MEM_ADDR_WIDTH - 2] == 0;
			interface_inst_waddr <= kv_mem_addr[$clog2(MAC_MULT_NUM / 2)+:$clog2(MAX_NUM_USER * CACHE_DEPTH)];
			interface_inst_wdata[kv_mem_addr[$clog2(MAC_MULT_NUM / 2) - 1:0] * (2 * IDATA_WIDTH)+:2 * IDATA_WIDTH] <= kv_mem_wdata;
			interface_inst_bwe[kv_mem_addr[$clog2(MAC_MULT_NUM / 2) - 1:0] * (2 * IDATA_WIDTH)+:2 * IDATA_WIDTH] <= 16'hffff;
		end
		else begin
			interface_inst_bwe <= 0;
			interface_inst_wen <= 0;
		end
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			interface_inst_ren <= 0;
			interface_inst_raddr <= 0;
		end
		else if (kv_mem_ren) begin
			interface_inst_ren <= kv_mem_addr[CORE_MEM_ADDR_WIDTH - 1:CORE_MEM_ADDR_WIDTH - 2] == 0;
			interface_inst_raddr <= kv_mem_addr[$clog2(MAC_MULT_NUM / 2)+:$clog2(MAX_NUM_USER * CACHE_DEPTH)];
		end
		else
			interface_inst_ren <= 0;
	reg kv_mem_ren_delay1;
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			kv_mem_ren_delay1 <= 0;
			kv_mem_rvld <= 0;
		end
		else begin
			kv_mem_ren_delay1 <= kv_mem_ren;
			kv_mem_rvld <= interface_inst_ren;
		end
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			interface_addr_delay1 <= 0;
			interface_addr_delay2 <= 0;
		end
		else begin
			interface_addr_delay1 <= kv_mem_addr;
			interface_addr_delay2 <= interface_addr_delay1;
		end
	always @(*) begin
		if (_sv2v_0)
			;
		inst_ren_f = inst_ren;
		inst_wen_f = inst_wen;
		inst_addr_f = inst_addr;
		inst_wdata_f = inst_wdata;
		inst_bwe_f = inst_bwe;
		if (clean_kv_cache_flag) begin
			inst_wen_f = clean_wen;
			inst_addr_f = clean_addr;
			inst_wdata_f = clean_wdata;
			inst_bwe_f = {DATA_WIDTH {1'b1}};
		end
		else if (interface_inst_wen) begin
			inst_wen_f = interface_inst_wen;
			inst_addr_f = interface_inst_waddr;
			inst_wdata_f = interface_inst_wdata;
			inst_bwe_f = interface_inst_bwe;
		end
		else if (interface_inst_ren) begin
			inst_ren_f = interface_inst_ren;
			inst_addr_f = interface_inst_raddr;
		end
	end
	localparam integer ADDR_BIT = $clog2(${kv_cache_depth});

	sram_sp_sky130 #(
		.DATA_BIT(ODATA_BIT),
		.DEPTH(${kv_cache_depth}),
		.ADDR_BIT(ADDR_BIT),
		.BWE(1)
	) kv_cache_mem (
		.clk(clk),
		.addr(inst_addr_f),
		.wen(inst_wen_f),
		.wdata(inst_wdata_f),
		.bwe(inst_bwe_f),
		.ren(inst_ren_f),
		.rdata(inst_rdata)
	);
	initial _sv2v_0 = 0;
endmodule



// module mem_sp_kv_cache #(
//     parameter   DATA_BIT = (`MAC_MULT_NUM * `IDATA_WIDTH),
//     parameter   DEPTH = `KV_CACHE_DEPTH_SINGLE_USER,
//     parameter   ADDR_BIT = $clog2(DEPTH),
//     parameter   BWE = 0 //bit write enable
// )(
//     // Global Signals
//     input                       clk,

//     // Data Signals
//     input       [ADDR_BIT-1:0]  addr,
//     input                       wen,
//     input       [DATA_BIT-1:0]  bwe,

//     input       [DATA_BIT-1:0]  wdata,
//     input                       ren,
//     output  reg [DATA_BIT-1:0]  rdata
// );

//     // 1. RAM/Memory initialization
//     reg [DATA_BIT-1:0]  mem [0:DEPTH-1];

//     // 2. Write channel
// generate
//     if (BWE == 0) begin
//         always @(posedge clk) begin
//             if (wen) begin
//                 mem[addr] <= wdata;
//             end
//         end
//     end
//     else begin
//         always @(posedge clk) begin
//             if (wen) begin
//                 mem[addr] <= (wdata & bwe) | (mem[addr] & (~bwe));
//             end
//         end
//     end
// endgenerate

//     // 3. Read channel
//     always @(posedge clk) begin
//         if (ren) begin
//             rdata <= mem[addr];
//         end
//     end

// endmodule

// module mem_sp_wmem #(
//     parameter   DATA_BIT = `MAC_MULT_NUM*`IDATA_WIDTH,
//     parameter   DEPTH = `WMEM_DEPTH,
//     parameter   ADDR_BIT = $clog2(DEPTH),
//     parameter   BWE = 0 //bit write enable
// )(
//     // Global Signals
//     input                       clk,

//     // Data Signals
//     input       [ADDR_BIT-1:0]  addr,
//     input                       wen,
//     input       [DATA_BIT-1:0]  bwe,

//     input       [DATA_BIT-1:0]  wdata,
//     input                       ren,
//     output  reg [DATA_BIT-1:0]  rdata
// );

//     // 1. RAM/Memory initialization
//     reg [DATA_BIT-1:0]  mem [0:DEPTH-1];

//     // 2. Write channel
// generate
//     if (BWE == 0) begin
//         always @(posedge clk) begin
//             if (wen) begin
//                 mem[addr] <= wdata;
//             end
//         end
//     end
//     else begin
//         always @(posedge clk) begin
//             if (wen) begin
//                 mem[addr] <= (wdata & bwe) | (mem[addr] & (~bwe));
//             end
//         end
//     end
// endgenerate

//     // 3. Read channel
//     always @(posedge clk) begin
//         if (ren) begin
//             rdata <= mem[addr];
//         end
//     end

// endmodule
