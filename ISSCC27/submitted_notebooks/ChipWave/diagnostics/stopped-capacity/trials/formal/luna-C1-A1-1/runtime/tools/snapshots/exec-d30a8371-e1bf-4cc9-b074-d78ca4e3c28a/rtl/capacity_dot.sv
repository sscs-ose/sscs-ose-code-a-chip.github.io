module capacity_dot (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        cmd_valid,
    output logic        cmd_ready,
    input  logic [7:0]  cmd_id,
    input  logic [6:0]  cmd_len,
    input  logic        data_valid,
    output logic        data_ready,
    input  logic [7:0]  data_id,
    input  logic [31:0] data_a,
    input  logic [31:0] data_b,
    input  logic        cancel_valid,
    input  logic [7:0]  cancel_id,
    output logic        rsp_valid,
    input  logic        rsp_ready,
    output logic [7:0]  rsp_id,
    output logic [31:0] rsp_data
);
    logic active;
    logic [7:0] live_id;
    logic [6:0] length_left;
    logic [31:0] accumulator;
    logic result_valid;
    logic [7:0] result_id;
    logic [31:0] result_data;
    logic matching_cancel;
    typedef enum logic [1:0] {BEAT_IDLE, BEAT_PAIR, BEAT_SUM, BEAT_ACC} beat_phase_t;
    beat_phase_t beat_phase;
    logic signed [15:0] product_q [0:3];
    logic signed [15:0] lane_product [0:3];
    logic signed [16:0] pair_q [0:1];
    logic signed [17:0] beat_sum_q;
    logic final_beat_q;
    logic [2:0] useful_lanes;

    assign matching_cancel = cancel_valid && active && (cancel_id == live_id);
    assign cmd_ready = rst_n && !matching_cancel && !active;
    // Stale or canceled trailing beats are consumed and ignored.  Beats for
    // the current command are also accepted immediately, one beat per cycle.
    assign data_ready = rst_n && !matching_cancel &&
                        (!active || (data_id != live_id) ||
                         ((beat_phase == BEAT_IDLE) && !result_valid));
    assign rsp_valid = rst_n && !matching_cancel && result_valid;
    assign rsp_id = result_id;
    assign rsp_data = result_data;

    always_comb begin
        useful_lanes = (length_left >= 4) ? 3'd4 : length_left[2:0];
        for (int lane = 0; lane < 4; lane++) begin
            lane_product[lane] = $signed(data_a[8*lane +: 8])
                               * $signed(data_b[8*lane +: 8]);
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active       <= 1'b0;
            live_id      <= 8'b0;
            length_left  <= 7'b0;
            accumulator  <= 32'b0;
            beat_phase   <= BEAT_IDLE;
            for (int lane = 0; lane < 4; lane++) product_q[lane] <= 16'sd0;
            pair_q[0]    <= 17'sd0;
            pair_q[1]    <= 17'sd0;
            beat_sum_q   <= 18'sd0;
            final_beat_q <= 1'b0;
            result_valid <= 1'b0;
            result_id    <= 8'b0;
            result_data  <= 32'b0;
        end else if (matching_cancel) begin
            active       <= 1'b0;
            length_left  <= 7'b0;
            accumulator  <= 32'b0;
            beat_phase   <= BEAT_IDLE;
            result_valid <= 1'b0;
        end else begin
            if (result_valid && rsp_ready) begin
                result_valid <= 1'b0;
                active <= 1'b0;
            end

            case (beat_phase)
                BEAT_PAIR: begin
                    pair_q[0] <= $signed({product_q[0][15], product_q[0]})
                               + $signed({product_q[1][15], product_q[1]});
                    pair_q[1] <= $signed({product_q[2][15], product_q[2]})
                               + $signed({product_q[3][15], product_q[3]});
                    beat_phase <= BEAT_SUM;
                end
                BEAT_SUM: begin
                    beat_sum_q <= $signed({pair_q[0][16], pair_q[0]})
                                + $signed({pair_q[1][16], pair_q[1]});
                    beat_phase <= BEAT_ACC;
                end
                BEAT_ACC: begin
                    accumulator <= accumulator + {{14{beat_sum_q[17]}}, beat_sum_q};
                    if (final_beat_q) begin
                        result_valid <= 1'b1;
                        result_id    <= live_id;
                        result_data  <= accumulator + {{14{beat_sum_q[17]}}, beat_sum_q};
                    end
                    beat_phase <= BEAT_IDLE;
                end
                default: begin end
            endcase

            if (cmd_valid && cmd_ready) begin
                active      <= 1'b1;
                live_id     <= cmd_id;
                length_left <= cmd_len;
                accumulator <= 32'b0;
                result_valid <= 1'b0;
            end

            if (data_valid && data_ready && active && (data_id == live_id) && !result_valid) begin
                for (int lane = 0; lane < 4; lane++)
                    product_q[lane] <= (lane < useful_lanes) ? lane_product[lane] : 16'sd0;
                final_beat_q <= (length_left <= 4);
                beat_phase <= BEAT_PAIR;
                if (length_left <= 4)
                    length_left  <= 0;
                else
                    length_left <= length_left - 4;
            end
        end
    end
endmodule
