module lb_feedback (
    input wire clk,
    input wire rst_n,
    input wire cfg_commit,
    input wire [15:0] cfg_map,
    input wire [9:0] cfg_bad,
    output wire cfg_locked,
    output wire cfg_error,
    input wire in_valid,
    output wire in_ready,
    input wire in_bank,
    input wire [2:0] in_word,
    input wire [63:0] in_data,
    input wire cmd_valid,
    output wire cmd_ready,
    input wire [6:0] cmd_k,
    input wire cmd_in_bank,
    input wire cmd_out_bank,
    output wire out_valid,
    input wire out_ready,
    output wire [63:0] out_data,
    output wire out_last,
    output wire out_bank,
    output wire out_error,
    output wire [9:0] phy_req_valid,
    input wire [9:0] phy_req_ready,
    output wire [159:0] phy_req_addr,
    output wire [9:0] phy_req_bank,
    input wire [9:0] phy_rsp_valid,
    input wire [319:0] phy_rsp_rdata,
    input wire [9:0] phy_rsp_error
);
    wire link_clk;
    wire link_rst_n;
    wire link_cfg_commit;
    wire [15:0] link_cfg_map;
    wire [9:0] link_cfg_bad;
    wire link_cfg_locked;
    wire link_cfg_error;
    wire link_in_valid;
    wire link_in_ready;
    wire link_in_bank;
    wire [2:0] link_in_word;
    wire [63:0] link_in_data;
    wire link_cmd_valid;
    wire link_cmd_ready;
    wire [6:0] link_cmd_k;
    wire link_cmd_in_bank;
    wire link_cmd_out_bank;
    wire link_out_valid;
    wire link_out_ready;
    wire [63:0] link_out_data;
    wire link_out_last;
    wire link_out_bank;
    wire link_out_error;
    wire [31:0] fold_x;
    wire [255:0] fold_w;
    wire fold_start;
    wire fold_consume;
    wire [255:0] fold_next;

    lb_l0 L0 (
        .clk(link_clk),
        .rst_n(link_rst_n),
        .cfg_commit(link_cfg_commit),
        .cfg_map(link_cfg_map),
        .cfg_bad(link_cfg_bad),
        .cfg_locked(link_cfg_locked),
        .cfg_error(link_cfg_error),
        .in_valid(link_in_valid),
        .in_ready(link_in_ready),
        .in_bank(link_in_bank),
        .in_word(link_in_word),
        .in_data(link_in_data),
        .cmd_valid(link_cmd_valid),
        .cmd_ready(link_cmd_ready),
        .cmd_k(link_cmd_k),
        .cmd_in_bank(link_cmd_in_bank),
        .cmd_out_bank(link_cmd_out_bank),
        .out_valid(link_out_valid),
        .out_ready(link_out_ready),
        .out_data(link_out_data),
        .out_last(link_out_last),
        .out_bank(link_out_bank),
        .out_error(link_out_error),
        .phy_req_valid(phy_req_valid),
        .phy_req_ready(phy_req_ready),
        .phy_req_addr(phy_req_addr),
        .phy_req_bank(phy_req_bank),
        .phy_rsp_valid(phy_rsp_valid),
        .phy_rsp_rdata(phy_rsp_rdata),
        .phy_rsp_error(phy_rsp_error),
        .fold_x(fold_x),
        .fold_w(fold_w),
        .fold_start(fold_start),
        .fold_consume(fold_consume),
        .fold_next(fold_next)
    );
    lb_l1 L1 (
        .clk(clk),
        .rst_n(rst_n),
        .cfg_commit(cfg_commit),
        .cfg_map(cfg_map),
        .cfg_bad(cfg_bad),
        .cfg_locked(cfg_locked),
        .cfg_error(cfg_error),
        .in_valid(in_valid),
        .in_ready(in_ready),
        .in_bank(in_bank),
        .in_word(in_word),
        .in_data(in_data),
        .cmd_valid(cmd_valid),
        .cmd_ready(cmd_ready),
        .cmd_k(cmd_k),
        .cmd_in_bank(cmd_in_bank),
        .cmd_out_bank(cmd_out_bank),
        .out_valid(out_valid),
        .out_ready(out_ready),
        .out_data(out_data),
        .out_last(out_last),
        .out_bank(out_bank),
        .out_error(out_error),
        .link_clk(link_clk),
        .link_rst_n(link_rst_n),
        .link_cfg_commit(link_cfg_commit),
        .link_cfg_map(link_cfg_map),
        .link_cfg_bad(link_cfg_bad),
        .link_cfg_locked(link_cfg_locked),
        .link_cfg_error(link_cfg_error),
        .link_in_valid(link_in_valid),
        .link_in_ready(link_in_ready),
        .link_in_bank(link_in_bank),
        .link_in_word(link_in_word),
        .link_in_data(link_in_data),
        .link_cmd_valid(link_cmd_valid),
        .link_cmd_ready(link_cmd_ready),
        .link_cmd_k(link_cmd_k),
        .link_cmd_in_bank(link_cmd_in_bank),
        .link_cmd_out_bank(link_cmd_out_bank),
        .link_out_valid(link_out_valid),
        .link_out_ready(link_out_ready),
        .link_out_data(link_out_data),
        .link_out_last(link_out_last),
        .link_out_bank(link_out_bank),
        .link_out_error(link_out_error),
        .fold_x(fold_x),
        .fold_w(fold_w),
        .fold_start(fold_start),
        .fold_consume(fold_consume),
        .fold_next(fold_next)
    );
