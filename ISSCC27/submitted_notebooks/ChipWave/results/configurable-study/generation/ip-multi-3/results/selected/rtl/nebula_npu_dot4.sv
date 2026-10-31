// Four-lane signed INT8 dot product using the supplied accumulating PEs.
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
    typedef enum logic [1:0] {IDLE, REDUCE, DELAY, RESPONSE} state_t;
    state_t state;
    logic accept;
    logic pe_reset;
    wire signed [31:0] lane_result [0:3];
    wire [3:0] lane_valid;

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign accept = req_valid && req_ready;
    assign pe_reset = !rst_n || kill;

    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        gemm_pe pe (
            .clk(clk),
            .rst(pe_reset),
            // Every non-accepting edge clears the accumulator and sticky
            // result_valid. On the reduction edge we read the old values.
            .clear(!accept),
            .a_in(req_a[8*lane +: 8]),
            .b_in(req_b[8*lane +: 8]),
            .a_valid(accept),
            .b_valid(accept),
            .a_last(accept),
            .b_last(accept),
            .a_out(),
            .b_out(),
            .a_out_valid(),
            .b_out_valid(),
            .a_out_last(),
            .b_out_last(),
            .accumulator(lane_result[lane]),
            .result_valid(lane_valid[lane])
        );
    end

    // Reset and kill are sampled on rising edges, as are the PE controls.
    // Output handshake signals are also masked immediately while asserted.
    always_ff @(posedge clk) begin
        if (!rst_n || kill) begin
            state <= IDLE;
            rsp_data <= 32'b0;
        end else begin
            case (state)
                IDLE: if (accept) state <= REDUCE;
                REDUCE: if (&lane_valid) begin
                    // Each PE already sign-extends its product to INT32.
                    rsp_data <= (lane_result[0] + lane_result[1]) +
                                (lane_result[2] + lane_result[3]);
                    state <= DELAY;
                end
                DELAY: state <= RESPONSE;
                RESPONSE: if (rsp_ready) state <= IDLE;
                default: begin
                    state <= IDLE;
                    rsp_data <= 32'b0;
                end
            endcase
        end
    end
endmodule
