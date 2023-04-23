module SRAM_2048x8_equivalent_wrapper (
	CLK,
	CEB,
	WEB,
	A,
	D,
	Q0,
	Q1,
	Q2,
	Q3
);
	parameter numWord = 4096;
	parameter numRow = 512;
	parameter numCM = 4;
	parameter numBit = 32;
	parameter numWordAddr = 12;
	parameter numRowAddr = 9;
	parameter numCMAddr = 2;
	parameter integer SRAM_blocks_per_row = 4;
	parameter integer SRAM_numBit = 8;
	input CLK;
	input CEB;
	input WEB;
	input [numWordAddr - 1:0] A;
	input [numBit - 1:0] D;
	output reg [SRAM_numBit - 1:0] Q0;
	output reg [SRAM_numBit - 1:0] Q1;
	output reg [SRAM_numBit - 1:0] Q2;
	output reg [SRAM_numBit - 1:0] Q3;
	reg [SRAM_numBit - 1:0] D_s [SRAM_blocks_per_row - 1:0];
	reg [numBit - 1:0] Q_s;
	genvar j;
	wire [SRAM_numBit:1] sv2v_tmp_9902E;
	assign sv2v_tmp_9902E = Q_s[7:0];
	always @(*) Q3 = sv2v_tmp_9902E;
	wire [SRAM_numBit:1] sv2v_tmp_02E1F;
	assign sv2v_tmp_02E1F = Q_s[15:8];
	always @(*) Q2 = sv2v_tmp_02E1F;
	wire [SRAM_numBit:1] sv2v_tmp_74CB9;
	assign sv2v_tmp_74CB9 = Q_s[23:16];
	always @(*) Q1 = sv2v_tmp_74CB9;
	wire [SRAM_numBit:1] sv2v_tmp_100AE;
	assign sv2v_tmp_100AE = Q_s[31:24];
	always @(*) Q0 = sv2v_tmp_100AE;
	ST_SPHD_LOLEAK_4096x32m8_bTMRl_wrapper SRAM_equivalent_i(
		.CK(CLK),
		.INITN(1'b1),
		.D(D),
		.A(A),
		.CSN(CEB),
		.WEN(WEB),
		.M(1'sb0),
		.Q(Q_s)
	);
endmodule
