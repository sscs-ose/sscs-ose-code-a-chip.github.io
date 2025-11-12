module counter (
	clk,
	rstn,
	inc,
	overflow,
	out
);
	parameter MAX_COUNT = 31;
	localparam BIT_WIDTH = $clog2(MAX_COUNT + 1);
	input clk;
	input rstn;
	input inc;
	output wire overflow;
	output reg [BIT_WIDTH - 1:0] out;
	always @(posedge clk or negedge rstn)
		if (!rstn)
			out <= 0;
		else if (inc && overflow)
			out <= 0;
		else if (inc)
			out <= out + 1;
		else
			out <= out;
	assign overflow = (out == MAX_COUNT) & inc;
endmodule
