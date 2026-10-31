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
    logic signed [15:0] products [0:3];
    wire signed [31:0] widened [0:3];
    logic signed [31:0] result;

    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : extend_products
        assign widened[lane] = {{16{products[lane][15]}}, products[lane]};
    end

    // Cancellation gates the handshake immediately; state is cleared at the edge.
    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = result;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            result <= 32'sd0;
            for (integer lane = 0; lane < 4; lane = lane + 1)
                products[lane] <= 16'sd0;
        end else if (kill) begin
            state <= IDLE;
            result <= 32'sd0;
            for (integer lane = 0; lane < 4; lane = lane + 1)
                products[lane] <= 16'sd0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid) begin
                        // Four independent signed 8-by-8 multipliers, sampled at n.
                        for (integer lane = 0; lane < 4; lane = lane + 1)
                            products[lane] <= $signed(req_a[8*lane +: 8]) *
                                              $signed(req_b[8*lane +: 8]);
                        state <= REDUCE;
                    end
                end
                REDUCE: begin
                    // Widen each product before adding, on edge n+1.
                    result <= widened[0] + widened[1] + widened[2] + widened[3];
                    state <= DELAY;
                end
                DELAY: state <= RESPONSE; // Response becomes visible after n+2.
                RESPONSE: begin
                    if (rsp_ready)
                        state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
