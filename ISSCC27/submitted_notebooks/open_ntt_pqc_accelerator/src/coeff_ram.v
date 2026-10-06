// ---------------------------------------------------------------------------
// coeff_ram : dual-port coefficient memory
//
// Two independent read/write ports so one butterfly reads two operands and
// writes two results. Synchronous read with 1-clock latency (read-before-write
// on a port: a simultaneous write returns the OLD contents on the read data).
// Yosys infers block RAM / register file on Sky130.
// ---------------------------------------------------------------------------
module coeff_ram #(
    parameter integer WIDTH = 24,
    parameter integer DEPTH = 256,
    parameter integer AW    = 8
) (
    input  wire            clk,
    // Port A
    input  wire            a_we,
    input  wire [AW-1:0]   a_addr,
    input  wire [WIDTH-1:0] a_wdata,
    output reg  [WIDTH-1:0] a_rdata,
    // Port B
    input  wire            b_we,
    input  wire [AW-1:0]   b_addr,
    input  wire [WIDTH-1:0] b_wdata,
    output reg  [WIDTH-1:0] b_rdata
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    always @(posedge clk) begin
        if (a_we) mem[a_addr] <= a_wdata;
        a_rdata <= mem[a_addr];
        if (b_we) mem[b_addr] <= b_wdata;
        b_rdata <= mem[b_addr];
    end
endmodule
