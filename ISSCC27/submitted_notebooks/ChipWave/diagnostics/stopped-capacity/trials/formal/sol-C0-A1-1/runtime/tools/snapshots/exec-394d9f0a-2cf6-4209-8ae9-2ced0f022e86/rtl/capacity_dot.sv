module capacity_dot (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        cmd_valid,
    output logic        cmd_ready,
    input  logic [7:0]  cmd_id,
    input  logic [6:0]  cmd_len,
    input  logic        data_valid,
    output logic        data_ready,
    input  logic [7:0]  data_id,
    input  logic [31:0] data_a,
    input  logic [31:0] data_b,
    input  logic        cancel_valid,
    input  logic [7:0]  cancel_id,
    output logic        rsp_valid,
    input  logic        rsp_ready,
    output logic [7:0]  rsp_id,
    output logic [31:0] rsp_data
);
    logic active, complete;
    logic [7:0] live_id;
    logic [6:0] remaining;
    logic [2:0] lanes_left;
    logic [31:0] operand_a, operand_b;
    logic signed [15:0] product;
    logic product_valid;
    // The greatest legal sum is 64 * (-128) * (-128) = 2^20.
    logic signed [21:0] accumulator;
    wire cancel_match = cancel_valid && active && cancel_id == live_id;
    wire data_match = active && data_id == live_id;
    wire engine_idle = lanes_left == 0 && !product_valid;

    assign cmd_ready = rst_n && !cancel_match && !active;
    // If command and first beat arrive together, defer the beat one cycle
    // so that it cannot be mistaken for trailing data from a dead ID.
    assign data_ready = rst_n && !cancel_match &&
        (data_match ? (engine_idle && !complete) :
         !(cmd_valid && cmd_ready && data_id == cmd_id));
    assign rsp_valid = rst_n && !cancel_match && active && complete;
    assign rsp_id = live_id;
    assign rsp_data = {{10{accumulator[21]}}, accumulator};

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 0;
            complete <= 0;
            live_id <= 0;
            remaining <= 0;
            lanes_left <= 0;
            product_valid <= 0;
            accumulator <= 0;
        end else if (cancel_match) begin
            active <= 0;
            complete <= 0;
            remaining <= 0;
            lanes_left <= 0;
            product_valid <= 0;
            accumulator <= 0;
        end else begin
            product_valid <= 0;
            if (cmd_valid && cmd_ready) begin
                active <= 1;
                complete <= 0;
                live_id <= cmd_id;
                remaining <= cmd_len;
                accumulator <= 0;
            end
            if (data_valid && data_ready && data_match && remaining != 0) begin
                if (remaining > 4) begin
                    remaining <= remaining - 7'd4;
                    lanes_left <= 3'd4;
                end else begin
                    remaining <= 0;
                    lanes_left <= remaining[2:0];
                end
            end
            if (lanes_left != 0) begin
                lanes_left <= lanes_left - 3'd1;
                product_valid <= 1;
            end
            if (product_valid) begin
                accumulator <= accumulator + {{6{product[15]}}, product};
                if (lanes_left == 0 && remaining == 0)
                    complete <= 1;
            end
            if (rsp_valid && rsp_ready) begin
                active <= 0;
                complete <= 0;
            end
        end
    end

    // Datapath registers need no reset: validity is cleared on reset/cancel.
    always_ff @(posedge clk) begin
        if (rst_n && !cancel_match) begin
            if (data_valid && data_ready && data_match && remaining != 0) begin
                operand_a <= data_a;
                operand_b <= data_b;
            end else if (lanes_left != 0) begin
                operand_a <= {8'b0, operand_a[31:8]};
                operand_b <= {8'b0, operand_b[31:8]};
            end
            if (lanes_left != 0)
                product <= $signed(operand_a[7:0]) * $signed(operand_b[7:0]);
        end
    end
endmodule
