module hullcirq_npu2_dispatcher (
    input wire clk,
    input wire rst,
    input wire [33:0] batch_data,
    input wire batch_data_valid,
    output wire batch_data_ready,
    output wire [17:0] pair00,
    output wire pair00_valid,
    input wire pair00_ready,
    output wire [17:0] pair01,
    output wire pair01_valid,
    input wire pair01_ready,
    output wire [17:0] pair10,
    output wire pair10_valid,
    input wire pair10_ready,
    output wire [17:0] pair11,
    output wire pair11_valid,
    input wire pair11_ready
);

reg [33:0] captured_batch;
reg pending;
reg [3:0] delivered;
wire [3:0] transfer_mask;

assign batch_data_ready = !rst && !pending;
assign pair00_valid = !rst && pending && !delivered[0];
assign pair01_valid = !rst && pending && !delivered[1];
assign pair10_valid = !rst && pending && !delivered[2];
assign pair11_valid = !rst && pending && !delivered[3];

assign transfer_mask = {pair11_valid && pair11_ready, pair10_valid && pair10_ready, pair01_valid && pair01_ready, pair00_valid && pair00_ready};

always @(posedge clk) begin
    if (rst) begin
        captured_batch <= 34'b0;
        pending <= 0;
        delivered <= 4'b0000;
    end else begin
        if (batch_data_valid && batch_data_ready) begin
            captured_batch <= batch_data;
            pending <= 1;
            delivered <= 4'b0000;
        end else if (pending) begin
            delivered <= delivered | transfer_mask;
            if ((delivered | transfer_mask) == 4'b1111) begin
                pending <= 1'b0;
            end
        end
    end
end

assign pair00 = {captured_batch[33], captured_batch[32], captured_batch[23:16], captured_batch[7:0]};
assign pair01 = {captured_batch[33], captured_batch[32], captured_batch[31:24], captured_batch[7:0]};
assign pair10 = {captured_batch[33], captured_batch[32], captured_batch[23:16], captured_batch[15:8]};
assign pair11 = {captured_batch[33], captured_batch[32], captured_batch[31:24], captured_batch[15:8]};

endmodule
