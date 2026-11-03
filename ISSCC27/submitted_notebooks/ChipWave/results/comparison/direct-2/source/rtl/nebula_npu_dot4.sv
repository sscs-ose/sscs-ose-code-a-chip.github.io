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

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            sum <= '0;
            rsp_data <= '0;
            for (int i = 0; i < 4; i = i + 1)
                products[i] <= '0;
        end else if (kill) begin
            state <= IDLE;
            sum <= '0;
            rsp_data <= '0;
            for (int i = 0; i < 4; i = i + 1)
                products[i] <= '0;
        end else begin
            case (state)
                IDLE: if (req_valid) begin
                    for (int i = 0; i < 4; i = i + 1)
                        products[i] <= $signed(req_a[8*i +: 8]) *
                                       $signed(req_b[8*i +: 8]);
                    state <= REDUCE;
                end
                REDUCE: begin
                    sum <= {{16{products[0][15]}}, products[0]} +
                           {{16{products[1][15]}}, products[1]} +
                           {{16{products[2][15]}}, products[2]} +
                           {{16{products[3][15]}}, products[3]};
                    state <= PUBLISH;
                end
                PUBLISH: begin
                    rsp_data <= sum;
                    state <= RESPONSE;
                end
                RESPONSE: if (rsp_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end
endmodule
