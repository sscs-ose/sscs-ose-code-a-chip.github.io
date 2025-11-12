module bus_fifo (
	clk,
	rstn,
	wr_en,
	rd_en,
	wr_data,
	wr_valid,
	rd_valid,
	rd_data,
	almost_full,
	full,
	empty
);
	reg _sv2v_0;
	parameter SIZE = 16;
	parameter WIDTH = 32;
	parameter ALERT_DEPTH = 3;
	parameter IN_DEPTH = 6;
	input clk;
	input rstn;
	input wr_en;
	input rd_en;
	input [(IN_DEPTH * WIDTH) - 1:0] wr_data;
	output wire wr_valid;
	output wire rd_valid;
	output wire [(IN_DEPTH * WIDTH) - 1:0] rd_data;
	output reg almost_full;
	output wire full;
	output wire empty;
	reg [(SIZE * WIDTH) - 1:0] mem;
	reg [$clog2(SIZE + 1) - 1:0] head;
	reg [$clog2(SIZE + 1) - 1:0] next_head;
	reg [$clog2(SIZE + 1) - 1:0] tail;
	reg [$clog2(SIZE + 1) - 1:0] next_tail;
	reg head_val;
	reg tail_val;
	reg rd_valid_d;
	reg wr_valid_d;
	assign wr_valid = wr_en && (!full || rd_en);
	assign rd_valid = rd_en && !empty;
	wire tail_overflow;
	wire head_overflow;
	assign tail_overflow = tail == (SIZE - 1);
	assign head_overflow = head == (SIZE - 1);
	always @(*) begin
		if (_sv2v_0)
			;
		if (wr_valid) begin
			if (tail_overflow)
				next_tail = 0;
			else
				next_tail = tail + 1;
		end
		else
			next_tail = tail;
		if (rd_valid) begin
			if (head_overflow)
				next_head = 0;
			else
				next_head = head + 1;
		end
		else
			next_head = head;
	end
	assign empty = (head == tail) && (head_val == tail_val);
	assign full = (head == tail) && (head_val ^ tail_val);
	always @(*) begin
		if (_sv2v_0)
			;
		if (head_val ^ tail_val)
			almost_full = (head - tail) == ALERT_DEPTH;
		else
			almost_full = (tail - head) == (SIZE - ALERT_DEPTH);
	end
	assign rd_data = mem[head * WIDTH+:WIDTH];
	always @(posedge clk or negedge rstn)
		if (~rstn) begin
			head_val <= 0;
			tail_val <= 0;
			head <= 0;
			tail <= 0;
			rd_valid_d <= 0;
			wr_valid_d <= 0;
			begin : sv2v_autoblock_1
				reg signed [31:0] i;
				for (i = 0; i < SIZE; i = i + 1)
					mem[i * WIDTH+:WIDTH] <= 0;
			end
		end
		else begin
			rd_valid_d <= rd_valid;
			wr_valid_d <= wr_valid;
			if (head_overflow && rd_valid_d)
				head_val <= !head_val;
			if (tail_overflow && wr_valid_d)
				tail_val <= !tail_val;
			tail <= next_tail;
			head <= next_head;
			if (wr_valid)
				mem[tail * WIDTH+:WIDTH] <= wr_data;
		end
	initial _sv2v_0 = 0;
endmodule
