// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: formal/uart_tx_formal.sv
// Module: uart_tx_formal
// Type: Formal harness (SymbiYosys)
// Hierarchy: uart_tx_formal
// Submodules: uart_tx
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module uart_tx_formal (
	input logic clk,
	input logic rst_n,
	input logic [7:0] tx_data,
	input logic tx_valid
);

(* anyconst *) logic [3:0] ratio;

logic tx_serial;
logic tx_ready;

uart_tx #(
	.RATIO_WIDTH(4)
) dut (
	.clk(clk),
	.rst_n(rst_n),
	.clk_ratio(ratio),
	.tx_data(tx_data),
	.tx_valid(tx_valid),
	.tx_serial(tx_serial),
	.tx_ready(tx_ready)
);

logic started;
logic active;
logic [3:0] bitNum;
logic [3:0] cycle;
logic [7:0] sent;
logic expected;

always_comb begin
	assume (ratio != 0);
end

initial assume (!rst_n);
initial started = 1'b0;

always_ff @(posedge clk) begin
	started <= 1'b1;
end

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		active <= 1'b0;
		bitNum <= '0;
		cycle <= '0;
		sent <= '0;
	end else if (!active) begin
		if (tx_valid && tx_ready) begin
			active <= 1'b1;
			bitNum <= '0;
			cycle <= '0;
			sent <= tx_data;
		end
	end else if (cycle == ratio - 1'b1) begin
		cycle <= '0;
		if (bitNum == 4'd9) begin
			active <= 1'b0;
		end else begin
			bitNum <= bitNum + 1'b1;
		end
	end else begin
		cycle <= cycle + 1'b1;
	end
end

always_comb begin
	if (bitNum == 0) begin
		expected = 1'b0;
	end else if (bitNum == 4'd9) begin
		expected = 1'b1;
	end else begin
		expected = sent[bitNum - 1'b1];
	end
end

always_comb begin
	if (started && rst_n) begin
		assert (tx_ready == !active);
		if (active) begin
			assert (tx_serial == expected);
			assert (bitNum <= 4'd9);
			assert (cycle < ratio);
		end else begin
			assert (tx_serial == 1'b1);
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		cover (active && bitNum == 4'd9 && cycle == ratio - 1'b1 && ratio == 4'd3 && sent == 8'hA5);
	end
end

endmodule
