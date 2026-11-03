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

    logic [3:0] slot_active, slot_cancelled, slot_complete;
    logic [7:0] slot_id [0:3];
    logic [6:0] slot_remaining [0:3];
    logic signed [31:0] slot_sum [0:3];

    logic [1:0] q_head, q_tail;
    logic [2:0] q_count;

    logic [31:0] beat_a [0:1], beat_b [0:1];
    logic [1:0] beat_slot [0:1];
    logic [2:0] beat_lanes [0:1];
    logic [1:0] beat_count;

    logic cancel_match;
    logic [1:0] cancel_slot;
    logic data_match;
    logic [1:0] data_slot;
    logic duplicate_id;
    logic q_pop;
    logic cmd_fire, data_fire, beat_pop;
    logic signed [31:0] beat_sum;

    function automatic logic signed [31:0] reduce_beat(
        input logic [31:0] a,
        input logic [31:0] b,
        input logic [2:0] lanes
    );
        logic signed [15:0] p0, p1, p2, p3;
        logic signed [17:0] total;
        begin
            p0 = $signed(a[7:0]) * $signed(b[7:0]);
            p1 = $signed(a[15:8]) * $signed(b[15:8]);
            p2 = $signed(a[23:16]) * $signed(b[23:16]);
            p3 = $signed(a[31:24]) * $signed(b[31:24]);
            total = 18'sd0;
            if (lanes > 0) total = total + {{2{p0[15]}},p0};
            if (lanes > 1) total = total + {{2{p1[15]}},p1};
            if (lanes > 2) total = total + {{2{p2[15]}},p2};
            if (lanes > 3) total = total + {{2{p3[15]}},p3};
            reduce_beat = {{14{total[17]}},total};
        end
    endfunction

    always_comb begin
        cancel_match = 1'b0;
        cancel_slot = 2'd0;
        data_match = 1'b0;
        data_slot = 2'd0;
        duplicate_id = 1'b0;
        for (int i = 0; i < 4; i++) begin
            if (slot_active[i] && !slot_cancelled[i] && slot_id[i] == cancel_id) begin
                cancel_match = 1'b1;
                cancel_slot = 2'(i);
            end
            if (slot_active[i] && !slot_cancelled[i] && slot_id[i] == data_id) begin
                data_match = 1'b1;
                data_slot = 2'(i);
            end
            if (slot_active[i] && !slot_cancelled[i] && slot_id[i] == cmd_id)
                duplicate_id = 1'b1;
        end

        cmd_ready = rst_n && (q_count < 4) && !duplicate_id &&
                    !(cancel_valid && cancel_match);
        data_ready = rst_n && !(cancel_valid && cancel_match) &&
                     (!data_match || slot_remaining[data_slot] == 0 || beat_count < 2);
        rsp_valid = rst_n && (q_count != 0) && slot_complete[q_head] &&
                    !slot_cancelled[q_head] &&
                    !(cancel_valid && cancel_match && cancel_slot == q_head);
        rsp_id = (q_count != 0) ? slot_id[q_head] : 8'b0;
        rsp_data = (q_count != 0) ? slot_sum[q_head] : 32'b0;

        q_pop = (q_count != 0) &&
                (slot_cancelled[q_head] || (rsp_valid && rsp_ready));
        cmd_fire = cmd_valid && cmd_ready;
        data_fire = data_valid && data_ready;
        beat_pop = (beat_count != 0) && !(cancel_valid && cancel_match);
        beat_sum = (beat_count != 0) ? reduce_beat(beat_a[0], beat_b[0], beat_lanes[0]) : 32'sd0;
    end

    always_ff @(posedge clk or negedge rst_n) begin : state_update
        logic [1:0] next_beat_count;
        logic [1:0] push_index;
        if (!rst_n) begin
            slot_active <= 4'b0;
            slot_cancelled <= 4'b0;
            slot_complete <= 4'b0;
            q_head <= 2'd0;
            q_tail <= 2'd0;
            q_count <= 3'd0;
            beat_count <= 2'd0;
            for (int i = 0; i < 4; i++) begin
                slot_id[i] <= 8'b0;
                slot_remaining[i] <= 7'b0;
                slot_sum[i] <= 32'sd0;
            end
            for (int i = 0; i < 2; i++) begin
                beat_a[i] <= 32'b0;
                beat_b[i] <= 32'b0;
                beat_slot[i] <= 2'b0;
                beat_lanes[i] <= 3'b0;
            end
        end else if (cancel_valid && cancel_match) begin
            slot_cancelled[cancel_slot] <= 1'b1;
            slot_complete[cancel_slot] <= 1'b0;

            // Compact the two-entry beat queue while removing the canceled ID.
            if (beat_count == 2) begin
                if (beat_slot[0] == cancel_slot) begin
                    if (beat_slot[1] == cancel_slot) begin
                        beat_count <= 0;
                    end else begin
                        beat_a[0] <= beat_a[1];
                        beat_b[0] <= beat_b[1];
                        beat_slot[0] <= beat_slot[1];
                        beat_lanes[0] <= beat_lanes[1];
                        beat_count <= 1;
                    end
                end else if (beat_slot[1] == cancel_slot) begin
                    beat_count <= 1;
                end
            end else if (beat_count == 1 && beat_slot[0] == cancel_slot) begin
                beat_count <= 0;
            end
        end else begin
            if (q_pop) begin
                slot_active[q_head] <= 1'b0;
                slot_cancelled[q_head] <= 1'b0;
                slot_complete[q_head] <= 1'b0;
                slot_remaining[q_head] <= 7'b0;
                slot_sum[q_head] <= 32'sd0;
                q_head <= q_head + 2'd1;
            end
            if (cmd_fire) begin
                slot_active[q_tail] <= 1'b1;
                slot_cancelled[q_tail] <= 1'b0;
                slot_complete[q_tail] <= 1'b0;
                slot_id[q_tail] <= cmd_id;
                slot_remaining[q_tail] <= cmd_len;
                slot_sum[q_tail] <= 32'sd0;
                q_tail <= q_tail + 2'd1;
            end
            case ({cmd_fire,q_pop})
                2'b10: q_count <= q_count + 3'd1;
                2'b01: q_count <= q_count - 3'd1;
                default: q_count <= q_count;
            endcase

            if (beat_pop) begin
                slot_sum[beat_slot[0]] <= slot_sum[beat_slot[0]] + beat_sum;
                if (beat_lanes[0] == 0 || slot_remaining[beat_slot[0]] <= 4)
                    slot_complete[beat_slot[0]] <= 1'b1;
                beat_a[0] <= beat_a[1];
                beat_b[0] <= beat_b[1];
                beat_slot[0] <= beat_slot[1];
                beat_lanes[0] <= beat_lanes[1];
            end

            next_beat_count = beat_count - beat_pop;
            if (data_fire && data_match && slot_remaining[data_slot] != 0) begin
                push_index = next_beat_count;
                beat_a[push_index] <= data_a;
                beat_b[push_index] <= data_b;
                beat_slot[push_index] <= data_slot;
                if (slot_remaining[data_slot] >= 4)
                    beat_lanes[push_index] <= 3'd4;
                else
                    beat_lanes[push_index] <= slot_remaining[data_slot][2:0];
                slot_remaining[data_slot] <= slot_remaining[data_slot] -
                                             ((slot_remaining[data_slot] >= 4) ? 7'd4 : slot_remaining[data_slot]);
                next_beat_count = next_beat_count + 2'd1;
            end
            beat_count <= next_beat_count;
        end
    end
endmodule
