// Technology-neutral behavioral models for A2 contract verification.
// These are not foundry SRAM macros and are not used by the FPGA project.

// One synchronous read/write port. A write occupies the port for the complete
// cycle; its read output is unspecified and must not be consumed.
module te_sram_1rw_model #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] addr,
    input  wire [WIDTH-1:0]      wdata,
    output reg  [WIDTH-1:0]      rdata
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    always @(posedge clk) begin
        if (we)
            mem[addr] <= wdata;
        else
            rdata <= mem[addr];
    end
endmodule

// One write port and one registered read port. The memory array intentionally
// has no reset; a system-level zeroize operation must scrub/invalidate it.
// Same-address read/write is illegal at the contract boundary and is checked
// by the dedicated A2 testbench rather than assigned a portable macro value.
module te_sram_1r1w_model #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] waddr,
    input  wire [WIDTH-1:0]      wdata,
    input  wire [ADDR_WIDTH-1:0] raddr,
    output reg  [WIDTH-1:0]      rdata
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    always @(posedge clk) begin
        if (we)
            mem[waddr] <= wdata;
        rdata <= mem[raddr];
    end
endmodule

// One write port and two independent registered read ports. Both reads may
// address the same word in the same cycle. A read/write collision on either
// read address is illegal at the contract boundary and is checked by the TB.
module te_sram_1w2r_model #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] waddr,
    input  wire [WIDTH-1:0]      wdata,
    input  wire [ADDR_WIDTH-1:0] raddr_a,
    output reg  [WIDTH-1:0]      rdata_a,
    input  wire [ADDR_WIDTH-1:0] raddr_b,
    output reg  [WIDTH-1:0]      rdata_b
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    always @(posedge clk) begin
        if (we)
            mem[waddr] <= wdata;
        rdata_a <= mem[raddr_a];
        rdata_b <= mem[raddr_b];
    end
endmodule

// Single read/write port with byte write-enable. Read-during-write at the
// same address is intentionally unspecified; the TB only samples reads from
// a different address during a write cycle.
module te_sram_1rw_be_model #(
    parameter integer WIDTH = 64,
    parameter integer DEPTH = 2048,
    parameter integer ADDR_WIDTH = 11,
    parameter integer BYTE_COUNT = WIDTH / 8
) (
    input  wire                    clk,
    input  wire                    we,
    input  wire [BYTE_COUNT-1:0]   be,
    input  wire [ADDR_WIDTH-1:0]   addr,
    input  wire [WIDTH-1:0]        wdata,
    output reg  [WIDTH-1:0]        rdata
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    integer b;

    always @(posedge clk) begin
        if (we) begin
            for (b = 0; b < BYTE_COUNT; b = b + 1)
                if (be[b])
                    mem[addr][(8*b) +: 8] <= wdata[(8*b) +: 8];
        end
        rdata <= mem[addr];
    end
endmodule

// Two symmetric read/write ports. A port with *_we asserted performs a write;
// its read output for that cycle is unspecified and must not be consumed.
// Same-address read/read is legal. If either port writes, both port addresses
// must differ so read/write and write/write collision behavior is never used.
module te_sram_2rw_model #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  a_we,
    input  wire [ADDR_WIDTH-1:0] a_addr,
    input  wire [WIDTH-1:0]      a_wdata,
    output reg  [WIDTH-1:0]      a_rdata,
    input  wire                  b_we,
    input  wire [ADDR_WIDTH-1:0] b_addr,
    input  wire [WIDTH-1:0]      b_wdata,
    output reg  [WIDTH-1:0]      b_rdata
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    // Separate processes match the true-dual-port inference style used by
    // the shared NTT coefficient RAM.
    always @(posedge clk) begin
        if (a_we)
            mem[a_addr] <= a_wdata;
        a_rdata <= mem[a_addr];
    end

    always @(posedge clk) begin
        if (b_we)
            mem[b_addr] <= b_wdata;
        b_rdata <= mem[b_addr];
    end
endmodule

// Exact contract binding used only by the ASIC-SRAM architectural regression.
// A1 synthesis instead reads the black-box contract from backend_contracts.sv.
`ifdef TRUSTEDGE_ASIC_SRAM
module te_sram_1rw #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] addr,
    input  wire [WIDTH-1:0]      wdata,
    output wire [WIDTH-1:0]      rdata
);
    te_sram_1rw_model #(
        .WIDTH(WIDTH), .DEPTH(DEPTH), .ADDR_WIDTH(ADDR_WIDTH)
    ) u_model (
        .clk(clk), .we(we), .addr(addr), .wdata(wdata), .rdata(rdata)
    );
endmodule

module te_sram_1r1w #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  we,
    input  wire [ADDR_WIDTH-1:0] waddr,
    input  wire [WIDTH-1:0]      wdata,
    input  wire [ADDR_WIDTH-1:0] raddr,
    output wire [WIDTH-1:0]      rdata
);
    te_sram_1r1w_model #(
        .WIDTH(WIDTH), .DEPTH(DEPTH), .ADDR_WIDTH(ADDR_WIDTH)
    ) u_model (
        .clk(clk), .we(we), .waddr(waddr), .wdata(wdata),
        .raddr(raddr), .rdata(rdata)
    );

    always @(posedge clk) begin
        if (we && (waddr == raddr))
            $fatal(1, "te_sram_1r1w contract collision at address %0d", waddr);
    end
endmodule

module te_sram_2rw #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  a_we,
    input  wire [ADDR_WIDTH-1:0] a_addr,
    input  wire [WIDTH-1:0]      a_wdata,
    output wire [WIDTH-1:0]      a_rdata,
    input  wire                  b_we,
    input  wire [ADDR_WIDTH-1:0] b_addr,
    input  wire [WIDTH-1:0]      b_wdata,
    output wire [WIDTH-1:0]      b_rdata
);
    te_sram_2rw_model #(
        .WIDTH(WIDTH), .DEPTH(DEPTH), .ADDR_WIDTH(ADDR_WIDTH)
    ) u_model (
        .clk(clk),
        .a_we(a_we), .a_addr(a_addr), .a_wdata(a_wdata), .a_rdata(a_rdata),
        .b_we(b_we), .b_addr(b_addr), .b_wdata(b_wdata), .b_rdata(b_rdata)
    );

    always @(posedge clk) begin
        if ((a_we || b_we) && (a_addr == b_addr))
            $fatal(1, "te_sram_2rw contract collision at address %0d", a_addr);
    end
endmodule
`endif
