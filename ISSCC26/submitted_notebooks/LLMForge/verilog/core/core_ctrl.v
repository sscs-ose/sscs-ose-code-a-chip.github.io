module core_ctrl (
	clk,
	rst_n,
	control_state,
	control_state_update,
	usr_cfg,
	model_cfg,
	start,
	finish,
	hlink_wen,
	hlink_rvalid,
	hlink_rdata,
	cmem_rvalid,
	cmem_rdata,
	rc_out_data,
	rc_out_data_vld,
	quant_odata,
	quant_odata_valid,
	parallel_data,
	parallel_data_valid,
	recompute_needed,
	self_cmem_ren,
	self_cmem_raddr,
	mac_opa_vld,
	mac_opa,
	mac_opb_vld,
	mac_opb,
	out_gbus_addr,
	out_gbus_wen,
	out_gbus_wdata
);
	reg _sv2v_0;
	parameter HLINK_DATA_WIDTH = 128;
	parameter VLINK_DATA_WIDTH = 128;
	parameter GBUS_DATA_WIDTH = 32;
	parameter IDATA_WIDTH = 8;
	parameter CMEM_ADDR_WIDTH = 13;
	parameter CMEM_DATA_WIDTH = 128;
	parameter ODATA_BIT = 25;
	parameter CORE_INDEX = 0;
	parameter CACHE_DEPTH = 256;
	parameter CACHE_NUM = 16;
	parameter CACHE_ADDR_WIDTH = $clog2(CACHE_NUM) + $clog2(CACHE_DEPTH);
	parameter MAX_EMBD_SIZE = 512;
	parameter HEAD_NUM = 8;
	parameter HEAD_CORE_NUM = 16;
	parameter MAC_MULT_NUM = 16;
	parameter WMEM_DEPTH = 1536;
	parameter WMEM_NUM_PER_CORE = 3;
	parameter MAX_CONTEXT_LENGTH = 256;
	parameter OP_GEN_CNT_WIDTH = 10;
	parameter TOKEN_PER_CORE_WIDTH = 6;
	parameter HEAD_SRAM_DEPTH = 32;
	parameter GLOBAL_SRAM_DEPTH = 32;
	input wire clk;
	input wire rst_n;
	input wire [31:0] control_state;
	input wire control_state_update;
	input wire [11:0] usr_cfg;
	input wire [29:0] model_cfg;
	input wire start;
	output reg finish;
	input wire hlink_wen;
	input wire hlink_rvalid;
	input wire [HLINK_DATA_WIDTH - 1:0] hlink_rdata;
	input wire cmem_rvalid;
	input wire [CMEM_DATA_WIDTH - 1:0] cmem_rdata;
	input wire [ODATA_BIT - 1:0] rc_out_data;
	input wire rc_out_data_vld;
	input wire [IDATA_WIDTH - 1:0] quant_odata;
	input wire quant_odata_valid;
	input wire [GBUS_DATA_WIDTH - 1:0] parallel_data;
	input wire parallel_data_valid;
	output reg recompute_needed;
	output reg self_cmem_ren;
	output reg [CMEM_ADDR_WIDTH - 1:0] self_cmem_raddr;
	output reg mac_opa_vld;
	output reg [CMEM_DATA_WIDTH - 1:0] mac_opa;
	output reg mac_opb_vld;
	output reg [CMEM_DATA_WIDTH - 1:0] mac_opb;
	localparam integer BUS_CMEM_ADDR_WIDTH = 13;
	localparam integer BUS_CORE_ADDR_WIDTH = 4;
	localparam integer HEAD_SRAM_BIAS_WIDTH = 2;
	output reg [((HEAD_SRAM_BIAS_WIDTH + BUS_CORE_ADDR_WIDTH) + BUS_CMEM_ADDR_WIDTH) - 1:0] out_gbus_addr;
	output reg out_gbus_wen;
	output reg [GBUS_DATA_WIDTH - 1:0] out_gbus_wdata;
	localparam Q_WEIGHT_ADDR_BASE = 0;
	localparam K_WEIGHT_ADDR_BASE = ((((MAX_EMBD_SIZE * MAX_EMBD_SIZE) / HEAD_NUM) / HEAD_CORE_NUM) / MAC_MULT_NUM) * 1;
	localparam V_WEIGHT_ADDR_BASE = ((((MAX_EMBD_SIZE * MAX_EMBD_SIZE) / HEAD_NUM) / HEAD_CORE_NUM) / MAC_MULT_NUM) * 2;
	localparam PROJ_WEIGHT_ADDR_BASE = ((((MAX_EMBD_SIZE * MAX_EMBD_SIZE) / HEAD_NUM) / HEAD_CORE_NUM) / MAC_MULT_NUM) * 3;
	localparam FFN0_WEIGHT_ADDR_BASE = WMEM_DEPTH / WMEM_NUM_PER_CORE;
	localparam FFN1_WEIGHT_ADDR_BASE = (WMEM_DEPTH / WMEM_NUM_PER_CORE) * 2;
	localparam K_CACHE_ADDR_BASE = 0;
	localparam V_CACHE_ADDR_BASE = (((MAX_CONTEXT_LENGTH * MAX_EMBD_SIZE) / HEAD_NUM) / HEAD_CORE_NUM) / MAC_MULT_NUM;
	reg [31:0] control_state_reg;
	reg start_reg;
	always @(posedge clk or negedge rst_n)
		if (~rst_n)
			start_reg <= 0;
		else if (start)
			start_reg <= 1;
		else
			start_reg <= 0;
	always @(posedge clk or negedge rst_n)
		if (~rst_n)
			control_state_reg <= 32'd0;
		else if (control_state_update)
			control_state_reg <= control_state;
	always @(*) begin
		if (_sv2v_0)
			;
		recompute_needed = 0;
		if (((((control_state_reg == 32'd1) || (control_state_reg == 32'd2)) || (control_state_reg == 32'd3)) || (control_state_reg == 32'd5)) || (control_state_reg == 32'd7))
			recompute_needed = 1;
	end
	reg nxt_finish;
	reg nxt_self_cmem_ren;
	reg [CMEM_ADDR_WIDTH - 1:0] nxt_self_cmem_raddr;
	reg [((HEAD_SRAM_BIAS_WIDTH + BUS_CORE_ADDR_WIDTH) + BUS_CMEM_ADDR_WIDTH) - 1:0] nxt_out_gbus_addr;
	reg nxt_out_gbus_wen;
	reg [GBUS_DATA_WIDTH - 1:0] nxt_out_gbus_wdata;
	reg [OP_GEN_CNT_WIDTH - 1:0] op_gen_cnt;
	reg [OP_GEN_CNT_WIDTH - 1:0] nxt_op_gen_cnt;
	reg [TOKEN_PER_CORE_WIDTH - 1:0] k_token_per_core_cnt;
	reg [TOKEN_PER_CORE_WIDTH - 1:0] nxt_k_token_per_core_cnt;
	reg [$clog2(HEAD_CORE_NUM) - 1:0] k_core_cnt;
	reg [$clog2(HEAD_CORE_NUM) - 1:0] nxt_k_core_cnt;
	reg [OP_GEN_CNT_WIDTH - 1:0] max_op_gen_cnt;
	always @(posedge clk or negedge rst_n)
		if (~rst_n) begin
			mac_opa_vld <= 0;
			mac_opa <= 0;
		end
		else if (hlink_rvalid) begin
			mac_opa_vld <= 1;
			mac_opa <= hlink_rdata;
		end
		else
			mac_opa_vld <= 0;
	always @(*) begin
		if (_sv2v_0)
			;
		mac_opb_vld = 0;
		mac_opb = 0;
		if (cmem_rvalid) begin
			mac_opb_vld = 1;
			mac_opb = cmem_rdata;
		end
	end
	always @(posedge clk or negedge rst_n)
		if (~rst_n)
			max_op_gen_cnt <= 0;
		else if (start_reg)
			case (control_state_reg)
				32'd1, 32'd2, 32'd3, 32'd5: max_op_gen_cnt <= model_cfg[19-:3];
				32'd4: max_op_gen_cnt <= model_cfg[16-:6] / 4;
				32'd6, 32'd8: max_op_gen_cnt <= model_cfg[10-:10] / HEAD_CORE_NUM;
				32'd7: max_op_gen_cnt <= model_cfg[19-:3] * 4;
			endcase
	always @(*) begin
		if (_sv2v_0)
			;
		nxt_self_cmem_ren = 0;
		nxt_self_cmem_raddr = self_cmem_raddr;
		case (control_state_reg)
			32'd0: begin
				nxt_self_cmem_ren = 0;
				nxt_self_cmem_raddr = 0;
			end
			32'd1, 32'd2, 32'd3, 32'd4, 32'd5, 32'd6, 32'd7, 32'd8: begin
				if (finish)
					nxt_self_cmem_ren = 0;
				else if (hlink_wen)
					nxt_self_cmem_ren = 1;
				else
					nxt_self_cmem_ren = 0;
				if (finish)
					nxt_self_cmem_raddr = 0;
				else if (start_reg) begin
					if (control_state_reg == 32'd1)
						nxt_self_cmem_raddr = Q_WEIGHT_ADDR_BASE;
					else if (control_state_reg == 32'd3)
						nxt_self_cmem_raddr = V_WEIGHT_ADDR_BASE;
					else if (control_state_reg == 32'd2)
						nxt_self_cmem_raddr = K_WEIGHT_ADDR_BASE;
					else if (control_state_reg == 32'd6)
						nxt_self_cmem_raddr = PROJ_WEIGHT_ADDR_BASE;
					else if (control_state_reg == 32'd4) begin
						nxt_self_cmem_raddr[0+:$clog2(CACHE_DEPTH)] = K_CACHE_ADDR_BASE;
						nxt_self_cmem_raddr[CMEM_ADDR_WIDTH - 1] = 1;
					end
					else if (control_state_reg == 32'd5) begin
						nxt_self_cmem_raddr[0+:$clog2(CACHE_DEPTH)] = V_CACHE_ADDR_BASE;
						nxt_self_cmem_raddr[CMEM_ADDR_WIDTH - 1] = 1;
					end
					else if (control_state_reg == 32'd7)
						nxt_self_cmem_raddr = FFN0_WEIGHT_ADDR_BASE;
					else if (control_state_reg == 32'd8)
						nxt_self_cmem_raddr = FFN1_WEIGHT_ADDR_BASE;
				end
				else if (self_cmem_ren) begin
					if (control_state_reg == 32'd5) begin
						nxt_self_cmem_raddr = self_cmem_raddr + model_cfg[19-:3];
						if (usr_cfg[0]) begin
							if (self_cmem_raddr[$clog2(CACHE_DEPTH) - 1:0] >= (((usr_cfg[9-:9] / MAC_MULT_NUM) * model_cfg[19-:3]) + V_CACHE_ADDR_BASE))
								nxt_self_cmem_raddr = (self_cmem_raddr - ((usr_cfg[9-:9] / MAC_MULT_NUM) * model_cfg[19-:3])) + 1;
						end
						else if (self_cmem_raddr[$clog2(CACHE_DEPTH) - 1:0] >= ((((model_cfg[29-:10] / MAC_MULT_NUM) - 1) * model_cfg[19-:3]) + V_CACHE_ADDR_BASE))
							nxt_self_cmem_raddr = (self_cmem_raddr - (((model_cfg[29-:10] / MAC_MULT_NUM) - 1) * model_cfg[19-:3])) + 1;
					end
					else
						nxt_self_cmem_raddr = self_cmem_raddr + 1;
				end
			end
		endcase
	end
	always @(*) begin
		if (_sv2v_0)
			;
		nxt_out_gbus_addr = out_gbus_addr;
		nxt_out_gbus_wen = 0;
		nxt_out_gbus_wdata = out_gbus_wdata;
		nxt_finish = 0;
		nxt_op_gen_cnt = op_gen_cnt;
		nxt_k_token_per_core_cnt = k_token_per_core_cnt;
		nxt_k_core_cnt = k_core_cnt;
		case (control_state_reg)
			32'd0: begin
				nxt_out_gbus_wen = 0;
				nxt_out_gbus_wdata = 0;
			end
			32'd1, 32'd4, 32'd5, 32'd6, 32'd7, 32'd8: begin
				if (finish) begin
					nxt_out_gbus_wen = 0;
					nxt_out_gbus_wdata = 0;
				end
				else if (rc_out_data_vld && ((control_state_reg == 32'd6) || (control_state_reg == 32'd8))) begin
					nxt_out_gbus_wdata = rc_out_data;
					nxt_out_gbus_wen = 1;
				end
				else if (parallel_data_valid && (control_state_reg == 32'd4)) begin
					nxt_out_gbus_wdata = parallel_data;
					nxt_out_gbus_wen = 1;
				end
				else if (((quant_odata_valid && (control_state_reg != 32'd6)) && (control_state_reg != 32'd8)) && (control_state_reg != 32'd4)) begin
					nxt_out_gbus_wdata = quant_odata;
					nxt_out_gbus_wen = 1;
				end
				if (finish) begin
					nxt_out_gbus_addr = 0;
					nxt_op_gen_cnt = 0;
				end
				else if (start_reg) begin
					nxt_op_gen_cnt = 0;
					if ((control_state_reg == 32'd6) || (control_state_reg == 32'd8))
						nxt_out_gbus_addr[HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))-:((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) >= (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) ? ((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0))) + 1 : ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) - (HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)))) + 1)] = 2;
					else
						nxt_out_gbus_addr[HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))-:((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) >= (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) ? ((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0))) + 1 : ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) - (HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)))) + 1)] = 1;
					if ((control_state_reg == 32'd1) || (control_state_reg == 32'd5)) begin
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(HEAD_SRAM_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = (CORE_INDEX * model_cfg[19-:3]) / MAC_MULT_NUM;
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = (CORE_INDEX * model_cfg[19-:3]) % MAC_MULT_NUM;
					end
					else if (control_state_reg == 32'd4) begin
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(HEAD_SRAM_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = (CORE_INDEX * model_cfg[16-:6]) / MAC_MULT_NUM;
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = (CORE_INDEX * model_cfg[16-:6]) % MAC_MULT_NUM;
					end
					else if ((control_state_reg == 32'd6) || (control_state_reg == 32'd8)) begin
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(GLOBAL_SRAM_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = (CORE_INDEX * (model_cfg[10-:10] / HEAD_CORE_NUM)) / MAC_MULT_NUM;
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(GLOBAL_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = (CORE_INDEX * (model_cfg[10-:10] / HEAD_CORE_NUM)) % MAC_MULT_NUM;
					end
					else if (control_state_reg == 32'd7) begin
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(HEAD_SRAM_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = ((CORE_INDEX * model_cfg[19-:3]) * 4) / MAC_MULT_NUM;
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = ((CORE_INDEX * model_cfg[19-:3]) * 4) % MAC_MULT_NUM;
					end
				end
				else if (out_gbus_wen) begin
					if (op_gen_cnt == (max_op_gen_cnt - 1)) begin
						nxt_finish = 1;
						nxt_op_gen_cnt = 0;
						nxt_out_gbus_addr = 0;
					end
					else if ((op_gen_cnt[$clog2(MAC_MULT_NUM) - 1:0] == (MAC_MULT_NUM - 1)) || ((control_state_reg == 32'd4) && (op_gen_cnt[$clog2(MAC_MULT_NUM) - 1:0] == ((MAC_MULT_NUM / 4) - 1)))) begin
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(HEAD_SRAM_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(HEAD_SRAM_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] + 1;
						nxt_op_gen_cnt = op_gen_cnt + 1;
						if ((control_state_reg == 32'd1) || (control_state_reg == 32'd5))
							nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = (CORE_INDEX * model_cfg[19-:3]) % MAC_MULT_NUM;
						else if (control_state_reg == 32'd4)
							nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = (CORE_INDEX * model_cfg[16-:6]) % MAC_MULT_NUM;
						else if ((control_state_reg == 32'd6) || (control_state_reg == 32'd8))
							nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(GLOBAL_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = (CORE_INDEX * (model_cfg[10-:10] / HEAD_CORE_NUM)) % MAC_MULT_NUM;
						else if (control_state_reg == 32'd7)
							nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = ((CORE_INDEX * model_cfg[19-:3]) * 4) % MAC_MULT_NUM;
					end
					else begin
						if ((control_state_reg == 32'd6) || (control_state_reg == 32'd8))
							nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(GLOBAL_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(GLOBAL_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] + 1;
						else if (control_state_reg == 32'd4)
							nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] + 4;
						else
							nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] = out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(HEAD_SRAM_DEPTH))+:$clog2(MAC_MULT_NUM)] + 1;
						nxt_op_gen_cnt = op_gen_cnt + 1;
					end
				end
			end
			32'd2: begin
				if (finish) begin
					nxt_out_gbus_wen = 0;
					nxt_out_gbus_wdata = 0;
				end
				else if (quant_odata_valid) begin
					nxt_out_gbus_wdata = quant_odata;
					nxt_out_gbus_wen = 1;
				end
				if (finish) begin
					nxt_op_gen_cnt = 0;
					nxt_out_gbus_addr = 0;
				end
				else if (start_reg) begin
					nxt_out_gbus_addr[HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))-:((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) >= (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) ? ((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0))) + 1 : ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) - (HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)))) + 1)] = 0;
					nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - (CMEM_ADDR_WIDTH - 1))] = 1;
					nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - (CACHE_ADDR_WIDTH - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(CACHE_DEPTH))] = (CORE_INDEX * model_cfg[19-:3]) % MAC_MULT_NUM;
					if (usr_cfg[9-:9] == 0) begin
						nxt_out_gbus_addr[BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)-:((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) >= (BUS_CMEM_ADDR_WIDTH + 0) ? ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) - (BUS_CMEM_ADDR_WIDTH + 0)) + 1 : ((BUS_CMEM_ADDR_WIDTH + 0) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) + 1)] = 0;
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(CACHE_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = K_CACHE_ADDR_BASE + ((CORE_INDEX * model_cfg[19-:3]) / MAC_MULT_NUM);
						nxt_k_token_per_core_cnt[usr_cfg[11-:2]] = 0;
						nxt_k_core_cnt[usr_cfg[11-:2]] = 0;
					end
					else if (k_token_per_core_cnt[usr_cfg[11-:2]] == (model_cfg[16-:6] - 1)) begin
						nxt_out_gbus_addr[BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)-:((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) >= (BUS_CMEM_ADDR_WIDTH + 0) ? ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) - (BUS_CMEM_ADDR_WIDTH + 0)) + 1 : ((BUS_CMEM_ADDR_WIDTH + 0) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) + 1)] = k_core_cnt[usr_cfg[11-:2]] + 1;
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(CACHE_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = K_CACHE_ADDR_BASE + ((CORE_INDEX * model_cfg[19-:3]) / MAC_MULT_NUM);
						nxt_k_token_per_core_cnt[usr_cfg[11-:2]] = 0;
						nxt_k_core_cnt[usr_cfg[11-:2]] = k_core_cnt[usr_cfg[11-:2]] + 1;
					end
					else begin
						nxt_out_gbus_addr[BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)-:((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) >= (BUS_CMEM_ADDR_WIDTH + 0) ? ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) - (BUS_CMEM_ADDR_WIDTH + 0)) + 1 : ((BUS_CMEM_ADDR_WIDTH + 0) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) + 1)] = k_core_cnt[usr_cfg[11-:2]];
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(CACHE_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = (K_CACHE_ADDR_BASE + ((CORE_INDEX * model_cfg[19-:3]) / MAC_MULT_NUM)) + ((((k_token_per_core_cnt[usr_cfg[11-:2]] + 1) * model_cfg[19-:3]) * HEAD_CORE_NUM) / MAC_MULT_NUM);
						nxt_k_token_per_core_cnt[usr_cfg[11-:2]] = k_token_per_core_cnt[usr_cfg[11-:2]] + 1;
					end
				end
				else if (out_gbus_wen) begin
					if (op_gen_cnt == (max_op_gen_cnt - 1))
						nxt_finish = 1;
					else if (out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - (CACHE_ADDR_WIDTH - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(CACHE_DEPTH))] == (MAC_MULT_NUM - 1)) begin
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(CACHE_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(CACHE_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] + 1;
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - (CACHE_ADDR_WIDTH - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(CACHE_DEPTH))] = 0;
						nxt_op_gen_cnt = op_gen_cnt + 1;
					end
					else begin
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - (CACHE_ADDR_WIDTH - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(CACHE_DEPTH))] = out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - (CACHE_ADDR_WIDTH - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(CACHE_DEPTH))] + 1;
						nxt_op_gen_cnt = op_gen_cnt + 1;
					end
				end
			end
			32'd3: begin
				if (finish) begin
					nxt_out_gbus_wen = 0;
					nxt_out_gbus_wdata = 0;
				end
				else if (quant_odata_valid) begin
					nxt_out_gbus_wdata = quant_odata;
					nxt_out_gbus_wen = 1;
				end
				if (finish) begin
					nxt_out_gbus_addr = 0;
					nxt_op_gen_cnt = 0;
				end
				else if (start_reg) begin
					nxt_out_gbus_addr[HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))-:((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) >= (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) ? ((HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0))) + 1 : ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH + 0)) - (HEAD_SRAM_BIAS_WIDTH + (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)))) + 1)] = 0;
					nxt_out_gbus_addr[BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)-:((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) >= (BUS_CMEM_ADDR_WIDTH + 0) ? ((BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1)) - (BUS_CMEM_ADDR_WIDTH + 0)) + 1 : ((BUS_CMEM_ADDR_WIDTH + 0) - (BUS_CORE_ADDR_WIDTH + (BUS_CMEM_ADDR_WIDTH - 1))) + 1)] = CORE_INDEX;
					nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - (CMEM_ADDR_WIDTH - 1))] = 1;
					nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - (CACHE_ADDR_WIDTH - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - $clog2(CACHE_DEPTH))] = usr_cfg[9-:9] % MAC_MULT_NUM;
					nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(CACHE_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = V_CACHE_ADDR_BASE + ((usr_cfg[9-:9] / MAC_MULT_NUM) * model_cfg[19-:3]);
					nxt_op_gen_cnt = 0;
				end
				else if (out_gbus_wen) begin
					if (op_gen_cnt == (max_op_gen_cnt - 1)) begin
						nxt_finish = 1;
						nxt_op_gen_cnt = 0;
						nxt_out_gbus_addr = 0;
					end
					else begin
						nxt_out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(CACHE_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] = out_gbus_addr[(BUS_CMEM_ADDR_WIDTH - 1) - ((BUS_CMEM_ADDR_WIDTH - 1) - ($clog2(CACHE_DEPTH) - 1)):(BUS_CMEM_ADDR_WIDTH - 1) - (BUS_CMEM_ADDR_WIDTH - 1)] + 1;
						nxt_op_gen_cnt = op_gen_cnt + 1;
					end
				end
			end
			default:
				;
		endcase
	end
	always @(posedge clk or negedge rst_n)
		if (~rst_n) begin
			self_cmem_ren <= 0;
			self_cmem_raddr <= 0;
			finish <= 0;
			out_gbus_addr <= 0;
			out_gbus_wen <= 0;
			out_gbus_wdata <= 0;
			op_gen_cnt <= 0;
			k_token_per_core_cnt <= 0;
			k_core_cnt <= 0;
		end
		else begin
			self_cmem_ren <= nxt_self_cmem_ren;
			self_cmem_raddr <= nxt_self_cmem_raddr;
			finish <= nxt_finish;
			out_gbus_addr <= nxt_out_gbus_addr;
			out_gbus_wen <= nxt_out_gbus_wen;
			out_gbus_wdata <= nxt_out_gbus_wdata;
			op_gen_cnt <= nxt_op_gen_cnt;
			k_token_per_core_cnt <= nxt_k_token_per_core_cnt;
			k_core_cnt <= nxt_k_core_cnt;
		end
	initial _sv2v_0 = 0;
endmodule
