`include "kyber_params.vh"

// Pointwise multiply trong mien NTT (256 he so, tuan tu)
module kyber_poly_mul (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    output reg         busy,
    output reg         done,
    input  wire [7:0]  addr_a,
    input  wire [15:0] data_a,
    input  wire        we_a,
    input  wire [7:0]  addr_b,
    input  wire [15:0] data_b,
    input  wire        we_b,
    output wire [15:0] data_out,
    input  wire [7:0]  addr_out
);
    reg [15:0] a [0:255];
    reg [15:0] b [0:255];
    reg [15:0] o [0:255];
    reg [8:0]  idx;
    reg [2:0]  st;

    localparam S_IDLE=0, S_MUL=1, S_DONE=2;

    wire [15:0] prod;
    kyber_fqmul u_mul (.a(a[idx[7:0]]), .b(b[idx[7:0]]), .out(prod));

    assign data_out = o[addr_out];

    always @(posedge clk) begin
        if (we_a) a[addr_a] <= data_a;
        if (we_b) b[addr_b] <= data_b;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; busy <= 0; done <= 0; idx <= 0;
        end else begin
            done <= 0;
            case (st)
                S_IDLE: begin
                    busy <= 0;
                    if (start) begin
                        busy <= 1; idx <= 0; st <= S_MUL;
                    end
                end
                S_MUL: begin
                    o[idx[7:0]] <= prod;
                    if (idx == 9'd255) begin
                        st <= S_DONE;
                    end else
                        idx <= idx + 9'd1;
                end
                S_DONE: begin
                    busy <= 0; done <= 1; st <= S_IDLE;
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
