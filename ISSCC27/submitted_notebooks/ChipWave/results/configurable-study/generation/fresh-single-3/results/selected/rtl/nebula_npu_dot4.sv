`timescale 1ns/1ps
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
    typedef enum logic [1:0] {IDLE, REDUCE, FINISH, RESPONSE} state_t;
    state_t state;
    logic signed [15:0] products [0:3];
    logic signed [31:0] pair_lo, pair_hi;

    assign req_ready = rst_n && !kill && (state == IDLE);
    assign rsp_valid = rst_n && !kill && (state == RESPONSE);

    // Four independent signed INT8 multipliers, sampled on acceptance.
    for (genvar lane = 0; lane < 4; lane = lane + 1) begin : lanes
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n)
                products[lane] <= 16'sd0;
            else if (kill)
                products[lane] <= 16'sd0;
            else if (req_valid && req_ready)
                products[lane] <= $signed(req_a[8*lane +: 8]) *
                                  $signed(req_b[8*lane +: 8]);
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= IDLE;
            pair_lo  <= 32'sd0;
            pair_hi  <= 32'sd0;
            rsp_data <= 32'd0;
        end else if (kill) begin
            state    <= IDLE;
            pair_lo  <= 32'sd0;
            pair_hi  <= 32'sd0;
            rsp_data <= 32'd0;
        end else begin
            case (state)
                IDLE: begin
                    if (req_valid)
                        state <= REDUCE;
                end
                REDUCE: begin
                    // Extend each product before any addition.
                    pair_lo <= $signed({{16{products[0][15]}}, products[0]}) +
                               $signed({{16{products[1][15]}}, products[1]});
                    pair_hi <= $signed({{16{products[2][15]}}, products[2]}) +
                               $signed({{16{products[3][15]}}, products[3]});
                    state <= FINISH;
                end
                FINISH: begin
                    rsp_data <= pair_lo + pair_hi;
                    state <= RESPONSE;
                end
                RESPONSE: begin
                    if (rsp_ready)
                        state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
