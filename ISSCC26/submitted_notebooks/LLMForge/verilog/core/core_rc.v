module core_rc (
	clk,
	rst_n,
	recompute_needed,
	rc_scale,
	rc_scale_vld,
	rc_scale_clear,
	rms_rc_shift,
	in_data,
	in_data_vld,
	out_data,
	out_data_vld,
	error
);
	reg _sv2v_0;
	parameter IN_DATA_WIDTH = 24;
	parameter OUT_DATA_WIDTH = 24;
	parameter RECOMPUTE_FIFO_DEPTH = 16;
	parameter RECOMPUTE_SHIFT_WIDTH = 5;
	parameter RETIMING_REG_NUM = 4;
	parameter RECOMPUTE_SCALE_WIDTH = 24;
	input wire clk;
	input wire rst_n;
	input wire recompute_needed;
	input wire [RECOMPUTE_SCALE_WIDTH - 1:0] rc_scale;
	input wire rc_scale_vld;
	input wire rc_scale_clear;
	input wire [RECOMPUTE_SHIFT_WIDTH - 1:0] rms_rc_shift;
	input wire [IN_DATA_WIDTH - 1:0] in_data;
	input wire in_data_vld;
	output reg [OUT_DATA_WIDTH - 1:0] out_data;
	output reg out_data_vld;
	output wire error;
	reg [RECOMPUTE_SCALE_WIDTH - 1:0] rc_scale_reg;
	reg rc_scale_reg_available;
	always @(posedge clk or negedge rst_n)
		if (~rst_n) begin
			rc_scale_reg <= 0;
			rc_scale_reg_available <= 0;
		end
		else if (rc_scale_vld) begin
			rc_scale_reg <= rc_scale;
			rc_scale_reg_available <= 1;
		end
		else if (rc_scale_clear)
			rc_scale_reg_available <= 0;
	reg [IN_DATA_WIDTH - 1:0] fifo_data_in;
	reg fifo_wr_en;
	wire signed [IN_DATA_WIDTH - 1:0] fifo_data_out;
	reg fifo_rd_en;
	wire fifo_empty;
	reg fifo_rvld;
	always @(*) begin
		if (_sv2v_0)
			;
		fifo_data_in = in_data;
		fifo_wr_en = in_data_vld;
		fifo_rd_en = 1;
		if (recompute_needed)
			fifo_rd_en = rc_scale_reg_available;
	end
	always @(posedge clk or negedge rst_n)
		if (~rst_n)
			fifo_rvld <= 0;
		else
			fifo_rvld <= ~fifo_empty & fifo_rd_en;
	reg signed [(RECOMPUTE_SCALE_WIDTH + IN_DATA_WIDTH) - 1:0] rc_data_rt_array [RETIMING_REG_NUM - 1:0];
	reg rc_data_vld_rt_array [RETIMING_REG_NUM - 1:0];
	genvar _gv_i_1;
	generate
		for (_gv_i_1 = 0; _gv_i_1 < RETIMING_REG_NUM; _gv_i_1 = _gv_i_1 + 1) begin : genblk1
			localparam i = _gv_i_1;
			if (i == 0) begin : genblk1
				always @(posedge clk or negedge rst_n)
					if (~rst_n) begin
						rc_data_rt_array[i] <= 0;
						rc_data_vld_rt_array[i] <= 0;
					end
					else begin
						if (recompute_needed)
							rc_data_rt_array[i] <= $signed(rc_scale_reg) * $signed(fifo_data_out);
						else
							rc_data_rt_array[i] <= $signed(fifo_data_out);
						rc_data_vld_rt_array[i] <= fifo_rvld;
					end
			end
			else begin : genblk1
				always @(posedge clk or negedge rst_n)
					if (~rst_n) begin
						rc_data_rt_array[i] <= 0;
						rc_data_vld_rt_array[i] <= 0;
					end
					else begin
						rc_data_rt_array[i] <= rc_data_rt_array[i - 1];
						rc_data_vld_rt_array[i] <= rc_data_vld_rt_array[i - 1];
					end
			end
		end
	endgenerate
	reg signed [(RECOMPUTE_SCALE_WIDTH + IN_DATA_WIDTH) - 1:0] rc_data_shift;
	reg rc_data_shift_vld;
	reg round;
	always @(posedge clk or negedge rst_n)
		if (~rst_n) begin
			rc_data_shift <= 0;
			rc_data_shift_vld <= 0;
			round <= 0;
		end
		else if (rc_data_vld_rt_array[RETIMING_REG_NUM - 1]) begin
			if (recompute_needed) begin
				rc_data_shift <= $signed(rc_data_rt_array[RETIMING_REG_NUM - 1]) >>> rms_rc_shift;
				round <= rc_data_rt_array[RETIMING_REG_NUM - 1][rms_rc_shift - 1];
			end
			else
				rc_data_shift <= rc_data_rt_array[RETIMING_REG_NUM - 1];
			rc_data_shift_vld <= 1;
		end
		else
			rc_data_shift_vld <= 0;
	reg signed [(RECOMPUTE_SCALE_WIDTH + IN_DATA_WIDTH) - 1:0] rc_data_rnd;
	reg signed [(RECOMPUTE_SCALE_WIDTH + IN_DATA_WIDTH) - 1:0] nxt_rc_data_rnd;
	reg rc_data_rnd_vld;
	always @(*) begin
		if (_sv2v_0)
			;
		nxt_rc_data_rnd = 0;
		if (recompute_needed) begin
			nxt_rc_data_rnd = rc_data_shift + round;
			if (nxt_rc_data_rnd > $signed({1'b0, {OUT_DATA_WIDTH - 1 {1'b1}}}))
				nxt_rc_data_rnd = {1'b0, {OUT_DATA_WIDTH - 1 {1'b1}}};
			else if (nxt_rc_data_rnd < $signed({1'b1, {OUT_DATA_WIDTH - 1 {1'b0}}}))
				nxt_rc_data_rnd = {1'b1, {OUT_DATA_WIDTH - 1 {1'b0}}};
		end
		else
			nxt_rc_data_rnd = rc_data_shift;
	end
	always @(posedge clk or negedge rst_n)
		if (~rst_n) begin
			rc_data_rnd_vld <= 0;
			rc_data_rnd <= 0;
		end
		else begin
			rc_data_rnd_vld <= rc_data_shift_vld;
			rc_data_rnd <= nxt_rc_data_rnd;
		end
	always @(posedge clk or negedge rst_n)
		if (~rst_n) begin
			out_data_vld <= 0;
			out_data <= 0;
		end
		else if (recompute_needed) begin
			out_data_vld <= rc_data_rnd_vld;
			out_data <= rc_data_rnd[OUT_DATA_WIDTH - 1:0];
		end
		else begin
			out_data_vld <= in_data_vld;
			out_data <= in_data;
		end
	sync_data_fifo #(
		.DATA_WIDTH(IN_DATA_WIDTH),
		.DATA_DEPTH(RECOMPUTE_FIFO_DEPTH)
	) inst_sync_data_fifo(
		.clk(clk),
		.rst_n(rst_n),
		.data_in(fifo_data_in),
		.wr_en(fifo_wr_en),
		.rd_en(fifo_rd_en),
		.data_out(fifo_data_out),
		.empty(fifo_empty),
		.full(error)
	);
	always @(negedge clk)
		;
	initial _sv2v_0 = 0;
