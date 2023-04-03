module SRAM_2048x64_equivalent (
	CLK,
	CEB,
	WEB,
	A,
	D,
	Q
);
	parameter numWord = 2048;
	parameter numRow = 512;
	parameter numCM = 4;
	parameter numBit = 64;
	parameter numWordAddr = 11;
	parameter numRowAddr = 9;
	parameter numCMAddr = 2;
	input CLK;
	input CEB;
	input WEB;
	input [numWordAddr - 1:0] A;
	input [numBit - 1:0] D;
	output reg [numBit - 1:0] Q;
	integer i;
	reg [numBit - 1:0] memory [numWord - 1:0];
	always @(posedge CLK)
		if ((CEB == 0) && (WEB == 0))
			memory[A] <= D;
	always @(posedge CLK)
		if ((CEB == 0) && (WEB == 1))
			Q <= memory[A];
endmodule
