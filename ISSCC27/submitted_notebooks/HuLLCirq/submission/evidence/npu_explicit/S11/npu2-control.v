module hullcirq_npu2_control (
    input wire clk,
    input wire rst,
    input wire [68:0] config_data,
    input wire config_data_valid,
    output wire config_data_ready,
    output wire [3:0] schedule_config,
    output wire schedule_config_valid,
    input wire schedule_config_ready,
    output wire [64:0] post_config,
    output wire post_config_valid,
    input wire post_config_ready,
    input wire output_transfer,
    output wire busy,
    output wire job_done
);

localparam IDLE = 2'b00, SEND = 2'b01, RUN = 2'b10, DONE = 2'b11;
reg [1:0] state;
reg [68:0] saved_config;
reg schedule_sent;
reg post_sent;
reg [2:0] output_count;

assign config_data_ready = ~rst & (state == IDLE) & (config_data[3:0] >= 4'd1) & (config_data[3:0] <= 4'd8);
assign schedule_config = saved_config[3:0];
assign schedule_config_valid = ~rst & (state == SEND) & ~schedule_sent;
assign post_config = saved_config[68:4];
assign post_config_valid = ~rst & (state == SEND) & ~post_sent;
assign busy = ~rst & (state != IDLE);
assign job_done = ~rst & (state == DONE);

always @(posedge clk) begin
    if (rst) begin
        state <= IDLE;
        saved_config <= 69'b0;
        schedule_sent <= 1'b0;
        post_sent <= 1'b0;
        output_count <= 3'b0;
    end else begin
        case (state)
            IDLE: begin
                if (config_data_valid && config_data_ready) begin
                    saved_config <= config_data;
                    schedule_sent <= 1'b0;
                    post_sent <= 1'b0;
                    output_count <= 3'b0;
                    state <= SEND;
                end
            end
            SEND: begin
                if (schedule_config_valid && schedule_config_ready)
                    schedule_sent <= 1'b1;
                if (post_config_valid && post_config_ready)
                    post_sent <= 1'b1;
                if ((schedule_sent || (schedule_config_valid && schedule_config_ready)) &&
                    (post_sent || (post_config_valid && post_config_ready)))
                    state <= RUN;
            end
            RUN: begin
                if (output_transfer) begin
                    output_count <= output_count + 1'b1;
                    if (output_count == 3'd3) begin
                        state <= DONE;
                    end
                end
            end
            DONE: begin
                state <= IDLE;
            end
        endcase
    end
end

endmodule
