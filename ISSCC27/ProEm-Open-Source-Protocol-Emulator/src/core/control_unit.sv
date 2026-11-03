// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/core/control_unit.sv
// Module: control_unit
// Type: RTL, core
// Hierarchy: tt_um_vertrex_star_proem > protocol_emulator > control_unit
// Submodules: none
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module control_unit (
	input logic clk,
	input logic rst_n,
	input logic [7:0] rx_data,
	input logic rx_valid,

	output logic cfg_we_a,
	output logic cfg_we_b,
	output logic [3:0] cfg_sel,
	output logic [7:0] cfg_compare,
	output logic [7:0] cfg_cycles,
	output logic [2:0] cfg_pin,
	output logic cfg_capture,
	output logic cfg_write,
	output logic [1:0] cfg_group,
	output logic cfg_sr,
	output logic cfg_any,
	output logic cfg_seek,
	output logic cfg_follow,
	output logic [15:0] cfg_main_cycles,
	output logic cfg_wait_end,
	output logic cfg_ack,
	output logic [15:0] cfg_end_pattern,
	output logic [2:0] cfg_pin_b,
	output logic cfg_pair,
	output logic cfg_invert,
	output logic cfg_error,
	output logic run_a,
	output logic run_b,
	output logic [1:0] run_mode,
	output logic halt_a,
	output logic halt_b,
	output logic clear_a,
	output logic clear_b,
	output logic host_we_a,
	output logic host_we_b,
	output logic [11:0] host_wdata,
	output logic [15:0] line_a,
	output logic [15:0] line_b,
	output logic [31:0] clock_a,
	output logic [31:0] clock_b,
	output logic [7:0] out_a,
	output logic [7:0] out_b,
	output logic [15:0] link_div,
	output logic cmd_error
);

localparam logic [3:0] OP_NOP = 4'h0;
localparam logic [3:0] OP_START = 4'h1;
localparam logic [3:0] OP_HDR = 4'h2;
localparam logic [3:0] OP_MAIN = 4'h3;
localparam logic [3:0] OP_END = 4'h4;
localparam logic [3:0] OP_WDOG = 4'h5;
localparam logic [3:0] OP_ORDER = 4'h6;
localparam logic [3:0] OP_RUN = 4'h7;
localparam logic [3:0] OP_HALT = 4'h8;
localparam logic [3:0] OP_CLEAR = 4'h9;
localparam logic [3:0] OP_LINE = 4'hA;
localparam logic [3:0] OP_CLOCK = 4'hB;
localparam logic [3:0] OP_DATA = 4'hC;
localparam logic [3:0] OP_OUT = 4'hD;
localparam logic [3:0] OP_LINK = 4'hE;
localparam logic [3:0] OP_BRANCH = 4'hF;

logic [31:0] operands;
logic [7:0] startValue;
logic [3:0] opcode;
logic [3:0] startCycles;
logic [2:0] index;
logic [2:0] needed;
logic [2:0] count;
logic [2:0] length;
logic chain;
logic msbA;
logic msbB;
logic startMsb;
logic chainWrite;

logic [3:0] internal_sel;
logic [7:0] internal_compare;
logic [7:0] internal_cycles;
logic [2:0] internal_pin;
logic [1:0] internal_group;
logic [15:0] internal_main_cycles;
logic [15:0] internal_end_pattern;
logic [2:0] internal_pin_b;
logic [1:0] internal_run_mode;
logic [11:0] internal_host_wdata;
logic [15:0] internal_line_a;
logic [15:0] internal_line_b;
logic [31:0] internal_clock_a;
logic [31:0] internal_clock_b;
logic [7:0] internal_out_a;
logic [7:0] internal_out_b;
logic [15:0] internal_link_div;
logic internal_we_a;
logic internal_we_b;
logic internal_capture;
logic internal_write;
logic internal_sr;
logic internal_any;
logic internal_seek;
logic internal_follow;
logic internal_wait_end;
logic internal_ack;
logic internal_pair;
logic internal_invert;
logic internal_error;
logic internal_run_a;
logic internal_run_b;
logic internal_halt_a;
logic internal_halt_b;
logic internal_clear_a;
logic internal_clear_b;
logic internal_host_we_a;
logic internal_host_we_b;
logic internal_cmd_error;

typedef enum logic [1:0] {
	OPCODE,
	OPERAND,
	EXECUTE
} sel;

sel select;

always_comb begin
	case (rx_data[7:4])
		OP_START, OP_HDR, OP_MAIN, OP_BRANCH: length = 3'd3;
		OP_END, OP_CLOCK: length = 3'd4;
		OP_WDOG, OP_LINE, OP_LINK: length = 3'd2;
		OP_DATA, OP_OUT: length = 3'd1;
		default: length = 3'd0;
	endcase