endmodule
module sync_data_fifo (
	clk,
	rst_n,
	data_in,
	wr_en,
	rd_en,
	data_out,
	empty,
	full
);
	parameter DATA_WIDTH = 24;
	parameter DATA_DEPTH = 4;
	input wire clk;
	input wire rst_n;
	input wire [DATA_WIDTH - 1:0] data_in;
	input wire wr_en;
	input wire rd_en;
	output reg [DATA_WIDTH - 1:0] data_out;
	output wire empty;
	output wire full;
	reg [DATA_WIDTH - 1:0] fifo_buffer [DATA_DEPTH - 1:0];
	reg [$clog2(DATA_DEPTH):0] wr_ptr;
	reg [$clog2(DATA_DEPTH):0] rd_ptr;
	wire [$clog2(DATA_DEPTH) - 1:0] real_wr_ptr;
	wire [$clog2(DATA_DEPTH) - 1:0] real_rd_ptr;
	wire wr_ptr_msb;
	wire rd_ptr_msb;
	assign {wr_ptr_msb, real_wr_ptr} = wr_ptr;
	assign {rd_ptr_msb, real_rd_ptr} = rd_ptr;
	always @(posedge clk or negedge rst_n)
		if (~rst_n)
			rd_ptr <= 'd0;
		else if (rd_en && !empty) begin
			data_out <= fifo_buffer[real_rd_ptr];
			rd_ptr <= rd_ptr + 1'd1;
		end
	always @(posedge clk or negedge rst_n)
		if (~rst_n)
			wr_ptr <= 0;
		else if (!full && wr_en) begin
			wr_ptr <= wr_ptr + 1'd1;
			fifo_buffer[real_wr_ptr] <= data_in;
		end
	assign empty = (wr_ptr == rd_ptr ? 1'b1 : 1'b0);
	assign full = ((wr_ptr_msb != rd_ptr_msb) && (real_wr_ptr == real_rd_ptr) ? 1'b1 : 1'b0);
endmodule
