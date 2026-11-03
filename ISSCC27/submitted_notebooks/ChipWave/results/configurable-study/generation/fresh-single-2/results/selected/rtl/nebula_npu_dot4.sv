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
    typedef enum logic [1:0] {IDLE, REDUCE, PRESENT, RESPONSE} state_t;
    state_t state;
    logic signed [15:0] products [0:3];
    wire signed [31:0] extended [0:3];
    logic signed [31:0] result;

    // Each multiplier has two signed eight-bit operands and a full product.
    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        wire signed [7:0] a = $signed(req_a[lane*8 +: 8]);
        wire signed [7:0] b = $signed(req_b[lane*8 +: 8]);
        wire signed [15:0] product = a * b;
        assign extended[lane] = {{16{products[lane][15]}}, products[lane]};
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                products[lane] <= 16'sd0;
            else if (kill)
                products[lane] <= 16'sd0;
            else if (state == IDLE && req_valid)
                products[lane] <= product;
        end
    end

    // Mask handshakes immediately, even between sampling edges.
    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = result;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            result <= 32'sd0;
        end else if (kill) begin
            state <= IDLE;
            result <= 32'sd0;
        end else begin
            case (state)
                IDLE: if (req_valid) state <= REDUCE;
                REDUCE: begin
                    // Widen every product before performing any addition.
                    result <= (extended[0] + extended[1]) +
                              (extended[2] + extended[3]);
                    state <= PRESENT;
                end
                PRESENT: state <= RESPONSE;
                RESPONSE: if (rsp_ready) state <= IDLE;
                default: begin
                    state <= IDLE;
                    result <= 32'sd0;
                end
            endcase
        end
    end
endmodule
