module nebula_npu_dot4 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        req_valid,
    output wire        req_ready,
    input  wire [31:0] req_a,
    input  wire [31:0] req_b,
    output wire        rsp_valid,
    input  wire        rsp_ready,
    output reg  [31:0] rsp_data,
    input  wire        kill
);
    localparam [1:0] IDLE = 2'd0, REDUCE = 2'd1,
                     PUBLISH = 2'd2, RESPONSE = 2'd3;
    reg [1:0] state;
    reg signed [15:0] product [0:3];
    reg signed [31:0] dot_sum;
    integer lane;

    assign req_ready = rst_n && !kill && state == IDLE;
    assign rsp_valid = rst_n && !kill && state == RESPONSE;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            dot_sum <= 32'sd0;
            rsp_data <= 32'd0;
            for (lane = 0; lane < 4; lane = lane + 1)
                product[lane] <= 16'sd0;
        end else if (kill) begin
            state <= IDLE;
            dot_sum <= 32'sd0;
            rsp_data <= 32'd0;
            for (lane = 0; lane < 4; lane = lane + 1)
                product[lane] <= 16'sd0;
        end else begin
            case (state)
                IDLE: if (req_valid && req_ready) begin
                    for (lane = 0; lane < 4; lane = lane + 1)
                        product[lane] <= $signed(req_a[lane*8 +: 8])
                                       * $signed(req_b[lane*8 +: 8]);
                    state <= REDUCE;
                end
                REDUCE: begin
                    dot_sum <= $signed({{16{product[0][15]}}, product[0]})
                             + $signed({{16{product[1][15]}}, product[1]})
                             + $signed({{16{product[2][15]}}, product[2]})
                             + $signed({{16{product[3][15]}}, product[3]});
                    state <= PUBLISH;
                end
                PUBLISH: begin
                    rsp_data <= dot_sum;
                    state <= RESPONSE;
                end
                RESPONSE: if (rsp_ready)
                    state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
