// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/return_path.sv
// Module: return_path
// Type: RTL, core
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > return_path
// Submodules: uart_tx
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module return_path #(
	parameter int RATIO_WIDTH = 16
) (
	input logic clk,
	input logic rst_n,
	input logic [RATIO_WIDTH-1:0] clk_ratio,
	input logic a_valid,
	input logic [3:0] a_len,
	input logic [7:0] a_data,
	input logic b_valid,
	input logic [3:0] b_len,
	input logic [7:0] b_data,
	input logic [3:0] events,

	output logic a_ready,
	output logic b_ready,
	output logic tx_serial
);

logic [7:0] firstByte;
logic [7:0] secondByte;
logic [7:0] sendByte;
logic [3:0] flags;
logic [1:0] turn;
logic [1:0] chosen;
logic msgValid;
logic byteIndex;
logic flagsPending;
logic anyReady;
logic uartReady;
logic uartValid;

assign flagsPending = flags != 4'd0;

always_comb begin
	chosen = 2'd3;
	case (turn)
		2'd0: begin
			if (a_valid) begin
				chosen = 2'd0;
			end else if (b_valid) begin
				chosen = 2'd1;
			end else if (flagsPending) begin
				chosen = 2'd2;
			end
		end
		2'd1: begin
			if (b_valid) begin
				chosen = 2'd1;
			end else if (flagsPending) begin
				chosen = 2'd2;
			end else if (a_valid) begin
				chosen = 2'd0;
			end
		end
		default: begin
			if (flagsPending) begin
				chosen = 2'd2;
			end else if (a_valid) begin
				chosen = 2'd0;
			end else if (b_valid) begin
				chosen = 2'd1;
			end
		end
	endcase
end

assign anyReady = !msgValid && (chosen != 2'd3);
assign a_ready = anyReady && (chosen == 2'd0);
assign b_ready = anyReady && (chosen == 2'd1);
assign sendByte = byteIndex ? secondByte : firstByte;
assign uartValid = msgValid && uartReady;

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		firstByte <= '0;
		secondByte <= '0;
		flags <= '0;
		turn <= '0;
		msgValid <= 1'b0;
		byteIndex <= 1'b0;
	end else begin
		if (anyReady && chosen == 2'd2) begin
			flags <= events;
		end else begin
			flags <= flags | events;
		end
		if (anyReady) begin
			msgValid <= 1'b1;
			byteIndex <= 1'b0;
			turn <= (chosen == 2'd2) ? 2'd0 : chosen + 1'b1;
			case (chosen)
				2'd0: begin
					firstByte <= {4'b1000, a_len};
					secondByte <= a_data;
				end
				2'd1: begin
					firstByte <= {4'b1010, b_len};
					secondByte <= b_data;
				end
				default: begin
					firstByte <= 8'hC0;
					secondByte <= {4'd0, flags};
				end
			endcase
		end else if (uartValid) begin
			if (byteIndex) begin
				msgValid <= 1'b0;
				byteIndex <= 1'b0;
			end else begin
				byteIndex <= 1'b1;
			end
		end
	end
end

uart_tx #(
	.RATIO_WIDTH(RATIO_WIDTH)
) sender (
	.clk(clk),
	.rst_n(rst_n),
	.clk_ratio(clk_ratio),
	.tx_data(sendByte),
	.tx_valid(uartValid),
	.tx_serial(tx_serial),
	.tx_ready(uartReady)
);

endmodule