end

assign startMsb = chain ? msbB : msbA;
assign startCycles = operands[19:16];
assign startValue = (!startMsb && startCycles != 4'd0 && startCycles < 4'd8) ? (operands[7:0] << (4'd8 - startCycles)) : operands[7:0];
assign chainWrite = (opcode == OP_START) || (opcode == OP_HDR && index != 3'd0 && index != 3'd7) || (opcode == OP_MAIN) || (opcode == OP_END) || (opcode == OP_WDOG) || (opcode == OP_ORDER) || (opcode == OP_BRANCH && index <= 3'd4);

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		select <= OPCODE;
		opcode <= '0;
		index <= '0;
		chain <= 1'b0;
		needed <= '0;
		count <= '0;
		operands <= '0;
		msbA <= 1'b0;
		msbB <= 1'b0;
		internal_sel <= '0;
		internal_compare <= '0;
		internal_cycles <= '0;
		internal_pin <= '0;
		internal_group <= '0;
		internal_main_cycles <= '0;
		internal_end_pattern <= '0;
		internal_pin_b <= '0;
		internal_run_mode <= '0;
		internal_host_wdata <= '0;
		internal_line_a <= '0;
		internal_line_b <= '0;
		internal_clock_a <= '0;
		internal_clock_b <= '0;
		internal_out_a <= '0;
		internal_out_b <= '0;
		internal_link_div <= '0;
		internal_we_a <= 1'b0;
		internal_we_b <= 1'b0;
		internal_capture <= 1'b0;
		internal_write <= 1'b0;
		internal_sr <= 1'b0;
		internal_any <= 1'b0;
		internal_seek <= 1'b0;
		internal_follow <= 1'b0;
		internal_wait_end <= 1'b0;
		internal_ack <= 1'b0;
		internal_pair <= 1'b0;
		internal_invert <= 1'b0;
		internal_error <= 1'b0;
		internal_run_a <= 1'b0;
		internal_run_b <= 1'b0;
		internal_halt_a <= 1'b0;
		internal_halt_b <= 1'b0;
		internal_clear_a <= 1'b0;
		internal_clear_b <= 1'b0;
		internal_host_we_a <= 1'b0;
		internal_host_we_b <= 1'b0;
		internal_cmd_error <= 1'b0;
	end else begin
		internal_we_a <= 1'b0;
		internal_we_b <= 1'b0;
		internal_run_a <= 1'b0;
		internal_run_b <= 1'b0;
		internal_halt_a <= 1'b0;
		internal_halt_b <= 1'b0;
		internal_clear_a <= 1'b0;
		internal_clear_b <= 1'b0;
		internal_host_we_a <= 1'b0;
		internal_host_we_b <= 1'b0;
		internal_cmd_error <= 1'b0;

		unique case (select)
			OPCODE: begin
				if (rx_valid) begin
					opcode <= rx_data[7:4];
					chain <= rx_data[3];
					index <= rx_data[2:0];
					needed <= length;
					count <= '0;
					if (length == 3'd0) begin
						select <= EXECUTE;
					end else begin
						select <= OPERAND;
					end
				end
			end

			OPERAND: begin
				if (rx_valid) begin
					operands <= {operands[23:0], rx_data};
					if (count + 1'b1 == needed) begin
						select <= EXECUTE;
					end else begin
						count <= count + 1'b1;
					end
				end
			end

			EXECUTE: begin
				select <= OPCODE;
				internal_we_a <= chainWrite && !chain;
				internal_we_b <= chainWrite && chain;
				case (opcode)
					OP_START, OP_HDR: begin
						internal_sel <= (opcode == OP_START) ? 4'd0 : {1'b0, index};
						internal_write <= operands[23];
						internal_capture <= operands[22];
						internal_group <= operands[21:20];
						internal_cycles <= {4'd0, operands[19:16]};
						internal_sr <= operands[15];
						internal_any <= (opcode == OP_HDR) && operands[14];
						internal_seek <= (opcode == OP_HDR) && operands[13];
						internal_pin <= operands[10:8];
						internal_compare <= (opcode == OP_START) ? startValue : operands[7:0];
						if (opcode == OP_HDR && (index == 3'd0 || index == 3'd7)) begin
							internal_cmd_error <= 1'b1;
						end
					end
					OP_MAIN: begin
						internal_sel <= 4'd14;
						internal_write <= (operands[23:22] == 2'd1);
						internal_follow <= (operands[23:22] == 2'd2);
						internal_wait_end <= operands[21];
						internal_ack <= operands[20];
						internal_sr <= operands[19];
						internal_pin <= operands[18:16];
						internal_main_cycles <= operands[15:0];
					end
					OP_END: begin
						internal_sel <= 4'd15;
						internal_cycles <= {3'd0, operands[31:27]};
						internal_pin <= operands[26:24];
						internal_pair <= operands[23];
						internal_invert <= operands[22];
						internal_error <= operands[21];
						internal_pin_b <= operands[18:16];
						internal_end_pattern <= operands[15:0];
					end
					OP_WDOG: begin
						internal_sel <= 4'd13;
						internal_main_cycles <= operands[15:0];
					end
					OP_ORDER: begin
						internal_sel <= 4'd12;
						internal_compare <= {7'd0, index[0]};
						if (chain) begin
							msbB <= index[0];
						end else begin
							msbA <= index[0];
						end
					end
					OP_RUN: begin
						internal_run_mode <= index[1:0];
						internal_run_a <= !chain;
						internal_run_b <= chain;
					end
					OP_HALT: begin
						internal_halt_a <= !chain;
						internal_halt_b <= chain;
					end
					OP_CLEAR: begin
						internal_clear_a <= !chain;
						internal_clear_b <= chain;
						if (chain) begin
							msbB <= 1'b0;
							internal_line_b <= '0;
							internal_clock_b <= '0;
							internal_out_b <= '0;
						end else begin
							msbA <= 1'b0;
							internal_line_a <= '0;
							internal_clock_a <= '0;
							internal_out_a <= '0;
						end
					end
					OP_LINE: begin
						if (chain) begin
							internal_line_b <= operands[15:0];
						end else begin
							internal_line_a <= operands[15:0];
						end
					end
					OP_CLOCK: begin
						if (chain) begin
							internal_clock_b <= operands;
						end else begin
							internal_clock_a <= operands;
						end
					end
					OP_DATA: begin
						internal_host_wdata <= {{1'b0, index} + 4'd1, operands[7:0]};
						internal_host_we_a <= !chain;
						internal_host_we_b <= chain;
					end
					OP_OUT: begin
						if (chain) begin
							internal_out_b <= operands[7:0];
						end else begin
							internal_out_a <= operands[7:0];
						end
					end
					OP_LINK: begin
						internal_link_div <= operands[15:0];
					end
					OP_BRANCH: begin
						case (index)
							3'd0: internal_sel <= 4'd8;
							3'd1: internal_sel <= 4'd9;
							3'd2: internal_sel <= 4'd10;
							3'd3: internal_sel <= 4'd11;
							default: internal_sel <= 4'd7;
						endcase
						internal_main_cycles <= {8'd0, operands[23:16]};
						internal_cycles <= operands[15:8];
						internal_compare <= operands[7:0];
						if (index > 3'd4) begin
							internal_cmd_error <= 1'b1;
						end
					end
					OP_NOP: begin
					end
					default: begin
						internal_cmd_error <= 1'b1;
					end
				endcase
			end

			default: begin
				select <= OPCODE;
			end
		endcase
	end
end

assign cfg_we_a = internal_we_a;
assign cfg_we_b = internal_we_b;
assign cfg_sel = internal_sel;
assign cfg_compare = internal_compare;
assign cfg_cycles = internal_cycles;
assign cfg_pin = internal_pin;
assign cfg_capture = internal_capture;
assign cfg_write = internal_write;
assign cfg_group = internal_group;
assign cfg_sr = internal_sr;
assign cfg_any = internal_any;
assign cfg_seek = internal_seek;
assign cfg_follow = internal_follow;
assign cfg_main_cycles = internal_main_cycles;
assign cfg_wait_end = internal_wait_end;
assign cfg_ack = internal_ack;
assign cfg_end_pattern = internal_end_pattern;
assign cfg_pin_b = internal_pin_b;
assign cfg_pair = internal_pair;
assign cfg_invert = internal_invert;
assign cfg_error = internal_error;
assign run_a = internal_run_a;
assign run_b = internal_run_b;
assign run_mode = internal_run_mode;
assign halt_a = internal_halt_a;
assign halt_b = internal_halt_b;
assign clear_a = internal_clear_a;
assign clear_b = internal_clear_b;
assign host_we_a = internal_host_we_a;
assign host_we_b = internal_host_we_b;
assign host_wdata = internal_host_wdata;
assign line_a = internal_line_a;
assign line_b = internal_line_b;
assign clock_a = internal_clock_a;
assign clock_b = internal_clock_b;
assign out_a = internal_out_a;
assign out_b = internal_out_b;
assign link_div = internal_link_div;
assign cmd_error = internal_cmd_error;

endmodule
