module SRAM_parametrizable_equivalent_with_reset (
	reset,
	CLK,
	CEB,
	WEB,
	A,
	D,
	Q
);
	parameter integer numWord = 2048;
	parameter integer numBit = 32;
	parameter numWordAddr = $clog2(numWord);
	input reset;
	input CLK;
	input CEB;
	input WEB;
	input [numWordAddr - 1:0] A;
	input [numBit - 1:0] D;
	output reg [numBit - 1:0] Q;
	integer i;
	reg [numBit - 1:0] memory [numWord - 1:0];
	always @(posedge CLK or negedge reset)
		if (!reset) begin
			for (i = 0; i < numWord; i = i + 1)
				memory[i] <= 0;
		end
		else if ((CEB == 0) && (WEB == 0))
			memory[A] <= D;
	always @(posedge CLK or negedge reset)
		if (!reset)
			Q <= 0;
		else if ((CEB == 0) && (WEB == 1))
			Q <= memory[A];
endmodule
