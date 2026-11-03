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
    logic signed [15:0] product [0:3];
    wire signed [31:0] widened [0:3];
    logic signed [31:0] result;

    // Each lane has its own signed 8 x 8 multiplier. Extend each product
    // before addition so intermediate sums cannot overflow at 16 bits.
    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        wire signed [7:0] a = req_a[8*lane +: 8];
        wire signed [7:0] b = req_b[8*lane +: 8];
        wire signed [15:0] multiplied = a * b;
        assign widened[lane] = {{16{product[lane][15]}}, product[lane]};
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                product[lane] <= 16'sd0;
            else if (kill)
                product[lane] <= 16'sd0;
            else if (state == IDLE && req_valid)
                product[lane] <= multiplied;
        end
    end

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);
    assign rsp_data = result;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state  <= IDLE;
            result <= 32'sd0;
        end else if (kill) begin
            state  <= IDLE;
            result <= 32'sd0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid)
                        state <= REDUCE;
                end
                REDUCE: begin
                    result <= (widened[0] + widened[1]) +
                              (widened[2] + widened[3]);
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
