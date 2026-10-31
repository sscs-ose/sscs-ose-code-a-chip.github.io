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
    wire live = rst_n && !kill;
    wire pe_execute = live && (state == EXECUTE);
    wire pe_clear = !live || (state != EXECUTE);
    wire signed [31:0] lane_sum [0:3];
    wire [3:0] lane_valid;

    assign req_ready = live && (state == IDLE);
    assign rsp_valid = live && (state == RESPONSE);

    // At acceptance (edge n), every PE is cleared while operands are sampled.
    // At n+1, all four PEs perform exactly one signed INT8 multiply-accumulate.
    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        gemm_pe pe (
            .clk(clk),
            .rst(!rst_n || kill),
            .clear(pe_clear),
            .a_in(sampled_a[8*lane +: 8]),
            .b_in(sampled_b[8*lane +: 8]),
            .a_valid(pe_execute),
            .b_valid(pe_execute),
            .a_last(pe_execute),
            .b_last(pe_execute),
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
                    if (req_valid && req_ready) begin
                        sampled_a <= req_a;
                        sampled_b <= req_b;
                        state <= EXECUTE;
                    end
                end
                EXECUTE: state <= REDUCE;
                REDUCE: begin
                    // PE outputs are already sign-extended to 32 bits. Read
                    // them at n+2, concurrently with clearing the sticky PEs.
                    if (&lane_valid) begin
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
