module SRAM_parametrizable_w_equivalent (
	CLK,
	CEB,
	WEB,
	scan_en_in,
	A,
	D,
	Q
);
	parameter integer numWord = 2048;
	parameter integer numBit = 32;
	parameter numWordAddr = $clog2(numWord);
	input CLK;
	input CEB;
	input WEB;
	input scan_en_in;
	input [numWordAddr - 1:0] A;
	input [numBit - 1:0] D;
	output reg [numBit - 1:0] Q;
	wire CLK_gated;
	MEMS1D_BUFG_512x32_wrapper SRAM_i(
		.CLK(CLK),
		.D(D),
		.AS(A[8]),
		.AW(A[7:2]),
		.AC(A[1:0]),
		.CEN(CEB),
		.RDWEN(WEB),
		.BW(1'sb1),
		.Q(Q)
	);
endmodule
