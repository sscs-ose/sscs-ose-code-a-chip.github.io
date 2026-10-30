// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: test/tb.v
// Module: tb
// Type: Test bench (cocotb, RTL and gate level)
// Hierarchy: tb > tt_um_vertrex_star_proem
// Submodules: tt_um_vertrex_star_proem
// Author: Paul Vincent Bezzina
// Language: Verilog
// Description:
// =============================================================================

`default_nettype none
`timescale 1ns / 1ps

module tb ();

initial begin
	$dumpfile("tb.fst");
	$dumpvars(0, tb);
	#1;
end

reg clk;
reg rst_n;
reg ena;
reg [7:0] ui_in;
reg [7:0] ext_in;
reg loop_uart;
reg loop_select;
reg i2c_bridge;
wire [7:0] uo_out;
wire [7:0] uio_out;
wire [7:0] uio_oe;
wire [7:0] uio_in;
wire [7:0] external;
wire pad_b_data;
wire bus_sda;

assign pad_b_data = uio_oe[3] ? uio_out[3] : ext_in[3];
assign bus_sda = (uio_oe[0] ? uio_out[0] : 1'b1) & (uio_oe[3] ? uio_out[3] : 1'b1);
assign external = {ext_in[7], loop_select ? uo_out[6] : ext_in[6], ext_in[5:4], i2c_bridge ? bus_sda : ext_in[3], ext_in[2:1], i2c_bridge ? bus_sda : (loop_uart ? pad_b_data : ext_in[0])};
assign uio_in = (uio_oe & uio_out) | (~uio_oe & external);

tt_um_vertrex_star_proem user_project (
	.ui_in(ui_in),
	.uo_out(uo_out),
	.uio_in(uio_in),
	.uio_out(uio_out),
	.uio_oe(uio_oe),
	.ena(ena),
	.clk(clk),
	.rst_n(rst_n)
);

endmodule
