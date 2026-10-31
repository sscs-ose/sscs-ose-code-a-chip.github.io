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
    typedef enum logic [1:0] {IDLE, EXECUTE, REDUCE, RESPOND} state_t;
    state_t state;
    logic [31:0] operand_a, operand_b;
    wire pe_reset = !rst_n || kill;
    // Clear on acceptance as well as on response retirement. The PE's
    // synchronous clear must precede the edge that performs the product.
    wire pe_clear = (state == IDLE) || (state == RESPOND);
    wire pe_enable = rst_n && !kill && (state == EXECUTE);
    wire signed [31:0] lane_sum [0:3];
    wire [3:0] lane_valid;
    wire signed [31:0] dot_sum =
        (lane_sum[0] + lane_sum[1]) + (lane_sum[2] + lane_sum[3]);

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPOND);

    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        // Each unchanged PE widens its signed INT8 product to INT32 before
        // accumulation; the adapter reduces only those INT32 results.
        gemm_pe pe (
            .clk(clk),
            .rst(pe_reset),
            .clear(pe_clear),
            .a_in(operand_a[8*lane +: 8]),
            .b_in(operand_b[8*lane +: 8]),
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
            operand_a <= '0;
            operand_b <= '0;
            rsp_data <= '0;
        end else if (kill) begin
            state <= IDLE;
            operand_a <= '0;
            operand_b <= '0;
            rsp_data <= '0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid) begin
                        operand_a <= req_a;
                        operand_b <= req_b;
                        state <= EXECUTE; // Acceptance edge n.
                    end
                end
                EXECUTE: state <= REDUCE; // PEs compute on edge n+1.
                REDUCE: begin
                    if (&lane_valid) begin
                        rsp_data <= dot_sum;
                        state <= RESPOND; // Result appears after edge n+2.
                    end
                end
                RESPOND: begin
                    if (rsp_ready)
                        state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
