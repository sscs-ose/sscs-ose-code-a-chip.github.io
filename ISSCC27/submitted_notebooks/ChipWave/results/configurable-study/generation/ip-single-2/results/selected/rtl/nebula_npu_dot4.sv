// Four-lane signed dot product using the supplied gemm_pe instances.
module nebula_npu_dot4 (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        req_valid,
    output logic        req_ready,
    input  logic [31:0] req_a,
    input  logic [31:0] req_b,
    output logic        rsp_valid,
    input  logic        rsp_ready,
    output logic [31:0] rsp_data,
    input  logic        kill
);
    typedef enum logic [1:0] {IDLE, EXECUTE, REDUCE, RESPONSE} state_t;
    state_t state;
    logic [31:0] sampled_a, sampled_b;
    wire signed [31:0] lane_sum [0:3];
    wire [3:0] lane_valid;
    wire pe_reset = !rst_n || kill;
    // IDLE clears on the acceptance edge. REDUCE clears after reading the
    // completed accumulators, so neither stalls nor later requests accumulate.
    wire pe_clear = (state != EXECUTE);
    wire pe_enable = (state == EXECUTE) && rst_n && !kill;

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);

    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        gemm_pe pe (
            .clk(clk),
            .rst(pe_reset),
            .clear(pe_clear),
            .a_in(sampled_a[8*lane +: 8]),
            .b_in(sampled_b[8*lane +: 8]),
            .a_valid(pe_enable),
            .b_valid(pe_enable),
            .a_last(pe_enable),
            .b_last(pe_enable),
            .a_out(),
            .b_out(),
            .a_out_valid(),
            .b_out_valid(),
            .a_out_last(),
            .b_out_last(),
            .accumulator(lane_sum[lane]),
            .result_valid(lane_valid[lane])
        );
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            sampled_a <= '0;
            sampled_b <= '0;
            rsp_data <= '0;
        end else if (kill) begin
            state <= IDLE;
            sampled_a <= '0;
            sampled_b <= '0;
            rsp_data <= '0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid) begin
                        sampled_a <= req_a;
                        sampled_b <= req_b;
                        state <= EXECUTE;
                    end
                end
                EXECUTE: state <= REDUCE;
                REDUCE: begin
                    if (&lane_valid) begin
                        // Each PE result is already signed and widened to 32 bits.
                        rsp_data <= (lane_sum[0] + lane_sum[1])
                                  + (lane_sum[2] + lane_sum[3]);
                        state <= RESPONSE;
                    end
                end
                RESPONSE: begin
                    if (rsp_ready)
                        state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
