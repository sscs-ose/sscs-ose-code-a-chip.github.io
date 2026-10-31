module counter (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       en,
    input  logic       load,
    input  logic [7:0] load_value,
    output logic [7:0] count,
    output logic       overflow
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count    <= 8'd0;
            overflow <= 1'b0;
        end else if (load) begin
            count    <= load_value;
            overflow <= 1'b0;
        end else if (en) begin
            count    <= count + 8'd1;
            overflow <= (count == 8'hff);
        end else begin
            overflow <= 1'b0;
        end
    end
endmodule
