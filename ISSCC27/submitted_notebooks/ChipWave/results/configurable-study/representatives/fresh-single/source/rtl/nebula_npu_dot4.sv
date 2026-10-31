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
    typedef enum logic [1:0] {IDLE, REDUCE, PUBLISH, RESPONSE} state_t;
    state_t state;
    wire signed [15:0] product [0:3];
    logic signed [15:0] product_q [0:3];
    logic signed [31:0] pair_lo_q, pair_hi_q;
    logic signed [31:0] result_q;

    // Four independent signed INT8 multipliers, sampled only on acceptance.
    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        wire signed [7:0] a = req_a[8*lane +: 8];
        wire signed [7:0] b = req_b[8*lane +: 8];
        assign product[lane] = a * b;
    end

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = (rst_n && !kill) ? result_q : 32'b0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            for (integer i = 0; i < 4; i = i + 1)
                product_q[i] <= '0;
            pair_lo_q <= '0;
            pair_hi_q <= '0;
            result_q <= '0;
        end else if (kill) begin
            state <= IDLE;
            for (integer i = 0; i < 4; i = i + 1)
                product_q[i] <= '0;
            pair_lo_q <= '0;
            pair_hi_q <= '0;
            result_q <= '0;
        end else begin
            case (state)
                IDLE: if (req_valid) begin
                    for (integer i = 0; i < 4; i = i + 1)
                        product_q[i] <= product[i];
                    state <= REDUCE;
                end
                // Sign-extend each product before performing any addition.
                REDUCE: begin
                    pair_lo_q <= $signed({{16{product_q[0][15]}}, product_q[0]})
                               + $signed({{16{product_q[1][15]}}, product_q[1]});
                    pair_hi_q <= $signed({{16{product_q[2][15]}}, product_q[2]})
                               + $signed({{16{product_q[3][15]}}, product_q[3]});
                    state <= PUBLISH;
                end
                // Acceptance is edge n; this edge is n+2.
                PUBLISH: begin
                    result_q <= pair_lo_q + pair_hi_q;
                    state <= RESPONSE;
                end
                RESPONSE: if (rsp_ready)
                    state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
