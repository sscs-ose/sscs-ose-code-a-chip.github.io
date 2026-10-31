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
    logic [31:0] a_saved, b_saved;
    logic [31:0] response_data;
    wire enabled = rst_n && !kill;
    wire pe_reset = !rst_n || kill;
    wire pe_clear = (state == IDLE);
    wire pe_valid = enabled && (state == EXECUTE);
    wire signed [31:0] lane_sum [0:3];
    wire [3:0] lane_done;

    assign req_ready = enabled && (state == IDLE);
    assign rsp_valid = enabled && (state == RESPONSE);
    assign rsp_data = enabled ? response_data : 32'd0;

    // Each idle edge clears all accumulators, including the acceptance edge.
    // The captured operands are accumulated exactly once, on edge n+1.
    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        gemm_pe pe (
            .clk(clk),
            .rst(pe_reset),
            .clear(pe_clear),
            .a_in(a_saved[8*lane +: 8]),
            .b_in(b_saved[8*lane +: 8]),
            .a_valid(pe_valid),
            .b_valid(pe_valid),
            .a_last(pe_valid),
            .b_last(pe_valid),
            .a_out(),
            .b_out(),
            .a_out_valid(),
            .b_out_valid(),
            .a_out_last(),
            .b_out_last(),
            .accumulator(lane_sum[lane]),
            .result_valid(lane_done[lane])
        );
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            a_saved <= '0;
            b_saved <= '0;
            response_data <= '0;
        end else if (kill) begin
            state <= IDLE;
            a_saved <= '0;
            b_saved <= '0;
            response_data <= '0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid) begin
                        a_saved <= req_a;
                        b_saved <= req_b;
                        state <= EXECUTE;
                    end
                end
                EXECUTE: state <= REDUCE;
                REDUCE: begin
                    if (&lane_done) begin
                        // PE products have already been sign extended to 32 bits.
                        response_data <= (lane_sum[0] + lane_sum[1])
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
