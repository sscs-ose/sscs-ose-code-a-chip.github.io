module true_mem_wrapper (
	clk,
	rst_n,
	wmem_addr,
	wmem_ren,
	wmem_wen,
	wmem_wdata,
	wmem_bwe,
	wmem_rdata,
	wmem_1024_ffn_deepslp,
	wmem_1024_ffn_bc1,
	wmem_1024_ffn_bc2,
	wmem_512_attn_deepslp,
	wmem_512_attn_bc1,
	wmem_512_attn_bc2
);
	reg _sv2v_0;
	parameter DATA_BIT = 128;
	parameter WMEM_DEPTH = 1536;
	parameter WMEM_ADDR_WIDTH = $clog2(WMEM_DEPTH);
	input wire clk;
	input wire rst_n;
	input wire [WMEM_ADDR_WIDTH - 1:0] wmem_addr;
	input wire wmem_ren;
	input wire wmem_wen;
	input wire [DATA_BIT - 1:0] wmem_wdata;
	input wire [DATA_BIT - 1:0] wmem_bwe;
	output reg [DATA_BIT - 1:0] wmem_rdata;
	input wire wmem_1024_ffn_deepslp;
	input wire wmem_1024_ffn_bc1;
	input wire wmem_1024_ffn_bc2;
	input wire wmem_512_attn_deepslp;
	input wire wmem_512_attn_bc1;
	input wire wmem_512_attn_bc2;
	reg wmem_1024_ffn_ren;
	reg wmem_1024_ffn_ren_delay1;
	reg wmem_1024_ffn_wen;
	reg [9:0] wmem_1024_ffn_adr;
	reg [127:0] wmem_1024_ffn_din;
	reg [127:0] wmem_1024_ffn_wbeb;
	wire [127:0] wmem_1024_ffn_q;
	reg wmem_512_attn_ren;
	reg wmem_512_attn_ren_delay1;
	reg wmem_512_attn_wen;
	reg [8:0] wmem_512_attn_adr;
	reg [127:0] wmem_512_attn_din;
	reg [127:0] wmem_512_attn_wbeb;
	wire [127:0] wmem_512_attn_q;
	always @(posedge clk or negedge rst_n)
		if (~rst_n) begin
			wmem_1024_ffn_ren_delay1 <= 0;
			wmem_512_attn_ren_delay1 <= 0;
		end
		else begin
			wmem_1024_ffn_ren_delay1 <= wmem_1024_ffn_ren;
			wmem_512_attn_ren_delay1 <= wmem_512_attn_ren;
		end
	always @(*) begin
		if (_sv2v_0)
			;
		if (wmem_1024_ffn_ren_delay1)
			wmem_rdata = wmem_1024_ffn_q;
		else
			wmem_rdata = wmem_512_attn_q;
	end
	always @(*) begin
		if (_sv2v_0)
			;
		wmem_512_attn_ren = wmem_ren && (wmem_addr < 512);
		wmem_512_attn_wen = wmem_wen && (wmem_addr < 512);
		wmem_512_attn_adr = wmem_addr[8:0];
		wmem_512_attn_din = wmem_wdata;
		wmem_512_attn_wbeb = ~wmem_bwe;
	end
	always @(*) begin
		if (_sv2v_0)
			;
		wmem_1024_ffn_ren = wmem_ren && (wmem_addr >= 512);
		wmem_1024_ffn_wen = wmem_wen && (wmem_addr >= 512);
		wmem_1024_ffn_adr = wmem_addr - 512;
		wmem_1024_ffn_din = wmem_wdata;
		wmem_1024_ffn_wbeb = ~wmem_bwe;
	end
	wmem_512 wmem_512_attn_r(
		.clk(clk),
		.ren(wmem_512_attn_ren),
		.wen(wmem_512_attn_wen),
		.adr(wmem_512_attn_adr),
		.mc(3'b000),
		.mcen(1'b0),
		.clkbyp(1'b0),
		.din(wmem_512_attn_din[63:0]),
		.wbeb(wmem_512_attn_wbeb[63:0]),
		.wa(2'b00),
		.wpulse(2'b00),
		.wpulseen(1'b1),
		.fwen(~rst_n),
		.deepslp(wmem_512_attn_deepslp),
		.shutoff(1'b0),
		.sleep(1'b0),
		.bc1(wmem_512_attn_bc1),
		.bc2(wmem_512_attn_bc2),
		.mpr(),
		.q(wmem_512_attn_q[63:0])
	);
	wmem_512 wmem_512_attn_l(
		.clk(clk),
		.ren(wmem_512_attn_ren),
		.wen(wmem_512_attn_wen),
		.adr(wmem_512_attn_adr),
		.mc(3'b000),
		.mcen(1'b0),
		.clkbyp(1'b0),
		.din(wmem_512_attn_din[127:64]),
		.wbeb(wmem_512_attn_wbeb[127:64]),
		.wa(2'b00),
		.wpulse(2'b00),
		.wpulseen(1'b1),
		.fwen(~rst_n),
		.deepslp(wmem_512_attn_deepslp),
		.shutoff(1'b0),
		.sleep(1'b0),
		.bc1(wmem_512_attn_bc1),
		.bc2(wmem_512_attn_bc2),
		.mpr(),
		.q(wmem_512_attn_q[127:64])
	);
	wmem_1024 wmem_1024_ffn_r(
		.clk(clk),
		.ren(wmem_1024_ffn_ren),
		.wen(wmem_1024_ffn_wen),
		.adr(wmem_1024_ffn_adr),
		.mc(3'b000),
		.mcen(1'b0),
		.clkbyp(1'b0),
		.din(wmem_1024_ffn_din[63:0]),
		.wbeb(wmem_1024_ffn_wbeb[63:0]),
		.wa(2'b00),
		.wpulse(2'b00),
		.wpulseen(1'b1),
		.fwen(~rst_n),
		.deepslp(wmem_1024_ffn_deepslp),
		.shutoff(1'b0),
		.sleep(1'b0),
		.bc1(wmem_1024_ffn_bc1),
		.bc2(wmem_1024_ffn_bc2),
		.mpr(),
		.q(wmem_1024_ffn_q[63:0])
	);
	wmem_1024 wmem_1024_ffn_l(
		.clk(clk),
		.ren(wmem_1024_ffn_ren),
		.wen(wmem_1024_ffn_wen),
		.adr(wmem_1024_ffn_adr),
		.mc(3'b000),
		.mcen(1'b0),
		.clkbyp(1'b0),
		.din(wmem_1024_ffn_din[127:64]),
		.wbeb(wmem_1024_ffn_wbeb[127:64]),
		.wa(2'b00),
		.wpulse(2'b00),
		.wpulseen(1'b1),
		.fwen(~rst_n),
		.deepslp(wmem_1024_ffn_deepslp),
		.shutoff(1'b0),
		.sleep(1'b0),
		.bc1(wmem_1024_ffn_bc1),
		.bc2(wmem_1024_ffn_bc2),
		.mpr(),
		.q(wmem_1024_ffn_q[127:64])
	);
	initial _sv2v_0 = 0;
endmodule
