// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/top/protocol_emulator_inst.sv
// Module: protocol_emulator_inst
// Type: Instantiation template (not part of the design)
// Hierarchy: protocol_emulator_inst > protocol_emulator
// Submodules: protocol_emulator
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module protocol_emulator_inst (
	input logic clk,
	input logic rst_n,
	input logic rx_serial,
	input logic [7:0] pin_in,

	output logic tx_serial,
	output logic data_out_a,
	output logic data_oe_a,
	output logic pair_out_a,
	output logic pair_oe_a,
	output logic clock_out_a,
	output logic clock_oe_a,
	output logic select_out_a,
	output logic armed_a,
	output logic host_full_a,
	output logic data_out_b,
	output logic data_oe_b,
	output logic pair_out_b,
	output logic pair_oe_b,
	output logic clock_out_b,
	output logic clock_oe_b,
	output logic select_out_b,
	output logic armed_b,
	output logic host_full_b,
	output logic baud_locked
);

protocol_emulator #(
	.RATIO_WIDTH(16),
	.blocks(7),
	.buffer_depth(16),
	.host_depth(8)
) emulator (
	.clk(clk),
	.rst_n(rst_n),
	.rx_serial(rx_serial),
	.pin_in(pin_in),
	.tx_serial(tx_serial),
	.data_out_a(data_out_a),
	.data_oe_a(data_oe_a),
	.pair_out_a(pair_out_a),
	.pair_oe_a(pair_oe_a),
	.clock_out_a(clock_out_a),
	.clock_oe_a(clock_oe_a),
	.select_out_a(select_out_a),
	.armed_a(armed_a),
	.host_full_a(host_full_a),
	.data_out_b(data_out_b),
	.data_oe_b(data_oe_b),
	.pair_out_b(pair_out_b),
	.pair_oe_b(pair_oe_b),
	.clock_out_b(clock_out_b),
	.clock_oe_b(clock_oe_b),
	.select_out_b(select_out_b),
	.armed_b(armed_b),
	.host_full_b(host_full_b),
	.baud_locked(baud_locked)
);

endmodule
