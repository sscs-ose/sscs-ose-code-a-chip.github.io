// =============================================================================
// Project: ProEm - Open Source Protocol Emulator
// File: formal/crc_unit_formal.sv
// Module: crc_unit_formal
// Type: Formal harness (SymbiYosys)
// Hierarchy: crc_unit_formal
// Submodules: crc_unit
// Author: Paul Vincent Bezzina
// Language: SystemVerilog
// Description:
// =============================================================================

module crc_unit_formal (
	input logic clk,
	input logic rst_n,
	input logic cfg_we,
	input logic [3:0] cfg_sel,
	input logic [7:0] cfg_rule,
	input logic [7:0] cfg_high,
	input logic [7:0] cfg_low,
	input logic restart,
	input logic feed,
	input logic [7:0] feed_bits,
	input logic [3:0] feed_len
);

logic enabled;
logic check;
logic append;
logic byte_only;
logic span;
logic [2:0] cover_from;
logic [4:0] width;
logic good;
logic [15:0] crc_out;

crc_unit dut (
	.clk(clk),
	.rst_n(rst_n),
	.cfg_we(cfg_we),
	.cfg_sel(cfg_sel),
	.cfg_rule(cfg_rule),
	.cfg_high(cfg_high),
	.cfg_low(cfg_low),
	.restart(restart),
	.feed(feed),
	.feed_bits(feed_bits),
	.feed_len(feed_len),
	.enabled(enabled),
	.check(check),
	.append(append),
	.byte_only(byte_only),
	.span(span),
	.cover_from(cover_from),
	.width(width),
	.good(good),
	.crc_out(crc_out)
);

logic started;
logic [3:0] widthLess;
logic [2:0] fromBlock;
logic initOnes;
logic [15:0] poly;
logic [15:0] residue;
logic crcOn;
logic checkOn;
logic appendOn;
logic invertOn;
logic byteOn;
logic spanOn;
logic [15:0] model;
logic [15:0] modelNext;
logic [15:0] mask;
logic [15:0] modelInit;
logic [15:0] aligned;
logic [15:0] tmp;
logic [3:0] shift;
logic [4:0] fedBits;
logic fb;
logic reload;

assign shift = 4'd15 - widthLess;
assign mask = 16'hFFFF >> shift;
assign modelInit = initOnes ? mask : 16'h0000;
assign aligned = model << shift;

initial assume (!rst_n);
initial started = 1'b0;

always_ff @(posedge clk) begin
	started <= 1'b1;
end

always_comb begin
	modelNext = model;
	fb = 1'b0;
	for (int i = 0; i < 8; i++) begin
		if (i < feed_len) begin
			fb = modelNext[widthLess] ^ feed_bits[i];
			modelNext = ((modelNext << 1) ^ (fb ? poly : 16'h0000)) & mask;
		end
	end
end

always_ff @(posedge clk or negedge rst_n) begin
	if (!rst_n) begin
		widthLess <= 4'd15;
		fromBlock <= 3'd7;
		initOnes <= 1'b0;
		poly <= '0;
		residue <= '0;
		crcOn <= 1'b0;
		checkOn <= 1'b0;
		appendOn <= 1'b0;
		invertOn <= 1'b0;
		byteOn <= 1'b0;
		spanOn <= 1'b0;
		model <= '0;
		fedBits <= '0;
		reload <= 1'b0;
	end else begin
		reload <= cfg_we && (cfg_sel == 4'd10 || cfg_sel == 4'd11);
		if (cfg_we && cfg_sel == 4'd10) begin
			widthLess <= cfg_rule[7:4];
			fromBlock <= cfg_rule[3:1];
			initOnes <= cfg_rule[0];
			poly <= {cfg_high, cfg_low};
		end
		if (cfg_we && cfg_sel == 4'd11) begin
			crcOn <= cfg_rule[7];
			checkOn <= cfg_rule[6];
			appendOn <= cfg_rule[5];
			invertOn <= cfg_rule[4];
			byteOn <= cfg_rule[3];
			spanOn <= cfg_rule[2];
			residue <= {cfg_high, cfg_low};
		end
		if (restart || reload) begin
			model <= modelInit;
			fedBits <= '0;
		end else if (feed && crcOn) begin
			model <= modelNext;
			if (fedBits != 5'd31) begin
				fedBits <= fedBits + 5'd1;
			end
		end
	end
end

always_comb begin
	tmp = aligned;
	for (int i = 0; i < 16; i++) begin
		if (i <= widthLess) begin
			tmp = {tmp[14:0], 1'b0} ^ ((tmp[15] ^ aligned[15 - i]) ? (poly << shift) : 16'h0000);
		end
	end
	if (started && rst_n) begin
		assert (enabled == crcOn);
		assert (check == (crcOn && checkOn));
		assert (append == (crcOn && appendOn));
		assert (cover_from == fromBlock);
		assert (byte_only == byteOn);
		assert (span == spanOn);
		assert (width == {1'b0, widthLess} + 5'd1);
		if (!reload) begin
			assert ((model & ~mask) == 16'h0000);
			assert (crc_out == (invertOn ? ~aligned : aligned));
			assert (good == (crcOn && (model == (residue & mask))));
			assert (tmp == 16'h0000);
		end
	end
end

always_comb begin
	if (started && rst_n) begin
		cover (crcOn && widthLess == 4'd15 && fedBits >= 5'd3 && good);
		cover (crcOn && widthLess == 4'd4 && fedBits >= 5'd2 && good && residue[4:0] == 5'h0C);
		cover (crcOn && invertOn && fedBits >= 5'd2 && crc_out == 16'hFFFF);
	end
end

endmodule
