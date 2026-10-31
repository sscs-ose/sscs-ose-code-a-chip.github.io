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
    logic live;
    logic [7:0] active_id;
    logic [6:0] remaining;
    logic signed [31:0] accumulator;
    logic cancel_match;
    logic signed [15:0] operand_a [0:3];
    logic signed [15:0] operand_b [0:3];
    logic signed [15:0] products [0:3];
    logic signed [31:0] beat_sum;

    assign cancel_match = live && cancel_valid && (cancel_id == active_id);
    assign cmd_ready = rst_n && !live && !(cancel_valid && live && (cancel_id == active_id));
    // A1 has no operand FIFO: each offered beat is consumed in its cycle.
    // Unknown or retired IDs are also consumed and discarded.
    assign data_ready = rst_n && !cancel_match;
    assign rsp_valid = rst_n && live && (remaining == 0) && !cancel_match;
    assign rsp_id = active_id;

    always_comb begin
        for (integer i = 0; i < 4; i = i + 1) begin
            operand_a[i] = $signed({{8{data_a[8*i+7]}}, data_a[8*i +: 8]});
            operand_b[i] = $signed({{8{data_b[8*i+7]}}, data_b[8*i +: 8]});
            products[i] = operand_a[i] * operand_b[i];
        end
        beat_sum = 32'sd0;
        for (integer j = 0; j < 4; j = j + 1) begin
            if (remaining > j)
                beat_sum = beat_sum + {{16{products[j][15]}}, products[j]};
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            live <= 1'b0;
            active_id <= 8'b0;
            remaining <= 7'b0;
            accumulator <= 32'sd0;
            rsp_data <= 32'b0;
        end else if (cancel_match) begin
            live <= 1'b0;
            remaining <= 7'b0;
            accumulator <= 32'sd0;
            rsp_data <= 32'b0;
        end else begin
            if (cmd_valid && cmd_ready) begin
                live <= 1'b1;
                active_id <= cmd_id;
                remaining <= cmd_len;
                accumulator <= 32'sd0;
                rsp_data <= 32'b0;
            end
            if (data_valid && data_ready && live && (data_id == active_id) && (remaining != 0)) begin
                if (remaining <= 4) begin
                    rsp_data <= accumulator + beat_sum;
                    remaining <= 0;
                end else begin
                    accumulator <= accumulator + beat_sum;
                    remaining <= remaining - 7'd4;
                end
            end
            if (rsp_valid && rsp_ready) begin
                live <= 1'b0;
                remaining <= 0;
                accumulator <= 32'sd0;
            end
        end
    end
endmodule
