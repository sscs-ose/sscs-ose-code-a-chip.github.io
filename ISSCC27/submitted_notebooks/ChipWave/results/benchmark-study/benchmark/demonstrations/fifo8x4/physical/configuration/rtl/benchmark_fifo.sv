module benchmark_fifo (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       wr_en,
    input  wire       rd_en,
    input  wire [7:0] wr_data,
    output wire [7:0] rd_data,
    output wire       full,
    output wire       empty
);
    reg [7:0] memory [0:3];
    reg [1:0] read_ptr;
    reg [1:0] write_ptr;
    reg [2:0] occupancy;

    wire push = wr_en && !full;
    wire pop  = rd_en && !empty;

    assign full = (occupancy == 3'd4);
    assign empty = (occupancy == 3'd0);
    assign rd_data = empty ? 8'd0 : memory[read_ptr];

    // Acceptance uses occupancy before the edge, including at both boundaries.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            read_ptr <= 2'd0;
            write_ptr <= 2'd0;
            occupancy <= 3'd0;
        end else begin
            if (push) begin
                memory[write_ptr] <= wr_data;
                write_ptr <= write_ptr + 2'd1;
            end
            if (pop)
                read_ptr <= read_ptr + 2'd1;
            case ({push, pop})
                2'b10: occupancy <= occupancy + 3'd1;
                2'b01: occupancy <= occupancy - 3'd1;
                default: occupancy <= occupancy;
            endcase
        end
    end
endmodule
