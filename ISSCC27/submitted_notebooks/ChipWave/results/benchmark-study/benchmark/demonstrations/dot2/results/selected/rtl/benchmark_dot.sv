module benchmark_dot (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        req_valid,
    output wire        req_ready,
    input  wire [15:0] req_a,
    input  wire [15:0] req_b,
    output wire        rsp_valid,
    input  wire        rsp_ready,
    output reg  [31:0] rsp_data,
    input  wire        kill
);
    localparam [1:0] IDLE = 2'd0,
                     REDUCE = 2'd1,
                     PUBLISH = 2'd2,
                     RESPONSE = 2'd3;
    reg [1:0] state;
    reg signed [15:0] product0, product1;
    reg signed [16:0] sum;

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);

    // Products are captured only on acceptance, so changing inputs while
    // busy cannot affect the outstanding transaction.
    always @(posedge clk) begin
        if (req_valid && req_ready) begin
            product0 <= $signed(req_a[7:0]) * $signed(req_b[7:0]);
            product1 <= $signed(req_a[15:8]) * $signed(req_b[15:8]);
        end
        if (state == REDUCE)
            sum <= {product0[15], product0} + {product1[15], product1};
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            rsp_data <= 32'd0;
        end else if (kill) begin
            state <= IDLE;
            rsp_data <= 32'd0;
        end else begin
            case (state)
                IDLE: if (req_valid) state <= REDUCE;
                REDUCE: state <= PUBLISH;
                PUBLISH: begin
                    rsp_data <= {{15{sum[16]}}, sum};
                    state <= RESPONSE;
                end
                RESPONSE: if (rsp_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
