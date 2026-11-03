module lb_feedback (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_commit,
    input  wire [15:0]  cfg_map,
    input  wire [9:0]   cfg_bad,
    output reg          cfg_locked,
    output reg          cfg_error,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire         in_bank,
    input  wire [2:0]   in_word,
    input  wire [63:0]  in_data,
    input  wire         cmd_valid,
    output wire         cmd_ready,
    input  wire [6:0]   cmd_k,
    input  wire         cmd_in_bank,
    input  wire         cmd_out_bank,
    output wire         out_valid,
    input  wire         out_ready,
    output wire [63:0]  out_data,
    output wire         out_last,
    output wire         out_bank,
    output wire         out_error,
    output reg  [9:0]   phy_req_valid,
    input  wire [9:0]   phy_req_ready,
    output reg  [159:0] phy_req_addr,
    output reg  [9:0]   phy_req_bank,
    input  wire [9:0]   phy_rsp_valid,
    input  wire [319:0] phy_rsp_rdata,
    input  wire [9:0]   phy_rsp_error
);
    reg [3:0] target [0:7];
    reg [3:0] candidate [0:7];
    reg [9:0] used_targets;
    reg legal_map;
    always_comb begin
        used_targets = 10'b0;
        legal_map = 1'b1;
        for (integer j = 0; j < 8; j = j + 1) begin
            case (cfg_map[2*j +: 2])
                2'd0: candidate[j] = 4'(j);
                2'd1: candidate[j] = 4'd8;
                2'd2: candidate[j] = 4'd9;
                default: begin
                    candidate[j] = 4'(j);
                    legal_map = 1'b0;
                end
            endcase
            if (used_targets[candidate[j]] || cfg_bad[candidate[j]])
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
    reg signed [31:0] accumulator [0:7];
    wire signed [15:0] product [0:7][0:3];
    wire signed [31:0] tile_sum [0:7];
    wire consume = active && (&row_valid[consume_tile[1:0]]);
    wire start_job = cmd_valid && cmd_ready;
    wire pop_job = out_valid && out_ready && out_last;
    reg response_error;

    assign in_ready = !(active && in_bank == active_in_bank);
    assign cmd_ready = cfg_locked && !active && !output_busy[cmd_out_bank]
                     && (cmd_k == 7'd4 || cmd_k == 7'd16 || cmd_k == 7'd64);
    assign out_bank = order_bank[order_head];
    assign out_valid = (order_count != 0) && output_done[out_bank];
    assign out_data = output_bank[out_bank][64*output_word +: 64];
    assign out_last = (output_word == 2'd3);
    assign out_error = output_error[out_bank];

    for (genvar j = 0; j < 8; j = j + 1) begin : mac_lane
        for (genvar k = 0; k < 4; k = k + 1) begin : mac_position
            assign product[j][k] =
                $signed(input_bank[active_in_bank][32*consume_tile[3:0]+8*k +: 8]) *
                $signed(weight_row[consume_tile[1:0]][32*j+8*k +: 8]);
        end
        assign tile_sum[j] = {{16{product[j][0][15]}}, product[j][0]}
                           + {{16{product[j][1][15]}}, product[j][1]}
                           + {{16{product[j][2][15]}}, product[j][2]}
                           + {{16{product[j][3][15]}}, product[j][3]};
    end

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

    always @(posedge clk) begin
        if (!rst_n) begin
            cfg_locked <= 1'b0;
            cfg_error <= 1'b0;
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
                accumulator[j] <= 32'sd0;
            end
            for (integer r = 0; r < 4; r = r + 1)
                row_valid[r] <= 8'b0;
        end else begin
            if (cfg_commit && !cfg_locked) begin
                cfg_error <= !legal_map;
                if (legal_map) begin
                    cfg_locked <= 1'b1;
                    for (integer j = 0; j < 8; j = j + 1)
                        target[j] <= candidate[j];
                end
            end
            if (in_valid && in_ready)
                input_bank[in_bank][64*in_word +: 64] <= in_data;

            case ({start_job, pop_job})
                2'b10: order_count <= order_count + 2'd1;
                2'b01: order_count <= order_count - 2'd1;
                default: ;
            endcase
            if (out_valid && out_ready) begin
                output_word <= output_word + 2'd1;
                if (out_last) begin
                    output_busy[out_bank] <= 1'b0;
                    output_done[out_bank] <= 1'b0;
                    order_head <= !order_head;
                end
            end
            if (start_job) begin
                active <= 1'b1;
                active_in_bank <= cmd_in_bank;
                active_out_bank <= cmd_out_bank;
                job_error <= 1'b0;
                tiles <= cmd_k[6:2];
                consume_tile <= 5'b0;
                output_busy[cmd_out_bank] <= 1'b1;
                output_done[cmd_out_bank] <= 1'b0;
                order_bank[order_tail] <= cmd_out_bank;
                order_tail <= !order_tail;
                for (integer j = 0; j < 8; j = j + 1) begin
                    issue_tile[j] <= 5'b0;
                    response_tile[j] <= 5'b0;
                    accumulator[j] <= 32'sd0;
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
                        accumulator[j] <= accumulator[j] + tile_sum[j];
                        if (consume_tile + 5'd1 == tiles)
                            output_bank[active_out_bank][32*j +: 32]
                                <= accumulator[j] + tile_sum[j];
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
