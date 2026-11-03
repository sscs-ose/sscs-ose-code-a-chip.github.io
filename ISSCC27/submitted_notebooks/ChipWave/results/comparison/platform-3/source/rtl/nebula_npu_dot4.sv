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
    logic signed [15:0] products [0:3];
    logic signed [31:0] sum;

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = (rst_n && !kill) ? sum : 32'b0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            sum <= 32'sd0;
            for (int lane = 0; lane < 4; lane = lane + 1)
                products[lane] <= 16'sd0;
        end else if (kill) begin
            state <= IDLE;
            sum <= 32'sd0;
            for (int lane = 0; lane < 4; lane = lane + 1)
                products[lane] <= 16'sd0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid && req_ready) begin
                        for (int lane = 0; lane < 4; lane = lane + 1)
                            products[lane] <= $signed(req_a[lane*8 +: 8])
                                            * $signed(req_b[lane*8 +: 8]);
                        state <= REDUCE;
                    end
                end
                REDUCE: begin
                    // Widen every product before the reduction can overflow INT16.
                    sum <= $signed({{16{products[0][15]}}, products[0]})
                         + $signed({{16{products[1][15]}}, products[1]})
                         + $signed({{16{products[2][15]}}, products[2]})
                         + $signed({{16{products[3][15]}}, products[3]});
                    state <= PUBLISH;
                end
                PUBLISH: state <= RESPONSE;
                RESPONSE: begin
                    if (rsp_ready)
                        state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
