// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: src/top/tt_um_vertrex_star_proem.sv
// Module: tt_um_vertrex_star_proem
// Type: Top level (Tiny Tapeout wrapper)
// Hierarchy: tt_um_vertrex_star_proem
// Submodules: protocol_emulator
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module tt_um_vertrex_star_proem (
	input logic [7:0] ui_in,
	output logic [7:0] uo_out,
	input logic [7:0] uio_in,
	output logic [7:0] uio_out,
	output logic [7:0] uio_oe,
	input logic ena,
	input logic clk,
	input logic rst_n
);

logic tx_serial;
logic data_out_a;
logic data_oe_a;
logic pair_out_a;
logic pair_oe_a;
logic clock_out_a;
logic clock_oe_a;
logic select_out_a;
logic armed_a;
logic host_full_a;
logic data_out_b;
logic data_oe_b;
logic pair_out_b;
logic pair_oe_b;
logic clock_out_b;
logic clock_oe_b;
logic select_out_b;
logic armed_b;
logic host_full_b;
logic baud_locked;
logic unused;

protocol_emulator core (
	.clk(clk),
	.rst_n(rst_n),
	.rx_serial(ui_in[0]),
	.pin_in(uio_in),
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

assign uo_out = {select_out_b, select_out_a, host_full_b, host_full_a, armed_b, armed_a, baud_locked, tx_serial};
assign uio_out = {2'b00, clock_out_b, pair_out_b, data_out_b, clock_out_a, pair_out_a, data_out_a};
assign uio_oe = {2'b00, clock_oe_b, pair_oe_b, data_oe_b, clock_oe_a, pair_oe_a, data_oe_a};
assign unused = &{ena, ui_in[7:1], 1'b0};

endmodule
