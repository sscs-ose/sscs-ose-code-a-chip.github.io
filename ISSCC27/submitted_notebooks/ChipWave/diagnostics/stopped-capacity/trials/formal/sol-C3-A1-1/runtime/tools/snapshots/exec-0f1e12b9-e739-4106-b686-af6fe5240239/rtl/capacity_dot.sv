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
    typedef enum logic [2:0] {IDLE, LOAD, PAIR, ACCUM, RESPONSE} phase_t;
    phase_t phase;
    logic [7:0] live_id;
    logic [6:0] remaining;
    logic signed [15:0] product [0:3];
    logic signed [16:0] pair_sum [0:1];
    // 64 * (-128) * (-128) = 1048576, requiring 22 signed bits.
    logic signed [21:0] accumulator;
    logic signed [17:0] beat_sum;
    logic cancel_match;

    assign cancel_match = cancel_valid && phase != IDLE && cancel_id == live_id;
    assign cmd_ready = rst_n && !cancel_match && phase == IDLE;
    // Unknown/trailing IDs are drained. A beat accompanying a new command
    // waits one cycle so command ownership is unambiguous.
    assign data_ready = rst_n && !cancel_match &&
        ((phase == LOAD) ||
         (phase != IDLE && data_id != live_id) ||
         (phase == IDLE && !(cmd_valid && data_id == cmd_id)));
    assign rsp_valid = rst_n && !cancel_match && phase == RESPONSE;
    assign rsp_id = live_id;
    assign rsp_data = {{10{accumulator[21]}}, accumulator};
    assign beat_sum = $signed({pair_sum[0][16], pair_sum[0]})
                    + $signed({pair_sum[1][16], pair_sum[1]});

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= IDLE;
            live_id <= 0;
            remaining <= 0;
            accumulator <= 0;
            for (int lane = 0; lane < 4; lane++) product[lane] <= 0;
            pair_sum[0] <= 0;
            pair_sum[1] <= 0;
        end else if (cancel_match) begin
            phase <= IDLE;
            remaining <= 0;
            accumulator <= 0;
        end else begin
            case (phase)
                IDLE: if (cmd_valid && cmd_ready) begin
                    live_id <= cmd_id;
                    remaining <= cmd_len;
                    accumulator <= 0;
                    phase <= LOAD;
                end
                LOAD: if (data_valid && data_ready && data_id == live_id) begin
                    for (int lane = 0; lane < 4; lane++) begin
                        if (remaining > lane)
                            product[lane] <= $signed(data_a[8*lane +: 8])
                                           * $signed(data_b[8*lane +: 8]);
                        else product[lane] <= 0;
                    end
                    if (remaining > 4) remaining <= remaining - 7'd4;
                    else remaining <= 0;
                    phase <= PAIR;
                end
                PAIR: begin
                    pair_sum[0] <= $signed({product[0][15], product[0]})
                                 + $signed({product[1][15], product[1]});
                    pair_sum[1] <= $signed({product[2][15], product[2]})
                                 + $signed({product[3][15], product[3]});
                    phase <= ACCUM;
                end
                ACCUM: begin
                    accumulator <= accumulator + {{4{beat_sum[17]}}, beat_sum};
                    if (remaining == 0) phase <= RESPONSE;
                    else phase <= LOAD;
                end
                RESPONSE: if (rsp_ready) phase <= IDLE;
                default: phase <= IDLE;
            endcase
        end
    end
endmodule
