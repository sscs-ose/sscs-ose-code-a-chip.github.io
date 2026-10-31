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
    typedef enum logic [1:0] {IDLE, PRODUCTS, SUM, RESPONSE} state_t;
    state_t state;
    logic signed [15:0] product [0:3];
    wire signed [31:0] widened [0:3];
    logic signed [31:0] sum_q;
    logic [31:0] result_q;

    for (genvar lane = 0; lane < 4; lane++) begin : widen_products
        assign widened[lane] = {{16{product[lane][15]}}, product[lane]};
    end

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = (rst_n && !kill) ? result_q : 32'b0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            sum_q <= 32'sd0;
            result_q <= 32'b0;
            for (integer lane = 0; lane < 4; lane++)
                product[lane] <= 16'sd0;
        end else if (kill) begin
            state <= IDLE;
            result_q <= 32'b0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid) begin
                        for (integer lane = 0; lane < 4; lane++)
                            product[lane] <= $signed(req_a[lane*8 +: 8])
                                           * $signed(req_b[lane*8 +: 8]);
                        state <= PRODUCTS;
                    end
                end
                PRODUCTS: begin
                    sum_q <= widened[0] + widened[1] + widened[2] + widened[3];
                    state <= SUM;
                end
                SUM: begin
                    result_q <= sum_q;
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
