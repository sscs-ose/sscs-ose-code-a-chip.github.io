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
    logic result_pending;
    logic [7:0] active_id;
    logic [6:0] remaining;
    logic signed [31:0] accumulator;

    logic cancel_match;
    logic signed [15:0] product0, product1, product2, product3;
    logic signed [17:0] beat_sum;
    logic signed [31:0] extended_beat_sum;
    logic [6:0] useful_lanes;

    always_comb begin
        product0 = $signed(data_a[7:0])   * $signed(data_b[7:0]);
        product1 = $signed(data_a[15:8])  * $signed(data_b[15:8]);
        product2 = $signed(data_a[23:16]) * $signed(data_b[23:16]);
        product3 = $signed(data_a[31:24]) * $signed(data_b[31:24]);

        useful_lanes = remaining;
        beat_sum = 18'sd0;
        if (useful_lanes != 0)
            beat_sum = beat_sum + {{2{product0[15]}}, product0};
        if (useful_lanes > 1)
            beat_sum = beat_sum + {{2{product1[15]}}, product1};
        if (useful_lanes > 2)
            beat_sum = beat_sum + {{2{product2[15]}}, product2};
        if (useful_lanes > 3)
            beat_sum = beat_sum + {{2{product3[15]}}, product3};
        extended_beat_sum = {{14{beat_sum[17]}}, beat_sum};

        cancel_match = cancel_valid && live &&
                       (cancel_id == active_id ||
                        (result_pending && cancel_id == rsp_id));
        cmd_ready = rst_n && !live && !cancel_match;
        data_ready = rst_n && !cancel_match;
        rsp_valid = rst_n && result_pending && !cancel_match;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            live            <= 1'b0;
            result_pending  <= 1'b0;
            active_id       <= 8'b0;
            remaining       <= 7'b0;
            accumulator     <= 32'sd0;
            rsp_id          <= 8'b0;
            rsp_data        <= 32'b0;
        end else if (cancel_match) begin
            live            <= 1'b0;
            result_pending  <= 1'b0;
            remaining       <= 7'b0;
            accumulator     <= 32'sd0;
            rsp_data        <= 32'b0;
        end else begin
            if (result_pending && rsp_ready) begin
                result_pending <= 1'b0;
                live           <= 1'b0;
            end

            if (cmd_valid && cmd_ready) begin
                live        <= 1'b1;
                active_id   <= cmd_id;
                remaining   <= cmd_len;
                accumulator <= 32'sd0;
            end

            if (data_valid && data_ready && live && !result_pending &&
                (data_id == active_id)) begin
                if (remaining <= 7'd4) begin
                    remaining      <= 7'b0;
                    result_pending <= 1'b1;
                    rsp_id         <= active_id;
                    rsp_data       <= accumulator + extended_beat_sum;
                end else begin
                    remaining   <= remaining - 7'd4;
                    accumulator <= accumulator + extended_beat_sum;
                end
            end
        end
    end
endmodule
