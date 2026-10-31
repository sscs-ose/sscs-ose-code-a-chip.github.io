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
    logic [31:0] operands_a, operands_b;
    logic pe_run, pe_clear;
    wire signed [31:0] lane_result [0:3];
    wire signed [31:0] pair_lo, pair_hi;

    // Suppress both handshakes immediately during reset or cancellation.
    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign pe_run = rst_n && !kill && (state == EXECUTE);
    // Clear on acceptance and after execution. At REDUCE's edge the adapter
    // reads the previous PE accumulators while the PEs clear synchronously.
    assign pe_clear = (state != EXECUTE);

    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        gemm_pe pe (
            .clk(clk),
            .rst(!rst_n || kill),
            .clear(pe_clear),
            .a_in(operands_a[8*lane +: 8]),
            .b_in(operands_b[8*lane +: 8]),
            .a_valid(pe_run),
            .b_valid(pe_run),
            .a_last(pe_run),
            .b_last(pe_run),
            .a_out(),
            .b_out(),
            .a_out_valid(),
            .b_out_valid(),
            .a_out_last(),
            .b_out_last(),
            .accumulator(lane_result[lane]),
            .result_valid()
        );
    end

    // Each PE already sign-extends its signed INT8 product to 32 bits.
    assign pair_lo = lane_result[0] + lane_result[1];
    assign pair_hi = lane_result[2] + lane_result[3];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            operands_a <= '0;
            operands_b <= '0;
            rsp_data <= '0;
        end else if (kill) begin
            state <= IDLE;
            operands_a <= '0;
            operands_b <= '0;
            rsp_data <= '0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid && req_ready) begin
                        operands_a <= req_a;
                        operands_b <= req_b;
                        state <= EXECUTE;
                    end
                end
                EXECUTE: state <= REDUCE;
                REDUCE: begin
                    rsp_data <= pair_lo + pair_hi;
                    state <= RESPONSE;
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
