module hullcirq_npu2_scheduler (
    input wire clk,
    input wire rst,
    input wire [3:0] schedule_config,
    input wire schedule_config_valid,
    output wire schedule_config_ready,
    output wire [2:0] read_index,
    output wire read_index_valid,
    input wire read_index_ready,
    input wire [31:0] operands,
    input wire operands_valid,
    output wire operands_ready,
    output wire [33:0] batch_data,
    output wire batch_data_valid,
    input wire batch_data_ready
);

reg [1:0] phase;
reg [3:0] saved_K;
reg [2:0] current_k;
reg [31:0] captured_operands;

assign schedule_config_ready = !rst && phase == 2'b00 && schedule_config >= 4'd1 && schedule_config <= 4'd8;
assign read_index = current_k;
assign read_index_valid = !rst && phase == 2'b01;
assign operands_ready = !rst && phase == 2'b10;
assign batch_data_valid = !rst && phase == 2'b11;

always @(posedge clk) begin
    if (rst) begin
        phase <= 2'b00;
        saved_K <= 4'b0000;
        current_k <= 3'b000;
        captured_operands <= 32'b0;
    end else begin
        case (phase)
            2'b00: begin
                if (schedule_config_valid && schedule_config_ready && schedule_config >= 4'b0001 && schedule_config <= 4'b1000) begin
                    saved_K <= schedule_config;
                    current_k <= 3'b000;
                    phase <= 2'b01;
                end
            end
            2'b01: begin
                if (read_index_ready) begin
                    phase <= 2'b10;
                end
            end
            2'b10: begin
                if (operands_valid && operands_ready) begin
                    captured_operands <= operands;
                    phase <= 2'b11;
                end
            end
            2'b11: begin
                if (batch_data_ready) begin
                    if (current_k == saved_K - 1'b1) begin
                        phase <= 2'b00;
                    end else begin
                        current_k <= current_k + 1'b1;
                        phase <= 2'b01;
                    end
                end
            end
        endcase
    end
end

assign batch_data = {(current_k == saved_K - 1'b1), (current_k == 3'b000), captured_operands};

endmodule
