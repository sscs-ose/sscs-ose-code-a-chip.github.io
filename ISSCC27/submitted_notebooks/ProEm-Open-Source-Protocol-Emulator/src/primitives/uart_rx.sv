// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/primitives/uart_rx.sv
// Module: uart_rx
// Type: Primitive
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > uart_rx
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module uart_rx #(
	parameter int RATIO_WIDTH = 16
) (
	input logic clk,
	input logic rst_n,
	input logic rx_serial,

	output logic [RATIO_WIDTH-1:0] clk_ratio,
	output logic locked,
	output logic [7:0] rx_data,
	output logic rx_valid,
	output logic frame_error
);

logic [RATIO_WIDTH+2:0] measure;
logic [RATIO_WIDTH-1:0] ratio;
logic [7:0] shiftReg;
logic [7:0] internal_data;
logic [RATIO_WIDTH-1:0] clkCount;
logic [2:0] bitIndex;
logic [2:0] fallCount;
logic serialBuffer;
logic serialR;
logic serialPrev;
logic fall;
logic internal_valid;
logic internal_error;
logic internal_locked;

typedef enum logic [2:0] {
	WAIT,
	CALIBRATE,
	SETTLE,
	IDLE,
	START,
	RECEIVE,
	STOP
} sel;

sel select;

assign fall = serialPrev && !serialR;

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		serialBuffer <= 1'b1;
		serialR <= 1'b1;
		serialPrev <= 1'b1;
	end else begin
		serialBuffer <= rx_serial;
		serialR <= serialBuffer;
		serialPrev <= serialR;
	end
end

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		select <= WAIT;
		measure <= '0;
		ratio <= '0;
		fallCount <= '0;
		clkCount <= '0;
		bitIndex <= '0;
		shiftReg <= '0;
		internal_data <= '0;
		internal_valid <= 1'b0;
		internal_error <= 1'b0;
		internal_locked <= 1'b0;
	end else begin
		internal_valid <= 1'b0;
		internal_error <= 1'b0;

		unique case (select)
			WAIT: begin
				measure <= '0;
				fallCount <= '0;
				if (fall) begin
					measure <= 1'b1;
					select <= CALIBRATE;
				end
			end

			CALIBRATE: begin
				measure <= measure + 1'b1;
				if (fall) begin
					if (fallCount == 3'd3) begin
						ratio <= measure[RATIO_WIDTH+2:3];
						internal_locked <= 1'b1;
						select <= SETTLE;
					end else begin
						fallCount <= fallCount + 1'b1;
					end
				end
			end

			SETTLE: begin
				if (serialR) begin
					select <= IDLE;
				end
			end

			IDLE: begin
				clkCount <= '0;
				bitIndex <= '0;
				if (!serialR) begin
					select <= START;
				end
			end

			START: begin
				if (clkCount == (ratio >> 1) - 1'b1) begin
					clkCount <= '0;
					if (!serialR) begin
						select <= RECEIVE;
					end else begin
						select <= IDLE;
					end
				end else begin
					clkCount <= clkCount + 1'b1;
				end
			end

			RECEIVE: begin
				if (clkCount == ratio - 1'b1) begin
					clkCount <= '0;
					shiftReg <= {serialR, shiftReg[7:1]};
					if (bitIndex == 3'd7) begin
						select <= STOP;
					end else begin
						bitIndex <= bitIndex + 1'b1;
					end
				end else begin
					clkCount <= clkCount + 1'b1;
				end
			end

			STOP: begin
				if (clkCount == ratio - 1'b1) begin
					clkCount <= '0;
					select <= IDLE;
					if (serialR) begin
						internal_data <= shiftReg;
						internal_valid <= 1'b1;
					end else begin
						internal_error <= 1'b1;
					end
				end else begin
					clkCount <= clkCount + 1'b1;
				end
			end

			default: begin
				select <= WAIT;
			end
		endcase
	end
end

assign clk_ratio = ratio;
assign locked = internal_locked;
assign rx_data = internal_data;
assign rx_valid = internal_valid;
assign frame_error = internal_error;

endmodule
