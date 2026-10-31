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
    logic active;
    logic [7:0] live_id;
    logic [6:0] length_left;
    logic [31:0] accumulator;
    logic result_valid;
    logic [7:0] result_id;
    logic [31:0] result_data;
    logic matching_cancel;
    logic [31:0] beat_sum;
    logic [2:0] useful_lanes;

    assign matching_cancel = cancel_valid && active && (cancel_id == live_id);
    assign cmd_ready = rst_n && !matching_cancel && !active;
    // Stale or canceled trailing beats are consumed and ignored.  Beats for
    // the current command are also accepted immediately, one beat per cycle.
    assign data_ready = rst_n && !matching_cancel;
    assign rsp_valid = rst_n && !matching_cancel && result_valid;
    assign rsp_id = result_id;
    assign rsp_data = result_data;

    always_comb begin
        beat_sum = 32'b0;
        useful_lanes = (length_left >= 4) ? 3'd4 : length_left[2:0];
        for (int lane = 0; lane < 4; lane++) begin
            if (lane < useful_lanes)
                beat_sum = beat_sum +
                    ($signed(data_a[8*lane +: 8]) * $signed(data_b[8*lane +: 8]));
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active       <= 1'b0;
            live_id      <= 8'b0;
            length_left  <= 7'b0;
            accumulator  <= 32'b0;
            result_valid <= 1'b0;
            result_id    <= 8'b0;
            result_data  <= 32'b0;
        end else if (matching_cancel) begin
            active       <= 1'b0;
            length_left  <= 7'b0;
            accumulator  <= 32'b0;
            result_valid <= 1'b0;
        end else begin
            if (result_valid && rsp_ready) begin
                result_valid <= 1'b0;
                active <= 1'b0;
            end

            if (cmd_valid && cmd_ready) begin
                active      <= 1'b1;
                live_id     <= cmd_id;
                length_left <= cmd_len;
                accumulator <= 32'b0;
                result_valid <= 1'b0;
            end

            if (data_valid && data_ready && active && (data_id == live_id) && !result_valid) begin
                accumulator <= accumulator + beat_sum;
                if (length_left <= 4) begin
                    result_valid <= 1'b1;
                    result_id    <= live_id;
                    result_data  <= accumulator + beat_sum;
                    length_left  <= 0;
                end else begin
                    length_left <= length_left - 4;
                end
            end
        end
    end
endmodule
