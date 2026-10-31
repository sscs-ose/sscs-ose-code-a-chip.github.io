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
    logic signed [15:0] products [0:3];
    logic signed [31:0] result;

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = (rst_n && !kill) ? result : 32'b0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            result <= 32'b0;
            for (int lane = 0; lane < 4; lane = lane + 1)
                products[lane] <= 16'b0;
        end else if (kill) begin
            state <= IDLE;
            result <= 32'b0;
            for (int lane = 0; lane < 4; lane = lane + 1)
                products[lane] <= 16'b0;
        end else begin
            case (state)
                IDLE: if (req_valid && req_ready) begin
                    for (int lane = 0; lane < 4; lane = lane + 1)
                        products[lane] <= $signed(req_a[8*lane +: 8]) *
                                          $signed(req_b[8*lane +: 8]);
                    state <= PRODUCTS;
                end
                PRODUCTS: begin
                    result <= $signed({{16{products[0][15]}}, products[0]}) +
                              $signed({{16{products[1][15]}}, products[1]}) +
                              $signed({{16{products[2][15]}}, products[2]}) +
                              $signed({{16{products[3][15]}}, products[3]});
                    state <= SUM;
                end
                SUM: state <= RESPONSE;
                RESPONSE: if (rsp_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
