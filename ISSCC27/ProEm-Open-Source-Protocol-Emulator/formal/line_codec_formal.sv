// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: formal/line_codec_formal.sv
// Module: line_codec_formal
// Type: Formal harness (SymbiYosys)
// Hierarchy: line_codec_formal
// Submodules: line_codec
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module line_codec_formal (
	input logic clk,
	input logic rst_n,
	input logic [7:0] pins,
	input logic [15:0] line_config,
	input logic [31:0] clock_config,
	input logic [7:0] out_config,
	input logic listen,
	input logic frame_mark,
	input logic halt,
	input logic tx_cancel,
	input logic tx_valid,
	input logic [3:0] tx_len,
	input logic [7:0] tx_data
);

logic tx_ready;
logic tx_done;
logic [7:0] view;
logic tick;
logic end_tick;
logic code_error;
logic strict_tx;
logic tx_mismatch;
logic i2c_target;
logic i2c_start;
logic i2c_stop;
logic data_out;
logic data_oe;
logic pair_out;
logic pair_oe;
logic clock_out;
logic clock_oe;
logic select_out;

line_codec dut (
	.clk(clk),
	.rst_n(rst_n),
	.pins(pins),
	.line_config(line_config),
	.clock_config(clock_config),
	.out_config(out_config),
	.listen(listen),
	.line_free(1'b1),
	.in_frame(1'b0),
	.frame_mark(frame_mark),
	.halt(halt),
	.tx_cancel(tx_cancel),
	.tx_valid(tx_valid),
	.tx_len(tx_len),
	.tx_data(tx_data),
	.tx_ready(tx_ready),
	.tx_done(tx_done),
	.view(view),
	.tick(tick),
	.end_tick(end_tick),
	.code_error(code_error),
	.strict_tx(strict_tx),
	.tx_mismatch(tx_mismatch),
	.i2c_target(i2c_target),
	.i2c_start(i2c_start),
	.i2c_stop(i2c_stop),
	.data_out(data_out),
	.data_oe(data_oe),
	.pair_out(pair_out),
	.pair_oe(pair_oe),
	.clock_out(clock_out),
	.clock_oe(clock_oe),
	.select_out(select_out)
);

logic started;
logic [3:0] outstanding;
logic [1:0] quiet;
logic accepted;
logic active;

assign accepted = tx_valid && tx_ready;
assign active = (select_out == out_config[1]);

initial assume (!rst_n);
initial started = 1'b0;

always_ff @(posedge clk) begin
	started <= 1'b1;
	if (started) begin
		assume (rst_n);
	end
end

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		outstanding <= '0;
		quiet <= '0;
	end else begin
		outstanding <= outstanding + {3'd0, accepted} - {3'd0, tx_done};
		if (active) begin
			quiet <= '0;
		end else if (quiet != 2'd3) begin
			quiet <= quiet + 1'b1;
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		assert (outstanding <= 4'd4);
		assert (!(tx_done && outstanding == 4'd0));
		if (quiet == 2'd3 && !active) begin
			assert (outstanding == 4'd0);
		end
		if (out_config[7:6] == 2'd0) begin
			assert (!data_oe && !pair_oe && !clock_oe);
		end
		if (out_config[7:6] == 2'd2) begin
			assert (!data_out && !clock_out);
		end
		if (clock_oe) begin
			assert (clock_config[31:30] == 2'd2);
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		cover (outstanding == 4'd2 && tx_cancel);
		cover (tx_done && clock_config[31:30] == 2'd1 && line_config[15:13] == 3'd3);
		cover (tx_done && clock_config[31:30] == 2'd2 && out_config[2]);
	end
end

endmodule
