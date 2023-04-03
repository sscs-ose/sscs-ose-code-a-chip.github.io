module panda_fsm (
	clk_i,
	rst_ni,
	test_mode_i,
	clear_i,
	ctrl_streamer_o,
	flags_streamer_i,
	ctrl_engine_o,
	flags_engine_i,
	ctrl_slave_o,
	flags_slave_i,
	reg_file_i
);
	input wire clk_i;
	input wire rst_ni;
	input wire test_mode_i;
	input wire clear_i;
	output reg [464:0] ctrl_streamer_o;
	input wire [83:0] flags_streamer_i;
	localparam [31:0] mac_package_MAC_CNT_LEN = 1024;
	output reg [25:0] ctrl_engine_o;
	input wire [75:0] flags_engine_i;
	localparam [31:0] hwpe_ctrl_package_REGFILE_N_EVT = 2;
	output reg [1:0] ctrl_slave_o;
	localparam [31:0] hwpe_ctrl_package_REGFILE_N_CORES = 8;
	input wire [(1 + (hwpe_ctrl_package_REGFILE_N_CORES * hwpe_ctrl_package_REGFILE_N_EVT)) + 2:0] flags_slave_i;
	localparam [31:0] hwpe_ctrl_package_REGFILE_N_MAX_GENERIC_REGS = 8;
	localparam [31:0] hwpe_ctrl_package_REGFILE_N_MAX_IO_REGS = 48;
	input wire [1791:0] reg_file_i;
	reg [31:0] curr_state;
	reg [31:0] next_state;
	wire a_stream_valid;
	wire b_stream_valid;
	wire c_stream_valid;
	wire streamers_ready;
	wire output_streamer_ready;
	assign streamers_ready = flags_streamer_i[83] && flags_streamer_i[55];
	assign output_streamer_ready = flags_streamer_i[27];
	wire fsm_write_en;
	reg [31:0] accelerator_memory_select;
	reg [31:0] trans_size;
	reg [31:0] base_address_address;
	reg [31:0] out_trans_size;
	reg [31:0] out_base_address_data;
	reg [31:0] base_address_data;
	reg fsm_stream_ready;
	reg fsm_output_stream_ready;
	reg [31:0] packet_cnt;
	wire [31:0] packet_cnt_next;
	reg packet_counter_clear;
	reg packet_counter_clear_next;
	wire packet_counter_enable;
	reg [31:0] out_packet_cnt;
	wire [31:0] out_packet_cnt_next;
	reg out_packet_counter_clear;
	reg out_packet_counter_clear_next;
	wire out_packet_counter_enable;
	reg tile_fsm_en;
	reg [4:0] tiling_en;
	reg [4:0] nb_tile;
	reg [4:0] count_nb_tile;
	reg [4:0] next_count_nb_tile;
	reg [1:0] load_next_param_tile;
	reg [1:0] next_load_next_param_tile;
	assign packet_counter_enable = (fsm_stream_ready && a_stream_valid) && b_stream_valid;
	assign out_packet_counter_enable = fsm_output_stream_ready && c_stream_valid;
	assign fsm_write_en = fsm_stream_ready;
	wire [1:1] sv2v_tmp_99DC1;
	assign sv2v_tmp_99DC1 = fsm_stream_ready;
	always @(*) ctrl_engine_o[0] = sv2v_tmp_99DC1;
	wire [1:1] sv2v_tmp_7AFF1;
	assign sv2v_tmp_7AFF1 = fsm_write_en;
	always @(*) ctrl_engine_o[1] = sv2v_tmp_7AFF1;
	wire [3:1] sv2v_tmp_2A43E;
	assign sv2v_tmp_2A43E = accelerator_memory_select;
	always @(*) ctrl_engine_o[4-:3] = sv2v_tmp_2A43E;
	assign a_stream_valid = flags_engine_i[2];
	assign b_stream_valid = flags_engine_i[1];
	assign c_stream_valid = flags_engine_i[0];
	always @(posedge clk_i or negedge rst_ni) begin : main_fsm_seq
		if (~rst_ni)
			curr_state <= 32'd0;
		else if (clear_i)
			curr_state <= 32'd0;
		else
			curr_state <= next_state;
	end
	always @(posedge clk_i or negedge rst_ni) begin : tile_fsm_seq
		if (~rst_ni) begin
			count_nb_tile <= 1'sb0;
			load_next_param_tile <= 1'sb0;
		end
		else if (clear_i) begin
			count_nb_tile <= 1'sb0;
			load_next_param_tile <= 1'sb0;
		end
		else begin
			count_nb_tile <= next_count_nb_tile;
			load_next_param_tile <= next_load_next_param_tile;
		end
	end
	always @(posedge clk_i or negedge rst_ni) begin : fsm_control_signals_seq
		if (~rst_ni)
			packet_counter_clear <= 1'sb0;
		else if (clear_i)
			packet_counter_clear <= 1'sb0;
		else
			packet_counter_clear <= packet_counter_clear_next;
	end
	always @(posedge clk_i or negedge rst_ni) begin : fsm_control_signals_seq_out
		if (~rst_ni)
			out_packet_counter_clear <= 1'sb0;
		else if (clear_i)
			out_packet_counter_clear <= 1'sb0;
		else
			out_packet_counter_clear <= out_packet_counter_clear_next;
	end
	localparam [31:0] mac_package_PANDA_NB_TILE = 17;
	always @(*) begin : main_fsm_comb
		ctrl_streamer_o[431-:32] = trans_size;
		ctrl_streamer_o[399-:16] = 1'sb0;
		ctrl_streamer_o[383-:16] = trans_size;
		ctrl_streamer_o[367-:16] = 1'sb0;
		ctrl_streamer_o[351-:16] = 1;
		ctrl_streamer_o[463-:32] = base_address_address;
		ctrl_streamer_o[335-:16] = 1'sb0;
		ctrl_streamer_o[319] = 1'sb0;
		ctrl_streamer_o[318] = 1'sb0;
		ctrl_streamer_o[276-:32] = trans_size;
		ctrl_streamer_o[244-:16] = 1'sb0;
		ctrl_streamer_o[228-:16] = trans_size;
		ctrl_streamer_o[212-:16] = 1'sb0;
		ctrl_streamer_o[196-:16] = 1;
		ctrl_streamer_o[308-:32] = base_address_data;
		ctrl_streamer_o[180-:16] = 1'sb0;
		ctrl_streamer_o[164] = 1'sb0;
		ctrl_streamer_o[163] = 1'sb0;
		ctrl_streamer_o[121-:32] = out_trans_size;
		ctrl_streamer_o[89-:16] = 1'sb0;
		ctrl_streamer_o[73-:16] = out_trans_size;
		ctrl_streamer_o[57-:16] = 1'sb0;
		ctrl_streamer_o[41-:16] = 1;
		ctrl_streamer_o[153-:32] = out_base_address_data;
		ctrl_streamer_o[25-:16] = 1'sb0;
		ctrl_streamer_o[9] = 1'sb0;
		ctrl_streamer_o[8] = 1'sb0;
		ctrl_slave_o[1] = 1'sb0;
		ctrl_slave_o[0-:1] = 1'sb0;
		tile_fsm_en = 1'b0;
		tiling_en = reg_file_i[800+:32];
		nb_tile = flags_engine_i[23-:8];
		next_load_next_param_tile = load_next_param_tile;
		next_count_nb_tile = count_nb_tile;
		ctrl_engine_o[25] = 1'sb0;
		ctrl_engine_o[24] = 1'sb1;
		ctrl_engine_o[21] = 1'sb0;
		ctrl_engine_o[23] = 1'sb0;
		next_state = curr_state;
		ctrl_streamer_o[464] = 1'sb0;
		ctrl_streamer_o[309] = 1'sb0;
		ctrl_streamer_o[154] = 1'sb0;
		fsm_stream_ready = 1'b0;
		fsm_output_stream_ready = 1'b0;
		packet_counter_clear_next = 1;
		out_packet_counter_clear_next = 1;
		case (curr_state)
			32'd0: begin
				ctrl_engine_o[25] = 1'sb1;
				ctrl_engine_o[24] = 1'sb0;
				tile_fsm_en = 1'b0;
				next_load_next_param_tile = 1'sb0;
				next_count_nb_tile = 1'sb0;
				if (flags_slave_i[1 + ((hwpe_ctrl_package_REGFILE_N_CORES * hwpe_ctrl_package_REGFILE_N_EVT) + 2)]) begin
					next_state = 32'd1;
					ctrl_engine_o[23] = 1'sb1;
				end
			end
			32'd1: begin
				ctrl_engine_o[23] = 1'sb1;
				packet_counter_clear_next = 1'sb0;
				fsm_stream_ready = (~packet_counter_clear && a_stream_valid) && b_stream_valid;
				if (packet_cnt == trans_size) begin
					fsm_stream_ready = 1'b0;
					next_state = 32'd2;
					packet_counter_clear_next = 1'sb1;
				end
				else if (streamers_ready) begin
					ctrl_streamer_o[464] = packet_cnt == {32 {1'sb0}};
					ctrl_streamer_o[309] = packet_cnt == {32 {1'sb0}};
				end
			end
			32'd2: begin
				ctrl_engine_o[23] = 1'sb1;
				packet_counter_clear_next = 1'sb0;
				fsm_stream_ready = (~packet_counter_clear && a_stream_valid) && b_stream_valid;
				if (packet_cnt == trans_size) begin
					fsm_stream_ready = 1'b0;
					next_state = 32'd3;
					packet_counter_clear_next = 1'sb1;
				end
				else if (streamers_ready) begin
					ctrl_streamer_o[464] = packet_cnt == {32 {1'sb0}};
					ctrl_streamer_o[309] = packet_cnt == {32 {1'sb0}};
				end
			end
			32'd3: begin
				ctrl_engine_o[23] = 1'sb1;
				packet_counter_clear_next = 1'sb0;
				fsm_stream_ready = (~packet_counter_clear && a_stream_valid) && b_stream_valid;
				if (packet_cnt == trans_size) begin
					fsm_stream_ready = 1'b0;
					next_state = 32'd4;
					packet_counter_clear_next = 1'sb1;
				end
				else if (streamers_ready) begin
					ctrl_streamer_o[464] = packet_cnt == {32 {1'sb0}};
					ctrl_streamer_o[309] = packet_cnt == {32 {1'sb0}};
				end
			end
			32'd4: begin
				ctrl_engine_o[23] = 1'sb1;
				packet_counter_clear_next = 1'sb0;
				fsm_stream_ready = (~packet_counter_clear && a_stream_valid) && b_stream_valid;
				if (packet_cnt == trans_size) begin
					fsm_stream_ready = 1'b0;
					next_state = 32'd7;
					packet_counter_clear_next = 1'sb1;
				end
				else if (streamers_ready) begin
					ctrl_streamer_o[464] = packet_cnt == {32 {1'sb0}};
					ctrl_streamer_o[309] = packet_cnt == {32 {1'sb0}};
				end
			end
			32'd7: begin
				ctrl_engine_o[23] = 1'sb1;
				packet_counter_clear_next = 1'sb0;
				fsm_stream_ready = (~packet_counter_clear && a_stream_valid) && b_stream_valid;
				if (packet_cnt == trans_size) begin
					fsm_stream_ready = 1'b0;
					if (flags_engine_i[15-:3] == 1)
						next_state = 32'd5;
					else if (flags_engine_i[15-:3] == 0)
						next_state = 32'd6;
					else
						next_state = 32'd8;
					packet_counter_clear_next = 1'sb1;
				end
				else if (streamers_ready) begin
					ctrl_streamer_o[464] = packet_cnt == {32 {1'sb0}};
					ctrl_streamer_o[309] = packet_cnt == {32 {1'sb0}};
				end
			end
			32'd5: begin
				ctrl_engine_o[23] = 1'sb1;
				packet_counter_clear_next = 1'sb0;
				fsm_stream_ready = (~packet_counter_clear && a_stream_valid) && b_stream_valid;
				if (packet_cnt == trans_size) begin
					fsm_stream_ready = 1'b0;
					if (tiling_en == 0)
						next_state = 32'd6;
					else begin
						next_state = 32'd8;
						next_count_nb_tile = count_nb_tile + 1;
					end
					packet_counter_clear_next = 1'sb1;
				end
				else if (streamers_ready) begin
					ctrl_streamer_o[464] = packet_cnt == {32 {1'sb0}};
					ctrl_streamer_o[309] = packet_cnt == {32 {1'sb0}};
				end
			end
			32'd6: begin
				ctrl_engine_o[23] = 1'sb1;
				packet_counter_clear_next = 1'sb0;
				fsm_stream_ready = (~packet_counter_clear && a_stream_valid) && b_stream_valid;
				if (packet_cnt == trans_size) begin
					fsm_stream_ready = 1'b0;
					next_state = 32'd8;
					if (tiling_en == 1)
						next_count_nb_tile = count_nb_tile + 1;
					packet_counter_clear_next = 1'sb1;
				end
				else if (streamers_ready) begin
					ctrl_streamer_o[464] = packet_cnt == {32 {1'sb0}};
					ctrl_streamer_o[309] = packet_cnt == {32 {1'sb0}};
				end
			end
			32'd8: begin
				ctrl_engine_o[23] = 1'sb1;
				ctrl_engine_o[21] = 1'b1;
				next_state = 32'd9;
			end
			32'd9: begin
				ctrl_engine_o[23] = 1'sb1;
				ctrl_engine_o[21] = 1'b0;
				tile_fsm_en = 1'b1;
				out_packet_counter_clear_next = 1'sb0;
				fsm_output_stream_ready = ~out_packet_counter_clear && c_stream_valid;
				packet_counter_clear_next = 1'sb0;
				fsm_stream_ready = (~packet_counter_clear && a_stream_valid) && b_stream_valid;
				if (out_packet_cnt == out_trans_size) begin
					fsm_output_stream_ready = 1'b0;
					out_packet_counter_clear_next = 1'sb1;
					if (count_nb_tile == nb_tile)
						next_count_nb_tile = 1'sb0;
					next_load_next_param_tile = 1'sb0;
				end
				else if (output_streamer_ready)
					ctrl_streamer_o[154] = out_packet_cnt == {32 {1'sb0}};
				else begin
					if (flags_engine_i[3])
						if (count_nb_tile == nb_tile)
							next_count_nb_tile = 1'sb0;
						else begin
							next_count_nb_tile = count_nb_tile + 1;
							next_load_next_param_tile = 1'sb0;
						end
					if (load_next_param_tile < 2)
						if (packet_cnt == trans_size) begin
							fsm_stream_ready = 1'b0;
							next_load_next_param_tile = load_next_param_tile + 1;
							packet_counter_clear_next = 1'sb1;
						end
						else if (streamers_ready) begin
							ctrl_streamer_o[464] = packet_cnt == {32 {1'sb0}};
							ctrl_streamer_o[309] = packet_cnt == {32 {1'sb0}};
						end
				end
				if (flags_engine_i[64])
					next_state = 32'd10;
			end
			32'd10: begin
				ctrl_engine_o[25] = 1'b0;
				ctrl_engine_o[24] = 1'b0;
				ctrl_engine_o[21] = 1'b0;
				ctrl_engine_o[23] = 1'sb0;
				if (streamers_ready) begin
					next_state = 32'd0;
					ctrl_slave_o[1] = 1'b1;
				end
			end
		endcase
	end
	localparam [31:0] mac_package_PANDA_ACTIVATION_AMEMORY_ADDRESS = 13;
	localparam [31:0] mac_package_PANDA_ACTIVATION_DMEMORY_ADDRESS = 6;
	localparam [31:0] mac_package_PANDA_ACTIVATION_MEMORY_N = 7;
	localparam [31:0] mac_package_PANDA_CONFIG_AMEMORY_ADDRESS = 14;
	localparam [31:0] mac_package_PANDA_CONFIG_DMEMORY_ADDRESS = 8;
	localparam [31:0] mac_package_PANDA_CONFIG_MEMORY_N = 9;
	localparam [31:0] mac_package_PANDA_FSM_SEL_ACTIVATION_MEMORY = 4;
	localparam [31:0] mac_package_PANDA_FSM_SEL_CONFIG_MEMORY = 0;
	localparam [31:0] mac_package_PANDA_FSM_SEL_INSTRUCTION_MEMORY = 1;
	localparam [31:0] mac_package_PANDA_FSM_SEL_LUT_MEMORY = 2;
	localparam [31:0] mac_package_PANDA_FSM_SEL_NULL = 7;
	localparam [31:0] mac_package_PANDA_FSM_SEL_SPARSITY_MEMORY = 3;
	localparam [31:0] mac_package_PANDA_FSM_SEL_WEIGHT_CONV_MEMORY = 5;
	localparam [31:0] mac_package_PANDA_FSM_SEL_WEIGHT_FC_MEMORY = 6;
	localparam [31:0] mac_package_PANDA_INSTRUCTION_AMEMORY_ADDRESS = 12;
	localparam [31:0] mac_package_PANDA_INSTRUCTION_DMEMORY_ADDRESS = 4;
	localparam [31:0] mac_package_PANDA_INSTRUCTION_MEMORY_N = 5;
	localparam [31:0] mac_package_PANDA_LUT_AMEMORY_ADDRESS = 20;
	localparam [31:0] mac_package_PANDA_LUT_DMEMORY_ADDRESS = 18;
	localparam [31:0] mac_package_PANDA_LUT_MEMORY_N = 19;
	localparam [31:0] mac_package_PANDA_OUTPUT_DATA = 15;
	localparam [31:0] mac_package_PANDA_OUTPUT_DATA_N = 16;
	localparam [31:0] mac_package_PANDA_SPARSITY_AMEMORY_ADDRESS = 23;
	localparam [31:0] mac_package_PANDA_SPARSITY_DMEMORY_ADDRESS = 21;
	localparam [31:0] mac_package_PANDA_SPARSITY_MEMORY_N = 22;
	localparam [31:0] mac_package_PANDA_WEIGHT_CONV_AMEMORY_ADDRESS = 10;
	localparam [31:0] mac_package_PANDA_WEIGHT_CONV_DMEMORY_ADDRESS = 0;
	localparam [31:0] mac_package_PANDA_WEIGHT_CONV_MEMORY_N = 1;
	localparam [31:0] mac_package_PANDA_WEIGHT_FC_AMEMORY_ADDRESS = 11;
	localparam [31:0] mac_package_PANDA_WEIGHT_FC_DMEMORY_ADDRESS = 2;
	localparam [31:0] mac_package_PANDA_WEIGHT_FC_MEMORY_N = 3;
	always @(*) begin : streamer_config
		trans_size = 1'sb0;
		base_address_address = 1'sb0;
		out_trans_size = 1'sb0;
		out_base_address_data = 1'sb0;
		base_address_data = 1'sb0;
		accelerator_memory_select = mac_package_PANDA_FSM_SEL_NULL;
		case (curr_state)
			32'd1: begin
				trans_size = reg_file_i[544+:32];
				base_address_address = reg_file_i[704+:32];
				base_address_data = reg_file_i[512+:32];
				accelerator_memory_select = mac_package_PANDA_FSM_SEL_CONFIG_MEMORY;
			end
			32'd2: begin
				trans_size = reg_file_i[416+:32];
				base_address_address = reg_file_i[640+:32];
				base_address_data = reg_file_i[384+:32];
				accelerator_memory_select = mac_package_PANDA_FSM_SEL_INSTRUCTION_MEMORY;
			end
			32'd3: begin
				trans_size = reg_file_i[864+:32];
				base_address_address = reg_file_i[896+:32];
				base_address_data = reg_file_i[832+:32];
				accelerator_memory_select = mac_package_PANDA_FSM_SEL_LUT_MEMORY;
			end
			32'd4: begin
				trans_size = reg_file_i[960+:32];
				base_address_address = reg_file_i[992+:32];
				base_address_data = reg_file_i[928+:32];
				accelerator_memory_select = mac_package_PANDA_FSM_SEL_SPARSITY_MEMORY;
			end
			32'd7: begin
				trans_size = reg_file_i[480+:32];
				base_address_address = reg_file_i[672+:32];
				base_address_data = reg_file_i[448+:32];
				accelerator_memory_select = mac_package_PANDA_FSM_SEL_ACTIVATION_MEMORY;
			end
			32'd5: begin
				trans_size = reg_file_i[288+:32];
				base_address_address = reg_file_i[576+:32];
				base_address_data = reg_file_i[256+:32];
				accelerator_memory_select = mac_package_PANDA_FSM_SEL_WEIGHT_CONV_MEMORY;
			end
			32'd6: begin
				trans_size = reg_file_i[352+:32];
				base_address_address = reg_file_i[608+:32];
				base_address_data = reg_file_i[320+:32];
				accelerator_memory_select = mac_package_PANDA_FSM_SEL_WEIGHT_FC_MEMORY;
			end
			32'd8: begin
				out_trans_size = reg_file_i[768+:32];
				out_base_address_data = reg_file_i[736+:32];
			end
			32'd9: begin
				out_trans_size = reg_file_i[768+:32];
				out_base_address_data = reg_file_i[736+:32];
				if ((count_nb_tile != 0) && (count_nb_tile < nb_tile))
					if ((load_next_param_tile == 0) && ((flags_engine_i[15-:3] == 1) || (flags_engine_i[15-:3] == 0))) begin
						if (flags_engine_i[4] == 0)
							trans_size = 0;
						else
							trans_size = flags_engine_i[12-:8] << 2;
						base_address_address = reg_file_i[992+:32] + (count_nb_tile * (flags_engine_i[12-:8] << 4));
						base_address_data = reg_file_i[928+:32] + (count_nb_tile * (flags_engine_i[12-:8] << 4));
						accelerator_memory_select = mac_package_PANDA_FSM_SEL_SPARSITY_MEMORY;
					end
					else if ((load_next_param_tile == 1) && (flags_engine_i[15-:3] == 1)) begin
						trans_size = flags_engine_i[47-:16] >> 2;
						base_address_address = reg_file_i[576+:32] + (count_nb_tile * flags_engine_i[47-:16]);
						base_address_data = reg_file_i[256+:32] + (count_nb_tile * flags_engine_i[47-:16]);
						accelerator_memory_select = mac_package_PANDA_FSM_SEL_WEIGHT_CONV_MEMORY;
					end
					else if ((load_next_param_tile == 1) && (flags_engine_i[15-:3] == 0)) begin
						trans_size = flags_engine_i[47-:16] >> 2;
						base_address_address = reg_file_i[608+:32] + (count_nb_tile * flags_engine_i[47-:16]);
						base_address_data = reg_file_i[320+:32] + (count_nb_tile * flags_engine_i[47-:16]);
						accelerator_memory_select = mac_package_PANDA_FSM_SEL_WEIGHT_FC_MEMORY;
					end
			end
		endcase
	end
	always @(posedge clk_i or negedge rst_ni) begin : packet_counter
		if (~rst_ni)
			packet_cnt <= 1'sb0;
		else if (clear_i || packet_counter_clear)
			packet_cnt <= 1'sb0;
		else if (packet_counter_enable)
			packet_cnt <= packet_cnt + 1;
	end
	always @(posedge clk_i or negedge rst_ni) begin : packet_counter_out
		if (~rst_ni)
			out_packet_cnt <= 1'sb0;
		else if (clear_i || out_packet_counter_clear)
			out_packet_cnt <= 1'sb0;
		else if (out_packet_counter_enable)
			out_packet_cnt <= out_packet_cnt + 1;
	end
endmodule
