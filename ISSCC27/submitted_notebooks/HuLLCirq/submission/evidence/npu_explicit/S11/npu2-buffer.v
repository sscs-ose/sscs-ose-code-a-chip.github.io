module hullcirq_npu2_buffer (
    input wire clk,
    input wire rst,
    input wire [12:0] load_data,
    input wire load_data_valid,
    output wire load_data_ready,
    input wire [2:0] read_index,
    input wire read_index_valid,
    output wire read_index_ready,
    output wire [31:0] operands,
    output wire operands_valid,
    input wire operands_ready
);

reg [7:0] bank_A [0:15];
reg [7:0] bank_B [0:15];
reg [31:0] response;
reg pending;

assign load_data_ready = !rst && !pending;
assign read_index_ready = !rst && !pending && !load_data_valid;
assign operands_valid = pending && !rst;
assign operands = pending ? response : 32'b0;

always @(posedge clk) begin
    if (rst) begin
        pending <= 0;
        response <= 32'b0;
    end else begin
        if (load_data_valid && load_data_ready) begin
            if (load_data[12]) begin
                bank_B[load_data[11:8]] <= load_data[7:0];
            end else begin
                bank_A[load_data[11:8]] <= load_data[7:0];
            end
            pending <= 0;
        end else if (read_index_valid && read_index_ready) begin
            response <= {bank_B[read_index * 2 + 1], bank_B[read_index * 2], bank_A[read_index + 8], bank_A[read_index]};
            pending <= 1;
        end
        if (pending && operands_ready) begin
            pending <= 0;
        end
    end
end

endmodule
