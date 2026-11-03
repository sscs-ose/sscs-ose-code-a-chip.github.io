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
    logic signed [15:0] product0, product1, product2, product3;
    logic [31:0] result;

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = (rst_n && !kill) ? result : 32'b0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            result <= 32'b0;
        end else if (kill) begin
            state <= IDLE;
            result <= 32'b0;
        end else begin
            case (state)
                IDLE: if (req_valid) begin
                    product0 <= $signed(req_a[7:0]) * $signed(req_b[7:0]);
                    product1 <= $signed(req_a[15:8]) * $signed(req_b[15:8]);
                    product2 <= $signed(req_a[23:16]) * $signed(req_b[23:16]);
                    product3 <= $signed(req_a[31:24]) * $signed(req_b[31:24]);
                    state <= REDUCE;
                end
                REDUCE: begin
                    result <= {{16{product0[15]}}, product0}
                            + {{16{product1[15]}}, product1}
                            + {{16{product2[15]}}, product2}
                            + {{16{product3[15]}}, product3};
                    state <= DELAY;
                end
                DELAY: state <= RESPONSE;
                RESPONSE: if (rsp_ready) state <= IDLE;
                default: begin
                    state <= IDLE;
                    result <= 32'b0;
                end
            endcase
        end
    end
endmodule
