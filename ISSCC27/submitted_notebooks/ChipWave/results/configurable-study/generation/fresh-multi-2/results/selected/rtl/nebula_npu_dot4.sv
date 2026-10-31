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
    logic signed [15:0] product [0:3];
    wire signed [31:0] wide_product [0:3];

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);

    // Capture all four signed products at acceptance. Each product is
    // sign-extended to INT32 before any addition takes place.
    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        wire signed [7:0] a = req_a[8*lane +: 8];
        wire signed [7:0] b = req_b[8*lane +: 8];
        assign wide_product[lane] = {{16{product[lane][15]}}, product[lane]};
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                product[lane] <= 16'sd0;
            else if (kill)
                product[lane] <= 16'sd0;
            else if (req_valid && req_ready)
                product[lane] <= a * b;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= IDLE;
            rsp_data <= 32'd0;
        end else if (kill) begin
            state    <= IDLE;
            rsp_data <= 32'd0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid && req_ready)
                        state <= REDUCE;
                end
                REDUCE: begin
                    rsp_data <= (wide_product[0] + wide_product[1])
                              + (wide_product[2] + wide_product[3]);
                    state <= DELAY;
                end
                // Acceptance is edge n; RESPONSE begins after edge n+2.
                DELAY: state <= RESPONSE;
                RESPONSE: begin
                    if (rsp_ready)
                        state <= IDLE;
                end
                default: begin
                    state    <= IDLE;
                    rsp_data <= 32'd0;
                end
            endcase
        end
    end
endmodule
