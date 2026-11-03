// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/primitives/uart_tx.sv
// Module: uart_tx
// Type: Primitive
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > return_path > uart_tx
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module uart_tx #(
	parameter int RATIO_WIDTH = 16
) (
	input logic clk,
	input logic rst_n,
	input logic [RATIO_WIDTH-1:0] clk_ratio,
	input logic [7:0] tx_data,
	input logic tx_valid,

	output logic tx_serial,
	output logic tx_ready
);

logic [7:0] shiftReg;
logic [RATIO_WIDTH-1:0] clkCount;
logic [2:0] bitIndex;
logic internal_serial;

typedef enum logic [1:0] {
	IDLE,
	START,
	SEND,
	STOP
} sel;

sel select;

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		select <= IDLE;
		clkCount <= '0;
		bitIndex <= '0;
		shiftReg <= '0;
		internal_serial <= 1'b1;
	end else begin
		unique case (select)
			IDLE: begin
				clkCount <= '0;
				bitIndex <= '0;
				internal_serial <= 1'b1;
				if (tx_valid) begin
					shiftReg <= tx_data;
					internal_serial <= 1'b0;
					select <= START;
				end
			end

			START: begin
				if (clkCount == clk_ratio - 1'b1) begin
					clkCount <= '0;
					internal_serial <= shiftReg[0];
					select <= SEND;
				end else begin
					clkCount <= clkCount + 1'b1;
				end
			end

			SEND: begin
				if (clkCount == clk_ratio - 1'b1) begin
					clkCount <= '0;
					shiftReg <= {1'b0, shiftReg[7:1]};
					if (bitIndex == 3'd7) begin
						internal_serial <= 1'b1;
						select <= STOP;
					end else begin
						bitIndex <= bitIndex + 1'b1;
						internal_serial <= shiftReg[1];
					end
				end else begin
					clkCount <= clkCount + 1'b1;
				end
			end

			STOP: begin
				if (clkCount == clk_ratio - 1'b1) begin
					clkCount <= '0;
					select <= IDLE;
				end else begin
					clkCount <= clkCount + 1'b1;
				end
			end
		endcase
	end
end

assign tx_serial = internal_serial;
assign tx_ready = (select == IDLE);

endmodule
