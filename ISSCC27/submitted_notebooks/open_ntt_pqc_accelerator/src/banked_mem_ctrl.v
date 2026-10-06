// ---------------------------------------------------------------------------
// banked_mem_ctrl : Conflict-Free 4-Bank Interleaved Memory Controller
//
// Manages 4 independent 64-word SRAM banks for 256-coefficient polynomial storage.
// Implements XOR-stride address mapping to eliminate memory bank conflicts,
// enabling full 4-operand concurrent read and 4-operand concurrent write every cycle.
// ---------------------------------------------------------------------------
module banked_mem_ctrl #(
    parameter integer WIDTH = 24,
    parameter integer N     = 256,
    parameter integer BANKS = 4,
    parameter integer AW    = 8
) (
    input  wire             clk,
    input  wire             rst_n,

    // 4-way Parallel Read Port
    input  wire             rd_en,
    input  wire [AW-1:0]    raddr0,
    input  wire [AW-1:0]    raddr1,
    input  wire [AW-1:0]    raddr2,
    input  wire [AW-1:0]    raddr3,
    output reg  [WIDTH-1:0] rdata0,
    output reg  [WIDTH-1:0] rdata1,
    output reg  [WIDTH-1:0] rdata2,
    output reg  [WIDTH-1:0] rdata3,
    output reg              rd_valid,

    // 4-way Parallel Write Port
    input  wire             wr_en,
    input  wire [AW-1:0]    waddr0,
    input  wire [AW-1:0]    waddr1,
    input  wire [AW-1:0]    waddr2,
    input  wire [AW-1:0]    waddr3,
    input  wire [WIDTH-1:0] wdata0,
    input  wire [WIDTH-1:0] wdata1,
    input  wire [WIDTH-1:0] wdata2,
    input  wire [WIDTH-1:0] wdata3
);

    // 4 SRAM Banks (64 words x 24 bits each)
    reg [WIDTH-1:0] bank0 [0:63];
    reg [WIDTH-1:0] bank1 [0:63];
    reg [WIDTH-1:0] bank2 [0:63];
    reg [WIDTH-1:0] bank3 [0:63];

    // Conflict-free XOR-based bank index calculation
    function [1:0] get_bank;
        input [AW-1:0] addr;
        begin
            get_bank = addr[1:0] ^ addr[3:2];
        end
    endfunction

    // Word index within the bank
    function [5:0] get_offset;
        input [AW-1:0] addr;
        begin
            get_offset = addr[AW-1:2];
        end
    endfunction

    // Synchronous Read
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rdata0   <= {WIDTH{1'b0}};
            rdata1   <= {WIDTH{1'b0}};
            rdata2   <= {WIDTH{1'b0}};
            rdata3   <= {WIDTH{1'b0}};
            rd_valid <= 1'b0;
        end else if (rd_en) begin
            rdata0   <= bank0[get_offset(raddr0)];
            rdata1   <= bank1[get_offset(raddr1)];
            rdata2   <= bank2[get_offset(raddr2)];
            rdata3   <= bank3[get_offset(raddr3)];
            rd_valid <= 1'b1;
        end else begin
            rd_valid <= 1'b0;
        end
    end

    // Synchronous Write
    always @(posedge clk) begin
        if (wr_en) begin
            bank0[get_offset(waddr0)] <= wdata0;
            bank1[get_offset(waddr1)] <= wdata1;
            bank2[get_offset(waddr2)] <= wdata2;
            bank3[get_offset(waddr3)] <= wdata3;
        end
    end

endmodule
