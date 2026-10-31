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
    logic live, complete;
    logic [7:0] live_id;
    logic [6:0] remaining;
    logic [31:0] operand_a, operand_b;
    logic [2:0] lanes;
    logic beat_last;
    logic signed [15:0] product;
    logic product_valid, product_last;
    // 64 * (-128) * (-128) = 2^20 requires 22 signed bits.
    logic signed [21:0] accumulator;
    wire matching_cancel = cancel_valid && live && cancel_id == live_id;
    wire data_matches = live && data_id == live_id;

    assign cmd_ready = rst_n && !matching_cancel && !live;
    // Dead IDs are drained even while the live command is busy.
    assign data_ready = rst_n && !matching_cancel &&
                        (!data_matches || (!complete && remaining != 0 &&
                                           lanes == 0 && !product_valid));
    assign rsp_valid = rst_n && !matching_cancel && live && complete;
    assign rsp_id = live_id;
    assign rsp_data = {{10{accumulator[21]}}, accumulator};

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            live <= 0;
            complete <= 0;
            live_id <= 0;
            remaining <= 0;
            operand_a <= 0;
            operand_b <= 0;
            lanes <= 0;
            beat_last <= 0;
            product <= 0;
            product_valid <= 0;
            product_last <= 0;
            accumulator <= 0;
        end else if (matching_cancel) begin
            live <= 0;
            complete <= 0;
            lanes <= 0;
            product_valid <= 0;
            remaining <= 0;
            accumulator <= 0;
        end else begin
            product_valid <= 0;
            if (rsp_valid && rsp_ready) begin
                live <= 0;
                complete <= 0;
            end
            if (cmd_valid && cmd_ready) begin
                live <= 1;
                complete <= 0;
                live_id <= cmd_id;
                remaining <= cmd_len;
                accumulator <= 0;
            end
            if (data_valid && data_ready && data_matches) begin
                operand_a <= data_a;
                operand_b <= data_b;
                lanes <= remaining >= 4 ? 3'd4 : remaining[2:0];
                beat_last <= remaining <= 4;
                remaining <= remaining > 4 ? remaining - 7'd4 : 7'd0;
            end
            if (lanes != 0) begin
                product <= $signed(operand_a[7:0]) * $signed(operand_b[7:0]);
                product_valid <= 1;
                product_last <= beat_last && lanes == 1;
                operand_a <= {8'b0, operand_a[31:8]};
                operand_b <= {8'b0, operand_b[31:8]};
                lanes <= lanes - 3'd1;
            end
            if (product_valid) begin
                accumulator <= accumulator + {{6{product[15]}}, product};
                if (product_last)
                    complete <= 1;
            end
        end
    end
endmodule
