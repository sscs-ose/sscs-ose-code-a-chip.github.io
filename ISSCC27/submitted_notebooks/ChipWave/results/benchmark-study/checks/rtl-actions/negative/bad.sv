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
    typedef enum logic [1:0] {IDLE, PRODUCTS, REDUCE, RESPONSE} phase_t;
    phase_t phase;
    logic signed [15:0] product [0:3];
    logic signed [16:0] pair_sum [0:1];

    assign req_ready = rst_n && !kill && (phase == IDLE);
    assign rsp_valid = rst_n && !kill && (phase == RESPONSE);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= IDLE;
            rsp_data <= 32'b0;
            for (int lane = 0; lane < 4; lane++)
                product[lane] <= 16'sd0;
            pair_sum[0] <= 17'sd0;
            pair_sum[1] <= 17'sd0;
        end else if (kill) begin
            phase <= IDLE;
            rsp_data <= 32'b0;
            for (int lane = 0; lane < 4; lane++)
                product[lane] <= 16'sd0;
            pair_sum[0] <= 17'sd0;
            pair_sum[1] <= 17'sd0;
        end else begin
            case (phase)
                IDLE: begin
                    if (req_valid) begin
                        for (int lane = 0; lane < 4; lane++)
                            product[lane] <= $signed(req_a[8*lane +: 8])
                                           * $signed(req_b[8*lane +: 8]);
                        phase <= RESPONSE;
                    end
                end
                PRODUCTS: begin
                    // Widen before addition: two positive products can total 32768.
                    pair_sum[0] <= $signed({product[0][15], product[0]})
                                 + $signed({product[1][15], product[1]});
                    pair_sum[1] <= $signed({product[2][15], product[2]})
                                 + $signed({product[3][15], product[3]});
                    phase <= REDUCE;
                end
                REDUCE: begin
                    rsp_data <= $signed({{15{pair_sum[0][16]}}, pair_sum[0]})
                              + $signed({{15{pair_sum[1][16]}}, pair_sum[1]});
                    phase <= RESPONSE;
                end
                RESPONSE: begin
                    if (rsp_ready)
                        phase <= IDLE;
                end
                default: phase <= IDLE;
            endcase
        end
    end
endmodule