endmodule

module lb_l0 (
    input wire clk,
    input wire rst_n,
    input wire cfg_commit,
    input wire [15:0] cfg_map,
    input wire [9:0] cfg_bad,
    output wire cfg_locked,
    output wire cfg_error,
    input wire in_valid,
    output wire in_ready,
    input wire in_bank,
    input wire [2:0] in_word,
    input wire [63:0] in_data,
    input wire cmd_valid,
    output wire cmd_ready,
    input wire [6:0] cmd_k,
    input wire cmd_in_bank,
    input wire cmd_out_bank,
    output wire out_valid,
    input wire out_ready,
    output wire [63:0] out_data,
    output wire out_last,
    output wire out_bank,
    output wire out_error,
    output reg [9:0] phy_req_valid,
    input wire [9:0] phy_req_ready,
    output reg [159:0] phy_req_addr,
    output reg [9:0] phy_req_bank,
    input wire [9:0] phy_rsp_valid,
    input wire [319:0] phy_rsp_rdata,
    input wire [9:0] phy_rsp_error,
    output wire [31:0] fold_x,
    output wire [255:0] fold_w,
    output wire fold_start,
    output wire fold_consume,
    input wire [255:0] fold_next
);
    wire core_clk;
    wire core_rst_n;
    wire core_cfg_commit;
    wire [15:0] core_cfg_map;
    wire [9:0] core_cfg_bad;
    reg core_cfg_locked;
    reg core_cfg_error;
    wire core_in_valid;
    wire core_in_ready;
    wire core_in_bank;
    wire [2:0] core_in_word;
    wire [63:0] core_in_data;
    wire core_cmd_valid;
    wire core_cmd_ready;
    wire [6:0] core_cmd_k;
    wire core_cmd_in_bank;
    wire core_cmd_out_bank;
    wire core_out_valid;
    wire core_out_ready;
    wire [63:0] core_out_data;
    wire core_out_last;
    wire core_out_bank;
    wire core_out_error;
    wire [255:0] core_fold_next;
    wire [31:0] core_fold_x;
    wire [255:0] core_fold_w;
    wire core_fold_start;
    wire core_fold_consume;

    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_clk (.A(clk), .X(core_clk));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_rst_n (.A(rst_n), .X(core_rst_n));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_cfg_commit (.A(cfg_commit), .X(core_cfg_commit));
    for (genvar b = 0; b < 16; b = b + 1) begin : endpoint_cfg_map
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(cfg_map[b]), .X(core_cfg_map[b]));
    end
    for (genvar b = 0; b < 10; b = b + 1) begin : endpoint_cfg_bad
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(cfg_bad[b]), .X(core_cfg_bad[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_cfg_locked (.A(core_cfg_locked), .X(cfg_locked));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_cfg_error (.A(core_cfg_error), .X(cfg_error));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_in_valid (.A(in_valid), .X(core_in_valid));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_in_ready (.A(core_in_ready), .X(in_ready));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_in_bank (.A(in_bank), .X(core_in_bank));
    for (genvar b = 0; b < 3; b = b + 1) begin : endpoint_in_word
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(in_word[b]), .X(core_in_word[b]));
    end
    for (genvar b = 0; b < 64; b = b + 1) begin : endpoint_in_data
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(in_data[b]), .X(core_in_data[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_cmd_valid (.A(cmd_valid), .X(core_cmd_valid));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_cmd_ready (.A(core_cmd_ready), .X(cmd_ready));
    for (genvar b = 0; b < 7; b = b + 1) begin : endpoint_cmd_k
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(cmd_k[b]), .X(core_cmd_k[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_cmd_in_bank (.A(cmd_in_bank), .X(core_cmd_in_bank));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_cmd_out_bank (.A(cmd_out_bank), .X(core_cmd_out_bank));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_out_valid (.A(core_out_valid), .X(out_valid));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_out_ready (.A(out_ready), .X(core_out_ready));
    for (genvar b = 0; b < 64; b = b + 1) begin : endpoint_out_data
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(core_out_data[b]), .X(out_data[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_out_last (.A(core_out_last), .X(out_last));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_out_bank (.A(core_out_bank), .X(out_bank));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_out_error (.A(core_out_error), .X(out_error));
    for (genvar b = 0; b < 32; b = b + 1) begin : endpoint_fold_x
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(core_fold_x[b]), .X(fold_x[b]));
    end
    for (genvar b = 0; b < 256; b = b + 1) begin : endpoint_fold_w
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(core_fold_w[b]), .X(fold_w[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_fold_start (.A(core_fold_start), .X(fold_start));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_fold_consume (.A(core_fold_consume), .X(fold_consume));
    for (genvar b = 0; b < 256; b = b + 1) begin : endpoint_fold_next
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(fold_next[b]), .X(core_fold_next[b]));
    end


    reg [3:0] target [0:7];
    reg [3:0] candidate [0:7];
    reg [9:0] used_targets;
    reg legal_map;
    always_comb begin
        used_targets = 10'b0;
        legal_map = 1'b1;
        for (integer j = 0; j < 8; j = j + 1) begin
            case (core_cfg_map[2*j +: 2])
                2'd0: candidate[j] = 4'(j);
                2'd1: candidate[j] = 4'd8;
                2'd2: candidate[j] = 4'd9;
                default: begin
                    candidate[j] = 4'(j);
                    legal_map = 1'b0;
                end
            endcase
            if (used_targets[candidate[j]] || core_cfg_bad[candidate[j]])
                legal_map = 1'b0;
            used_targets[candidate[j]] = 1'b1;
        end
    end

    reg [511:0] input_bank [0:1];
    reg [255:0] output_bank [0:1];
    reg [1:0] output_busy, output_done, output_error;
    reg order_bank [0:1];
    reg order_head, order_tail;
    reg [1:0] order_count;
    reg [1:0] output_word;

    reg active, active_in_bank, active_out_bank, job_error;
    reg [4:0] tiles, consume_tile;
    reg [4:0] issue_tile [0:7];
    reg [4:0] response_tile [0:7];
    // One central four-row queue; a row is reusable only after all eight lanes retire.
    reg [255:0] weight_row [0:3];
    reg [7:0] row_valid [0:3];
    wire consume = active && (&row_valid[consume_tile[1:0]]);
    wire start_job = core_cmd_valid && core_cmd_ready;
    wire pop_job = core_out_valid && core_out_ready && core_out_last;
    reg response_error;

    assign core_fold_x = input_bank[active_in_bank][32*consume_tile[3:0] +: 32];
    assign core_fold_w = weight_row[consume_tile[1:0]];
    assign core_fold_start = start_job;
    assign core_fold_consume = consume;


    assign core_in_ready = !(active && core_in_bank == active_in_bank);
    assign core_cmd_ready = core_cfg_locked && !active && !output_busy[core_cmd_out_bank]
                     && (core_cmd_k == 7'd4 || core_cmd_k == 7'd16 || core_cmd_k == 7'd64);
    assign core_out_bank = order_bank[order_head];
    assign core_out_valid = (order_count != 0) && output_done[core_out_bank];
    assign core_out_data = output_bank[core_out_bank][64*output_word +: 64];
    assign core_out_last = (output_word == 2'd3);
    assign core_out_error = output_error[core_out_bank];

    always @* begin
        phy_req_valid = 10'b0;
        phy_req_addr = 160'b0;
        phy_req_bank = 10'b0;
        response_error = 1'b0;
        for (integer j = 0; j < 8; j = j + 1) begin
            if (active) begin
                if (issue_tile[j] < tiles &&
                    {1'b0, issue_tile[j]} < ({1'b0, consume_tile} + 6'd4)) begin
                    phy_req_valid[target[j]] = 1'b1;
                    phy_req_addr[16*target[j] +: 16] = {12'b0, issue_tile[j][4:1]};
                    phy_req_bank[target[j]] = issue_tile[j][0];
                end
                if (phy_rsp_valid[target[j]] && response_tile[j] < issue_tile[j])
                    response_error = response_error | phy_rsp_error[target[j]];
            end
        end
    end

    always @(posedge core_clk) begin
        if (!core_rst_n) begin
            core_cfg_locked <= 1'b0;
            core_cfg_error <= 1'b0;
            active <= 1'b0;
            active_in_bank <= 1'b0;
            active_out_bank <= 1'b0;
            job_error <= 1'b0;
            tiles <= 5'b0;
            consume_tile <= 5'b0;
            output_busy <= 2'b0;
            output_done <= 2'b0;
            output_error <= 2'b0;
            order_head <= 1'b0;
            order_tail <= 1'b0;
            order_count <= 2'b0;
            output_word <= 2'b0;
            order_bank[0] <= 1'b0;
            order_bank[1] <= 1'b0;
            for (integer j = 0; j < 8; j = j + 1) begin
                target[j] <= 4'(j);
                issue_tile[j] <= 5'b0;
                response_tile[j] <= 5'b0;

            end
            for (integer r = 0; r < 4; r = r + 1)
                row_valid[r] <= 8'b0;
        end else begin
            if (core_cfg_commit && !core_cfg_locked) begin
                core_cfg_error <= !legal_map;
                if (legal_map) begin
                    core_cfg_locked <= 1'b1;
                    for (integer j = 0; j < 8; j = j + 1)
                        target[j] <= candidate[j];
                end
            end
            if (core_in_valid && core_in_ready)
                input_bank[core_in_bank][64*core_in_word +: 64] <= core_in_data;

            case ({start_job, pop_job})
                2'b10: order_count <= order_count + 2'd1;
                2'b01: order_count <= order_count - 2'd1;
                default: ;
            endcase
            if (core_out_valid && core_out_ready) begin
                output_word <= output_word + 2'd1;
                if (core_out_last) begin
                    output_busy[core_out_bank] <= 1'b0;
                    output_done[core_out_bank] <= 1'b0;
                    order_head <= !order_head;
                end
            end
            if (start_job) begin
                active <= 1'b1;
                active_in_bank <= core_cmd_in_bank;
                active_out_bank <= core_cmd_out_bank;
                job_error <= 1'b0;
                tiles <= core_cmd_k[6:2];
                consume_tile <= 5'b0;
                output_busy[core_cmd_out_bank] <= 1'b1;
                output_done[core_cmd_out_bank] <= 1'b0;
                order_bank[order_tail] <= core_cmd_out_bank;
                order_tail <= !order_tail;
                for (integer j = 0; j < 8; j = j + 1) begin
                    issue_tile[j] <= 5'b0;
                    response_tile[j] <= 5'b0;

                end
                for (integer r = 0; r < 4; r = r + 1)
                    row_valid[r] <= 8'b0;
            end
            if (active) begin
                job_error <= job_error | response_error;
                for (integer j = 0; j < 8; j = j + 1) begin
                    if (phy_req_valid[target[j]] && phy_req_ready[target[j]])
                        issue_tile[j] <= issue_tile[j] + 5'd1;
                    if (phy_rsp_valid[target[j]] && response_tile[j] < issue_tile[j]) begin
                        weight_row[response_tile[j][1:0]][32*j +: 32]
                            <= phy_rsp_rdata[32*target[j] +: 32];
                        row_valid[response_tile[j][1:0]][j] <= 1'b1;
                        response_tile[j] <= response_tile[j] + 5'd1;
                    end
                end
                if (consume) begin
                    row_valid[consume_tile[1:0]] <= 8'b0;
                    consume_tile <= consume_tile + 5'd1;
                    for (integer j = 0; j < 8; j = j + 1) begin

                        if (consume_tile + 5'd1 == tiles)
                            output_bank[active_out_bank][32*j +: 32]
                                <= core_fold_next[32*j +: 32];
                    end
                    if (consume_tile + 5'd1 == tiles) begin
                        active <= 1'b0;
                        output_done[active_out_bank] <= 1'b1;
                        output_error[active_out_bank] <= job_error | response_error;
                    end
                end
            end
        end
    end
endmodule

module lb_l1 (
    input wire clk,
    input wire rst_n,
    input wire cfg_commit,
    input wire [15:0] cfg_map,
    input wire [9:0] cfg_bad,
    output wire cfg_locked,
    output wire cfg_error,
    input wire in_valid,
    output wire in_ready,
    input wire in_bank,
    input wire [2:0] in_word,
    input wire [63:0] in_data,
    input wire cmd_valid,
    output wire cmd_ready,
    input wire [6:0] cmd_k,
    input wire cmd_in_bank,
    input wire cmd_out_bank,
    output wire out_valid,
    input wire out_ready,
    output wire [63:0] out_data,
    output wire out_last,
    output wire out_bank,
    output wire out_error,
    output wire link_clk,
    output wire link_rst_n,
    output wire link_cfg_commit,
    output wire [15:0] link_cfg_map,
    output wire [9:0] link_cfg_bad,
    input wire link_cfg_locked,
    input wire link_cfg_error,
    output wire link_in_valid,
    input wire link_in_ready,
    output wire link_in_bank,
    output wire [2:0] link_in_word,
    output wire [63:0] link_in_data,
    output wire link_cmd_valid,
    input wire link_cmd_ready,
    output wire [6:0] link_cmd_k,
    output wire link_cmd_in_bank,
    output wire link_cmd_out_bank,
    input wire link_out_valid,
    output wire link_out_ready,
    input wire [63:0] link_out_data,
    input wire link_out_last,
    input wire link_out_bank,
    input wire link_out_error,
    input wire [31:0] fold_x,
    input wire [255:0] fold_w,
    input wire fold_start,
    input wire fold_consume,
    output wire [255:0] fold_next
);

    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_clk (.A(clk), .X(link_clk));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_rst_n (.A(rst_n), .X(link_rst_n));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_cfg_commit (.A(cfg_commit), .X(link_cfg_commit));
    for (genvar b = 0; b < 16; b = b + 1) begin : endpoint_link_cfg_map
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(cfg_map[b]), .X(link_cfg_map[b]));
    end
    for (genvar b = 0; b < 10; b = b + 1) begin : endpoint_link_cfg_bad
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(cfg_bad[b]), .X(link_cfg_bad[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_link_cfg_locked (.A(link_cfg_locked), .X(cfg_locked));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_link_cfg_error (.A(link_cfg_error), .X(cfg_error));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_in_valid (.A(in_valid), .X(link_in_valid));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_link_in_ready (.A(link_in_ready), .X(in_ready));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_in_bank (.A(in_bank), .X(link_in_bank));
    for (genvar b = 0; b < 3; b = b + 1) begin : endpoint_link_in_word
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(in_word[b]), .X(link_in_word[b]));
    end
    for (genvar b = 0; b < 64; b = b + 1) begin : endpoint_link_in_data
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(in_data[b]), .X(link_in_data[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_cmd_valid (.A(cmd_valid), .X(link_cmd_valid));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_link_cmd_ready (.A(link_cmd_ready), .X(cmd_ready));
    for (genvar b = 0; b < 7; b = b + 1) begin : endpoint_link_cmd_k
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(cmd_k[b]), .X(link_cmd_k[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_cmd_in_bank (.A(cmd_in_bank), .X(link_cmd_in_bank));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_cmd_out_bank (.A(cmd_out_bank), .X(link_cmd_out_bank));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_link_out_valid (.A(link_out_valid), .X(out_valid));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx_link_out_ready (.A(out_ready), .X(link_out_ready));
    for (genvar b = 0; b < 64; b = b + 1) begin : endpoint_link_out_data
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(link_out_data[b]), .X(out_data[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_link_out_last (.A(link_out_last), .X(out_last));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_link_out_bank (.A(link_out_bank), .X(out_bank));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_link_out_error (.A(link_out_error), .X(out_error));
    wire [31:0] core_fold_x;
    wire [255:0] core_fold_w;
    wire core_fold_start;
    wire core_fold_consume;
    wire [255:0] core_fold_next;

    for (genvar b = 0; b < 32; b = b + 1) begin : endpoint_fold_x
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(fold_x[b]), .X(core_fold_x[b]));
    end
    for (genvar b = 0; b < 256; b = b + 1) begin : endpoint_fold_w
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx (.A(fold_w[b]), .X(core_fold_w[b]));
    end
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_fold_start (.A(fold_start), .X(core_fold_start));
    (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_2 rx_fold_consume (.A(fold_consume), .X(core_fold_consume));
    for (genvar b = 0; b < 256; b = b + 1) begin : endpoint_fold_next
        (* keep = 1, dont_touch = 1 *) sky130_fd_sc_hd__buf_4 tx (.A(core_fold_next[b]), .X(fold_next[b]));
    end

    reg signed [31:0] accumulator [0:7];
    wire signed [15:0] product [0:7][0:3];
    wire signed [31:0] tile_sum [0:7];
    for (genvar j = 0; j < 8; j = j + 1) begin : mac_lane
        for (genvar k = 0; k < 4; k = k + 1) begin : mac_position
            assign product[j][k] =
                $signed(core_fold_x[8*k +: 8]) *
                $signed(core_fold_w[32*j+8*k +: 8]);
        end
        assign tile_sum[j] = {{16{product[j][0][15]}}, product[j][0]}
                           + {{16{product[j][1][15]}}, product[j][1]}
                           + {{16{product[j][2][15]}}, product[j][2]}
                           + {{16{product[j][3][15]}}, product[j][3]};
        assign core_fold_next[32*j +: 32] = accumulator[j] + tile_sum[j];
    end

    always @(posedge clk) begin
        for (integer j = 0; j < 8; j = j + 1) begin
            if (!rst_n)
                accumulator[j] <= 32'sd0;
            else if (core_fold_start)
                accumulator[j] <= 32'sd0;
            else if (core_fold_consume)
                accumulator[j] <= core_fold_next[32*j +: 32];
        end
    end
endmodule

// Standalone simulation only; synthesis loads actual Liberty blackboxes first.
`ifndef SYNTHESIS
module sky130_fd_sc_hd__buf_4 (input wire A, output wire X);
    assign X = A;
endmodule
module sky130_fd_sc_hd__buf_2 (input wire A, output wire X);
    assign X = A;
endmodule
`endif
