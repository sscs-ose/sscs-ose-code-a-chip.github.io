module capacity_dot (
    input  logic clk, rst_n,
    input  logic cmd_valid,
    output logic cmd_ready,
    input  logic [7:0] cmd_id,
    input  logic [6:0] cmd_len,
    input  logic data_valid,
    output logic data_ready,
    input  logic [7:0] data_id,
    input  logic [31:0] data_a, data_b,
    input  logic cancel_valid,
    input  logic [7:0] cancel_id,
    output logic rsp_valid,
    input  logic rsp_ready,
    output logic [7:0] rsp_id,
    output logic [31:0] rsp_data
);
    // Command ring: canceled entries remain reserved until reaching the head.
    logic [1:0] head, tail;
    logic [2:0] occupied;
    logic [3:0] live, complete;
    logic [7:0] id [0:3];
    logic [6:0] remaining [0:3];
    // 64 * (-128) * (-128) = 2**20, requiring 22 signed bits.
    logic signed [21:0] total [0:3];

    // Exactly two owned operand beats, shared by all four commands.
    logic beat_head, beat_tail;
    logic [1:0] beat_count;
    logic [1:0] beat_live;
    logic [31:0] beat_a [0:1], beat_b [0:1];
    logic [2:0] lanes [0:1];
    logic [1:0] owner [0:1];
    logic [1:0] final_beat;

    logic cancel_hit;
    logic [1:0] cancel_slot;
    logic data_hit;
    logic [1:0] data_slot;
    logic [6:0] data_remaining;
    logic cmd_fire, data_fire, enqueue, retire, pop_beat, issue;

    // Multiplier register breaks the multiply/accumulate timing path.
    logic product_valid, product_final;
    logic [1:0] product_slot;
    logic signed [15:0] product;

    always_comb begin
        cancel_hit = 1'b0;
        cancel_slot = 2'b0;
        for (integer s = 0; s < 4; s = s + 1) begin
            if (cancel_valid && live[s] && id[s] == cancel_id) begin
                cancel_hit = 1'b1;
                cancel_slot = s[1:0];
            end
        end
    end

    assign cmd_ready = rst_n && !cancel_hit && occupied < 4;
    assign cmd_fire = cmd_valid && cmd_ready;

    always_comb begin
        data_hit = 1'b0;
        data_slot = 2'b0;
        data_remaining = 7'b0;
        // A command and its first beat may be accepted on the same edge.
        if (cmd_fire && data_id == cmd_id) begin
            data_hit = 1'b1;
            data_slot = tail;
            data_remaining = cmd_len;
        end
        for (integer s = 0; s < 4; s = s + 1) begin
            if (live[s] && id[s] == data_id) begin
                data_hit = 1'b1;
                data_slot = s[1:0];
                data_remaining = remaining[s];
            end
        end
    end

    // Unknown or already fully loaded IDs need no buffer space.
    assign data_ready = rst_n && !cancel_hit &&
                        (!data_hit || data_remaining == 0 || beat_count < 2);
    assign data_fire = data_valid && data_ready;
    assign enqueue = data_fire && data_hit && data_remaining != 0;
    assign rsp_valid = rst_n && !cancel_hit && occupied != 0 &&
                       live[head] && complete[head];
    assign rsp_id = id[head];
    assign rsp_data = {{10{total[head][21]}}, total[head]};
    assign retire = occupied != 0 &&
                    (!live[head] || (complete[head] && rsp_ready));
    assign issue = beat_count != 0 && beat_live[beat_head];
    assign pop_beat = beat_count != 0 &&
                      (!beat_live[beat_head] || lanes[beat_head] == 1);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            head <= 0;
            tail <= 0;
            occupied <= 0;
            live <= 0;
            complete <= 0;
            beat_head <= 0;
            beat_tail <= 0;
            beat_count <= 0;
            beat_live <= 0;
            product_valid <= 0;
        end else if (cancel_hit) begin
            live[cancel_slot] <= 1'b0;
            complete[cancel_slot] <= 1'b0;
            for (integer b = 0; b < 2; b = b + 1)
                if (owner[b] == cancel_slot) beat_live[b] <= 1'b0;
            if (product_slot == cancel_slot) product_valid <= 1'b0;
        end else begin
            case ({cmd_fire, retire})
                2'b10: occupied <= occupied + 1'b1;
                2'b01: occupied <= occupied - 1'b1;
                default: begin end
            endcase
            if (retire) begin
                head <= head + 1'b1;
                live[head] <= 1'b0;
                complete[head] <= 1'b0;
            end
            if (cmd_fire) begin
                tail <= tail + 1'b1;
                live[tail] <= 1'b1;
                complete[tail] <= 1'b0;
            end
            if (product_valid) begin
                if (product_final) complete[product_slot] <= 1'b1;
            end

            case ({enqueue, pop_beat})
                2'b10: beat_count <= beat_count + 1'b1;
                2'b01: beat_count <= beat_count - 1'b1;
                default: begin end
            endcase
            if (pop_beat) begin
                beat_head <= !beat_head;
                beat_live[beat_head] <= 1'b0;
            end
            if (enqueue) begin
                beat_tail <= !beat_tail;
                beat_live[beat_tail] <= 1'b1;
            end
            product_valid <= issue;
        end
    end

    // Payload registers need no reset: all reads are guarded by resettable valid
    // state, and every new command initializes its own sum before use.
    always_ff @(posedge clk) begin
        if (rst_n && !cancel_hit) begin
            for (integer s = 0; s < 4; s = s + 1) begin
                if (product_valid && product_slot == s[1:0])
                    total[s] <= total[s] + {{6{product[15]}}, product};
                if (cmd_fire && tail == s[1:0]) begin
                    id[s] <= cmd_id;
                    remaining[s] <= cmd_len;
                    total[s] <= 22'sd0;
                end
                if (enqueue && data_slot == s[1:0])
                    remaining[s] <= data_remaining > 4 ? data_remaining - 7'd4 : 7'd0;
            end
            if (issue) begin
                product <= $signed(beat_a[beat_head][7:0]) *
                           $signed(beat_b[beat_head][7:0]);
                product_slot <= owner[beat_head];
                product_final <= final_beat[beat_head] && lanes[beat_head] == 1;
            end
            for (integer b = 0; b < 2; b = b + 1) begin
                if (issue && beat_head == b[0:0]) begin
                    beat_a[b] <= {8'b0, beat_a[b][31:8]};
                    beat_b[b] <= {8'b0, beat_b[b][31:8]};
                    lanes[b] <= lanes[b] - 1'b1;
                end
                if (enqueue && beat_tail == b[0:0]) begin
                    beat_a[b] <= data_a;
                    beat_b[b] <= data_b;
                    lanes[b] <= data_remaining > 4 ? 3'd4 : data_remaining[2:0];
                    owner[b] <= data_slot;
                    final_beat[b] <= data_remaining <= 4;
                end
            end
        end
    end
endmodule
