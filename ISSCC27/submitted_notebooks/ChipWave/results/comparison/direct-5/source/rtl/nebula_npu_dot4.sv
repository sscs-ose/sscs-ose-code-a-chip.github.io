module nebula_npu_dot4 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        req_valid,
    output wire        req_ready,
    input  wire [31:0] req_a,
    input  wire [31:0] req_b,
    output wire        rsp_valid,
    input  wire        rsp_ready,
    output wire [31:0] rsp_data,
    input  wire        kill
);
    typedef enum logic [1:0] {IDLE, REDUCE, DELAY, RESPONSE} state_t;
    state_t state;
    logic signed [15:0] product [0:3];
    logic signed [31:0] result;
    wire signed [31:0] wide_product [0:3];

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = (rst_n && !kill) ? result : 32'b0;

    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        assign wide_product[lane] = {{16{product[lane][15]}}, product[lane]};
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            result <= 32'sd0;
            for (integer lane = 0; lane < 4; lane = lane + 1)
                product[lane] <= 16'sd0;
        end else if (kill) begin
            state <= IDLE;
            result <= 32'sd0;
            for (integer lane = 0; lane < 4; lane = lane + 1)
                product[lane] <= 16'sd0;
        end else begin
            case (state)
                IDLE: if (req_valid) begin
                    for (integer lane = 0; lane < 4; lane = lane + 1)
                        product[lane] <= $signed(req_a[8*lane +: 8])
                                       * $signed(req_b[8*lane +: 8]);
                    state <= REDUCE;
                end
                REDUCE: begin
                    result <= wide_product[0] + wide_product[1]
                            + wide_product[2] + wide_product[3];
                    state <= DELAY;
                end
                DELAY: state <= RESPONSE;
                RESPONSE: if (rsp_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
