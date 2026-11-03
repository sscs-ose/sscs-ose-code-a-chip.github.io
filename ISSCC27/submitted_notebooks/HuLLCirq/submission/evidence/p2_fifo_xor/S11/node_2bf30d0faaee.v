module release_fifo2 (
    input wire clk_pipe, input wire rst_pipe_n,
    input wire [7:0] data_i, input wire data_i_valid, output wire data_i_ready,
    output wire [7:0] data_o, output wire data_o_valid, input wire data_o_ready
);
reg [7:0] head;
reg [7:0] tail;
reg [1:0] count;
wire push = data_i_valid && (count < 2);
wire pop = data_o_ready && (count > 0);
assign data_i_ready = (count < 2);
assign data_o_valid = (count > 0);
assign data_o = (count > 0) ? head : 8'd0;
always @(posedge clk_pipe) begin
    if (!rst_pipe_n) begin
        head <= 8'd0;
        tail <= 8'd0;
        count <= 2'd0;
    end else begin
        case ({push, pop})
            2'b10: begin
                if (count == 0) head <= data_i;
                else tail <= data_i;
                count <= count + 2'd1;
            end
            2'b01: begin
                if (count == 2) head <= tail;
                count <= count - 2'd1;
            end
            2'b11: begin
                head <= data_i;
            end
            default: begin end
        endcase
    end
end
endmodule
